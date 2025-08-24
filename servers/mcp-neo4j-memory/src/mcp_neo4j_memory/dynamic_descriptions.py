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
            
            descriptions = []
            for record in result.records:
                desc = dict(record)
                # Convert datetime objects to ISO format for JSON serialization
                if desc.get("created"):
                    desc["created"] = desc["created"].isoformat()
                if desc.get("last_accessed"):
                    desc["last_accessed"] = desc["last_accessed"].isoformat()
                descriptions.append(desc)
            
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
    
    # Phase 2: Evo-Memory Integration - Schema Management and Seeding
    
    async def setup_schema(self) -> Dict:
        """
        Create Neo4j schema (constraints and indexes) for ToolDescription entities.
        
        This creates the necessary database schema for storing and efficiently
        querying tool descriptions with evo-memory patterns.
        
        Returns:
            Dictionary with schema setup results and status
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        try:
            schema_operations = []
            
            # Create unique constraint on (tool_name, version, environment)
            constraint_query = """
            CREATE CONSTRAINT tool_description_unique IF NOT EXISTS
            FOR (desc:ToolDescription) 
            REQUIRE (desc.tool_name, desc.version, desc.environment) IS UNIQUE
            """
            
            result = await self.driver.execute_query(constraint_query)
            schema_operations.append({
                "operation": "unique_constraint",
                "target": "(tool_name, version, environment)",
                "status": "created"
            })
            
            # Create index on tool_name for fast lookups
            tool_name_index = """
            CREATE INDEX tool_description_name_idx IF NOT EXISTS
            FOR (desc:ToolDescription) ON (desc.tool_name)
            """
            
            await self.driver.execute_query(tool_name_index)
            schema_operations.append({
                "operation": "index",
                "target": "tool_name",
                "status": "created"
            })
            
            # Create index on environment for environment-specific queries
            env_index = """
            CREATE INDEX tool_description_env_idx IF NOT EXISTS
            FOR (desc:ToolDescription) ON (desc.environment)
            """
            
            await self.driver.execute_query(env_index)
            schema_operations.append({
                "operation": "index",
                "target": "environment", 
                "status": "created"
            })
            
            # Create index on effectiveness_score for performance optimization
            effectiveness_index = """
            CREATE INDEX tool_description_effectiveness_idx IF NOT EXISTS
            FOR (desc:ToolDescription) ON (desc.effectiveness_score)
            """
            
            await self.driver.execute_query(effectiveness_index)
            schema_operations.append({
                "operation": "index",
                "target": "effectiveness_score",
                "status": "created"
            })
            
            # Create compound index on (tool_name, environment, status) for main queries
            compound_index = """
            CREATE INDEX tool_description_lookup_idx IF NOT EXISTS
            FOR (desc:ToolDescription) ON (desc.tool_name, desc.environment, desc.status)
            """
            
            await self.driver.execute_query(compound_index)
            schema_operations.append({
                "operation": "compound_index",
                "target": "(tool_name, environment, status)",
                "status": "created"
            })
            
            logger.info(f"Schema setup completed: {len(schema_operations)} operations")
            
            return {
                "status": "success",
                "enabled": True,
                "operations": schema_operations,
                "total_operations": len(schema_operations)
            }
            
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "operations": schema_operations if 'schema_operations' in locals() else []
            }
    
    async def seed_initial_descriptions(self, overwrite: bool = False) -> Dict:
        """
        Seed initial tool descriptions from hardcoded descriptions.
        
        Creates version 1.0 descriptions in Neo4j based on the current hardcoded
        fallback descriptions, enabling the transition to dynamic descriptions.
        
        Args:
            overwrite: Whether to overwrite existing descriptions
            
        Returns:
            Dictionary with seeding results and created descriptions
        """
        if not self.enabled:
            return {
                "status": "skipped", 
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        try:
            created_descriptions = []
            skipped_descriptions = []
            failed_descriptions = []
            
            for tool_name, description_text in self.fallback_descriptions.items():
                try:
                    # Check if description already exists
                    existing = await self._check_existing_description(tool_name, "1.0", self.environment)
                    
                    if existing and not overwrite:
                        skipped_descriptions.append({
                            "tool_name": tool_name,
                            "reason": "already_exists",
                            "version": "1.0"
                        })
                        continue
                    
                    # Create ToolDescriptionModel for this tool
                    description_model = ToolDescriptionModel(
                        tool_name=tool_name,
                        version="1.0",
                        description=description_text,
                        environment=self.environment,
                        created_by="system_seeding",
                        status="active"
                    )
                    
                    # Create the description in Neo4j
                    success = await self.create_tool_description(description_model)
                    
                    if success:
                        created_descriptions.append({
                            "tool_name": tool_name,
                            "version": "1.0",
                            "environment": self.environment,
                            "length": len(description_text)
                        })
                        logger.info(f"Seeded description for {tool_name} v1.0")
                    else:
                        failed_descriptions.append({
                            "tool_name": tool_name,
                            "reason": "creation_failed",
                            "version": "1.0"
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to seed description for {tool_name}: {e}")
                    failed_descriptions.append({
                        "tool_name": tool_name,
                        "reason": str(e),
                        "version": "1.0"
                    })
            
            logger.info(f"Seeding completed: {len(created_descriptions)} created, "
                       f"{len(skipped_descriptions)} skipped, {len(failed_descriptions)} failed")
            
            return {
                "status": "completed",
                "enabled": True,
                "created": created_descriptions,
                "skipped": skipped_descriptions, 
                "failed": failed_descriptions,
                "summary": {
                    "total_tools": len(self.fallback_descriptions),
                    "created_count": len(created_descriptions),
                    "skipped_count": len(skipped_descriptions),
                    "failed_count": len(failed_descriptions)
                }
            }
            
        except Exception as e:
            logger.error(f"Seeding process failed: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "created": created_descriptions if 'created_descriptions' in locals() else [],
                "failed": failed_descriptions if 'failed_descriptions' in locals() else []
            }
    
    async def _check_existing_description(self, tool_name: str, version: str, environment: str) -> bool:
        """
        Check if a tool description already exists in Neo4j.
        
        Args:
            tool_name: Name of the tool
            version: Version of the description
            environment: Environment (dev/staging/production)
            
        Returns:
            True if description exists, False otherwise
        """
        try:
            query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                environment: $environment
            })
            RETURN count(desc) as count
            """
            
            result = await self.driver.execute_query(
                query,
                tool_name=tool_name,
                version=version,
                environment=environment
            )
            
            return result.records[0]["count"] > 0
            
        except Exception as e:
            logger.error(f"Error checking existing description for {tool_name}: {e}")
            return False
    
    async def get_schema_info(self) -> Dict:
        """
        Get information about the current Neo4j schema for ToolDescription entities.
        
        Returns:
            Dictionary with schema information including constraints and indexes
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "enabled": False
            }
            
        try:
            # Get constraints
            constraints_query = """
            SHOW CONSTRAINTS
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE 'ToolDescription' IN labelsOrTypes
            RETURN name, type, properties
            """
            
            constraints_result = await self.driver.execute_query(constraints_query)
            constraints = [
                {
                    "name": record["name"],
                    "type": record["type"], 
                    "properties": record["properties"]
                }
                for record in constraints_result.records
            ]
            
            # Get indexes
            indexes_query = """
            SHOW INDEXES
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE 'ToolDescription' IN labelsOrTypes
            RETURN name, type, properties
            """
            
            indexes_result = await self.driver.execute_query(indexes_query)
            indexes = [
                {
                    "name": record["name"],
                    "type": record["type"],
                    "properties": record["properties"]
                }
                for record in indexes_result.records
            ]
            
            # Get total description count
            count_query = """
            MATCH (desc:ToolDescription)
            RETURN count(desc) as total_descriptions,
                   count(DISTINCT desc.tool_name) as unique_tools,
                   count(DISTINCT desc.environment) as environments
            """
            
            count_result = await self.driver.execute_query(count_query)
            stats = count_result.records[0] if count_result.records else {}
            
            return {
                "status": "success",
                "enabled": True,
                "constraints": constraints,
                "indexes": indexes,
                "statistics": {
                    "total_descriptions": stats.get("total_descriptions", 0),
                    "unique_tools": stats.get("unique_tools", 0),
                    "environments": stats.get("environments", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e)
            }
    
    # Phase 3: Description Lifecycle Management
    
    async def mark_tool_description_deprecated(
        self, 
        tool_name: str, 
        version: str, 
        reason: str,
        deprecated_by: str = "system",
        environment: Optional[str] = None
    ) -> Dict:
        """
        Mark a tool description as deprecated with reason tracking.
        
        Follows evo-memory philosophy of preserving learning data rather than deletion.
        Deprecated descriptions remain for analysis and potential reactivation.
        
        Args:
            tool_name: Name of the tool
            version: Version to deprecate
            reason: Reason for deprecation (e.g., "ineffective", "replaced", "outdated")
            deprecated_by: Who is deprecating this description
            environment: Environment to target (defaults to manager environment)
            
        Returns:
            Dictionary with deprecation results
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        target_environment = environment or self.environment
        
        try:
            # Check if description exists and is not already deprecated
            check_query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                environment: $environment
            })
            RETURN desc.status as current_status, desc.deprecated_at as deprecated_at
            """
            
            check_result = await self.driver.execute_query(
                check_query,
                tool_name=tool_name,
                version=version,
                environment=target_environment
            )
            
            if not check_result.records:
                return {
                    "status": "not_found",
                    "enabled": True,
                    "tool_name": tool_name,
                    "version": version,
                    "environment": target_environment
                }
                
            current_status = check_result.records[0]["current_status"]
            if current_status == "deprecated":
                return {
                    "status": "already_deprecated",
                    "enabled": True,
                    "tool_name": tool_name,
                    "version": version,
                    "environment": target_environment,
                    "deprecated_at": check_result.records[0]["deprecated_at"]
                }
            
            # Mark as deprecated
            deprecate_query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                environment: $environment
            })
            SET desc.status = 'deprecated',
                desc.deprecated_at = datetime(),
                desc.deprecated_by = $deprecated_by,
                desc.deprecation_reason = $reason
            RETURN desc.deprecated_at as deprecated_at,
                   desc.effectiveness_score as final_score
            """
            
            result = await self.driver.execute_query(
                deprecate_query,
                tool_name=tool_name,
                version=version,
                environment=target_environment,
                deprecated_by=deprecated_by,
                reason=reason
            )
            
            logger.info(f"Deprecated description {tool_name} v{version}: {reason}")
            
            return {
                "status": "deprecated",
                "enabled": True,
                "tool_name": tool_name,
                "version": version,
                "environment": target_environment,
                "reason": reason,
                "deprecated_by": deprecated_by,
                "deprecated_at": result.records[0]["deprecated_at"].isoformat(),
                "final_effectiveness_score": result.records[0]["final_score"]
            }
            
        except Exception as e:
            logger.error(f"Error deprecating description {tool_name} v{version}: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "tool_name": tool_name,
                "version": version
            }
    
    async def reactivate_tool_description(
        self,
        tool_name: str,
        version: str,
        reactivated_by: str = "system",
        environment: Optional[str] = None
    ) -> Dict:
        """
        Reactivate a deprecated tool description.
        
        Enables bringing back previously deprecated descriptions when needed,
        supporting iterative improvement and learning from past decisions.
        
        Args:
            tool_name: Name of the tool
            version: Version to reactivate
            reactivated_by: Who is reactivating this description
            environment: Environment to target (defaults to manager environment)
            
        Returns:
            Dictionary with reactivation results
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        target_environment = environment or self.environment
        
        try:
            # Check if description exists and is deprecated
            check_query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                environment: $environment
            })
            RETURN desc.status as current_status, 
                   desc.deprecated_at as deprecated_at,
                   desc.deprecation_reason as deprecation_reason
            """
            
            check_result = await self.driver.execute_query(
                check_query,
                tool_name=tool_name,
                version=version,
                environment=target_environment
            )
            
            if not check_result.records:
                return {
                    "status": "not_found",
                    "enabled": True,
                    "tool_name": tool_name,
                    "version": version,
                    "environment": target_environment
                }
                
            current_status = check_result.records[0]["current_status"]
            if current_status != "deprecated":
                return {
                    "status": "not_deprecated",
                    "enabled": True,
                    "tool_name": tool_name,
                    "version": version,
                    "environment": target_environment,
                    "current_status": current_status
                }
            
            # Reactivate the description
            reactivate_query = """
            MATCH (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                environment: $environment
            })
            SET desc.status = 'active',
                desc.reactivated_at = datetime(),
                desc.reactivated_by = $reactivated_by
            RETURN desc.reactivated_at as reactivated_at,
                   desc.effectiveness_score as current_score
            """
            
            result = await self.driver.execute_query(
                reactivate_query,
                tool_name=tool_name,
                version=version,
                environment=target_environment,
                reactivated_by=reactivated_by
            )
            
            logger.info(f"Reactivated description {tool_name} v{version}")
            
            return {
                "status": "reactivated",
                "enabled": True,
                "tool_name": tool_name,
                "version": version,
                "environment": target_environment,
                "reactivated_by": reactivated_by,
                "reactivated_at": result.records[0]["reactivated_at"].isoformat(),
                "current_effectiveness_score": result.records[0]["current_score"],
                "previous_deprecation_reason": check_result.records[0]["deprecation_reason"]
            }
            
        except Exception as e:
            logger.error(f"Error reactivating description {tool_name} v{version}: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "tool_name": tool_name,
                "version": version
            }
    
    async def create_description_version(
        self,
        tool_name: str,
        base_version: str,
        new_version: str,
        new_description: str,
        created_by: str = "system",
        environment: Optional[str] = None
    ) -> Dict:
        """
        Create a new version of a tool description based on an existing one.
        
        Enables iterative improvement while maintaining evolution history.
        Creates evolution relationship between versions.
        
        Args:
            tool_name: Name of the tool
            base_version: Version to base the new version on
            new_version: Version identifier for the new description
            new_description: The new description text
            created_by: Who is creating this version
            environment: Environment to target (defaults to manager environment)
            
        Returns:
            Dictionary with creation results
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        target_environment = environment or self.environment
        
        try:
            # Check if base version exists
            base_check_query = """
            MATCH (base:ToolDescription {
                tool_name: $tool_name,
                version: $base_version,
                environment: $environment
            })
            RETURN base.effectiveness_score as base_score,
                   base.description as base_description
            """
            
            base_result = await self.driver.execute_query(
                base_check_query,
                tool_name=tool_name,
                base_version=base_version,
                environment=target_environment
            )
            
            if not base_result.records:
                return {
                    "status": "base_not_found",
                    "enabled": True,
                    "tool_name": tool_name,
                    "base_version": base_version,
                    "environment": target_environment
                }
            
            # Check if new version already exists
            existing_check = await self._check_existing_description(tool_name, new_version, target_environment)
            if existing_check:
                return {
                    "status": "version_exists",
                    "enabled": True,
                    "tool_name": tool_name,
                    "new_version": new_version,
                    "environment": target_environment
                }
            
            # Create new description model
            description_model = ToolDescriptionModel(
                tool_name=tool_name,
                version=new_version,
                description=new_description,
                environment=target_environment,
                created_by=created_by,
                status="testing"  # New versions start as testing
            )
            
            # Create the new description
            success = await self.create_tool_description(description_model)
            
            if not success:
                return {
                    "status": "creation_failed",
                    "enabled": True,
                    "tool_name": tool_name,
                    "new_version": new_version
                }
            
            # Create evolution relationship
            evolution_query = """
            MATCH (base:ToolDescription {
                tool_name: $tool_name,
                version: $base_version,
                environment: $environment
            })
            MATCH (new:ToolDescription {
                tool_name: $tool_name,
                version: $new_version,
                environment: $environment
            })
            CREATE (base)-[:EVOLVED_TO {
                created: datetime(),
                evolution_type: 'version_evolution',
                created_by: $created_by
            }]->(new)
            RETURN new.created as new_created
            """
            
            await self.driver.execute_query(
                evolution_query,
                tool_name=tool_name,
                base_version=base_version,
                new_version=new_version,
                environment=target_environment,
                created_by=created_by
            )
            
            logger.info(f"Created new version {tool_name} v{new_version} from v{base_version}")
            
            return {
                "status": "created",
                "enabled": True,
                "tool_name": tool_name,
                "base_version": base_version,
                "new_version": new_version,
                "environment": target_environment,
                "created_by": created_by,
                "base_effectiveness_score": base_result.records[0]["base_score"],
                "description_length": len(new_description)
            }
            
        except Exception as e:
            logger.error(f"Error creating version {tool_name} v{new_version}: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "tool_name": tool_name,
                "new_version": new_version
            }
    
    async def get_description_versions(
        self,
        tool_name: str,
        environment: Optional[str] = None,
        include_deprecated: bool = True
    ) -> Dict:
        """
        Get all versions of a tool description with their status and metrics.
        
        Provides comprehensive view of description evolution and performance.
        
        Args:
            tool_name: Name of the tool
            environment: Environment to query (defaults to manager environment)
            include_deprecated: Whether to include deprecated versions
            
        Returns:
            Dictionary with all versions and their details
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        target_environment = environment or self.environment
        
        try:
            # Build query based on whether to include deprecated
            if include_deprecated:
                status_filter = ""
            else:
                status_filter = "WHERE desc.status <> 'deprecated'"
            
            query = f"""
            MATCH (desc:ToolDescription {{
                tool_name: $tool_name,
                environment: $environment
            }})
            {status_filter}
            RETURN desc.version as version,
                   desc.status as status,
                   desc.effectiveness_score as effectiveness_score,
                   desc.access_count as access_count,
                   desc.confidence as confidence,
                   desc.created as created,
                   desc.last_accessed as last_accessed,
                   desc.created_by as created_by,
                   desc.deprecated_at as deprecated_at,
                   desc.deprecation_reason as deprecation_reason,
                   desc.reactivated_at as reactivated_at,
                   size(desc.description) as description_length
            ORDER BY desc.created DESC
            """
            
            result = await self.driver.execute_query(
                query,
                tool_name=tool_name,
                environment=target_environment
            )
            
            versions = []
            for record in result.records:
                version_info = {
                    "version": record["version"],
                    "status": record["status"],
                    "effectiveness_score": record["effectiveness_score"],
                    "access_count": record["access_count"],
                    "confidence": record["confidence"],
                    "created": record["created"].isoformat() if record["created"] else None,
                    "last_accessed": record["last_accessed"].isoformat() if record["last_accessed"] else None,
                    "created_by": record["created_by"],
                    "description_length": record["description_length"]
                }
                
                # Add deprecation info if relevant
                if record["deprecated_at"]:
                    version_info.update({
                        "deprecated_at": record["deprecated_at"].isoformat(),
                        "deprecation_reason": record["deprecation_reason"]
                    })
                
                # Add reactivation info if relevant
                if record["reactivated_at"]:
                    version_info["reactivated_at"] = record["reactivated_at"].isoformat()
                
                versions.append(version_info)
            
            # Get evolution relationships
            evolution_query = """
            MATCH (from:ToolDescription {tool_name: $tool_name, environment: $environment})
            -[rel:EVOLVED_TO]->
            (to:ToolDescription {tool_name: $tool_name, environment: $environment})
            RETURN from.version as from_version,
                   to.version as to_version,
                   rel.evolution_type as evolution_type,
                   rel.created as evolution_created,
                   rel.created_by as evolution_created_by
            ORDER BY rel.created DESC
            """
            
            evolution_result = await self.driver.execute_query(
                evolution_query,
                tool_name=tool_name,
                environment=target_environment
            )
            
            evolutions = [
                {
                    "from_version": record["from_version"],
                    "to_version": record["to_version"],
                    "evolution_type": record["evolution_type"],
                    "created": record["evolution_created"].isoformat() if record["evolution_created"] else None,
                    "created_by": record["evolution_created_by"]
                }
                for record in evolution_result.records
            ]
            
            return {
                "status": "success",
                "enabled": True,
                "tool_name": tool_name,
                "environment": target_environment,
                "versions": versions,
                "evolutions": evolutions,
                "summary": {
                    "total_versions": len(versions),
                    "active_versions": len([v for v in versions if v["status"] == "active"]),
                    "deprecated_versions": len([v for v in versions if v["status"] == "deprecated"]),
                    "testing_versions": len([v for v in versions if v["status"] == "testing"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting versions for {tool_name}: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "tool_name": tool_name
            }
    
    async def find_low_performing_descriptions(
        self,
        effectiveness_threshold: float = 0.3,
        access_threshold: int = 5,
        environment: Optional[str] = None
    ) -> Dict:
        """
        Find descriptions that are performing below thresholds and may need deprecation.
        
        Helps identify descriptions that should be reviewed for potential deprecation
        based on low effectiveness scores after sufficient usage.
        
        Args:
            effectiveness_threshold: Minimum effectiveness score (default 0.3)
            access_threshold: Minimum access count to consider (default 5)
            environment: Environment to analyze (defaults to manager environment)
            
        Returns:
            Dictionary with low-performing descriptions and recommendations
        """
        if not self.enabled:
            return {
                "status": "skipped",
                "reason": "Dynamic descriptions disabled",
                "enabled": False
            }
            
        target_environment = environment or self.environment
        
        try:
            query = """
            MATCH (desc:ToolDescription {
                environment: $environment,
                status: 'active'
            })
            WHERE desc.access_count >= $access_threshold 
            AND desc.effectiveness_score < $effectiveness_threshold
            RETURN desc.tool_name as tool_name,
                   desc.version as version,
                   desc.effectiveness_score as effectiveness_score,
                   desc.access_count as access_count,
                   desc.confidence as confidence,
                   desc.created as created,
                   desc.last_accessed as last_accessed,
                   desc.created_by as created_by
            ORDER BY desc.effectiveness_score ASC, desc.access_count DESC
            """
            
            result = await self.driver.execute_query(
                query,
                environment=target_environment,
                access_threshold=access_threshold,
                effectiveness_threshold=effectiveness_threshold
            )
            
            low_performing = []
            for record in result.records:
                desc_info = {
                    "tool_name": record["tool_name"],
                    "version": record["version"],
                    "effectiveness_score": record["effectiveness_score"],
                    "access_count": record["access_count"],
                    "confidence": record["confidence"],
                    "created": record["created"].isoformat() if record["created"] else None,
                    "last_accessed": record["last_accessed"].isoformat() if record["last_accessed"] else None,
                    "created_by": record["created_by"]
                }
                
                # Add recommendation based on performance
                if record["effectiveness_score"] < 0.1:
                    desc_info["recommendation"] = "immediate_deprecation"
                elif record["effectiveness_score"] < 0.2:
                    desc_info["recommendation"] = "deprecate_soon"
                else:
                    desc_info["recommendation"] = "monitor_closely"
                
                low_performing.append(desc_info)
            
            # Get summary statistics
            summary_query = """
            MATCH (desc:ToolDescription {environment: $environment, status: 'active'})
            RETURN count(desc) as total_active,
                   avg(desc.effectiveness_score) as avg_effectiveness,
                   count(CASE WHEN desc.effectiveness_score < $effectiveness_threshold THEN 1 END) as below_threshold,
                   count(CASE WHEN desc.access_count >= $access_threshold THEN 1 END) as sufficient_usage
            """
            
            summary_result = await self.driver.execute_query(
                summary_query,
                environment=target_environment,
                effectiveness_threshold=effectiveness_threshold,
                access_threshold=access_threshold
            )
            
            summary = summary_result.records[0] if summary_result.records else {}
            
            return {
                "status": "success",
                "enabled": True,
                "environment": target_environment,
                "thresholds": {
                    "effectiveness_threshold": effectiveness_threshold,
                    "access_threshold": access_threshold
                },
                "low_performing_descriptions": low_performing,
                "summary": {
                    "total_active_descriptions": summary.get("total_active", 0),
                    "average_effectiveness": summary.get("avg_effectiveness", 0.0),
                    "below_threshold_count": summary.get("below_threshold", 0),
                    "sufficient_usage_count": summary.get("sufficient_usage", 0),
                    "low_performing_count": len(low_performing)
                },
                "recommendations": {
                    "immediate_deprecation": len([d for d in low_performing if d.get("recommendation") == "immediate_deprecation"]),
                    "deprecate_soon": len([d for d in low_performing if d.get("recommendation") == "deprecate_soon"]),
                    "monitor_closely": len([d for d in low_performing if d.get("recommendation") == "monitor_closely"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error finding low performing descriptions: {e}")
            return {
                "status": "error",
                "enabled": self.enabled,
                "error": str(e),
                "environment": target_environment
            }
