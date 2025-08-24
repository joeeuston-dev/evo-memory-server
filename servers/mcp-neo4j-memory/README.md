# Evo-Memory Server

A fork of [neo4j-contrib/mcp-neo4j](https://github.com/neo4j-contrib/mcp-neo4j) enhanced with intent-guided tool descriptions for evo-memory patterns.

## Enhancements

### Intent-Guided Tool Descriptions
Each tool now includes detailed guidance on WHEN and HOW to use it, enabling better LLM tool selection in fresh sessions:

- **`search_memories`**: "**PRIMARY DISCOVERY TOOL** - Use this FIRST when user asks about past work..."
- **`read_graph`**: "**FULL CONTEXT TOOL** - Use ONLY when you need complete system state..."
- **`create_entities`**: "**KNOWLEDGE CREATION TOOL** - Create new entities with evo metadata..."
- **`create_relations`**: "**EVO STRENGTHENING TOOL** - Create relationships for knowledge discovery..."
- **`add_observations`**: "**EVO CONSOLIDATION TOOL** - Add new insights to existing entities..."
- **`find_memories_by_name`**: "**DIRECT ACCESS TOOL** - Find specific entities by exact name..."

### Evo-Memory Patterns
- **Evo Strengthening**: Tools guide toward relationship creation and usage tracking
- **Evo Consolidation**: Emphasis on updating existing knowledge rather than creating duplicates
- **Discovery Over Retrieval**: Search-first patterns rather than full graph reads
- **Intent Recognition**: Tool descriptions encode when each tool should be used

## Key Problem Solved

**The "Fresh Session Problem"**: In new sessions without context, LLMs default to obvious tool choices (like `read_graph`) rather than efficient patterns (like `search_memories` first). Our enhanced descriptions guide the LLM toward evo-memory patterns from the very first interaction.

## Installation

This is a Python FastMCP server requiring:

```bash
cd /Users/jeuston/SOURCE/evo-memory-server
pip install -e .
```

## Usage in Goose

Configure as a command-line extension:

```bash
goose configure
# Select: Add Extension -> Command-line Extension
# Name: evo-memory
# Command: python -m mcp_neo4j_memory
# Environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
```

## Differences from Original

1. **Enhanced Tool Docstrings**: Each FastMCP tool description includes intent guidance and usage patterns
2. **Evo Metadata Emphasis**: Tools encourage inclusion of access_count, confidence, timestamps in observations
3. **Relationship Focus**: Stronger emphasis on creating and maintaining entity relationships for knowledge discovery
4. **Discovery Patterns**: Search-first methodology rather than full graph reads for efficiency

## Development

This fork maintains compatibility with the original neo4j-contrib/mcp-neo4j while adding evo-memory guidance layers through enhanced tool descriptions.

## Project Naming

"Evo-Memory Server" reflects the core enhancement: providing evolutionary, adaptive knowledge graph operations with intent-guided patterns.
