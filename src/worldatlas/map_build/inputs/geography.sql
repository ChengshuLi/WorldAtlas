WITH rev AS
  (SELECT *
   FROM atlas.decision_revisions
   WHERE revision=%(revision)s),
     ent AS
  (SELECT entity_revision revision
   FROM rev),
     source_refs(source_id, version) AS
  (SELECT source_id,
          source_version
   FROM atlas.decision_features
   WHERE revision=%(revision)s
   UNION SELECT source_id,
                source_version
   FROM atlas.decision_mainland_boundary_sources
   WHERE revision=%(revision)s
   UNION SELECT s.source_id,
                s.source_version
   FROM atlas.decision_case_sources s
   WHERE s.revision=%(revision)s
     AND EXISTS
       (SELECT 1
        FROM atlas.decision_affiliations a
        WHERE (a.revision,
               a.case_id)=(s.revision,
                           s.case_id))
   UNION SELECT ref->>'source_id',
                      ref->>'version'
   FROM
     (SELECT evidence
      FROM atlas.decision_endpoints
      WHERE revision=%(revision)s
      UNION ALL SELECT evidence
      FROM atlas.decision_routes
      WHERE revision=%(revision)s) r
   CROSS JOIN LATERAL jsonb_array_elements(COALESCE(evidence->'source_refs', '[]'::jsonb)) ref)
SELECT jsonb_build_object(
  'schema', 'worldatlas-geography-selection-v2',
  'decision_revision',
    (SELECT jsonb_build_object('id',
                revision, 'entity_revision', entity_revision, 'evidence', evidence)
       FROM rev),
  'entity_revision',
    (SELECT jsonb_build_object('id', revision)
       FROM ent),
  'sources',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('source_id',
                                   source_id, 'version', version)
                                 ORDER BY source_id, version)
                FROM source_refs),'[]'::jsonb),
  'entities',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(e)-'revision'
                                 ORDER BY e.id)
                FROM atlas.geographic_entities e
                JOIN ent USING(revision)),'[]'::jsonb),
  'category_bindings',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(b)-'revision'
                                 ORDER BY b.code)
                FROM atlas.review_category_bindings b
                JOIN ent USING(revision)),'[]'::jsonb),
  'features',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(f)-'revision'-'geometry'
                                 ORDER BY f.feature_id)
                FROM atlas.decision_features f
                WHERE revision=%(revision)s),'[]'::jsonb),
  'endpoints',
    COALESCE(
               (SELECT jsonb_agg((to_jsonb(p)-'revision')||jsonb_build_object('longitude',
                                                             p.longitude::text, 'latitude', p.latitude::text)
                                 ORDER BY p.endpoint_id)
                FROM atlas.decision_endpoints p
                WHERE revision=%(revision)s),'[]'::jsonb),
  'routes',
    COALESCE(
               (SELECT jsonb_agg(obj
                                 ORDER BY id)
                FROM
                  (SELECT r.route_id id,

           (to_jsonb(r)-'revision')||jsonb_build_object('points',

                                       COALESCE(
                                                  (SELECT jsonb_agg(to_jsonb(p)-'revision'-'route_id'
                                                                    ORDER BY p.ordinal)
                                                   FROM atlas.decision_route_points p
                                                   WHERE (p.revision,
                                                   p.route_id)=(r.revision,
                                                         r.route_id)),'[]'::jsonb)) obj
                   FROM atlas.decision_routes r
                   WHERE revision=%(revision)s
                   UNION ALL SELECT r.route_id,

            (to_jsonb(r)-'revision'-'start_boundary_id'-'start_endpoint'-'end_boundary_id'-'end_endpoint')||jsonb_build_object('start_terminal',

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
                   WHERE revision=%(revision)s) r),'[]'::jsonb),
  'basins',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('id',
                                   b.basin_id, 'feature_id', b.feature_id, 'source_id', f.source_id,
                                   'source_version', f.source_version, 'source_feature_id', f.source_feature_id,
                                   'geometry_sha256', f.geometry_sha256, 'assignment_method', b.method, 'tie_rules', b.tie_rules,
                                   'evidence', b.evidence)
                                 ORDER BY b.basin_id)
                FROM atlas.decision_basins b
                JOIN atlas.decision_features f USING(revision,
                                    feature_id)
                WHERE b.revision=%(revision)s),'[]'::jsonb),
  'affiliations',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(a)-'revision'-'entity_revision'
                                 ORDER BY affiliation_id)
                FROM atlas.decision_affiliations a
                WHERE revision=%(revision)s),'[]'::jsonb),
  'cases',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(c)-'revision'
                                 ORDER BY case_id)
                FROM atlas.decision_cases c
                WHERE revision=%(revision)s
                  AND EXISTS
                    (SELECT 1
                     FROM atlas.decision_affiliations a
                     WHERE (a.revision, a.case_id)=(c.revision, c.case_id))),'[]'::jsonb),
  'case_sources',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(s)-'revision'
                                 ORDER BY case_id, source_id, source_version)
                FROM atlas.decision_case_sources s
                WHERE revision=%(revision)s
                  AND EXISTS
                    (SELECT 1
                     FROM atlas.decision_affiliations a
                     WHERE (a.revision, a.case_id)=(s.revision, s.case_id))),'[]'::jsonb),
  'ocean_seeds',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(s)-'revision'-'entity_revision'
                                 ORDER BY seed_id)
                FROM atlas.decision_ocean_seeds s
                WHERE revision=%(revision)s),'[]'::jsonb),
  'policies',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_object('id',
                                   policy_id, 'kind', kind, 'definition', definition, 'evidence', evidence)
                                 ORDER BY policy_id)
                FROM atlas.decision_policies
                WHERE revision=%(revision)s
                  AND kind<>'mainland_assignment'),'[]'::jsonb),
  'mainland_boundaries',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(b)-'revision'||jsonb_build_object('source_refs',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('source_id',
                                                                                          source_id, 'version',
                                                                                          source_version, 'relationship',
                                                                                          relationship)
                                                                                        ORDER BY source_id,
                                                                       source_version)
                                                                       FROM atlas.decision_mainland_boundary_sources s
                                                                       WHERE (s.revision,
                                                             s.boundary_id)=(b.revision,
                                                            b.boundary_id)),'[]'::jsonb))
                                 ORDER BY boundary_id)
                FROM atlas.decision_mainland_boundaries b
                WHERE revision=%(revision)s),'[]'::jsonb),
  'land_baseline_policy',
    (SELECT definition||jsonb_build_object('region_ids',

                            COALESCE(
                                       (SELECT jsonb_agg(region_id
                                                         ORDER BY region_id)
                                        FROM atlas.decision_mainland_seed_regions
                                        WHERE revision=%(revision)s),'[]'::jsonb), 'mainland_rule_ids',
                            COALESCE(
                                       (SELECT jsonb_agg(rule_id
                                                         ORDER BY rule_id)
                                        FROM atlas.decision_mainland_component_rules
                                        WHERE revision=%(revision)s),'[]'::jsonb))
       FROM atlas.decision_policies
       WHERE revision=%(revision)s
         AND kind='mainland_assignment'),
  'seed_regions',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(r)-'revision'||jsonb_build_object('segments',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(jsonb_build_object('kind',
                                                                                          kind, 'id',
                                                                                          COALESCE(boundary_id,
                                                                                            route_id), 'reverse', reverse)
                                                                                        ORDER BY ordinal)
                                                                       FROM atlas.decision_mainland_region_segments s
                                                                       WHERE (s.revision,
                                                                       s.region_id)=(r.revision,
                                                                              r.region_id)),'[]'::jsonb))
                                 ORDER BY region_id)
                FROM atlas.decision_mainland_seed_regions r
                WHERE revision=%(revision)s),'[]'::jsonb),
  'mainland_component_rules',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(r)-'revision'-'entity_revision'
                                 ORDER BY rule_id)
                FROM atlas.decision_mainland_component_rules r
                WHERE revision=%(revision)s),'[]'::jsonb),
  'mainland_witnesses',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(w)-'revision'
                                 ORDER BY witness_id)
                FROM atlas.decision_mainland_witnesses w
                WHERE revision=%(revision)s),'[]'::jsonb),
  'mainland_witness_groups',
    COALESCE(
               (SELECT jsonb_agg(to_jsonb(g)-'revision'||jsonb_build_object('witness_ids',

                                                           COALESCE(
                                                                      (SELECT jsonb_agg(witness_id
                                                                                        ORDER BY witness_id)
                                                                       FROM atlas.decision_mainland_witness_group_members m
                                                                       WHERE (m.revision,
                                                                      m.group_id)=(g.revision,
                                                                           g.group_id)),'[]'::jsonb), 'target_entity_ids',
                                                           COALESCE(
                                                                      (SELECT jsonb_agg(entity_id
                                                                                        ORDER BY entity_id)
                                                                       FROM atlas.decision_mainland_witness_group_targets t
                                                                       WHERE (t.revision,
                                                                      t.group_id)=(g.revision,
                                                                           g.group_id)),'[]'::jsonb))
                                 ORDER BY group_id)
                FROM atlas.decision_mainland_witness_groups g
                WHERE revision=%(revision)s),'[]'::jsonb),
  'distinct_groups',
    COALESCE(
               (SELECT jsonb_agg(jsonb_build_array(group_a, group_b)
                                 ORDER BY group_a, group_b)
                FROM atlas.decision_mainland_distinct_groups
                WHERE revision=%(revision)s),'[]'::jsonb)
)::text;
