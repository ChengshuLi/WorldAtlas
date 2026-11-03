-- Set :revision in psql to the desired revision. The result is a single JSON value.
SELECT jsonb_build_object(
  'entity_registry', jsonb_build_object(
    'schema_version','worldatlas-entity-registry-v1', 'revision',r.revision, 'status',r.status,
    'entities', (SELECT jsonb_agg(jsonb_build_object('id',e.id,'name',e.name,'level',e.level,
      'parent_id',e.parent_id,'physical_class',e.physical_class) ORDER BY e.id)
      FROM atlas.geographic_entities e WHERE e.revision=r.revision)),
  'category_bindings', (SELECT jsonb_agg(jsonb_build_object('code',b.code,'entity_id',b.entity_id,
      'physical_class',b.physical_class) ORDER BY b.code)
      FROM atlas.review_category_bindings b WHERE b.revision=r.revision)
) FROM atlas.entity_registry_revisions r WHERE r.revision = :'revision';
