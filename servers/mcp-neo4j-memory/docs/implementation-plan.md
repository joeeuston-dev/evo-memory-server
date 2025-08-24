# Dynamic Tool Descriptions - Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for the Dynamic Tool Descriptions feature. Each phase is designed to be completed incrementally with testing and validation.

## Phase 1: Foundation (Basic Storage and Retrieval)

### 1.1 Create Branch and Initial Setup
- [x] Create `feature/dynamic-tool-descriptions` branch
- [ ] Create basic file structure for new components
- [ ] Add configuration for dynamic descriptions feature flag

**Files to create:**
- `src/mcp_neo4j_memory/dynamic_descriptions.py` - Core manager class
- `src/mcp_neo4j_memory/description_schemas.py` - Data models
- `tests/test_dynamic_descriptions.py` - Test suite

**Estimated time:** 1 hour

### 1.2 Implement ToolDescription Data Model

**Create:** `src/mcp_neo4j_memory/description_schemas.py`

```python
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

class ToolDescriptionModel(BaseModel):
    tool_name: str
    version: str
    description: str
    effectiveness_score: float = 0.0
    access_count: int = 0
    created: datetime
    last_accessed: Optional[datetime] = None
    status: Literal["active", "testing", "deprecated"] = "active"
    confidence: float = 0.5
    environment: str = "production"
    created_by: Optional[str] = None

class DescriptionEvolution(BaseModel):
    from_version: str
    to_version: str
    evolution_type: Literal["evolved_to", "tested_against", "inspired_by"]
    reason: Optional[str] = None
```

**Estimated time:** 30 minutes

### 1.3 Implement Basic DynamicToolDescriptionManager

**Create:** `src/mcp_neo4j_memory/dynamic_descriptions.py`

```python
import asyncio
import logging
from typing import Dict, Optional
from neo4j import AsyncDriver
from .description_schemas import ToolDescriptionModel

logger = logging.getLogger(__name__)

class DynamicToolDescriptionManager:
    def __init__(self, driver: AsyncDriver, enabled: bool = True):
        self.driver = driver
        self.enabled = enabled
        self.fallback_descriptions = self._load_hardcoded_descriptions()
        
    def _load_hardcoded_descriptions(self) -> Dict[str, str]:
        """Load current hardcoded descriptions as fallback"""
        return {
            "search_memories": "**PRIMARY DISCOVERY TOOL**: Use this FIRST when user asks about past work, concepts, or relationships...",
            "read_graph": "**FULL CONTEXT TOOL**: Use ONLY when you need complete system state overview...",
            "create_entities": "**KNOWLEDGE CREATION TOOL**: Create new entities with evo metadata...",
            "create_relations": "**EVO STRENGTHENING TOOL**: Create relationships between entities...",
            "add_observations": "**EVO CONSOLIDATION TOOL**: Add new insights to existing entities...",
            "find_memories_by_name": "**DIRECT ACCESS TOOL**: Find specific entities by exact name...",
            "delete_entities": "Delete multiple entities and their associated relations.",
            "delete_observations": "Delete specific observations from entities.",
            "delete_relations": "Delete multiple relations from the graph."
        }
    
    async def get_tool_description(self, tool_name: str, environment: str = "production") -> str:
        """Get the most effective tool description, with fallback to hardcoded"""
        
        if not self.enabled:
            return self.fallback_descriptions.get(tool_name, f"Tool: {tool_name}")
        
        try:
            query = """
            MATCH (desc:ToolDescription {tool_name: $tool_name, environment: $environment, status: 'active'})
            RETURN desc.description as description, desc.effectiveness_score as score
            ORDER BY desc.effectiveness_score DESC
            LIMIT 1
            """
            
            result = await self.driver.execute_query(
                query, 
                tool_name=tool_name, 
                environment=environment
            )
            
            if result.records:
                # Trigger evo-strengthening
                await self._increment_access_count(tool_name, environment)
                return result.records[0]["description"]
            
        except Exception as e:
            logger.error(f"Error fetching dynamic description for {tool_name}: {e}")
        
        # Fallback to hardcoded descriptions
        return self.fallback_descriptions.get(tool_name, f"Tool: {tool_name}")
    
    async def _increment_access_count(self, tool_name: str, environment: str):
        """Evo-strengthening: increment access count and update last_accessed"""
        try:
            query = """
            MATCH (desc:ToolDescription {tool_name: $tool_name, environment: $environment, status: 'active'})
            SET desc.access_count = desc.access_count + 1,
                desc.last_accessed = datetime()
            RETURN desc.access_count as new_count
            """
            await self.driver.execute_query(query, tool_name=tool_name, environment=environment)
        except Exception as e:
            logger.error(f"Error incrementing access count for {tool_name}: {e}")
    
    async def create_tool_description(self, description: ToolDescriptionModel) -> bool:
        """Create a new tool description in Neo4j"""
        try:
            query = """
            CREATE (desc:ToolDescription {
                tool_name: $tool_name,
                version: $version,
                description: $description,
                effectiveness_score: $effectiveness_score,
                access_count: $access_count,
                created: datetime($created),
                last_accessed: CASE WHEN $last_accessed IS NOT NULL THEN datetime($last_accessed) ELSE NULL END,
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
            
            return len(result.records) > 0
            
        except Exception as e:
            logger.error(f"Error creating tool description: {e}")
            return False
```

**Estimated time:** 2 hours

### 1.4 Add Configuration Support

**Update:** `src/mcp_neo4j_memory/utils.py`

```python
# Add to existing config processing
def process_config(args):
    config = {
        # ... existing config ...
        
        # Dynamic descriptions configuration
        "dynamic_descriptions_enabled": os.getenv("DYNAMIC_DESCRIPTIONS_ENABLED", "false").lower() == "true",
        "description_environment": os.getenv("DESCRIPTION_ENVIRONMENT", "production"),
        "effectiveness_threshold": float(os.getenv("EFFECTIVENESS_THRESHOLD", "0.75")),
    }
    
    # Override with command line args if provided
    if hasattr(args, 'dynamic_descriptions') and args.dynamic_descriptions is not None:
        config["dynamic_descriptions_enabled"] = args.dynamic_descriptions
        
    return config
```

**Add command line arguments:** Update `src/mcp_neo4j_memory/__init__.py`

```python
def main():
    parser = argparse.ArgumentParser(description='Neo4j Memory MCP Server')
    # ... existing arguments ...
    parser.add_argument("--dynamic-descriptions", action="store_true", 
                       help="Enable dynamic tool descriptions from Neo4j")
    parser.add_argument("--description-environment", default=None, 
                       help="Environment for description selection (dev/staging/production)")
```

**Estimated time:** 30 minutes

### 1.5 Basic Integration with Server

**Update:** `src/mcp_neo4j_memory/server.py`

```python
from .dynamic_descriptions import DynamicToolDescriptionManager

# Add to server initialization
description_manager = None

async def serve():
    global description_manager
    
    # ... existing Neo4j setup ...
    
    # Initialize dynamic descriptions manager
    description_manager = DynamicToolDescriptionManager(
        driver=driver,
        enabled=config.get("dynamic_descriptions_enabled", False)
    )
    
    # ... rest of server setup ...
```

**Estimated time:** 1 hour

### 1.6 Basic Testing

**Create:** `tests/test_dynamic_descriptions.py`

```python
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from mcp_neo4j_memory.dynamic_descriptions import DynamicToolDescriptionManager
from mcp_neo4j_memory.description_schemas import ToolDescriptionModel

@pytest.fixture
def mock_driver():
    driver = AsyncMock()
    return driver

@pytest.fixture
def description_manager(mock_driver):
    return DynamicToolDescriptionManager(driver=mock_driver, enabled=True)

@pytest.mark.asyncio
async def test_fallback_when_disabled():
    """Test that hardcoded descriptions are used when disabled"""
    disabled_manager = DynamicToolDescriptionManager(driver=None, enabled=False)
    description = await disabled_manager.get_tool_description("search_memories")
    assert "PRIMARY DISCOVERY TOOL" in description

@pytest.mark.asyncio
async def test_neo4j_description_retrieval(description_manager, mock_driver):
    """Test retrieving description from Neo4j"""
    # Mock Neo4j response
    mock_result = MagicMock()
    mock_result.records = [{"description": "Dynamic description from Neo4j", "score": 0.85}]
    mock_driver.execute_query.return_value = mock_result
    
    description = await description_manager.get_tool_description("search_memories")
    assert description == "Dynamic description from Neo4j"
    
    # Verify access count increment was called
    assert mock_driver.execute_query.call_count == 2  # One for retrieval, one for increment

@pytest.mark.asyncio
async def test_fallback_on_error(description_manager, mock_driver):
    """Test fallback to hardcoded when Neo4j fails"""
    mock_driver.execute_query.side_effect = Exception("Neo4j connection failed")
    
    description = await description_manager.get_tool_description("search_memories")
    assert "PRIMARY DISCOVERY TOOL" in description
```

**Run tests:**
```bash
cd /Users/jeuston/SOURCE/evo-memory-server/servers/mcp-neo4j-memory
pytest tests/test_dynamic_descriptions.py -v
```

**Estimated time:** 1.5 hours

## Phase 2: Evo-Memory Integration

### 2.1 Schema Creation and Constraints

**Create:** `src/mcp_neo4j_memory/schema_setup.py`

```python
async def setup_dynamic_descriptions_schema(driver):
    """Create Neo4j schema for dynamic tool descriptions"""
    
    constraints_and_indexes = [
        # Unique constraint for tool descriptions
        """
        CREATE CONSTRAINT tool_description_unique IF NOT EXISTS
        FOR (td:ToolDescription) 
        REQUIRE (td.tool_name, td.version, td.environment) IS UNIQUE
        """,
        
        # Index for efficient lookups
        """
        CREATE INDEX tool_description_lookup IF NOT EXISTS
        FOR (td:ToolDescription) 
        ON (td.tool_name, td.environment, td.status)
        """,
        
        # Index for effectiveness sorting
        """
        CREATE INDEX effectiveness_score_index IF NOT EXISTS
        FOR (td:ToolDescription)
        ON td.effectiveness_score
        """,
        
        # Index for access pattern analysis
        """
        CREATE INDEX access_count_index IF NOT EXISTS
        FOR (td:ToolDescription)
        ON td.access_count
        """
    ]
    
    for statement in constraints_and_indexes:
        try:
            await driver.execute_query(statement)
            print(f"✅ Schema statement executed successfully")
        except Exception as e:
            print(f"⚠️  Schema statement failed (may already exist): {e}")
```

**Estimated time:** 45 minutes

### 2.2 Seed Initial Descriptions

**Create:** `src/mcp_neo4j_memory/seed_descriptions.py`

```python
from datetime import datetime
from .description_schemas import ToolDescriptionModel

async def seed_initial_descriptions(description_manager: DynamicToolDescriptionManager):
    """Seed Neo4j with current hardcoded descriptions as version 1.0"""
    
    initial_descriptions = [
        ToolDescriptionModel(
            tool_name="search_memories",
            version="1.0",
            description="**PRIMARY DISCOVERY TOOL**: Use this FIRST when user asks about past work, concepts, or relationships. Performs evo-memory discovery through relationship traversal and semantic search rather than full graph reads. Triggers evo strengthening on accessed knowledge. WHEN TO USE: 'What did we work on yesterday?', 'Tell me about X', 'How does Y relate to Z?', 'What do I know about...?'",
            effectiveness_score=0.8,
            created=datetime.now(),
            confidence=0.9,
            created_by="system_migration"
        ),
        
        ToolDescriptionModel(
            tool_name="create_entities",
            version="1.0", 
            description="**KNOWLEDGE CREATION TOOL**: Create new entities with evo metadata (access_count, confidence, created timestamp). Always include evo metadata and meaningful observations. WHEN TO USE: Learning new concepts, storing insights, capturing project knowledge. Include relationships to existing entities for knowledge integration.",
            effectiveness_score=0.75,
            created=datetime.now(),
            confidence=0.9,
            created_by="system_migration"
        ),
        
        # Add all current tools...
    ]
    
    for desc in initial_descriptions:
        success = await description_manager.create_tool_description(desc)
        if success:
            print(f"✅ Seeded description for {desc.tool_name} v{desc.version}")
        else:
            print(f"❌ Failed to seed {desc.tool_name} v{desc.version}")
```

**Estimated time:** 1 hour

### 2.3 Effectiveness Tracking

**Add to:** `src/mcp_neo4j_memory/dynamic_descriptions.py`

```python
async def record_effectiveness(self, tool_name: str, environment: str, 
                              success: bool, context: Optional[str] = None):
    """Record whether a tool usage was effective for evo-strengthening"""
    
    try:
        # Update effectiveness score based on success/failure
        adjustment = 0.05 if success else -0.02
        
        query = """
        MATCH (desc:ToolDescription {tool_name: $tool_name, environment: $environment, status: 'active'})
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
        RETURN desc.effectiveness_score as new_score
        """
        
        await self.driver.execute_query(
            query, 
            tool_name=tool_name, 
            environment=environment,
            adjustment=adjustment
        )
        
    except Exception as e:
        logger.error(f"Error recording effectiveness for {tool_name}: {e}")
```

**Estimated time:** 1 hour

## Phase 3: Full Integration and Testing

### 3.1 Dynamic Tool Registration

**Update:** `src/mcp_neo4j_memory/server.py`

```python
async def register_tools_with_dynamic_descriptions():
    """Register all tools with dynamic descriptions"""
    
    if description_manager and description_manager.enabled:
        # Update tool docstrings dynamically
        search_memories.__doc__ = await description_manager.get_tool_description("search_memories")
        create_entities.__doc__ = await description_manager.get_tool_description("create_entities")
        create_relations.__doc__ = await description_manager.get_tool_description("create_relations")
        add_observations.__doc__ = await description_manager.get_tool_description("add_observations")
        find_memories_by_name.__doc__ = await description_manager.get_tool_description("find_memories_by_name")
        read_graph.__doc__ = await description_manager.get_tool_description("read_graph")
        delete_entities.__doc__ = await description_manager.get_tool_description("delete_entities")
        delete_observations.__doc__ = await description_manager.get_tool_description("delete_observations")
        delete_relations.__doc__ = await description_manager.get_tool_description("delete_relations")

# Call during server initialization
async def serve():
    # ... existing setup ...
    
    # Register tools with dynamic descriptions
    await register_tools_with_dynamic_descriptions()
    
    # ... start server ...
```

**Estimated time:** 1 hour

### 3.2 Management Tools

**Add new tools for managing descriptions:**

```python
@app.tool()
async def create_tool_description(
    tool_name: str,
    version: str, 
    description: str,
    environment: str = "production"
) -> dict:
    """Create a new tool description version in Neo4j"""
    
    if not description_manager or not description_manager.enabled:
        return {"error": "Dynamic descriptions not enabled"}
    
    desc_model = ToolDescriptionModel(
        tool_name=tool_name,
        version=version,
        description=description,
        created=datetime.now(),
        environment=environment,
        created_by="user"
    )
    
    success = await description_manager.create_tool_description(desc_model)
    
    if success:
        return {"success": True, "message": f"Created description for {tool_name} v{version}"}
    else:
        return {"error": "Failed to create tool description"}

@app.tool()
async def list_tool_descriptions(tool_name: Optional[str] = None) -> dict:
    """List all tool descriptions, optionally filtered by tool name"""
    
    if not description_manager or not description_manager.enabled:
        return {"error": "Dynamic descriptions not enabled"}
    
    query = """
    MATCH (desc:ToolDescription)
    WHERE CASE WHEN $tool_name IS NOT NULL THEN desc.tool_name = $tool_name ELSE true END
    RETURN desc.tool_name as tool_name, desc.version as version, 
           desc.effectiveness_score as effectiveness, desc.access_count as access_count,
           desc.status as status, desc.environment as environment
    ORDER BY desc.tool_name, desc.effectiveness_score DESC
    """
    
    try:
        result = await description_manager.driver.execute_query(query, tool_name=tool_name)
        descriptions = [dict(record) for record in result.records]
        return {"descriptions": descriptions}
    except Exception as e:
        return {"error": f"Failed to list descriptions: {e}"}
```

**Estimated time:** 2 hours

### 3.3 Comprehensive Testing

**Create end-to-end tests:**

```python
@pytest.mark.asyncio
async def test_dynamic_description_flow():
    """Test complete flow: create description, use tool, track effectiveness"""
    
    # Test will require actual Neo4j instance or testcontainers
    # This ensures the full integration works correctly
    pass

@pytest.mark.asyncio
async def test_effectiveness_evolution():
    """Test that effectiveness scores evolve based on usage"""
    pass

@pytest.mark.asyncio 
async def test_version_management():
    """Test creating multiple versions and selection logic"""
    pass
```

**Estimated time:** 3 hours

## Phase 4: Documentation and Deployment

### 4.1 User Documentation

**Create:** `docs/using-dynamic-descriptions.md`

- How to enable the feature
- Creating and managing descriptions
- Best practices for description writing
- Effectiveness tracking and optimization

**Estimated time:** 2 hours

### 4.2 Migration Guide

**Create:** `docs/migration-to-dynamic-descriptions.md`

- Step-by-step migration from hardcoded descriptions
- Backup and rollback procedures
- Troubleshooting common issues

**Estimated time:** 1.5 hours

## Total Estimated Time

**Phase 1:** 6 hours
**Phase 2:** 2.75 hours  
**Phase 3:** 6 hours
**Phase 4:** 3.5 hours

**Total:** ~18 hours of development work

## Risk Mitigation

### Technical Risks
1. **Neo4j dependency**: Always maintain hardcoded fallbacks
2. **Performance impact**: Cache frequently accessed descriptions
3. **Concurrency issues**: Use proper locking for description updates

### Operational Risks
1. **Description corruption**: Version control and rollback capability
2. **Effectiveness degradation**: Automatic rollback triggers
3. **Team conflicts**: Clear ownership and approval processes

## Success Criteria

### Phase 1 Complete When:
- [ ] Basic description retrieval working
- [ ] Fallback to hardcoded descriptions working
- [ ] Configuration system in place
- [ ] Basic tests passing

### Phase 2 Complete When:
- [ ] Evo-memory metadata tracking active
- [ ] Effectiveness scoring implemented
- [ ] Schema and constraints created
- [ ] Initial descriptions seeded

### Phase 3 Complete When:
- [ ] All tools using dynamic descriptions
- [ ] Management tools available
- [ ] Full test suite passing
- [ ] Performance acceptable

### Phase 4 Complete When:
- [ ] Documentation complete
- [ ] Migration procedures tested
- [ ] Feature ready for team use

This implementation plan provides a structured approach to building the dynamic tool descriptions feature while maintaining system reliability and enabling incremental testing.
