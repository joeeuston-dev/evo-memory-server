"""
Tests for dynamic tool descriptions functionality.

This module tests the DynamicToolDescriptionManager and related components
to ensure proper functionality of Neo4j-stored tool descriptions with
evo-memory patterns.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from mcp_neo4j_memory.dynamic_descriptions import DynamicToolDescriptionManager
from mcp_neo4j_memory.description_schemas import ToolDescriptionModel


@pytest.fixture
def mock_driver():
    """Mock Neo4j driver for testing."""
    driver = AsyncMock()
    return driver


@pytest.fixture
def description_manager(mock_driver):
    """Create a DynamicToolDescriptionManager with mocked driver."""
    return DynamicToolDescriptionManager(driver=mock_driver, enabled=True)


@pytest.fixture
def disabled_description_manager(mock_driver):
    """Create a disabled DynamicToolDescriptionManager for testing fallback."""
    return DynamicToolDescriptionManager(driver=mock_driver, enabled=False)


@pytest.fixture
def sample_tool_description():
    """Sample tool description model for testing."""
    return ToolDescriptionModel(
        tool_name="search_memories",
        version="2.0",
        description="Enhanced search tool with improved effectiveness",
        effectiveness_score=0.85,
        access_count=0,
        created=datetime.now(),
        status="active",
        confidence=0.9,
        environment="production",
        created_by="test_user"
    )


class TestDynamicToolDescriptionManager:
    """Test cases for DynamicToolDescriptionManager."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_initialization(self, mock_driver):
        """Test proper initialization of DynamicToolDescriptionManager."""
        manager = DynamicToolDescriptionManager(
            driver=mock_driver, 
            enabled=True, 
            environment="staging"
        )
        
        assert manager.enabled is True
        assert manager.environment == "staging"
        assert manager.driver == mock_driver
        assert len(manager.fallback_descriptions) > 0
        assert "search_memories" in manager.fallback_descriptions
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_fallback_when_disabled(self, disabled_description_manager):
        """Test that hardcoded descriptions are used when disabled."""
        description = await disabled_description_manager.get_tool_description("search_memories")
        
        assert "PRIMARY DISCOVERY TOOL" in description
        assert disabled_description_manager.enabled is False
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_neo4j_description_retrieval(self, description_manager, mock_driver):
        """Test retrieving description from Neo4j."""
        # Mock Neo4j responses - need two different responses for retrieval and increment
        retrieval_result = MagicMock()
        retrieval_result.records = [{
            "description": "Dynamic description from Neo4j", 
            "score": 0.85,
            "version": "2.0"
        }]
        
        increment_result = MagicMock()
        increment_result.records = [{"new_count": 1}]
        
        # Set up side effects for multiple calls
        mock_driver.execute_query.side_effect = [retrieval_result, increment_result]
        
        description = await description_manager.get_tool_description("search_memories")
        
        assert description == "Dynamic description from Neo4j"
        
        # Wait a bit for the async task to complete
        await asyncio.sleep(0.01)
        
        # Verify queries were called (one for retrieval, one for access count increment)
        assert mock_driver.execute_query.call_count == 2
        
        # Verify the retrieval query was called correctly
        retrieval_call = mock_driver.execute_query.call_args_list[0]
        assert "MATCH (desc:ToolDescription" in retrieval_call[0][0]
        assert retrieval_call[1]["tool_name"] == "search_memories"
        assert retrieval_call[1]["environment"] == "production"
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_fallback_on_error(self, description_manager, mock_driver):
        """Test fallback to hardcoded when Neo4j fails."""
        mock_driver.execute_query.side_effect = Exception("Neo4j connection failed")
        
        description = await description_manager.get_tool_description("search_memories")
        
        assert "PRIMARY DISCOVERY TOOL" in description
        assert mock_driver.execute_query.call_count == 1  # Only one call before exception
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_fallback_on_no_results(self, description_manager, mock_driver):
        """Test fallback when no dynamic descriptions found."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.records = []
        mock_driver.execute_query.return_value = mock_result
        
        description = await description_manager.get_tool_description("search_memories")
        
        assert "PRIMARY DISCOVERY TOOL" in description
        assert mock_driver.execute_query.call_count == 1  # Only retrieval query
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_tool_description(self, description_manager, mock_driver, sample_tool_description):
        """Test creating a new tool description."""
        # Mock successful creation
        mock_result = MagicMock()
        mock_result.records = [{"created": "search_memories"}]
        mock_driver.execute_query.return_value = mock_result
        
        success = await description_manager.create_tool_description(sample_tool_description)
        
        assert success is True
        assert mock_driver.execute_query.call_count == 1
        
        # Verify the creation query
        call_args = mock_driver.execute_query.call_args
        assert "CREATE (desc:ToolDescription" in call_args[0][0]
        assert call_args[1]["tool_name"] == "search_memories"
        assert call_args[1]["version"] == "2.0"
        assert call_args[1]["effectiveness_score"] == 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_tool_description_failure(self, description_manager, mock_driver, sample_tool_description):
        """Test handling of tool description creation failure."""
        mock_driver.execute_query.side_effect = Exception("Database error")
        
        success = await description_manager.create_tool_description(sample_tool_description)
        
        assert success is False
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_list_tool_descriptions(self, description_manager, mock_driver):
        """Test listing tool descriptions with filtering."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.records = [
            {
                "tool_name": "search_memories",
                "version": "2.0", 
                "effectiveness_score": 0.85,
                "access_count": 10,
                "status": "active",
                "environment": "production",
                "confidence": 0.9,
                "created": datetime.now(),
                "last_accessed": datetime.now(),
                "created_by": "test_user"
            }
        ]
        mock_driver.execute_query.return_value = mock_result
        
        descriptions = await description_manager.list_tool_descriptions(tool_name="search_memories")
        
        assert len(descriptions) == 1
        assert descriptions[0]["tool_name"] == "search_memories"
        assert descriptions[0]["effectiveness_score"] == 0.85
        
        # Verify query parameters
        call_args = mock_driver.execute_query.call_args
        assert call_args[1]["tool_name"] == "search_memories"
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_record_effectiveness(self, description_manager, mock_driver):
        """Test recording effectiveness for evo-strengthening."""
        # Mock successful update
        mock_result = MagicMock()
        mock_result.records = [{"new_score": 0.9, "version": "2.0"}]
        mock_driver.execute_query.return_value = mock_result
        
        await description_manager.record_effectiveness(
            tool_name="search_memories",
            success=True,
            context="User found relevant information"
        )
        
        assert mock_driver.execute_query.call_count == 1
        
        # Verify the effectiveness update query
        call_args = mock_driver.execute_query.call_args
        assert "SET desc.effectiveness_score" in call_args[0][0]
        assert call_args[1]["adjustment"] == 0.05  # Success adjustment
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_record_effectiveness_failure(self, description_manager, mock_driver):
        """Test recording effectiveness for failed usage."""
        mock_result = MagicMock()
        mock_result.records = [{"new_score": 0.75, "version": "2.0"}]
        mock_driver.execute_query.return_value = mock_result
        
        await description_manager.record_effectiveness(
            tool_name="search_memories",
            success=False,
            context="Tool selection was inappropriate"
        )
        
        call_args = mock_driver.execute_query.call_args
        assert call_args[1]["adjustment"] == -0.02  # Failure adjustment
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_disabled(self, disabled_description_manager):
        """Test health check when dynamic descriptions are disabled."""
        health = await disabled_description_manager.health_check()
        
        assert health["status"] == "disabled"
        assert health["enabled"] is False
        assert "fallback_descriptions_count" in health
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, description_manager, mock_driver):
        """Test health check with active descriptions."""
        mock_result = MagicMock()
        mock_result.records = [{
            "active_count": 5,
            "environments": ["production", "staging"],
            "tools": ["search_memories", "create_entities"]
        }]
        mock_driver.execute_query.return_value = mock_result
        
        health = await description_manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["enabled"] is True
        assert health["active_descriptions"] == 5
        assert "production" in health["environments"]
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_health_check_error(self, description_manager, mock_driver):
        """Test health check when Neo4j query fails."""
        mock_driver.execute_query.side_effect = Exception("Connection failed")
        
        health = await description_manager.health_check()
        
        assert health["status"] == "error"
        assert "error" in health
    
    def test_get_hardcoded_description(self, description_manager):
        """Test getting hardcoded fallback descriptions."""
        description = description_manager.get_hardcoded_description("search_memories")
        assert description is not None
        assert "PRIMARY DISCOVERY TOOL" in description
        
        # Test non-existent tool
        description = description_manager.get_hardcoded_description("non_existent_tool")
        assert description is None
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_environment_override(self, description_manager, mock_driver):
        """Test environment override in get_tool_description."""
        mock_result = MagicMock()
        mock_result.records = [{
            "description": "Staging description",
            "score": 0.8,
            "version": "2.0-staging"
        }]
        mock_driver.execute_query.return_value = mock_result
        
        # Override environment
        description = await description_manager.get_tool_description(
            "search_memories", 
            environment="staging"
        )
        
        assert description == "Staging description"
        
        # Verify environment parameter in query
        call_args = mock_driver.execute_query.call_args_list[0]
        assert call_args[1]["environment"] == "staging"


class TestToolDescriptionModel:
    """Test cases for ToolDescriptionModel."""
    
    def test_model_creation(self):
        """Test creating a ToolDescriptionModel."""
        model = ToolDescriptionModel(
            tool_name="test_tool",
            version="1.0",
            description="Test description"
        )
        
        assert model.tool_name == "test_tool"
        assert model.version == "1.0"
        assert model.description == "Test description"
        assert model.effectiveness_score == 0.0  # Default
        assert model.status == "active"  # Default
        assert model.environment == "production"  # Default
    
    def test_model_validation(self):
        """Test model validation constraints."""
        # Test effectiveness_score bounds
        with pytest.raises(ValueError):
            ToolDescriptionModel(
                tool_name="test",
                version="1.0", 
                description="test",
                effectiveness_score=-0.1  # Below 0
            )
        
        with pytest.raises(ValueError):
            ToolDescriptionModel(
                tool_name="test",
                version="1.0",
                description="test", 
                effectiveness_score=1.1  # Above 1
            )
    
    def test_model_json_encoding(self):
        """Test JSON encoding with datetime fields."""
        model = ToolDescriptionModel(
            tool_name="test_tool",
            version="1.0",
            description="Test description",
            created=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        # Should not raise an exception
        json_data = model.model_dump_json()
        assert "2024-01-01T12:00:00" in json_data


# Integration test fixtures and tests would go here
# These would require a real Neo4j instance or testcontainers
class TestPhase2SchemaManagement:
    """Test Phase 2 schema management functionality."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver."""
        driver = AsyncMock()
        driver.execute_query = AsyncMock()
        return driver
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_setup_schema_disabled(self, mock_driver):
        """Test schema setup when dynamic descriptions are disabled."""
        manager = DynamicToolDescriptionManager(mock_driver, enabled=False)
        
        result = await manager.setup_schema()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "Dynamic descriptions disabled"
        assert result["enabled"] is False
        mock_driver.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_setup_schema_success(self, mock_driver):
        """Test successful schema setup."""
        mock_driver.execute_query.return_value = AsyncMock()
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.setup_schema()
        
        assert result["status"] == "success"
        assert result["enabled"] is True
        assert result["total_operations"] == 5
        assert len(result["operations"]) == 5
        
        # Verify all expected operations
        operations = [op["operation"] for op in result["operations"]]
        assert "unique_constraint" in operations
        assert "index" in operations
        assert "compound_index" in operations
        
        # Should have made 5 calls to execute_query (constraint + 4 indexes)
        assert mock_driver.execute_query.call_count == 5
    
    @pytest.mark.asyncio
    async def test_setup_schema_error(self, mock_driver):
        """Test schema setup with database error."""
        mock_driver.execute_query.side_effect = Exception("Database connection failed")
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.setup_schema()
        
        assert result["status"] == "error"
        assert result["enabled"] is True
        assert "Database connection failed" in result["error"]
        assert result["operations"] == []
    
    @pytest.mark.asyncio
    async def test_get_schema_info_disabled(self, mock_driver):
        """Test schema info when disabled."""
        manager = DynamicToolDescriptionManager(mock_driver, enabled=False)
        
        result = await manager.get_schema_info()
        
        assert result["status"] == "disabled"
        assert result["enabled"] is False
        mock_driver.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_schema_info_success(self, mock_driver):
        """Test successful schema info retrieval."""
        # Mock constraints query result
        constraints_result = AsyncMock()
        constraints_result.records = [
            {"name": "tool_description_unique", "type": "UNIQUENESS", "properties": ["tool_name", "version", "environment"]}
        ]
        
        # Mock indexes query result  
        indexes_result = AsyncMock()
        indexes_result.records = [
            {"name": "tool_description_name_idx", "type": "RANGE", "properties": ["tool_name"]},
            {"name": "tool_description_env_idx", "type": "RANGE", "properties": ["environment"]}
        ]
        
        # Mock count query result
        count_result = AsyncMock()
        count_result.records = [
            {"total_descriptions": 10, "unique_tools": 5, "environments": 2}
        ]
        
        mock_driver.execute_query.side_effect = [constraints_result, indexes_result, count_result]
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.get_schema_info()
        
        assert result["status"] == "success"
        assert result["enabled"] is True
        assert len(result["constraints"]) == 1
        assert len(result["indexes"]) == 2
        assert result["statistics"]["total_descriptions"] == 10
        assert result["statistics"]["unique_tools"] == 5
        assert result["statistics"]["environments"] == 2
        
        # Should have made 3 queries
        assert mock_driver.execute_query.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_schema_info_error(self, mock_driver):
        """Test schema info with database error."""
        mock_driver.execute_query.side_effect = Exception("Query failed")
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.get_schema_info()
        
        assert result["status"] == "error"
        assert result["enabled"] is True
        assert "Query failed" in result["error"]


class TestPhase2Seeding:
    """Test Phase 2 seeding functionality."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver."""
        driver = AsyncMock()
        driver.execute_query = AsyncMock()
        return driver
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_disabled(self, mock_driver):
        """Test seeding when dynamic descriptions are disabled."""
        manager = DynamicToolDescriptionManager(mock_driver, enabled=False)
        
        result = await manager.seed_initial_descriptions()
        
        assert result["status"] == "skipped"
        assert result["reason"] == "Dynamic descriptions disabled"
        assert result["enabled"] is False
        mock_driver.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_success(self, mock_driver):
        """Test successful seeding of initial descriptions."""
        # Mock check existing - return False (no existing descriptions)
        check_result = AsyncMock()
        check_result.records = [{"count": 0}]
        
        # Mock create result - return success
        create_result = AsyncMock()
        create_result.records = [{"created": "read_graph"}]
        
        # Set up side_effect for multiple calls
        mock_driver.execute_query.side_effect = [
            check_result, create_result,  # read_graph
            check_result, create_result,  # create_entities  
            check_result, create_result,  # create_relations
            check_result, create_result,  # add_observations
            check_result, create_result,  # delete_entities
            check_result, create_result,  # delete_observations
            check_result, create_result,  # delete_relations
            check_result, create_result,  # search_memories
            check_result, create_result,  # find_memories_by_name
        ]
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.seed_initial_descriptions()
        
        assert result["status"] == "completed"
        assert result["enabled"] is True
        assert result["summary"]["total_tools"] == len(manager.fallback_descriptions)
        assert result["summary"]["created_count"] > 0
        assert result["summary"]["skipped_count"] == 0
        assert result["summary"]["failed_count"] == 0
        assert len(result["created"]) > 0
        
        # Each tool requires 2 calls: check existing + create
        expected_calls = len(manager.fallback_descriptions) * 2
        assert mock_driver.execute_query.call_count == expected_calls
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_with_existing(self, mock_driver):
        """Test seeding when some descriptions already exist."""
        # Mock check existing - first tool exists, second doesn't
        existing_result = AsyncMock()
        existing_result.records = [{"count": 1}]
        
        new_result = AsyncMock()  
        new_result.records = [{"count": 0}]
        
        create_result = AsyncMock()
        create_result.records = [{"created": "tool"}]
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        # First tool exists, rest are new
        side_effects = [existing_result]  # First check returns existing
        for _ in range(len(manager.fallback_descriptions) - 1):
            side_effects.extend([new_result, create_result])  # Rest are new + created
        
        mock_driver.execute_query.side_effect = side_effects
        
        result = await manager.seed_initial_descriptions(overwrite=False)
        
        assert result["status"] == "completed"
        assert result["summary"]["skipped_count"] == 1
        assert result["summary"]["created_count"] == len(manager.fallback_descriptions) - 1
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_with_overwrite(self, mock_driver):
        """Test seeding with overwrite enabled."""
        # Mock all as existing but should still create due to overwrite
        existing_result = AsyncMock()
        existing_result.records = [{"count": 1}]
        
        create_result = AsyncMock()
        create_result.records = [{"created": "tool"}]
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        # All tools exist but we'll overwrite
        side_effects = []
        for _ in range(len(manager.fallback_descriptions)):
            side_effects.extend([existing_result, create_result])
        
        mock_driver.execute_query.side_effect = side_effects
        
        result = await manager.seed_initial_descriptions(overwrite=True)
        
        assert result["status"] == "completed"
        assert result["summary"]["skipped_count"] == 0
        assert result["summary"]["created_count"] == len(manager.fallback_descriptions)
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_creation_failure(self, mock_driver):
        """Test seeding when creation fails."""
        # Mock check existing - no existing descriptions
        check_result = AsyncMock()
        check_result.records = [{"count": 0}]
        
        # Mock create result - return empty (failure)
        create_result = AsyncMock()
        create_result.records = []
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        mock_driver.execute_query.side_effect = [check_result, create_result] * len(manager.fallback_descriptions)
        
        result = await manager.seed_initial_descriptions()
        
        assert result["status"] == "completed"
        assert result["summary"]["created_count"] == 0
        assert result["summary"]["failed_count"] == len(manager.fallback_descriptions)
    
    @pytest.mark.asyncio
    async def test_seed_initial_descriptions_database_error(self, mock_driver):
        """Test seeding with database error - individual tools fail but process completes."""
        mock_driver.execute_query.side_effect = Exception("Database error")
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        result = await manager.seed_initial_descriptions()
        
        # Individual tool failures result in "completed" status with failed tools tracked
        assert result["status"] == "completed"
        assert result["enabled"] is True
        assert result["summary"]["failed_count"] == len(manager.fallback_descriptions)
        assert result["summary"]["created_count"] == 0
        assert len(result["failed"]) == len(manager.fallback_descriptions)
    
    @pytest.mark.asyncio
    async def test_check_existing_description_success(self, mock_driver):
        """Test checking existing description."""
        result = AsyncMock()
        result.records = [{"count": 1}]
        mock_driver.execute_query.return_value = result
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        exists = await manager._check_existing_description("test_tool", "1.0", "production")
        
        assert exists is True
        mock_driver.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_existing_description_not_found(self, mock_driver):
        """Test checking non-existing description."""
        result = AsyncMock()
        result.records = [{"count": 0}]
        mock_driver.execute_query.return_value = result
        
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        exists = await manager._check_existing_description("test_tool", "1.0", "production")
        
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_check_existing_description_error(self, mock_driver):
        """Test checking existing description with error."""
        mock_driver.execute_query.side_effect = Exception("Query error")
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True)
        
        exists = await manager._check_existing_description("test_tool", "1.0", "production")
        
        assert exists is False


class TestPhase3LifecycleManagement:
    """Test Phase 3: Description Lifecycle Management methods."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager for Phase 3 tests."""
        mock_driver = AsyncMock()
        manager = DynamicToolDescriptionManager(mock_driver, enabled=True, environment="test")
        return manager, mock_driver
    
    # Test deprecation functionality
    
    @pytest.mark.asyncio
    async def test_mark_description_deprecated_disabled(self):
        """Test deprecation when manager is disabled."""
        mock_driver = AsyncMock()
        manager = DynamicToolDescriptionManager(mock_driver, enabled=False)
        
        result = await manager.mark_tool_description_deprecated(
            "test_tool", "1.0", "ineffective"
        )
        
        assert result["status"] == "skipped"
        assert result["reason"] == "Dynamic descriptions disabled"
        assert not result["enabled"]
        mock_driver.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mark_description_deprecated_success(self, mock_manager):
        """Test successful description deprecation."""
        manager, mock_driver = mock_manager
        
        # Mock check query result - description exists and is active
        check_result = MagicMock()
        check_result.records = [{"current_status": "active", "deprecated_at": None}]
        
        # Mock deprecate query result
        deprecate_result = MagicMock()
        deprecate_result.records = [{
            "deprecated_at": datetime.now(),
            "final_score": 0.4
        }]
        
        mock_driver.execute_query.side_effect = [check_result, deprecate_result]
        
        result = await manager.mark_tool_description_deprecated(
            "test_tool", "1.0", "ineffective", "test_user"
        )
        
        assert result["status"] == "deprecated"
        assert result["tool_name"] == "test_tool"
        assert result["version"] == "1.0"
        assert result["reason"] == "ineffective"
        assert result["deprecated_by"] == "test_user"
        assert result["final_effectiveness_score"] == 0.4
        assert mock_driver.execute_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_mark_description_deprecated_not_found(self, mock_manager):
        """Test deprecation when description doesn't exist."""
        manager, mock_driver = mock_manager
        
        # Mock empty result
        check_result = MagicMock()
        check_result.records = []
        mock_driver.execute_query.return_value = check_result
        
        result = await manager.mark_tool_description_deprecated(
            "nonexistent_tool", "1.0", "ineffective"
        )
        
        assert result["status"] == "not_found"
        assert result["tool_name"] == "nonexistent_tool"
        assert result["version"] == "1.0"
        assert mock_driver.execute_query.call_count == 1
    
    @pytest.mark.asyncio
    async def test_mark_description_deprecated_already_deprecated(self, mock_manager):
        """Test deprecation when description is already deprecated."""
        manager, mock_driver = mock_manager
        
        deprecated_time = datetime.now()
        check_result = MagicMock()
        check_result.records = [{
            "current_status": "deprecated", 
            "deprecated_at": deprecated_time
        }]
        mock_driver.execute_query.return_value = check_result
        
        result = await manager.mark_tool_description_deprecated(
            "test_tool", "1.0", "ineffective"
        )
        
        assert result["status"] == "already_deprecated"
        assert result["deprecated_at"] == deprecated_time
        assert mock_driver.execute_query.call_count == 1
    
    # Test reactivation functionality
    
    @pytest.mark.asyncio
    async def test_reactivate_description_success(self, mock_manager):
        """Test successful description reactivation."""
        manager, mock_driver = mock_manager
        
        # Mock check query result - description exists and is deprecated
        check_result = MagicMock()
        check_result.records = [{
            "current_status": "deprecated",
            "deprecated_at": datetime.now(),
            "deprecation_reason": "ineffective"
        }]
        
        # Mock reactivate query result
        reactivate_result = MagicMock()
        reactivate_result.records = [{
            "reactivated_at": datetime.now(),
            "current_score": 0.6
        }]
        
        mock_driver.execute_query.side_effect = [check_result, reactivate_result]
        
        result = await manager.reactivate_tool_description(
            "test_tool", "1.0", "test_user"
        )
        
        assert result["status"] == "reactivated"
        assert result["tool_name"] == "test_tool"
        assert result["version"] == "1.0"
        assert result["reactivated_by"] == "test_user"
        assert result["current_effectiveness_score"] == 0.6
        assert result["previous_deprecation_reason"] == "ineffective"
        assert mock_driver.execute_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reactivate_description_not_deprecated(self, mock_manager):
        """Test reactivation when description is not deprecated."""
        manager, mock_driver = mock_manager
        
        check_result = MagicMock()
        check_result.records = [{"current_status": "active"}]
        mock_driver.execute_query.return_value = check_result
        
        result = await manager.reactivate_tool_description("test_tool", "1.0")
        
        assert result["status"] == "not_deprecated"
        assert result["current_status"] == "active"
        assert mock_driver.execute_query.call_count == 1
    
    # Test version creation functionality
    
    @pytest.mark.asyncio
    async def test_create_description_version_success(self, mock_manager):
        """Test successful version creation."""
        manager, mock_driver = mock_manager
        
        # Mock base check result
        base_result = MagicMock()
        base_result.records = [{
            "base_score": 0.7,
            "base_description": "Original description"
        }]
        
        # Mock existing check (private method result)
        manager._check_existing_description = AsyncMock(return_value=False)
        
        # Mock create_tool_description success
        manager.create_tool_description = AsyncMock(return_value=True)
        
        # Mock evolution query
        evolution_result = MagicMock()
        evolution_result.records = [{"new_created": datetime.now()}]
        
        mock_driver.execute_query.side_effect = [base_result, evolution_result]
        
        result = await manager.create_description_version(
            "test_tool", "1.0", "2.0", "Improved description", "test_user"
        )
        
        assert result["status"] == "created"
        assert result["tool_name"] == "test_tool"
        assert result["base_version"] == "1.0"
        assert result["new_version"] == "2.0"
        assert result["created_by"] == "test_user"
        assert result["base_effectiveness_score"] == 0.7
    
    @pytest.mark.asyncio
    async def test_create_description_version_base_not_found(self, mock_manager):
        """Test version creation when base version doesn't exist."""
        manager, mock_driver = mock_manager
        
        base_result = MagicMock()
        base_result.records = []
        mock_driver.execute_query.return_value = base_result
        
        result = await manager.create_description_version(
            "test_tool", "1.0", "2.0", "New description"
        )
        
        assert result["status"] == "base_not_found"
        assert result["base_version"] == "1.0"
    
    @pytest.mark.asyncio 
    async def test_create_description_version_already_exists(self, mock_manager):
        """Test version creation when new version already exists."""
        manager, mock_driver = mock_manager
        
        # Mock base exists
        base_result = MagicMock()
        base_result.records = [{"base_score": 0.7}]
        
        # Mock new version already exists
        manager._check_existing_description = AsyncMock(return_value=True)
        
        mock_driver.execute_query.return_value = base_result
        
        result = await manager.create_description_version(
            "test_tool", "1.0", "2.0", "New description"
        )
        
        assert result["status"] == "version_exists"
        assert result["new_version"] == "2.0"
    
    # Test version listing functionality
    
    @pytest.mark.asyncio
    async def test_get_description_versions_success(self, mock_manager):
        """Test successful version listing."""
        manager, mock_driver = mock_manager
        
        now = datetime.now()
        
        # Mock versions query result
        versions_result = MagicMock()
        versions_result.records = [
            {
                "version": "2.0",
                "status": "active",
                "effectiveness_score": 0.8,
                "access_count": 15,
                "confidence": 0.9,
                "created": now,
                "last_accessed": now,
                "created_by": "user1",
                "deprecated_at": None,
                "deprecation_reason": None,
                "reactivated_at": None,
                "description_length": 100
            },
            {
                "version": "1.0",
                "status": "deprecated",
                "effectiveness_score": 0.3,
                "access_count": 5,
                "confidence": 0.4,
                "created": now,
                "last_accessed": now,
                "created_by": "system",
                "deprecated_at": now,
                "deprecation_reason": "ineffective",
                "reactivated_at": None,
                "description_length": 80
            }
        ]
        
        # Mock evolution query result
        evolution_result = MagicMock()
        evolution_result.records = [{
            "from_version": "1.0",
            "to_version": "2.0",
            "evolution_type": "version_evolution",
            "evolution_created": now,
            "evolution_created_by": "user1"
        }]
        
        mock_driver.execute_query.side_effect = [versions_result, evolution_result]
        
        result = await manager.get_description_versions("test_tool")
        
        assert result["status"] == "success"
        assert result["tool_name"] == "test_tool"
        assert len(result["versions"]) == 2
        assert len(result["evolutions"]) == 1
        assert result["summary"]["total_versions"] == 2
        assert result["summary"]["active_versions"] == 1
        assert result["summary"]["deprecated_versions"] == 1
        
        # Check version details
        active_version = next(v for v in result["versions"] if v["status"] == "active")
        assert active_version["version"] == "2.0"
        assert active_version["effectiveness_score"] == 0.8
        
        deprecated_version = next(v for v in result["versions"] if v["status"] == "deprecated")
        assert deprecated_version["deprecation_reason"] == "ineffective"
    
    # Test analytics functionality
    
    @pytest.mark.asyncio
    async def test_find_low_performing_descriptions_success(self, mock_manager):
        """Test finding low performing descriptions."""
        manager, mock_driver = mock_manager
        
        now = datetime.now()
        
        # Mock low performing query result
        low_perf_result = MagicMock()
        low_perf_result.records = [
            {
                "tool_name": "bad_tool",
                "version": "1.0",
                "effectiveness_score": 0.05,
                "access_count": 10,
                "confidence": 0.3,
                "created": now,
                "last_accessed": now,
                "created_by": "system"
            },
            {
                "tool_name": "mediocre_tool",
                "version": "1.0", 
                "effectiveness_score": 0.25,
                "access_count": 8,
                "confidence": 0.5,
                "created": now,
                "last_accessed": now,
                "created_by": "user1"
            }
        ]
        
        # Mock summary query result
        summary_result = MagicMock()
        summary_result.records = [{
            "total_active": 10,
            "avg_effectiveness": 0.65,
            "below_threshold": 3,
            "sufficient_usage": 8
        }]
        
        mock_driver.execute_query.side_effect = [low_perf_result, summary_result]
        
        result = await manager.find_low_performing_descriptions(
            effectiveness_threshold=0.3, access_threshold=5
        )
        
        assert result["status"] == "success"
        assert len(result["low_performing_descriptions"]) == 2
        assert result["summary"]["total_active_descriptions"] == 10
        assert result["summary"]["average_effectiveness"] == 0.65
        assert result["recommendations"]["immediate_deprecation"] == 1  # score < 0.1
        assert result["recommendations"]["monitor_closely"] == 1  # score 0.2-0.3
        
        # Check recommendations
        bad_desc = next(d for d in result["low_performing_descriptions"] if d["tool_name"] == "bad_tool")
        assert bad_desc["recommendation"] == "immediate_deprecation"
        
        mediocre_desc = next(d for d in result["low_performing_descriptions"] if d["tool_name"] == "mediocre_tool")
        assert mediocre_desc["recommendation"] == "monitor_closely"


class TestIntegration:
    """Integration tests requiring real Neo4j instance."""
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real Neo4j instance")
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """Test complete flow with real Neo4j."""
        # This would test:
        # 1. Create description in Neo4j
        # 2. Retrieve description
        # 3. Track usage and effectiveness
        # 4. Verify evo-strengthening
        pass
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real Neo4j instance")
    @pytest.mark.asyncio
    async def test_phase2_full_flow(self):
        """Test complete Phase 2 flow with real Neo4j."""
        # This would test:
        # 1. Setup schema
        # 2. Seed initial descriptions
        # 3. Verify schema info
        # 4. List descriptions
        # 5. Test effectiveness tracking
        pass
