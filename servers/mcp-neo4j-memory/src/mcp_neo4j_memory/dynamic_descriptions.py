"""
Dynamic Tool Description Manager for Neo4j-stored MCP tool descriptions.

This module provides the core functionality for storing, retrieving, and managing
tool descriptions in Neo4j with evo-memory patterns. Tool descriptions can be
dynamically updated without code changes, enabling continuous optimization
through effectiveness tracking and evo-strengthening.
"""

import asyncio
import logging
from typing import Dict, Optional, List
from neo4j import AsyncDriver
from .description_schemas import ToolDescriptionModel, DescriptionUsageEvent

logger = logging.getLogger(__name__)


class DynamicToolDescriptionManager:
    """
    Manages dynamic tool descriptions stored in Neo4j with evo-memory patterns.
    
    Provides functionality to:
    - Retrieve tool descriptions with effectiveness-based selection
    - Track usage and implement evo-strengthening
    - Create and manage description versions
    - Fallback gracefully to hardcoded descriptions
    """
    
    def __init__(self, driver: AsyncDriver, enabled: bool = True, environment: str = "production"):
        """
        Initialize the Dynamic Tool Description Manager.
        
        Args:
            driver: Neo4j async driver for database operations
            enabled: Whether dynamic descriptions are enabled (fallback if False)
            environment: Environment for description selection (dev/staging/production)
        """
        self.driver = driver
        self.enabled = enabled
        self.environment = environment
        self.fallback_descriptions = self._load_hardcoded_descriptions()
        logger.info(f"DynamicToolDescriptionManager initialized: enabled={enabled}, environment={environment}")
        
    def _load_hardcoded_descriptions(self) -> Dict[str, str]:
        """
        Load current hardcoded descriptions as fallback.
        
        These are the current evo-memory tool descriptions that will be used
        if dynamic descriptions are disabled or if Neo4j is unavailable.
        
        Returns:
            Dictionary mapping tool names to their hardcoded descriptions
        """
        return {
            "search_memories": (
                "**PRIMARY DISCOVERY TOOL**: Use this FIRST when user asks about past work, "
                "concepts, or relationships. Performs evo-memory discovery through relationship "
                "traversal and semantic search rather than full graph reads. Triggers evo "
                "strengthening on accessed knowledge. WHEN TO USE: 'What did we work on "
                "yesterday?', 'Tell me about X', 'How does Y relate to Z?', 'What do I know about...?'"
            ),
            "read_graph": (
                "**FULL CONTEXT TOOL**: Use ONLY when you need complete system state overview "
                "or when search_memories fails to find relevant context. This is computationally "
                "expensive and should be avoided for targeted queries. WHEN TO USE: System "
                "architecture review, complete knowledge audit, debugging knowledge graph issues. "
                "AVOID: Use search_memories instead for specific topic discovery."
            ),
            "create_entities": (
                "**KNOWLEDGE CREATION TOOL**: Create new entities with evo metadata (access_count, "
                "confidence, created timestamp). Always include evo metadata and meaningful "
                "observations. WHEN TO USE: Learning new concepts, storing insights, capturing "
                "project knowledge. Include relationships to existing entities for knowledge integration."
            ),
            "create_relations": (
                "**EVO STRENGTHENING TOOL**: Create relationships between entities to enable "
                "knowledge discovery through traversal. Essential for evo-memory patterns. WHEN "
                "TO USE: After creating entities, when discovering connections, building knowledge "
                "networks. Relationship types: part_of, implements, validates, coordinates_with, etc."
            ),
            "add_observations": (
                "**EVO CONSOLIDATION TOOL**: Add new insights to existing entities, simulating "
                "evo strengthening. Update evo metadata (increment access_count, update last_accessed). "
                "WHEN TO USE: Learning new details about existing concepts, consolidating session "
                "insights, updating project status."
            ),
            "find_memories_by_name": (
                "**DIRECT ACCESS TOOL**: Find specific entities by exact name when you know what "
                "you're looking for. More efficient than search_memories for known entity names. "
                "WHEN TO USE: Accessing specific projects, methodologies, or entities by name. "
                "Triggers evo strengthening on accessed entities."
            ),
            "delete_entities": "Delete multiple entities and their associated relations.",
            "delete_observations": "Delete specific observations from entities.",
            "delete_relations": "Delete multiple relations from the graph."
        }
    
    async def get_tool_description(self, tool_name: str, environment: Optional[str] = None) -> str:
        """
        Get the most effective tool description, with fallback to hardcoded.
        
        Retrieves tool descriptions from Neo4j based on effectiveness score,
        implements evo-strengthening by tracking access, and falls back gracefully
        to hardcoded descriptions if needed.
        
        Args:
            tool_name: Name of the MCP tool
            environment: Override environment (uses instance default if None)
            
        Returns:
            Tool description string that guides LLM behavior
        """
        env = environment or self.environment
        
        if not self.enabled:
            logger.debug(f"Dynamic descriptions disabled, using fallback for {tool_name}")
            return self.fallback_descriptions.get(tool_name, f"Tool: {tool_name}")
        
        try:
            # Query for the most effective active description
            query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name, 
                environment: $environment, 
                status: 'active'
            })
            RETURN desc.description as description, 
                   desc.effectiveness_score as score,
                   desc.version as version
            ORDER BY desc.effectiveness_score DESC
            LIMIT 1
            """
            
            result = await self.driver.execute_query(
                query, 
                tool_name=tool_name, 
                environment=env
            )
            
            if result.records:
                description = result.records[0]["description"]
                version = result.records[0]["version"]
                
                # Trigger evo-strengthening asynchronously
                asyncio.create_task(self._increment_access_count(tool_name, env, version))
                
                logger.debug(f"Retrieved dynamic description for {tool_name} v{version}")
                return description
            else:
                logger.debug(f"No dynamic description found for {tool_name}, using fallback")
            
        except Exception as e:
            logger.error(f"Error fetching dynamic description for {tool_name}: {e}")
        
        # Fallback to hardcoded descriptions
        return self.fallback_descriptions.get(tool_name, f"Tool: {tool_name}")
    
    async def _increment_access_count(self, tool_name: str, environment: str, version: str):
        """
        Evo-strengthening: increment access count and update last_accessed.
        
        This implements the core evo-memory pattern of strengthening frequently
        accessed knowledge. Updates are done asynchronously to avoid impacting
        tool description retrieval performance.
        
        Args:
            tool_name: Name of the tool accessed
            environment: Environment the description was accessed in
            version: Version of the description accessed
        """
        try:
            query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name, 
                environment: $environment, 
                status: 'active'
            })
            SET desc.access_count = desc.access_count + 1,
                desc.last_accessed = datetime()
            RETURN desc.access_count as new_count
            """
            
            result = await self.driver.execute_query(
                query, 
                tool_name=tool_name, 
                environment=environment
            )
            
            if result.records:
                new_count = result.records[0]["new_count"]
                logger.debug(f"Evo-strengthening: {tool_name} access count now {new_count}")
            
        except Exception as e:
            logger.error(f"Error incrementing access count for {tool_name}: {e}")
    
    async def create_tool_description(self, description: ToolDescriptionModel) -> bool:
        """
        Create a new tool description in Neo4j.
        
        Stores a tool description with full evo-memory metadata, enabling
        effectiveness tracking and version management.
        
        Args:
            description: ToolDescriptionModel with all required fields
            
        Returns:
            True if creation was successful, False otherwise
        """
        try:
            query = """
            CREATE (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                description: $description,
                effectiveness_score: $effectiveness_score,
                access_count: $access_count,
                created: datetime($created),
                last_accessed: CASE 
                    WHEN $last_accessed IS NOT NULL 
                    THEN datetime($last_accessed) 
                    ELSE NULL 
                END,
                status: $status,
                confidence: $confidence,
                environment: $environment,
                created_by: $created_by
            })
            RETURN desc.tool_name as created
            """
            
            result = await self.driver.execute_query(
                query,
                tool_name=description.tool_name,
                version=description.version,
                description=description.description,
                effectiveness_score=description.effectiveness_score,
                access_count=description.access_count,
                created=description.created.isoformat(),
                last_accessed=description.last_accessed.isoformat() if description.last_accessed else None,
                status=description.status,
                confidence=description.confidence,
                environment=description.environment,
                created_by=description.created_by
            )
            
            success = len(result.records) > 0
            if success:
                logger.info(f"Created tool description: {description.tool_name} v{description.version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating tool description: {e}")
            return False
    
    async def list_tool_descriptions(
        self, 
        tool_name: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        List tool descriptions with optional filtering.
        
        Args:
            tool_name: Filter by specific tool name (optional)
            environment: Filter by environment (optional)
            status: Filter by status (optional)
            
        Returns:
            List of dictionaries containing description metadata
        """
        try:
            # Build dynamic WHERE clause based on filters
            where_conditions = []
            params = {}
            
            if tool_name:
                where_conditions.append("desc.tool_name = $tool_name")
                params["tool_name"] = tool_name
                
            if environment:
                where_conditions.append("desc.environment = $environment")
                params["environment"] = environment
                
            if status:
                where_conditions.append("desc.status = $status")
                params["status"] = status
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            query = f"""
            MATCH (desc:ToolDescription)
            {where_clause}
            RETURN desc.tool_name as tool_name, 
                   desc.version as version,
                   desc.effectiveness_score as effectiveness_score, 
                   desc.access_count as access_count,
                   desc.status as status, 
                   desc.environment as environment,
                   desc.confidence as confidence,
                   desc.created as created,
                   desc.last_accessed as last_accessed,
                   desc.created_by as created_by
            ORDER BY desc.tool_name, desc.effectiveness_score DESC
            """
            
            result = await self.driver.execute_query(query, **params)
            descriptions = [dict(record) for record in result.records]
            
            logger.debug(f"Listed {len(descriptions)} tool descriptions")
            return descriptions
            
        except Exception as e:
            logger.error(f"Error listing tool descriptions: {e}")
            return []
    
    async def record_effectiveness(
        self, 
        tool_name: str, 
        success: bool, 
        environment: Optional[str] = None,
        context: Optional[str] = None,
        response_quality: Optional[float] = None
    ):
        """
        Record whether a tool usage was effective for evo-strengthening.
        
        Updates effectiveness scores based on success/failure and implements
        evo-memory learning patterns.
        
        Args:
            tool_name: Name of the tool used
            success: Whether the tool usage was successful
            environment: Environment where tool was used
            context: Optional context about the usage
            response_quality: Optional quality score (0.0-1.0)
        """
        env = environment or self.environment
        
        try:
            # Calculate effectiveness adjustment based on success
            adjustment = 0.05 if success else -0.02
            
            # Update effectiveness score with bounds checking
            query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name, 
                environment: $environment, 
                status: 'active'
            })
            SET desc.effectiveness_score = CASE 
                WHEN desc.effectiveness_score + $adjustment > 1.0 THEN 1.0
                WHEN desc.effectiveness_score + $adjustment < 0.0 THEN 0.0  
                ELSE desc.effectiveness_score + $adjustment
            END,
            desc.confidence = CASE
                WHEN desc.access_count > 10 THEN 0.95
                WHEN desc.access_count > 5 THEN 0.8
                ELSE desc.confidence
            END
            RETURN desc.effectiveness_score as new_score, desc.version as version
            """
            
            result = await self.driver.execute_query(
                query, 
                tool_name=tool_name, 
                environment=env,
                adjustment=adjustment
            )
            
            if result.records:
                new_score = result.records[0]["new_score"]
                version = result.records[0]["version"]
                logger.debug(f"Updated effectiveness for {tool_name} v{version}: {new_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error recording effectiveness for {tool_name}: {e}")
    
    def get_hardcoded_description(self, tool_name: str) -> Optional[str]:
        """
        Get hardcoded fallback description for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Hardcoded description if available, None otherwise
        """
        return self.fallback_descriptions.get(tool_name)
    
    async def health_check(self) -> Dict:
        """
        Perform health check on the dynamic descriptions system.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "enabled": False,
                    "fallback_descriptions_count": len(self.fallback_descriptions)
                }
            
            # Count active descriptions
            query = """
            MATCH (desc:ToolDescription {status: 'active'})
            RETURN count(desc) as active_count,
                   collect(DISTINCT desc.environment) as environments,
                   collect(DISTINCT desc.tool_name) as tools
            """
            
            result = await self.driver.execute_query(query)
            
            if result.records:
                record = result.records[0]
                return {
                    "status": "healthy",
                    "enabled": True,
                    "active_descriptions": record["active_count"],
                    "environments": record["environments"],
                    "tools_with_descriptions": record["tools"],
                    "fallback_descriptions_count": len(self.fallback_descriptions)
                }
            else:
                return {
                    "status": "no_descriptions",
                    "enabled": True,
                    "active_descriptions": 0,
                    "fallback_descriptions_count": len(self.fallback_descriptions)
                }
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "fallback_descriptions_count": len(self.fallback_descriptions)
            }
