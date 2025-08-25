// Full Evo-Metadata Migration Script
// Date: 2025-08-25
// Purpose: Migrate all legacy entities to full evo-metadata for Phase 2 readiness
// Version: 1.0

// ============================================================================
// PRE-MIGRATION ANALYSIS
// ============================================================================

// Step 1: Count entities that need migration
MATCH (legacy) 
WHERE legacy.confidence IS NULL
RETURN 
  count(legacy) as total_legacy_entities,
  count(CASE WHEN legacy.access_count IS NOT NULL THEN 1 END) as with_access_count,
  count(CASE WHEN legacy.access_count IS NULL THEN 1 END) as without_access_count,
  avg(CASE WHEN legacy.access_count IS NOT NULL THEN legacy.access_count END) as avg_access_count;

// Step 2: Show breakdown by entity type
MATCH (legacy) 
WHERE legacy.confidence IS NULL
RETURN 
  legacy.type as entity_type,
  count(legacy) as count,
  avg(CASE WHEN legacy.access_count IS NOT NULL THEN legacy.access_count END) as avg_access
ORDER BY count DESC
LIMIT 15;

// ============================================================================
// FULL MIGRATION EXECUTION
// ============================================================================

// Step 3: Migrate all legacy entities to full evo-metadata
MATCH (legacy) 
WHERE legacy.confidence IS NULL
SET legacy.confidence = 0.5,
    legacy.effectiveness_score = CASE 
        WHEN legacy.access_count IS NOT NULL THEN legacy.access_count * 0.01
        ELSE 0.01 
    END,
    legacy.status = 'active',
    legacy.created = datetime(),
    legacy.migrated_on = datetime(),
    legacy.migration_version = 'full_v1',
    legacy.migration_type = CASE 
        WHEN legacy.access_count IS NOT NULL THEN 'access_based'
        ELSE 'default_values'
    END
RETURN count(legacy) as entities_migrated;

// ============================================================================
// POST-MIGRATION VALIDATION
// ============================================================================

// Step 4: Verify migration completeness
MATCH (n)
RETURN 
  count(n) as total_entities,
  count(CASE WHEN n.confidence IS NOT NULL THEN 1 END) as with_full_metadata,
  count(CASE WHEN n.confidence IS NULL THEN 1 END) as still_missing_metadata,
  (count(CASE WHEN n.confidence IS NOT NULL THEN 1 END) * 100.0 / count(n)) as metadata_coverage_percent;

// Step 5: Show migration results breakdown
MATCH (n) 
WHERE n.migration_version = 'full_v1'
RETURN 
  n.migration_type as migration_type,
  count(n) as count,
  min(n.effectiveness_score) as min_effectiveness,
  max(n.effectiveness_score) as max_effectiveness,
  avg(n.effectiveness_score) as avg_effectiveness
ORDER BY count DESC;

// Step 6: Test Phase 2 query performance
MATCH (n) 
WHERE n.confidence >= 0.4 
  AND n.status = 'active'
  AND n.effectiveness_score >= 0.02
RETURN 
  n.type as entity_type,
  count(n) as matching_entities,
  avg(n.effectiveness_score) as avg_effectiveness
ORDER BY avg_effectiveness DESC
LIMIT 10;

// Step 7: Show top entities by effectiveness (mixed original + migrated)
MATCH (n) 
WHERE n.confidence >= 0.3 
  AND n.status IN ['active', 'testing']
RETURN 
  n.name,
  n.type,
  n.effectiveness_score,
  n.confidence,
  n.access_count,
  CASE 
    WHEN n.migration_version IS NOT NULL THEN 'migrated'
    ELSE 'original' 
  END as metadata_source
ORDER BY n.effectiveness_score DESC
LIMIT 15;
