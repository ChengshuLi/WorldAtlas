WITH source_refs(source_id) AS
  (SELECT source_id
   FROM atlas.source_features
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
               (SELECT jsonb_agg(to_jsonb(b)
                                 ORDER BY b.code)
                FROM atlas.map_category_bindings b
                ),'[]'::jsonb),
  'features',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(f)-'geometry'
                                 ORDER BY f.feature_id)
                FROM atlas.source_features f
                ),'[]'::jsonb),
  'endpoints',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(p))||jsonb_build_object('longitude',
                                                             p.longitude::text, 'latitude', p.latitude::text)
                                 ORDER BY p.endpoint_id)
                FROM atlas.decision_endpoints p
                ),'[]'::jsonb),
  'routes',
    COALESCE(
               (SELECT jsonb_agg(obj
                                 ORDER BY id)
                FROM
                  (SELECT r.route_id id,

           (to_jsonb(r))||jsonb_build_object('points',

                                       COALESCE(
                                                  (SELECT jsonb_agg(to_jsonb(p)-'route_id'
                                                                    ORDER BY p.ordinal)
                                                   FROM atlas.decision_route_points p
                                                   WHERE p.route_id=r.route_id),'[]'::jsonb)) obj
                   FROM atlas.decision_routes r
                   UNION ALL SELECT r.route_id,

            (to_jsonb(r)-'start_boundary_id'-'start_endpoint'-'end_boundary_id'-'end_endpoint')||jsonb_build_object('start_terminal',

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
                                   b.basin_id, 'feature_id', b.feature_id, 'source_id', f.source_id, 'source_feature_id', f.source_feature_id,
                                   'assignment_method', b.method, 'tie_rules', b.tie_rules,
                                   'evidence', b.evidence)
                                 ORDER BY b.basin_id)
                FROM atlas.decision_basins b
                JOIN atlas.source_features f USING(feature_id)
                ),'[]'::jsonb),
  'assignments',
    COALESCE((SELECT jsonb_agg(to_jsonb(a) ORDER BY assignment_id)
              FROM atlas.geographic_assignments a), '[]'::jsonb),
  'assignment_sources',
    COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY assignment_id, source_id)
              FROM atlas.geographic_assignment_sources s), '[]'::jsonb),
  'ocean_seeds',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(s)
                                 ORDER BY seed_id)
                FROM atlas.decision_ocean_seeds s
                ),'[]'::jsonb),
  'policies',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('id',
                                   policy_id, 'kind', kind, 'definition', definition, 'evidence', evidence)
                                 ORDER BY policy_id)
                FROM atlas.decision_policies
                WHERE kind<>'mainland_assignment'),'[]'::jsonb),
  'mainland_boundaries',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(b)||jsonb_build_object('source_refs',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('source_id', source_id, 'relationship',
                                                                                          relationship)
                                                                                        ORDER BY source_id)
                                                                       FROM atlas.decision_mainland_boundary_sources s
                                                                       WHERE s.boundary_id=b.boundary_id),'[]'::jsonb))
                                 ORDER BY boundary_id)
                FROM atlas.decision_mainland_boundaries b
                ),'[]'::jsonb),
  'land_baseline_policy',
    (SELECT definition||jsonb_build_object('region_ids',

                            COALESCE(
                                       (SELECT jsonb_agg(region_id
                                                         ORDER BY region_id)
                                        FROM atlas.decision_mainland_seed_regions
                                        ),'[]'::jsonb), 'mainland_rule_ids',
                            COALESCE(
                                       (SELECT jsonb_agg(rule_id
                                                         ORDER BY rule_id)
                                        FROM atlas.decision_mainland_component_rules
                                        ),'[]'::jsonb))
       FROM atlas.decision_policies
       WHERE kind='mainland_assignment'),
  'seed_regions',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(r)||jsonb_build_object('segments',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('kind',
                                                                                          kind, 'id',
                                                                                          COALESCE(boundary_id,
                                                                                            route_id), 'reverse', reverse)
                                                                                        ORDER BY ordinal)
                                                                       FROM atlas.decision_mainland_region_segments s
                                                                       WHERE s.region_id=r.region_id),'[]'::jsonb))
                                 ORDER BY region_id)
                FROM atlas.decision_mainland_seed_regions r
                ),'[]'::jsonb),
  'mainland_component_rules',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(r)
                                 ORDER BY rule_id)
                FROM atlas.decision_mainland_component_rules r
                ),'[]'::jsonb),
  'mainland_witnesses',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(w)
                                 ORDER BY witness_id)
                FROM atlas.decision_mainland_witnesses w
                ),'[]'::jsonb),
  'mainland_witness_groups',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(g)||jsonb_build_object('witness_ids',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(witness_id
                                                                                        ORDER BY witness_id)
                                                                       FROM atlas.decision_mainland_witness_group_members m
                                                                       WHERE m.group_id=g.group_id),'[]'::jsonb), 'target_entity_ids',
                                                           COALESCE(
                                                                      (SELECT jsonb_agg(entity_id
                                                                                        ORDER BY entity_id)
                                                                       FROM atlas.decision_mainland_witness_group_targets t
                                                                       WHERE t.group_id=g.group_id),'[]'::jsonb))
                                 ORDER BY group_id)
                FROM atlas.decision_mainland_witness_groups g
                ),'[]'::jsonb),
  'distinct_groups',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_array(group_a, group_b)
                                 ORDER BY group_a, group_b)
                FROM atlas.decision_mainland_distinct_groups
                ),'[]'::jsonb)
)::text;
