// Rollback Script for Test Migration
// Date: 2025-08-25
// Purpose: Remove test migration fields if needed

// Remove migration-added fields from test entities
MATCH (n) 
WHERE n.migration_version = 'test_v1'
REMOVE n.confidence, n.effectiveness_score, n.status, n.created, n.migrated_on, n.migration_version
RETURN count(n) as entities_rolled_back;

// Verify rollback
MATCH (n) 
WHERE n.name IN [
  'Evolutionary Memory Extension Project',
  'TypeScript Lambda Standards', 
  'Lambda Modernization Templates',
  'Strategic Infrastructure Independence Framework',
  'InboundEventFunction Modernization Analysis',
  'Technical Standards Patterns',
  'Code Analysis Principle',
  'Principle-Guided Operation Protocol'
]
RETURN n.name, n.access_count, n.confidence, n.effectiveness_score, n.status, n.migration_version;
