WITH source_refs(source_id) AS (
  SELECT source_id FROM atlas.construction_sources
  UNION SELECT source_id FROM atlas.geographic_assignment_sources
)
SELECT jsonb_build_object(
  'schema', 'worldatlas-geography-selection-v4',
  'sources', COALESCE((SELECT jsonb_agg(jsonb_build_object('source_id',source_id)
                                     ORDER BY source_id) FROM source_refs),'[]'::jsonb),
  'entities', COALESCE((SELECT jsonb_agg(to_jsonb(e) ORDER BY id)
                       FROM atlas.geographic_entities e),'[]'::jsonb),
  'category_bindings', COALESCE((SELECT jsonb_agg((to_jsonb(b)-'id') || jsonb_build_object('code',id)
                                                ORDER BY id) FROM atlas.map_category_bindings b),'[]'::jsonb),
  'features', COALESCE((SELECT jsonb_agg((to_jsonb(f)-'geometry'-'id') || jsonb_build_object('feature_id',id)
                                       ORDER BY id) FROM atlas.source_features f),'[]'::jsonb),
  'partitions', COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY id)
                         FROM atlas.geographic_partitions p),'[]'::jsonb),
  'construction_sources', COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY construction_id,source_id)
                                   FROM atlas.construction_sources s),'[]'::jsonb),
  'region_closures', COALESCE((SELECT jsonb_agg((to_jsonb(r)-'id') || jsonb_build_object(
      'route_id',id,
      'start_terminal',jsonb_build_object('boundary_id',start_boundary_id,'endpoint',start_endpoint),
      'end_terminal',jsonb_build_object('boundary_id',end_boundary_id,'endpoint',end_endpoint))
      ORDER BY id) FROM atlas.decision_mainland_closure_routes r),'[]'::jsonb),
  'basins', COALESCE((SELECT jsonb_agg(jsonb_build_object(
      'id',b.id,'feature_id',b.feature_id,'source_feature_id',f.source_feature_id,
      'assignment_method',b.method,'tie_rules',b.tie_rules,'evidence',b.evidence) ORDER BY b.id)
      FROM atlas.decision_basins b JOIN atlas.source_features f ON f.id=b.feature_id),'[]'::jsonb),
  'assignments', COALESCE((SELECT jsonb_agg((to_jsonb(a)-'id') || jsonb_build_object('assignment_id',id)
                                          ORDER BY id) FROM atlas.geographic_assignments a),'[]'::jsonb),
  'assignment_sources', COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY assignment_id,source_id)
                                 FROM atlas.geographic_assignment_sources s),'[]'::jsonb),
  'ocean_seeds', COALESCE((SELECT jsonb_agg((to_jsonb(s)-'id') || jsonb_build_object('entity_id',id)
                                          ORDER BY id) FROM atlas.ocean_seeds s),'[]'::jsonb),
  'policies', COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY id)
                       FROM atlas.decision_policies p),'[]'::jsonb),
  'land_baseline_policy', jsonb_build_object('region_ids',
      COALESCE((SELECT jsonb_agg(id ORDER BY id) FROM atlas.decision_mainland_seed_regions),'[]'::jsonb)),
  'seed_regions', COALESCE((SELECT jsonb_agg((to_jsonb(r)-'id') || jsonb_build_object(
      'region_id',r.id,'segments',COALESCE((SELECT jsonb_agg(jsonb_build_object(
          'kind',kind,'id',COALESCE(boundary_id,route_id),'reverse',reverse) ORDER BY ordinal)
          FROM atlas.decision_mainland_region_segments s WHERE s.region_id=r.id),'[]'::jsonb))
      ORDER BY r.id) FROM atlas.decision_mainland_seed_regions r),'[]'::jsonb),
  'mainland_witnesses', COALESCE((SELECT jsonb_agg((to_jsonb(w)-'id') || jsonb_build_object('witness_id',id)
                                                ORDER BY id) FROM atlas.decision_mainland_witnesses w),'[]'::jsonb),
  'mainland_witness_groups', COALESCE((SELECT jsonb_agg((to_jsonb(g)-'id') || jsonb_build_object(
      'group_id',g.id,
      'witness_ids',COALESCE((SELECT jsonb_agg(witness_id ORDER BY witness_id)
          FROM atlas.decision_mainland_witness_group_members m WHERE m.group_id=g.id),'[]'::jsonb),
      'target_entity_ids',COALESCE((SELECT jsonb_agg(entity_id ORDER BY entity_id)
          FROM atlas.decision_mainland_witness_group_targets t WHERE t.group_id=g.id),'[]'::jsonb))
      ORDER BY g.id) FROM atlas.decision_mainland_witness_groups g),'[]'::jsonb),
  'distinct_groups', COALESCE((SELECT jsonb_agg(jsonb_build_array(group_a,group_b) ORDER BY group_a,group_b)
                              FROM atlas.decision_mainland_distinct_groups),'[]'::jsonb)
)::text;
