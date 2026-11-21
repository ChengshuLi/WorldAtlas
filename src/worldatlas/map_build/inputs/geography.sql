WITH selected_rules AS (
  SELECT * FROM atlas.geographic_rules WHERE %s::bigint[] IS NULL OR parent_id=ANY(%s)
), selected_entities AS (
  SELECT * FROM atlas.geographic_entities WHERE id IN (SELECT parent_id FROM selected_rules)
    OR parent_id IN (SELECT parent_id FROM selected_rules)
), selected_features(id) AS (
  SELECT feature_id FROM atlas.geographic_rule_features WHERE rule_id IN (SELECT id FROM selected_rules)
  UNION SELECT label_point_id FROM atlas.geographic_rule_targets WHERE label_point_id IS NOT NULL AND rule_id IN (SELECT id FROM selected_rules)
), selected_constructions(id) AS (
  SELECT DISTINCT construction_id FROM atlas.source_features WHERE id IN (SELECT id FROM selected_features)
), source_refs(source_id) AS (
  SELECT source_id FROM atlas.construction_sources WHERE construction_id IN (SELECT id FROM selected_constructions)
  UNION SELECT source_id FROM atlas.geographic_rule_sources WHERE rule_id IN (SELECT id FROM selected_rules)
)
SELECT jsonb_build_object(
  'schema','worldatlas-geographic-division-v2',
  'levels',COALESCE((SELECT jsonb_agg(to_jsonb(l) ORDER BY id) FROM atlas.geographic_levels l),'[]'::jsonb),
  'entities',COALESCE((SELECT jsonb_agg(to_jsonb(e) ORDER BY id) FROM selected_entities e),'[]'::jsonb),
  'category_bindings',COALESCE((SELECT jsonb_agg((to_jsonb(b)-'id')||jsonb_build_object('code',id)
      ORDER BY id) FROM atlas.map_category_bindings b WHERE entity_id IN (SELECT id FROM selected_entities)),'[]'::jsonb),
  'rules',COALESCE((SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM selected_rules r),'[]'::jsonb),
  'rule_features',COALESCE((SELECT jsonb_agg(to_jsonb(l) ORDER BY rule_id,role,feature_id)
      FROM atlas.geographic_rule_features l WHERE rule_id IN (SELECT id FROM selected_rules)),'[]'::jsonb),
  'rule_targets',COALESCE((SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM atlas.geographic_rule_targets t WHERE rule_id IN (SELECT id FROM selected_rules)),'[]'::jsonb),
  'rule_sources',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY rule_id,source_id)
      FROM atlas.geographic_rule_sources s WHERE rule_id IN (SELECT id FROM selected_rules)),'[]'::jsonb),
  'features',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',f.id,'construction_id',f.construction_id)
      ORDER BY f.id) FROM atlas.source_features f WHERE f.id IN (SELECT id FROM selected_features)),'[]'::jsonb),
  'construction_sources',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY construction_id,source_id)
      FROM atlas.construction_sources s WHERE construction_id IN (SELECT id FROM selected_constructions)),'[]'::jsonb),
  'sources',COALESCE((SELECT jsonb_agg(jsonb_build_object('source_id',source_id) ORDER BY source_id)
      FROM source_refs),'[]'::jsonb)
)::text;
