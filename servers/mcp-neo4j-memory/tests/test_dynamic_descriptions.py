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
    async def test_fallback_when_disabled(self, disabled_description_manager):
        """Test that hardcoded descriptions are used when disabled."""
        description = await disabled_description_manager.get_tool_description("search_memories")
        
        assert "PRIMARY DISCOVERY TOOL" in description
        assert disabled_description_manager.enabled is False
    
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
    async def test_fallback_on_error(self, description_manager, mock_driver):
        """Test fallback to hardcoded when Neo4j fails."""
        mock_driver.execute_query.side_effect = Exception("Neo4j connection failed")
        
        description = await description_manager.get_tool_description("search_memories")
        
        assert "PRIMARY DISCOVERY TOOL" in description
        assert mock_driver.execute_query.call_count == 1  # Only one call before exception
    
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
    async def test_create_tool_description_failure(self, description_manager, mock_driver, sample_tool_description):
        """Test handling of tool description creation failure."""
        mock_driver.execute_query.side_effect = Exception("Database error")
        
        success = await description_manager.create_tool_description(sample_tool_description)
        
        assert success is False
    
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
    async def test_health_check_disabled(self, disabled_description_manager):
        """Test health check when dynamic descriptions are disabled."""
        health = await disabled_description_manager.health_check()
        
        assert health["status"] == "disabled"
        assert health["enabled"] is False
        assert "fallback_descriptions_count" in health
    
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
class TestIntegration:
    """Integration tests requiring real Neo4j instance."""
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real Neo4j instance")
    async def test_end_to_end_flow(self):
        """Test complete flow with real Neo4j."""
        # This would test:
        # 1. Create description in Neo4j
        # 2. Retrieve description
        # 3. Track usage and effectiveness
        # 4. Verify evo-strengthening
        pass
