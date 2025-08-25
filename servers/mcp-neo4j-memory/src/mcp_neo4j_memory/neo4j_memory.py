import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from neo4j import AsyncDriver, RoutingControl
from pydantic import BaseModel, Field


# Set up logging
logger = logging.getLogger('mcp_neo4j_memory')
logger.setLevel(logging.INFO)

# Models for our knowledge graph
class Entity(BaseModel):
    name: str
    type: str
    observations: List[str]
    # Evo-memory metadata fields
    access_count: int = Field(default=0, ge=0, description="Number of times this entity has been accessed")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this entity's information quality")
    effectiveness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Effectiveness score from usage patterns")
    created: datetime = Field(default_factory=datetime.now, description="When this entity was created")
    last_accessed: Optional[datetime] = Field(default=None, description="When this entity was last accessed")
    status: str = Field(default="active", description="Status of this entity (active/archived/deprecated)")

class Relation(BaseModel):
    source: str
    target: str
    relationType: str

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relations: List[Relation]

class ObservationAddition(BaseModel):
    entityName: str
    observations: List[str]

class ObservationDeletion(BaseModel):
    entityName: str
    observations: List[str]

class Neo4jMemory:
    def __init__(self, neo4j_driver: AsyncDriver):
        self.driver = neo4j_driver

    async def create_fulltext_index(self):
        """Create a fulltext search index for entities if it doesn't exist."""
        try:
            query = "CREATE FULLTEXT INDEX search IF NOT EXISTS FOR (m:Memory) ON EACH [m.name, m.type, m.observations];"
            await self.driver.execute_query(query, routing_control=RoutingControl.WRITE)
            logger.info("Created fulltext search index")
        except Exception as e:
            # Index might already exist, which is fine
            logger.debug(f"Fulltext index creation: {e}")

    async def load_graph(self, filter_query: str = "*"):
        """Load the entire knowledge graph from Neo4j with evo-metadata and evo-strengthening."""
        logger.info(f"Loading knowledge graph from Neo4j with evo-strengthening for filter: '{filter_query}'")
        
        # Phase 2.1: Find entities, apply evo-strengthening, and calculate multi-dimensional discovery scores
        update_query = """
            CALL db.index.fulltext.queryNodes('search', $filter) yield node as entity, score
            SET entity.access_count = coalesce(entity.access_count, 0) + 1,
                entity.last_accessed = datetime()
            WITH entity, score
            // Phase 2.1: Calculate multi-dimensional discovery score
            WITH entity, score,
                coalesce(entity.confidence, 0.5) as conf,
                coalesce(entity.effectiveness_score, 0.0) as eff,
                log(coalesce(entity.access_count, 0) + 1) as usage_factor,
                CASE coalesce(entity.status, "active")
                    WHEN "active" THEN 1.0
                    WHEN "testing" THEN 0.8
                    WHEN "deprecated" THEN 0.4
                    ELSE 0.6
                END as status_weight
            WITH entity, score,
                (conf * 0.4 + eff * 0.3 + usage_factor * 0.2 + status_weight * 0.1) as discovery_score
            ORDER BY discovery_score DESC, score DESC
            WITH collect(distinct entity) as entities
            UNWIND entities as entity
            OPTIONAL MATCH (entity)-[r]-(other)
            RETURN collect(distinct {
                name: entity.name, 
                type: entity.type, 
                observations: entity.observations,
                access_count: entity.access_count,
                confidence: coalesce(entity.confidence, 0.5),
                effectiveness_score: coalesce(entity.effectiveness_score, 0.0),
                created: entity.created,
                last_accessed: entity.last_accessed,
                status: coalesce(entity.status, "active")
            }) as nodes,
            collect(distinct {
                source: startNode(r).name, 
                target: endNode(r).name, 
                relationType: type(r)
            }) as relations
        """
        
        result = await self.driver.execute_query(update_query, {"filter": filter_query}, routing_control=RoutingControl.WRITE)
        
        if not result.records:
            return KnowledgeGraph(entities=[], relations=[])
        
        record = result.records[0]
        nodes = record.get('nodes', list())
        rels = record.get('relations', list())
        
        entities = []
        for node in nodes:
            if node.get('name'):
                # Convert datetime objects from Neo4j properly
                created = node.get('created')
                last_accessed = node.get('last_accessed')
                
                # Handle created datetime
                if created is None:
                    created = datetime.now()
                elif hasattr(created, 'to_native'):
                    # Neo4j DateTime object
                    created = created.to_native()
                elif isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                
                # Handle last_accessed datetime
                if last_accessed is not None:
                    if hasattr(last_accessed, 'to_native'):
                        # Neo4j DateTime object
                        last_accessed = last_accessed.to_native()
                    elif isinstance(last_accessed, str):
                        last_accessed = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                
                entities.append(Entity(
                    name=node['name'],
                    type=node['type'],
                    observations=node.get('observations', list()),
                    access_count=node.get('access_count', 0),
                    confidence=node.get('confidence', 0.5),
                    effectiveness_score=node.get('effectiveness_score', 0.0),
                    created=created or datetime.now(),
                    last_accessed=last_accessed,
                    status=node.get('status', 'active')
                ))
        
        relations = [
            Relation(
                source=rel['source'],
                target=rel['target'],
                relationType=rel['relationType']
            )
            for rel in rels if rel.get('relationType')
        ]
        
        logger.debug(f"Loaded entities: {entities}")
        logger.debug(f"Loaded relations: {relations}")
        
        return KnowledgeGraph(entities=entities, relations=relations)

    async def create_entities(self, entities: List[Entity]) -> List[Entity]:
        """Create multiple new entities in the knowledge graph with evo-metadata."""
        logger.info(f"Creating {len(entities)} entities with evo-metadata")
        for entity in entities:
            # Serialize datetime fields to ISO format for Neo4j storage
            entity_data = entity.model_dump()
            if entity_data.get('created'):
                entity_data['created'] = entity_data['created'].isoformat()
            if entity_data.get('last_accessed'):
                entity_data['last_accessed'] = entity_data['last_accessed'].isoformat()
            
            query = f"""
            WITH $entity as entity
            MERGE (e:Memory {{ name: entity.name }})
            SET e += entity
            SET e:`{entity.type}`
            """
            await self.driver.execute_query(query, {"entity": entity_data}, routing_control=RoutingControl.WRITE)

        return entities

    async def create_relations(self, relations: List[Relation]) -> List[Relation]:
        """Create multiple new relations between entities."""
        logger.info(f"Creating {len(relations)} relations")
        for relation in relations:
            query = f"""
            WITH $relation as relation
            MATCH (from:Memory),(to:Memory)
            WHERE from.name = relation.source
            AND  to.name = relation.target
            MERGE (from)-[r:`{relation.relationType}`]->(to)
            """
            
            await self.driver.execute_query(
                query, 
                {"relation": relation.model_dump()},
                routing_control=RoutingControl.WRITE
            )

        return relations

    async def add_observations(self, observations: List[ObservationAddition]) -> List[Dict[str, Any]]:
        """Add new observations to existing entities."""
        logger.info(f"Adding observations to {len(observations)} entities")
        query = """
        UNWIND $observations as obs  
        MATCH (e:Memory { name: obs.entityName })
        WITH e, [o in obs.observations WHERE NOT o IN e.observations] as new
        SET e.observations = coalesce(e.observations,[]) + new
        RETURN e.name as name, new
        """
            
        result = await self.driver.execute_query(
            query, 
            {"observations": [obs.model_dump() for obs in observations]},
            routing_control=RoutingControl.WRITE
        )

        results = [{"entityName": record.get("name"), "addedObservations": record.get("new")} for record in result.records]
        return results

    async def delete_entities(self, entity_names: List[str]) -> None:
        """Delete multiple entities and their associated relations."""
        logger.info(f"Deleting {len(entity_names)} entities")
        query = """
        UNWIND $entities as name
        MATCH (e:Memory { name: name })
        DETACH DELETE e
        """
        
        await self.driver.execute_query(query, {"entities": entity_names}, routing_control=RoutingControl.WRITE)
        logger.info(f"Successfully deleted {len(entity_names)} entities")

    async def delete_observations(self, deletions: List[ObservationDeletion]) -> None:
        """Delete specific observations from entities."""
        logger.info(f"Deleting observations from {len(deletions)} entities")
        query = """
        UNWIND $deletions as d  
        MATCH (e:Memory { name: d.entityName })
        SET e.observations = [o in coalesce(e.observations,[]) WHERE NOT o IN d.observations]
        """
        await self.driver.execute_query(
            query, 
            {"deletions": [deletion.model_dump() for deletion in deletions]},
            routing_control=RoutingControl.WRITE
        )
        logger.info(f"Successfully deleted observations from {len(deletions)} entities")

    async def delete_relations(self, relations: List[Relation]) -> None:
        """Delete multiple relations from the graph."""
        logger.info(f"Deleting {len(relations)} relations")
        for relation in relations:
            query = f"""
            WITH $relation as relation
            MATCH (source:Memory)-[r:`{relation.relationType}`]->(target:Memory)
            WHERE source.name = relation.source
            AND target.name = relation.target
            DELETE r
            """
            await self.driver.execute_query(
                query, 
                {"relation": relation.model_dump()},
                routing_control=RoutingControl.WRITE
            )
        logger.info(f"Successfully deleted {len(relations)} relations")

    async def read_graph(self) -> KnowledgeGraph:
        """Read the entire knowledge graph."""
        return await self.load_graph()

    async def search_memories(self, query: str) -> KnowledgeGraph:
        """Search for memories based on a query with Fulltext Search."""
        logger.info(f"Searching for memories with query: '{query}'")
        return await self.load_graph(query)

    async def find_memories_by_name(self, names: List[str]) -> KnowledgeGraph:
        """Find specific memories by their names with evo-strengthening."""
        logger.info(f"Finding {len(names)} memories by name with evo-strengthening")
        
        # First, update access patterns for evo-strengthening
        update_query = """
        MATCH (e:Memory)
        WHERE e.name IN $names
        SET e.access_count = coalesce(e.access_count, 0) + 1,
            e.last_accessed = datetime()
        RETURN  e.name as name, 
                e.type as type, 
                e.observations as observations,
                e.access_count as access_count,
                coalesce(e.confidence, 0.5) as confidence,
                coalesce(e.effectiveness_score, 0.0) as effectiveness_score,
                e.created as created,
                e.last_accessed as last_accessed,
                coalesce(e.status, "active") as status
        """
        result_nodes = await self.driver.execute_query(update_query, {"names": names}, routing_control=RoutingControl.WRITE)
        entities: list[Entity] = list()
        for record in result_nodes.records:
            # Parse datetime fields properly from Neo4j DateTime objects
            created = record['created']
            last_accessed = record['last_accessed']
            
            # Handle None values
            if created is None:
                created = datetime.now()
            elif hasattr(created, 'to_native'):
                # Neo4j DateTime object
                created = created.to_native()
            elif isinstance(created, str):
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            
            if last_accessed is not None:
                if hasattr(last_accessed, 'to_native'):
                    # Neo4j DateTime object  
                    last_accessed = last_accessed.to_native()
                elif isinstance(last_accessed, str):
                    last_accessed = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
            
            entities.append(Entity(
                name=record['name'],
                type=record['type'],
                observations=record.get('observations', list()),
                access_count=record['access_count'],
                confidence=record['confidence'],
                effectiveness_score=record['effectiveness_score'],
                created=created,
                last_accessed=last_accessed,
                status=record['status']
            ))
        
        # Get relations for found entities
        relations: list[Relation] = list()
        if entities:
            query = """
            MATCH (source:Memory)-[r]->(target:Memory)
            WHERE source.name IN $names OR target.name IN $names
            RETURN  source.name as source, 
                    target.name as target, 
                    type(r) as relationType
            """
            result_relations = await self.driver.execute_query(query, {"names": names}, routing_control=RoutingControl.READ)
            for record in result_relations.records:
                relations.append(Relation(
                    source=record["source"],
                    target=record["target"],
                    relationType=record["relationType"]
                ))
        
        logger.info(f"Found {len(entities)} entities and {len(relations)} relations with evo-strengthening applied")
        return KnowledgeGraph(entities=entities, relations=relations)