WITH source_refs(source_id) AS
  (SELECT source_id
   FROM atlas.construction_sources
   UNION SELECT source_id
   FROM atlas.decision_mainland_boundary_sources
   UNION SELECT source_id
   FROM atlas.geographic_assignment_sources
   UNION SELECT ref->>'source_id'
   FROM
     (SELECT evidence
      FROM atlas.decision_endpoints
      UNION ALL SELECT evidence
      FROM atlas.decision_routes
      ) r
   CROSS JOIN LATERAL jsonb_array_elements(COALESCE(evidence->'source_refs', '[]'::jsonb)) ref)
SELECT jsonb_build_object(
  'schema', 'worldatlas-geography-selection-v3',
  'sources',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('source_id', source_id)
                                 ORDER BY source_id)
                FROM source_refs),'[]'::jsonb),
  'entities',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(e)
                                 ORDER BY e.id)
                FROM atlas.geographic_entities e
                ),'[]'::jsonb),
  'category_bindings',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(b)-'id') || jsonb_build_object('code',b.id)
                                 ORDER BY b.id)
                FROM atlas.map_category_bindings b
                ),'[]'::jsonb),
  'features',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(f)-'geometry'-'id') || jsonb_build_object('feature_id',f.id)
                                 ORDER BY f.id)
                FROM atlas.source_features f
                ),'[]'::jsonb),
  'partitions',
    COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY id) FROM atlas.geographic_partitions p),'[]'::jsonb),
  'construction_sources',
    COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY construction_id,source_id)
              FROM atlas.construction_sources s),'[]'::jsonb),
  'endpoints',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(p)-'id')||jsonb_build_object('endpoint_id',p.id,'longitude',
                                                             p.longitude::text, 'latitude', p.latitude::text)
                                 ORDER BY p.id)
                FROM atlas.decision_endpoints p
                ),'[]'::jsonb),
  'routes',
    COALESCE(
               (SELECT jsonb_agg(obj
                                 ORDER BY id)
                FROM
                  (SELECT r.id,

           (to_jsonb(r)-'id')||jsonb_build_object('route_id',r.id,'points',

                                       COALESCE(
                                                  (SELECT jsonb_agg(to_jsonb(p)-'route_id'
                                                                    ORDER BY p.ordinal)
                                                   FROM atlas.decision_route_points p
                                                   WHERE p.route_id=r.id),'[]'::jsonb)) obj
                   FROM atlas.decision_routes r
                   UNION ALL SELECT r.id,

            (to_jsonb(r)-'id'-'start_boundary_id'-'start_endpoint'-'end_boundary_id'-'end_endpoint')||jsonb_build_object('route_id',r.id,'start_terminal',

                                                                                                              jsonb_build_object('boundary_id',

                                                                                                                start_boundary_id,
                                                                                                                'endpoint',
                                                                                                                start_endpoint),
                                                                                                              'end_terminal',
                                                                                                              jsonb_build_object('boundary_id',

                                                                                                                end_boundary_id,
                                                                                                                'endpoint',
                                                                                                                end_endpoint),
                                                                                                              'points',
                                                                                                              '[]'::jsonb)
                   FROM atlas.decision_mainland_closure_routes r
                   ) r),'[]'::jsonb),
  'basins',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('id',
                                   b.id, 'feature_id', b.feature_id, 'source_feature_id', f.source_feature_id,
                                   'assignment_method', b.method, 'tie_rules', b.tie_rules,
                                   'evidence', b.evidence)
                                 ORDER BY b.id)
                FROM atlas.decision_basins b
                JOIN atlas.source_features f ON f.id=b.feature_id
                ),'[]'::jsonb),
  'assignments',
    COALESCE((SELECT jsonb_agg((to_jsonb(a)-'id') || jsonb_build_object('assignment_id',a.id) ORDER BY a.id)
              FROM atlas.geographic_assignments a), '[]'::jsonb),
  'assignment_sources',
    COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY assignment_id, source_id)
              FROM atlas.geographic_assignment_sources s), '[]'::jsonb),
  'ocean_seeds',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(s)-'id') || jsonb_build_object('seed_id',s.id)
                                 ORDER BY s.id)
                FROM atlas.decision_ocean_seeds s
                ),'[]'::jsonb),
  'policies',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('id',
                                   id, 'kind', kind, 'definition', definition, 'evidence', evidence)
                                 ORDER BY id)
                FROM atlas.decision_policies),'[]'::jsonb),
  'mainland_boundaries',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(b)-'id')||jsonb_build_object('boundary_id',b.id,'source_refs',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('source_id', source_id, 'relationship',
                                                                                          relationship)
                                                                                        ORDER BY source_id)
                                                                       FROM atlas.decision_mainland_boundary_sources s
                                                                       WHERE s.boundary_id=b.id),'[]'::jsonb))
                                 ORDER BY b.id)
                FROM atlas.decision_mainland_boundaries b
                ),'[]'::jsonb),
  'land_baseline_policy',
    jsonb_build_object(
      'region_ids', COALESCE(
        (SELECT jsonb_agg(id ORDER BY id)
         FROM atlas.decision_mainland_seed_regions), '[]'::jsonb),
      'mainland_rule_ids', COALESCE(
        (SELECT jsonb_agg(id ORDER BY id)
         FROM (SELECT id FROM atlas.decision_mainland_component_rules
               UNION ALL SELECT id FROM atlas.geographic_partitions WHERE mainland_group_id IS NOT NULL) r), '[]'::jsonb)),
  'seed_regions',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(r)-'id')||jsonb_build_object('region_id',r.id,'segments',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('kind',
                                                                                          kind, 'id',
                                                                                          COALESCE(boundary_id,
                                                                                            route_id), 'reverse', reverse)
                                                                                        ORDER BY ordinal)
                                                                       FROM atlas.decision_mainland_region_segments s
                                                                       WHERE s.region_id=r.id),'[]'::jsonb))
                                 ORDER BY r.id)
                FROM atlas.decision_mainland_seed_regions r
                ),'[]'::jsonb),
  'mainland_component_rules',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(r)-'id') || jsonb_build_object('rule_id',r.id)
                                 ORDER BY r.id)
                FROM atlas.decision_mainland_component_rules r
                ),'[]'::jsonb),
  'mainland_witnesses',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(w)-'id') || jsonb_build_object('witness_id',w.id)
                                 ORDER BY w.id)
                FROM atlas.decision_mainland_witnesses w
                ),'[]'::jsonb),
  'mainland_witness_groups',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(g)-'id')||jsonb_build_object('group_id',g.id,'witness_ids',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(witness_id
                                                                                        ORDER BY witness_id)
                                                                       FROM atlas.decision_mainland_witness_group_members m
                                                                       WHERE m.group_id=g.id),'[]'::jsonb), 'target_entity_ids',
                                                           COALESCE(
                                                                      (SELECT jsonb_agg(entity_id
                                                                                        ORDER BY entity_id)
                                                                       FROM atlas.decision_mainland_witness_group_targets t
                                                                       WHERE t.group_id=g.id),'[]'::jsonb))
                                 ORDER BY g.id)
                FROM atlas.decision_mainland_witness_groups g
                ),'[]'::jsonb),
  'distinct_groups',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_array(group_a, group_b)
                                 ORDER BY group_a, group_b)
                FROM atlas.decision_mainland_distinct_groups
                ),'[]'::jsonb)
)::text;
