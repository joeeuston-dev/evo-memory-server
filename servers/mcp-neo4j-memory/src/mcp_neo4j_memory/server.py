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


class DynamicToolProvider:
    """Provides tools with dynamic descriptions following FastMCP best practices."""
    
    def __init__(self, mcp: FastMCP, memory: Neo4jMemory, description_manager: DynamicToolDescriptionManager = None):
        self.mcp = mcp
        self.memory = memory
        self.description_manager = description_manager
    
    async def initialize(self):
        """Register all tools with enhanced descriptions from Neo4j."""
        logger.info("Initializing tools with dynamic descriptions")
        
        # Register core memory tools with dynamic descriptions
        await self._register_search_memories()
        await self._register_read_graph()
        await self._register_create_entities()
        await self._register_create_relations()
        await self._register_add_observations()
        await self._register_find_memories_by_name()
        await self._register_delete_entities()
        await self._register_delete_observations()
        await self._register_delete_relations()
        
        # Register dynamic description management tools if enabled
        if self.description_manager and self.description_manager.enabled:
            await self._register_dynamic_description_tools()
        
        logger.info("Dynamic tool registration complete")
    
    async def _get_dynamic_description(self, tool_name: str, fallback: str) -> str:
        """Get enhanced description from Neo4j or fallback to hardcoded."""
        if self.description_manager and self.description_manager.enabled:
            try:
                return await self.description_manager.get_tool_description(tool_name)
            except Exception as e:
                logger.warning(f"Failed to get dynamic description for {tool_name}: {e}")
        return fallback
    
    async def _register_search_memories(self):
        description = await self._get_dynamic_description(
            "search_memories",
            "Search for memories based on a query containing search terms."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Search Memories", 
                                      readOnlyHint=True, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def search_memories(query: str = Field(..., description="Search query for nodes")) -> KnowledgeGraph:
            """Search for memories based on a query containing search terms."""
            logger.info(f"MCP tool: search_memories (query: {query})")
            try:
                result = await self.memory.search_memories(query)
                return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error searching memories: {e}")
                raise ToolError(f"Neo4j error searching memories: {e}")
            except Exception as e:
                logger.error(f"Error searching memories: {e}")
                raise ToolError(f"Error searching memories: {e}")
    
    async def _register_read_graph(self):
        description = await self._get_dynamic_description(
            "read_graph",
            "Read the entire knowledge graph."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Read Graph", 
                                      readOnlyHint=True, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def read_graph() -> KnowledgeGraph:
            """Read the entire knowledge graph."""
            logger.info("MCP tool: read_graph")
            try:
                result = await self.memory.read_graph()
                return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error reading full knowledge graph: {e}")
                raise ToolError(f"Neo4j error reading full knowledge graph: {e}")
            except Exception as e:
                logger.error(f"Error reading full knowledge graph: {e}")
                raise ToolError(f"Error reading full knowledge graph: {e}")
    
    async def _register_create_entities(self):
        description = await self._get_dynamic_description(
            "create_entities",
            "Create multiple new entities in the knowledge graph."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Create Entities", 
                                      readOnlyHint=False, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def create_entities(entities: list[Entity] = Field(..., description="List of entities to create")) -> list[Entity]:
            """Create multiple new entities in the knowledge graph."""
            logger.info(f"MCP tool: create_entities ({len(entities)} entities)")
            try:
                entity_objects = [Entity.model_validate(entity) for entity in entities]
                result = await self.memory.create_entities(entity_objects)
                return ToolResult(content=[TextContent(type="text", text=json.dumps([e.model_dump() for e in result]))],
                              structured_content={"result": result})
            except Neo4jError as e:
                logger.error(f"Neo4j error creating entities: {e}")
                raise ToolError(f"Neo4j error creating entities: {e}")
            except Exception as e:
                logger.error(f"Error creating entities: {e}")
                raise ToolError(f"Error creating entities: {e}")

    async def _register_create_relations(self):
        description = await self._get_dynamic_description(
            "create_relations",
            "Create multiple new relations between entities."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Create Relations", 
                                      readOnlyHint=False, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def create_relations(relations: list[Relation] = Field(..., description="List of relations to create")) -> list[Relation]:
            """Create multiple new relations between entities."""
            logger.info(f"MCP tool: create_relations ({len(relations)} relations)")
            try:
                relation_objects = [Relation.model_validate(relation) for relation in relations]
                result = await self.memory.create_relations(relation_objects)
                return ToolResult(content=[TextContent(type="text", text=json.dumps([r.model_dump() for r in result]))],
                              structured_content={"result": result})
            except Neo4jError as e:
                logger.error(f"Neo4j error creating relations: {e}")
                raise ToolError(f"Neo4j error creating relations: {e}")
            except Exception as e:
                logger.error(f"Error creating relations: {e}")
                raise ToolError(f"Error creating relations: {e}")

    async def _register_add_observations(self):
        description = await self._get_dynamic_description(
            "add_observations",
            "Add new observations to existing entities."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Add Observations", 
                                      readOnlyHint=False, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def add_observations(observations: list[ObservationAddition] = Field(..., description="List of observations to add")) -> list[dict[str, str | list[str]]]:
            """Add new observations to existing entities."""
            logger.info(f"MCP tool: add_observations ({len(observations)} additions)")
            try:
                observation_objects = [ObservationAddition.model_validate(obs) for obs in observations]
                result = await self.memory.add_observations(observation_objects)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content={"result": result})
            except Neo4jError as e:
                logger.error(f"Neo4j error adding observations: {e}")
                raise ToolError(f"Neo4j error adding observations: {e}")
            except Exception as e:
                logger.error(f"Error adding observations: {e}")
                raise ToolError(f"Error adding observations: {e}")

    async def _register_find_memories_by_name(self):
        description = await self._get_dynamic_description(
            "find_memories_by_name",
            "Find specific memories by name."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Find Memories By Name", 
                                      readOnlyHint=True, 
                                      destructiveHint=False, 
                                      idempotentHint=True, 
                                      openWorldHint=True)
        )
        async def find_memories_by_name(names: list[str] = Field(..., description="List of node names to find")) -> KnowledgeGraph:
            """Find specific memories by name."""
            logger.info(f"MCP tool: find_memories_by_name ({len(names)} names)")
            try:
                result = await self.memory.find_memories_by_name(names)
                return ToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error finding memories by name: {e}")
                raise ToolError(f"Neo4j error finding memories by name: {e}")
            except Exception as e:
                logger.error(f"Error finding memories by name: {e}")
                raise ToolError(f"Error finding memories by name: {e}")

    async def _register_delete_entities(self):
        description = await self._get_dynamic_description(
            "delete_entities",
            "Delete multiple entities and their associated relations."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Delete Entities", 
                                      readOnlyHint=False, 
                                      destructiveHint=True, 
                                      idempotentHint=False, 
                                      openWorldHint=True)
        )
        async def delete_entities(entityNames: list[str] = Field(..., description="List of entity names to delete")) -> dict[str, str]:
            """Delete multiple entities and their associated relations."""
            logger.info(f"MCP tool: delete_entities ({len(entityNames)} entities)")
            try:
                result = await self.memory.delete_entities(entityNames)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting entities: {e}")
                raise ToolError(f"Neo4j error deleting entities: {e}")
            except Exception as e:
                logger.error(f"Error deleting entities: {e}")
                raise ToolError(f"Error deleting entities: {e}")

    async def _register_delete_observations(self):
        description = await self._get_dynamic_description(
            "delete_observations",
            "Delete specific observations from entities."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Delete Observations", 
                                      readOnlyHint=False, 
                                      destructiveHint=True, 
                                      idempotentHint=False, 
                                      openWorldHint=True)
        )
        async def delete_observations(deletions: list[ObservationDeletion] = Field(..., description="List of observations to delete")) -> dict[str, str]:
            """Delete specific observations from entities."""
            logger.info(f"MCP tool: delete_observations ({len(deletions)} deletions)")
            try:
                deletion_objects = [ObservationDeletion.model_validate(deletion) for deletion in deletions]
                result = await self.memory.delete_observations(deletion_objects)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting observations: {e}")
                raise ToolError(f"Neo4j error deleting observations: {e}")
            except Exception as e:
                logger.error(f"Error deleting observations: {e}")
                raise ToolError(f"Error deleting observations: {e}")

    async def _register_delete_relations(self):
        description = await self._get_dynamic_description(
            "delete_relations",
            "Delete multiple relations from the graph."
        )
        
        @self.mcp.tool(
            description=description,
            annotations=ToolAnnotations(title="Delete Relations", 
                                      readOnlyHint=False, 
                                      destructiveHint=True, 
                                      idempotentHint=False, 
                                      openWorldHint=True)
        )
        async def delete_relations(relations: list[Relation] = Field(..., description="List of relations to delete")) -> dict[str, str]:
            """Delete multiple relations from the graph."""
            logger.info(f"MCP tool: delete_relations ({len(relations)} relations)")
            try:
                relation_objects = [Relation.model_validate(relation) for relation in relations]
                result = await self.memory.delete_relations(relation_objects)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting relations: {e}")
                raise ToolError(f"Neo4j error deleting relations: {e}")
            except Exception as e:
                logger.error(f"Error deleting relations: {e}")
                raise ToolError(f"Error deleting relations: {e}")

    async def _register_dynamic_description_tools(self):
        """Register dynamic description management tools."""
        
        @self.mcp.tool(annotations=ToolAnnotations(title="Dynamic Descriptions Health", 
                                                  readOnlyHint=True, 
                                                  destructiveHint=False, 
                                                  idempotentHint=True, 
                                                  openWorldHint=False))
        async def dynamic_descriptions_health() -> dict:
            """Check the health status of the dynamic descriptions system."""
            logger.info("MCP tool: dynamic_descriptions_health")
            try:
                health_status = await self.description_manager.health_check()
                return ToolResult(content=[TextContent(type="text", text=json.dumps(health_status))],
                              structured_content=health_status)
            except Exception as e:
                logger.error(f"Error checking dynamic descriptions health: {e}")
                raise ToolError(f"Error checking dynamic descriptions health: {e}")

        @self.mcp.tool(annotations=ToolAnnotations(title="Setup Dynamic Descriptions Schema", 
                                                  readOnlyHint=False, 
                                                  destructiveHint=False, 
                                                  idempotentHint=True, 
                                                  openWorldHint=False))
        async def setup_dynamic_descriptions_schema() -> dict:
            """Create Neo4j schema (constraints and indexes) for ToolDescription entities."""
            logger.info("MCP tool: setup_dynamic_descriptions_schema")
            try:
                schema_result = await self.description_manager.setup_schema()
                return ToolResult(content=[TextContent(type="text", text=json.dumps(schema_result))],
                              structured_content=schema_result)
            except Exception as e:
                logger.error(f"Error setting up dynamic descriptions schema: {e}")
                raise ToolError(f"Error setting up dynamic descriptions schema: {e}")

        @self.mcp.tool(annotations=ToolAnnotations(title="Seed Initial Descriptions", 
                                                  readOnlyHint=False, 
                                                  destructiveHint=False, 
                                                  idempotentHint=True, 
                                                  openWorldHint=False))
        async def seed_initial_descriptions(
            overwrite: bool = Field(default=False, description="Whether to overwrite existing descriptions")
        ) -> dict:
            """Seed initial tool descriptions from hardcoded descriptions into Neo4j."""
            logger.info(f"MCP tool: seed_initial_descriptions (overwrite={overwrite})")
            try:
                seed_result = await self.description_manager.seed_initial_descriptions(overwrite=overwrite)
                return ToolResult(content=[TextContent(type="text", text=json.dumps(seed_result))],
                              structured_content=seed_result)
            except Exception as e:
                logger.error(f"Error seeding initial descriptions: {e}")
                raise ToolError(f"Error seeding initial descriptions: {e}")

        # Add all the Phase 3 lifecycle management tools...
        await self._register_lifecycle_management_tools()

    async def _register_lifecycle_management_tools(self):
        """Register Phase 3 lifecycle management tools."""
        
        @self.mcp.tool(annotations=ToolAnnotations(title="List Tool Descriptions", 
                                                  readOnlyHint=True, 
                                                  destructiveHint=False, 
                                                  idempotentHint=True, 
                                                  openWorldHint=False))
        async def list_tool_descriptions(
            environment: str = Field(default=None, description="Filter by environment (dev/staging/production). If None, uses current environment."),
            tool_name: str = Field(default=None, description="Filter by specific tool name. If None, returns all tools.")
        ) -> dict:
            """List tool descriptions stored in Neo4j."""
            logger.info(f"MCP tool: list_tool_descriptions (env={environment}, tool={tool_name})")
            try:
                descriptions = await self.description_manager.list_tool_descriptions(environment=environment, tool_name=tool_name)
                # Wrap list in dictionary for structured_content compliance
                structured_data = {"descriptions": descriptions, "count": len(descriptions)}
                return ToolResult(content=[TextContent(type="text", text=json.dumps(descriptions))],
                              structured_content=structured_data)
            except Exception as e:
                logger.error(f"Error listing tool descriptions: {e}")
                raise ToolError(f"Error listing tool descriptions: {e}")

        @self.mcp.tool(annotations=ToolAnnotations(title="Mark Dynamic Description Deprecated", 
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
                result = await self.description_manager.mark_tool_description_deprecated(
                    tool_name=tool_name,
                    version=version,
                    reason=reason,
                    deprecated_by=deprecated_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Exception as e:
                logger.error(f"Error marking description deprecated: {e}")
                raise ToolError(f"Error marking description deprecated: {e}")

        # Add remaining lifecycle tools...
        @self.mcp.tool(annotations=ToolAnnotations(title="Promote Testing Description to Active", 
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
            logger.info(f"MCP tool: promote_testing_to_active ({tool_name} v{version})")
            try:
                result = await self.description_manager.promote_testing_to_active(
                    tool_name=tool_name,
                    version=version,
                    promoted_by=promoted_by
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Exception as e:
                logger.error(f"Error promoting description to active: {e}")
                raise ToolError(f"Error promoting description to active: {e}")

        @self.mcp.tool(annotations=ToolAnnotations(title="Reactivate Dynamic Description", 
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
                result = await self.description_manager.reactivate_tool_description(
                    tool_name=tool_name,
                    version=version,
                    reactivated_by=reactivated_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Exception as e:
                logger.error(f"Error reactivating description: {e}")
                raise ToolError(f"Error reactivating description: {e}")

        @self.mcp.tool(annotations=ToolAnnotations(title="Create Description Version", 
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
                result = await self.description_manager.create_description_version(
                    tool_name=tool_name,
                    base_version=base_version,
                    new_version=new_version,
                    new_description=new_description,
                    created_by=created_by,
                    environment=environment
                )
                return ToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                              structured_content=result)
            except Exception as e:
                logger.error(f"Error creating description version: {e}")
                raise ToolError(f"Error creating description version: {e}")


async def create_mcp_server(memory: Neo4jMemory, description_manager: DynamicToolDescriptionManager = None) -> FastMCP:
    """Create an MCP server instance with dynamic tool descriptions."""
    
    mcp: FastMCP = FastMCP("mcp-neo4j-memory", dependencies=["neo4j", "pydantic"], stateless_http=True)
    
    # Create and initialize dynamic tool provider
    tool_provider = DynamicToolProvider(mcp, memory, description_manager)
    await tool_provider.initialize()
    
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
    
    # Auto-setup dynamic descriptions on first run if enabled
    if dynamic_descriptions_enabled:
        try:
            # Check if schema exists, if not set it up
            health_status = await description_manager.health_check()
            if health_status.get("active_descriptions", 0) == 0:
                logger.info("No active descriptions found - performing first-run setup")
                
                # Setup schema
                await description_manager.setup_schema()
                logger.info("Dynamic descriptions schema created")
                
                # Seed initial descriptions
                seed_result = await description_manager.seed_initial_descriptions()
                created_count = len(seed_result.get("created", []))
                logger.info(f"Seeded {created_count} initial tool descriptions")
                
                if created_count > 0:
                    logger.info("Dynamic descriptions auto-setup completed successfully")
                else:
                    logger.warning("No descriptions were created during auto-setup")
            else:
                logger.info(f"Dynamic descriptions already initialized ({health_status.get('active_descriptions')} active)")
                
        except Exception as e:
            logger.error(f"Error during dynamic descriptions auto-setup: {e}")
            logger.info("Falling back to hardcoded descriptions")
    
    # Create fulltext index
    await memory.create_fulltext_index()
    
    # Create MCP server with dynamic descriptions
    mcp = await create_mcp_server(memory, description_manager)
    logger.info("MCP server created with dynamic tool registration")

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
