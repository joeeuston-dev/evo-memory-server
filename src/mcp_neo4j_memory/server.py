import json
import logging
from typing import Literal

from neo4j import AsyncGraphDatabase
from pydantic import Field

from fastmcp.server import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.tool import ToolResult, TextContent
from neo4j.exceptions import Neo4jError
from mcp.types import ToolAnnotations

from .neo4j_memory import Neo4jMemory, Entity, Relation, ObservationAddition, ObservationDeletion, KnowledgeGraph

# Set up logging
logger = logging.getLogger('mcp_neo4j_memory')
logger.setLevel(logging.INFO)


def create_mcp_server(memory: Neo4jMemory) -> FastMCP:
    """Create an MCP server instance for memory management."""
    
    mcp: FastMCP = FastMCP("mcp-neo4j-memory", dependencies=["neo4j", "pydantic"], stateless_http=True)

    @mcp.tool(annotations=ToolAnnotations(title="Read Graph", 
                                          readOnlyHint=True, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def read_graph() -> KnowledgeGraph:
        """**FULL CONTEXT TOOL**: Use ONLY when you need complete system state overview or when search_memories fails to find relevant context. This is computationally expensive and should be avoided for targeted queries. WHEN TO USE: System architecture review, complete knowledge audit, debugging knowledge graph issues. AVOID: Use search_memories instead for specific topic discovery."""
        logger.info("MCP tool: read_graph")
        try:
            result = await memory.read_graph()
            return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                          structured_content=result)
        except Neo4jError as e:
            logger.error(f"Neo4j error reading full knowledge graph: {e}")
            raise ToolError(f"Neo4j error reading full knowledge graph: {e}")
        except Exception as e:
            logger.error(f"Error reading full knowledge graph: {e}")
            raise ToolError(f"Error reading full knowledge graph: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Create Entities", 
                                          readOnlyHint=False, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def create_entities(entities: list[Entity] = Field(..., description="List of entities to create")) -> list[Entity]:
        """**KNOWLEDGE CREATION TOOL**: Create new entities with evo metadata (access_count, confidence, created timestamp). Always include evo metadata and meaningful observations. WHEN TO USE: Learning new concepts, storing insights, capturing project knowledge. Include relationships to existing entities for knowledge integration."""
        logger.info(f"MCP tool: create_entities ({len(entities)} entities)")
        try:
            entity_objects = [Entity.model_validate(entity) for entity in entities]
            result = await memory.create_entities(entity_objects)
            return ToolResult(content=[TextContent(type="text", text=json.dumps([e.model_dump() for e in result]))],
                          structured_content={"result": result})
        except Neo4jError as e:
            logger.error(f"Neo4j error creating entities: {e}")
            raise ToolError(f"Neo4j error creating entities: {e}")
        except Exception as e:
            logger.error(f"Error creating entities: {e}")
            raise ToolError(f"Error creating entities: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Create Relations", 
                                          readOnlyHint=False, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def create_relations(relations: list[Relation] = Field(..., description="List of relations to create")) -> list[Relation]:
        """**EVO STRENGTHENING TOOL**: Create relationships between entities to enable knowledge discovery through traversal. Essential for evo-memory patterns. WHEN TO USE: After creating entities, when discovering connections, building knowledge networks. Relationship types: part_of, implements, validates, coordinates_with, etc."""
        logger.info(f"MCP tool: create_relations ({len(relations)} relations)")
        try:
            relation_objects = [Relation.model_validate(relation) for relation in relations]
            result = await memory.create_relations(relation_objects)
            return ToolResult(content=[TextContent(type="text", text=json.dumps([r.model_dump() for r in result]))],
                          structured_content={"result": result})
        except Neo4jError as e:
            logger.error(f"Neo4j error creating relations: {e}")
            raise ToolError(f"Neo4j error creating relations: {e}")
        except Exception as e:
            logger.error(f"Error creating relations: {e}")
            raise ToolError(f"Error creating relations: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Add Observations", 
                                          readOnlyHint=False, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def add_observations(observations: list[ObservationAddition] = Field(..., description="List of observations to add")) -> list[dict[str, str | list[str]]]:
        """**EVO CONSOLIDATION TOOL**: Add new insights to existing entities, simulating evo strengthening. Update evo metadata (increment access_count, update last_accessed). WHEN TO USE: Learning new details about existing concepts, consolidating session insights, updating project status."""
        logger.info(f"MCP tool: add_observations ({len(observations)} additions)")
        try:
            observation_objects = [ObservationAddition.model_validate(obs) for obs in observations]
            result = await memory.add_observations(observation_objects)
            return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                          structured_content={"result": result})
        except Neo4jError as e:
            logger.error(f"Neo4j error adding observations: {e}")
            raise ToolError(f"Neo4j error adding observations: {e}")
        except Exception as e:
            logger.error(f"Error adding observations: {e}")
            raise ToolError(f"Error adding observations: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Delete Entities", 
                                          readOnlyHint=False, 
                                          destructiveHint=True, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def delete_entities(entityNames: list[str] = Field(..., description="List of entity names to delete")) -> str:
        """Delete multiple entities and their associated relations."""
        logger.info(f"MCP tool: delete_entities ({len(entityNames)} entities)")
        try:
            await memory.delete_entities(entityNames)
            return ToolResult(content=[TextContent(type="text", text="Entities deleted successfully")],
                              structured_content={"result": "Entities deleted successfully"})
        except Neo4jError as e:
            logger.error(f"Neo4j error deleting entities: {e}")
            raise ToolError(f"Neo4j error deleting entities: {e}")
        except Exception as e:
            logger.error(f"Error deleting entities: {e}")
            raise ToolError(f"Error deleting entities: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Delete Observations", 
                                          readOnlyHint=False, 
                                          destructiveHint=True, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def delete_observations(deletions: list[ObservationDeletion] = Field(..., description="List of observations to delete")) -> str:
        """Delete specific observations from entities."""
        logger.info(f"MCP tool: delete_observations ({len(deletions)} deletions)")
        try:    
            deletion_objects = [ObservationDeletion.model_validate(deletion) for deletion in deletions]
            await memory.delete_observations(deletion_objects)
            return ToolResult(content=[TextContent(type="text", text="Observations deleted successfully")],
                          structured_content={"result": "Observations deleted successfully"})
        except Neo4jError as e:
            logger.error(f"Neo4j error deleting observations: {e}")
            raise ToolError(f"Neo4j error deleting observations: {e}")
        except Exception as e:
            logger.error(f"Error deleting observations: {e}")
            raise ToolError(f"Error deleting observations: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Delete Relations", 
                                          readOnlyHint=False, 
                                          destructiveHint=True, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def delete_relations(relations: list[Relation] = Field(..., description="List of relations to delete")) -> str:
        """Delete multiple relations from the graph."""
        logger.info(f"MCP tool: delete_relations ({len(relations)} relations)")
        try:
            relation_objects = [Relation.model_validate(relation) for relation in relations]
            await memory.delete_relations(relation_objects)
            return ToolResult(content=[TextContent(type="text", text="Relations deleted successfully")],
                          structured_content={"result": "Relations deleted successfully"})
        except Neo4jError as e:
            logger.error(f"Neo4j error deleting relations: {e}")
            raise ToolError(f"Neo4j error deleting relations: {e}")
        except Exception as e:
            logger.error(f"Error deleting relations: {e}")
            raise ToolError(f"Error deleting relations: {e}")

    @mcp.tool(annotations=ToolAnnotations(title="Search Memories", 
                                          readOnlyHint=True, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def search_memories(query: str = Field(..., description="Search query for nodes")) -> KnowledgeGraph:
        """**PRIMARY DISCOVERY TOOL**: Use this FIRST when user asks about past work, concepts, or relationships. Performs evo-memory discovery through relationship traversal and semantic search rather than full graph reads. Triggers evo strengthening on accessed knowledge. WHEN TO USE: 'What did we work on yesterday?', 'Tell me about X', 'How does Y relate to Z?', 'What do I know about...?'"""
        logger.info(f"MCP tool: search_memories ('{query}')")
        try:
            result = await memory.search_memories(query)
            return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                              structured_content=result)
        except Neo4jError as e:
            logger.error(f"Neo4j error searching memories: {e}")
            raise ToolError(f"Neo4j error searching memories: {e}")
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            raise ToolError(f"Error searching memories: {e}")
        
    @mcp.tool(annotations=ToolAnnotations(title="Find Memories by Name", 
                                          readOnlyHint=True, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def find_memories_by_name(names: list[str] = Field(..., description="List of node names to find")) -> KnowledgeGraph:
        """**DIRECT ACCESS TOOL**: Find specific entities by exact name when you know what you're looking for. More efficient than search_memories for known entity names. WHEN TO USE: Accessing specific projects, methodologies, or entities by name. Triggers evo strengthening on accessed entities."""
        logger.info(f"MCP tool: find_memories_by_name ({len(names)} names)")
        try:
            result = await memory.find_memories_by_name(names)
            return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                              structured_content=result)
        except Neo4jError as e:
            logger.error(f"Neo4j error finding memories by name: {e}")
            raise ToolError(f"Neo4j error finding memories by name: {e}")
        except Exception as e:
            logger.error(f"Error finding memories by name: {e}")
            raise ToolError(f"Error finding memories by name: {e}")

    return mcp


async def main(
    neo4j_uri: str, 
    neo4j_user: str, 
    neo4j_password: str, 
    neo4j_database: str,
    transport: Literal["stdio", "sse", "http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp/",
) -> None:
    logger.info(f"Starting Neo4j MCP Memory Server")
    logger.info(f"Connecting to Neo4j with DB URL: {neo4j_uri}")

    # Connect to Neo4j
    neo4j_driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password), 
        database=neo4j_database
    )
    
    # Verify connection
    try:
        await neo4j_driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {neo4j_uri}")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        exit(1)

    # Initialize memory
    memory = Neo4jMemory(neo4j_driver)
    logger.info("Neo4jMemory initialized")
    
    # Create fulltext index
    await memory.create_fulltext_index()
    
    # Create MCP server
    mcp = create_mcp_server(memory)
    logger.info("MCP server created")

    # Run the server with the specified transport
    logger.info(f"Starting server with transport: {transport}")
    match transport:
        case "http":
            logger.info(f"HTTP server starting on {host}:{port}{path}")
            await mcp.run_http_async(host=host, port=port, path=path)
        case "stdio":
            logger.info("STDIO server starting")
            await mcp.run_stdio_async()
        case "sse":
            logger.info(f"SSE server starting on {host}:{port}{path}")
            await mcp.run_sse_async(host=host, port=port, path=path)
        case _:
            raise ValueError(f"Unsupported transport: {transport}")
