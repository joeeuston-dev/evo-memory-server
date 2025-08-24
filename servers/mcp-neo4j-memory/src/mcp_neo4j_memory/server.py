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
from .dynamic_descriptions import DynamicToolDescriptionManager

# Set up logging
logger = logging.getLogger('mcp_neo4j_memory')
logger.setLevel(logging.INFO)


def create_mcp_server(memory: Neo4jMemory, description_manager: DynamicToolDescriptionManager = None) -> FastMCP:
    """Create an MCP server instance for memory management."""
    
    mcp: FastMCP = FastMCP("mcp-neo4j-memory", dependencies=["neo4j", "pydantic"], stateless_http=True)

    @mcp.tool(annotations=ToolAnnotations(title="Read Graph", 
                                          readOnlyHint=True, 
                                          destructiveHint=False, 
                                          idempotentHint=True, 
                                          openWorldHint=True))
    async def read_graph() -> KnowledgeGraph:
        """Read the entire knowledge graph."""
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
        """Create multiple new entities in the knowledge graph."""
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
        """Create multiple new relations between entities."""
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
        """Add new observations to existing entities."""
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
        """Search for memories based on a query containing search terms."""
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
        """Find specific memories by name."""
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
    
    # Add health check tool for dynamic descriptions (if available)
    if description_manager:
        @mcp.tool(annotations=ToolAnnotations(title="Dynamic Descriptions Health Check", 
                                              readOnlyHint=True, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def dynamic_descriptions_health() -> dict:
            """Check the health status of the dynamic descriptions system."""
            logger.info("MCP tool: dynamic_descriptions_health")
            try:
                health_status = await description_manager.health_check()
                return ToolResult(content=[TextContent(type="text", text=json.dumps(health_status, indent=2))],
                                  structured_content=health_status)
            except Exception as e:
                logger.error(f"Error checking dynamic descriptions health: {e}")
                raise ToolError(f"Error checking dynamic descriptions health: {e}")

        # Phase 2: Evo-Memory Integration Tools
        @mcp.tool(annotations=ToolAnnotations(title="Setup Dynamic Descriptions Schema", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def setup_dynamic_descriptions_schema() -> dict:
            """Create Neo4j schema (constraints and indexes) for ToolDescription entities."""
            logger.info("MCP tool: setup_dynamic_descriptions_schema")
            try:
                schema_result = await description_manager.setup_schema()
                return ToolResult(content=[TextContent(type="text", text=json.dumps(schema_result, indent=2))],
                                  structured_content=schema_result)
            except Exception as e:
                logger.error(f"Error setting up dynamic descriptions schema: {e}")
                raise ToolError(f"Error setting up dynamic descriptions schema: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Seed Initial Tool Descriptions", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=False, 
                                              openWorldHint=False))
        async def seed_initial_descriptions(overwrite: bool = False) -> dict:
            """Seed initial tool descriptions from hardcoded descriptions into Neo4j.
            
            Args:
                overwrite: Whether to overwrite existing descriptions (default: False)
            """
            logger.info(f"MCP tool: seed_initial_descriptions (overwrite={overwrite})")
            try:
                seed_result = await description_manager.seed_initial_descriptions(overwrite=overwrite)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(seed_result, indent=2))],
                                  structured_content=seed_result)
            except Exception as e:
                logger.error(f"Error seeding initial descriptions: {e}")
                raise ToolError(f"Error seeding initial descriptions: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Get Dynamic Descriptions Schema Info", 
                                              readOnlyHint=True, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def get_dynamic_descriptions_schema_info() -> dict:
            """Get information about the current Neo4j schema for ToolDescription entities."""
            logger.info("MCP tool: get_dynamic_descriptions_schema_info")
            try:
                schema_info = await description_manager.get_schema_info()
                return ToolResult(content=[TextContent(type="text", text=json.dumps(schema_info, indent=2))],
                                  structured_content=schema_info)
            except Exception as e:
                logger.error(f"Error getting dynamic descriptions schema info: {e}")
                raise ToolError(f"Error getting dynamic descriptions schema info: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="List Tool Descriptions", 
                                              readOnlyHint=True, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def list_tool_descriptions(environment: str = None, tool_name: str = None) -> dict:
            """List tool descriptions stored in Neo4j.
            
            Args:
                environment: Filter by environment (dev/staging/production). If None, uses current environment.
                tool_name: Filter by specific tool name. If None, returns all tools.
            """
            logger.info(f"MCP tool: list_tool_descriptions (environment={environment}, tool_name={tool_name})")
            try:
                descriptions = await description_manager.list_tool_descriptions(environment=environment, tool_name=tool_name)
                # Wrap list in dictionary for structured_content compliance
                structured_data = {"descriptions": descriptions, "count": len(descriptions)}
                return ToolResult(content=[TextContent(type="text", text=json.dumps(descriptions, indent=2))],
                                  structured_content=structured_data)
            except Exception as e:
                logger.error(f"Error listing tool descriptions: {e}")
                raise ToolError(f"Error listing tool descriptions: {e}")

        # Phase 3: Description Lifecycle Management Tools
        
        @mcp.tool(annotations=ToolAnnotations(title="Mark Dynamic Description Deprecated", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def mark_dynamic_description_deprecated(
            tool_name: str = Field(..., description="Name of the tool"),
            version: str = Field(..., description="Version to deprecate"),
            reason: str = Field(..., description="Reason for deprecation"),
            deprecated_by: str = Field(default="user", description="Who is deprecating this description"),
            environment: str = Field(default=None, description="Environment (defaults to manager environment)")
        ) -> dict:
            """Mark a tool description as deprecated with reason tracking."""
            logger.info(f"MCP tool: mark_dynamic_description_deprecated ({tool_name} v{version})")
            try:
                result = await description_manager.mark_tool_description_deprecated(
                    tool_name=tool_name,
                    version=version,
                    reason=reason,
                    deprecated_by=deprecated_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error marking description deprecated: {e}")
                raise ToolError(f"Error marking description deprecated: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Reactivate Dynamic Description", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def reactivate_dynamic_description(
            tool_name: str = Field(..., description="Name of the tool"),
            version: str = Field(..., description="Version to reactivate"),
            reactivated_by: str = Field(default="user", description="Who is reactivating this description"),
            environment: str = Field(default=None, description="Environment (defaults to manager environment)")
        ) -> dict:
            """Reactivate a deprecated tool description."""
            logger.info(f"MCP tool: reactivate_dynamic_description ({tool_name} v{version})")
            try:
                result = await description_manager.reactivate_tool_description(
                    tool_name=tool_name,
                    version=version,
                    reactivated_by=reactivated_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error reactivating description: {e}")
                raise ToolError(f"Error reactivating description: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Create Description Version", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=False, 
                                              openWorldHint=False))
        async def create_description_version(
            tool_name: str = Field(..., description="Name of the tool"),
            base_version: str = Field(..., description="Version to base the new version on"),
            new_version: str = Field(..., description="Version identifier for the new description"),
            new_description: str = Field(..., description="The new description text"),
            created_by: str = Field(default="user", description="Who is creating this version"),
            environment: str = Field(default=None, description="Environment (defaults to manager environment)")
        ) -> dict:
            """Create a new version of a tool description based on an existing one."""
            logger.info(f"MCP tool: create_description_version ({tool_name} v{base_version} -> v{new_version})")
            try:
                result = await description_manager.create_description_version(
                    tool_name=tool_name,
                    base_version=base_version,
                    new_version=new_version,
                    new_description=new_description,
                    created_by=created_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error creating description version: {e}")
                raise ToolError(f"Error creating description version: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Get Description Versions", 
                                              readOnlyHint=True, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def get_description_versions(
            tool_name: str = Field(..., description="Name of the tool"),
            environment: str = Field(default=None, description="Environment (defaults to manager environment)"),
            include_deprecated: bool = Field(default=True, description="Whether to include deprecated versions")
        ) -> dict:
            """Get all versions of a tool description with their status and metrics."""
            logger.info(f"MCP tool: get_description_versions ({tool_name})")
            try:
                result = await description_manager.get_description_versions(
                    tool_name=tool_name,
                    environment=environment,
                    include_deprecated=include_deprecated
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error getting description versions: {e}")
                raise ToolError(f"Error getting description versions: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Find Low Performing Descriptions", 
                                              readOnlyHint=True, 
                                              destructiveHint=False, 
                                              idempotentHint=True, 
                                              openWorldHint=False))
        async def find_low_performing_descriptions(
            effectiveness_threshold: float = Field(default=0.3, description="Minimum effectiveness score"),
            access_threshold: int = Field(default=5, description="Minimum access count to consider"),
            environment: str = Field(default=None, description="Environment (defaults to manager environment)")
        ) -> dict:
            """Find descriptions that are performing below thresholds and may need deprecation."""
            logger.info(f"MCP tool: find_low_performing_descriptions (threshold={effectiveness_threshold})")
            try:
                result = await description_manager.find_low_performing_descriptions(
                    effectiveness_threshold=effectiveness_threshold,
                    access_threshold=access_threshold,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error finding low performing descriptions: {e}")
                raise ToolError(f"Error finding low performing descriptions: {e}")

        @mcp.tool(annotations=ToolAnnotations(title="Promote Testing Description to Active", 
                                              readOnlyHint=False, 
                                              destructiveHint=False, 
                                              idempotentHint=False, 
                                              openWorldHint=False))
        async def promote_testing_to_active(
            tool_name: str = Field(..., description="Name of the tool"),
            version: str = Field(..., description="Version to promote"),
            promoted_by: str = Field(default="user", description="Who is promoting this description")
        ) -> dict:
            """Promote a testing tool description to active status."""
            logger.info(f"MCP tool: promote_testing_to_active for {tool_name} v{version}")
            try:
                result = await description_manager.promote_testing_to_active(
                    tool_name=tool_name,
                    version=version,
                    promoted_by=promoted_by
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                                  structured_content=result)
            except Exception as e:
                logger.error(f"Error promoting description: {e}")
                raise ToolError(f"Error promoting description: {e}")

    # TODO: Dynamic description integration will be implemented as a post-startup process
    # Currently disabled to prevent server startup hanging on Neo4j connection
    if description_manager and description_manager.enabled:
        logger.info("Dynamic descriptions enabled - integration will be implemented post-startup")
    else:
        logger.info("Dynamic descriptions disabled - using hardcoded descriptions")

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
    dynamic_descriptions_enabled: bool = False,
    description_environment: str = "production",
    effectiveness_threshold: float = 0.75,
    ab_test_probability: float = 0.1,
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
    
    # Initialize dynamic descriptions manager
    description_manager = DynamicToolDescriptionManager(
        driver=neo4j_driver,
        enabled=dynamic_descriptions_enabled,
        environment=description_environment
    )
    logger.info(f"DynamicToolDescriptionManager initialized (enabled={dynamic_descriptions_enabled})")
    
    # Create fulltext index
    await memory.create_fulltext_index()
    
    # Create MCP server
    mcp = create_mcp_server(memory, description_manager)
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
