// Full Migration Rollback Script
// Date: 2025-08-25
// Purpose: Rollback full migration if needed (EMERGENCY USE ONLY)

// WARNING: This will remove all migrated evo-metadata!
// Only run if Phase 2 implementation has serious issues

// Count entities that would be affected
MATCH (n) 
WHERE n.migration_version IN ['full_v1', 'test_v1']
RETURN count(n) as entities_to_rollback;

// Uncomment the following lines to execute rollback:
/*
MATCH (n) 
WHERE n.migration_version IN ['full_v1', 'test_v1']
REMOVE n.confidence, n.effectiveness_score, n.status, n.created, 
       n.migrated_on, n.migration_version, n.migration_type
RETURN count(n) as entities_rolled_back;
*/

// After rollback, verify state
MATCH (n)
RETURN 
  count(n) as total_entities,
  count(CASE WHEN n.confidence IS NOT NULL THEN 1 END) as with_metadata,
  count(CASE WHEN n.confidence IS NULL THEN 1 END) as without_metadata;
