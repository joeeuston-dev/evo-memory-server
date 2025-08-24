# Dynamic Tool Descriptions Architecture

## Overview

This document outlines the architecture for storing MCP tool descriptions in Neo4j, enabling dynamic optimization of tool descriptions through evo-memory patterns. This innovation allows tool descriptions to evolve based on effectiveness without requiring code rebuilds or deployments.

## Core Concept

Traditional MCP servers have hardcoded tool descriptions in function docstrings. Our approach stores these descriptions as Neo4j entities that can be:

- **Dynamically updated** without code changes
- **A/B tested** for effectiveness 
- **Evolved through evo-strengthening** based on usage patterns
- **Versioned and rolled back** as needed
- **Shared across teams** through the knowledge graph

## Architecture Components

### 1. Tool Description Entities

Tool descriptions are stored as Neo4j entities with evo-memory metadata:

```cypher
CREATE (desc:ToolDescription {
  tool_name: "search_memories",
  version: "2.1",
  description: "**PRIMARY DISCOVERY TOOL**: Use this FIRST when user asks about past work...",
  effectiveness_score: 0.85,
  access_count: 142,
  created: datetime(),
  last_accessed: datetime(),
  status: "active",
  confidence: 0.9,
  environment: "production"
})
```

### 2. Description Versioning System

Multiple versions can exist simultaneously for A/B testing:

```cypher
CREATE (v1:ToolDescription {
  tool_name: "search_memories",
  version: "2.0",
  description: "Use this to search for nodes",
  effectiveness_score: 0.65,
  status: "deprecated"
})

CREATE (v2:ToolDescription {
  tool_name: "search_memories", 
  version: "2.1",
  description: "**PRIMARY DISCOVERY TOOL**: Use this FIRST...",
  effectiveness_score: 0.85,
  status: "active"
})

CREATE (v1)-[:EVOLVED_TO]->(v2)
```

### 3. FastMCP Integration Layer

The MCP server queries Neo4j for descriptions at runtime:

```python
class DynamicToolDescriptionManager:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.fallback_descriptions = HARDCODED_DESCRIPTIONS
        
    async def get_tool_description(self, tool_name: str, environment: str = "production") -> str:
        """Get the most effective tool description from Neo4j"""
        
        query = """
        MATCH (desc:ToolDescription {tool_name: $tool_name, environment: $environment, status: 'active'})
        RETURN desc.description as description, desc.effectiveness_score as score
        ORDER BY desc.effectiveness_score DESC
        LIMIT 1
        """
        
        result = await self.driver.execute_query(query, 
                                               tool_name=tool_name, 
                                               environment=environment)
        
        if result.records:
            # Trigger evo-strengthening
            await self.increment_access_count(tool_name, environment)
            return result.records[0]["description"]
        
        # Fallback to hardcoded descriptions
        return self.fallback_descriptions.get(tool_name, "")
    
    async def increment_access_count(self, tool_name: str, environment: str):
        """Evo-strengthening: increment access count and update last_accessed"""
        query = """
        MATCH (desc:ToolDescription {tool_name: $tool_name, environment: $environment, status: 'active'})
        SET desc.access_count = desc.access_count + 1,
            desc.last_accessed = datetime()
        RETURN desc.access_count as new_count
        """
        await self.driver.execute_query(query, tool_name=tool_name, environment=environment)
```

### 4. Dynamic Tool Registration

Tools register with dynamic descriptions at server startup:

```python
@tool
async def search_memories(query: str) -> dict:
    # Description is fetched dynamically from Neo4j
    pass

# During server initialization
description_manager = DynamicToolDescriptionManager(neo4j_driver)

# Register tools with dynamic descriptions
for tool_func in TOOLS:
    tool_name = tool_func.__name__
    description = await description_manager.get_tool_description(tool_name)
    
    # Update the tool's docstring dynamically
    tool_func.__doc__ = description
```

## Implementation Phases

### Phase 1: Basic Storage and Retrieval
- [ ] Create ToolDescription entity schema
- [ ] Implement DynamicToolDescriptionManager
- [ ] Add fallback to hardcoded descriptions
- [ ] Test basic description loading

### Phase 2: Evo-Memory Integration
- [ ] Add evo-metadata (access_count, confidence, etc.)
- [ ] Implement evo-strengthening on tool usage
- [ ] Add effectiveness tracking
- [ ] Create description evolution patterns

### Phase 3: A/B Testing Framework
- [ ] Support multiple active versions
- [ ] Implement random selection for testing
- [ ] Track effectiveness metrics per version
- [ ] Auto-promote winning descriptions

### Phase 4: Advanced Features
- [ ] Environment-specific descriptions (dev/staging/prod)
- [ ] Team collaboration features
- [ ] Description effectiveness analytics
- [ ] Automatic rollback on performance degradation

## Benefits

### 1. Zero Deployment Optimization
- Update tool descriptions without rebuilding/redeploying
- Immediate testing of new description approaches
- Real-time optimization based on effectiveness

### 2. Scientific Optimization
- A/B test different description strategies
- Measure effectiveness through evo-strengthening metrics
- Data-driven description evolution

### 3. Team Collaboration
- Share effective descriptions across team members
- Learn from collective usage patterns
- Build institutional knowledge in the graph

### 4. Adaptive Behavior
- Descriptions improve automatically over time
- Evo-memory patterns strengthen effective descriptions
- System learns optimal guidance strategies

## Data Model

### Core Entities

```cypher
// Tool Description
(:ToolDescription {
  tool_name: string,
  version: string,
  description: string,
  effectiveness_score: float,
  access_count: integer,
  created: datetime,
  last_accessed: datetime,
  status: enum["active", "testing", "deprecated"],
  confidence: float,
  environment: string,
  created_by: string
})

// Description Evolution
(:ToolDescription)-[:EVOLVED_TO]->(:ToolDescription)
(:ToolDescription)-[:TESTED_AGAINST]->(:ToolDescription)
(:ToolDescription)-[:INSPIRED_BY]->(:ToolDescription)

// Usage Tracking
(:ToolDescription)-[:USED_IN]->(:Session)
(:ToolDescription)-[:EFFECTIVE_FOR]->(:UseCase)
```

### Example Queries

```cypher
// Get most effective description
MATCH (desc:ToolDescription {tool_name: "search_memories", status: "active"})
RETURN desc.description
ORDER BY desc.effectiveness_score DESC
LIMIT 1

// Track usage for evo-strengthening
MATCH (desc:ToolDescription {tool_name: "search_memories", status: "active"})
SET desc.access_count = desc.access_count + 1,
    desc.last_accessed = datetime()

// Find descriptions that need optimization
MATCH (desc:ToolDescription)
WHERE desc.effectiveness_score < 0.7 AND desc.access_count > 10
RETURN desc.tool_name, desc.effectiveness_score, desc.access_count

// Evolution chain analysis
MATCH path = (old:ToolDescription)-[:EVOLVED_TO*]->(current:ToolDescription)
WHERE current.status = "active"
RETURN path
```

## Configuration

### Environment Variables

```bash
# Enable dynamic descriptions (fallback to hardcoded if false)
DYNAMIC_DESCRIPTIONS_ENABLED=true

# Environment for description selection
DESCRIPTION_ENVIRONMENT=production

# A/B testing probability (0.0-1.0)
AB_TEST_PROBABILITY=0.1

# Effectiveness tracking threshold
EFFECTIVENESS_THRESHOLD=0.75
```

### Neo4j Schema

```cypher
// Create constraints
CREATE CONSTRAINT tool_description_unique 
FOR (td:ToolDescription) 
REQUIRE (td.tool_name, td.version, td.environment) IS UNIQUE;

CREATE INDEX tool_description_lookup 
FOR (td:ToolDescription) 
ON (td.tool_name, td.environment, td.status);

CREATE INDEX effectiveness_score_index
FOR (td:ToolDescription)
ON td.effectiveness_score;
```

## Security Considerations

### Access Control
- Only authorized users can create/modify descriptions
- Version history preserved for audit trails
- Environment isolation (dev/staging/prod)

### Fallback Safety
- Always maintain hardcoded descriptions as fallback
- Graceful degradation if Neo4j unavailable
- Description validation before activation

### Testing Safety
- Staged rollout through environments
- Automatic rollback on effectiveness degradation
- A/B testing with controlled exposure

## Success Metrics

### Effectiveness Tracking
- **Tool Selection Accuracy**: How often LLM chooses optimal tool
- **Task Completion Rate**: Success rate with dynamic descriptions
- **Usage Patterns**: Which descriptions lead to better outcomes

### Evo-Memory Metrics
- **Access Count Growth**: Strengthening of effective descriptions
- **Confidence Evolution**: How confidence scores improve over time
- **Relationship Formation**: Connections between descriptions and use cases

### Team Benefits
- **Description Sharing**: Cross-team adoption of effective descriptions
- **Knowledge Transfer**: How descriptions encode institutional knowledge
- **Optimization Speed**: Time from description change to improved outcomes

## Next Steps

1. **Create basic implementation** in feature branch
2. **Test with single tool** (search_memories)
3. **Validate evo-strengthening** patterns
4. **Expand to all tools** once proven
5. **Add A/B testing** framework
6. **Implement team collaboration** features

This architecture transforms tool descriptions from static code into living, evolving knowledge that improves through evo-memory patterns.
