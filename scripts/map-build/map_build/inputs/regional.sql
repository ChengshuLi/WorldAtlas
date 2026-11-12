-- The build snapshot format retains its original status fields for V8 compatibility.
WITH RECURSIVE
rev AS (SELECT * FROM atlas.decision_revisions WHERE revision = %(revision)s),
ent AS (SELECT e.* FROM atlas.entity_registry_revisions e JOIN rev d ON e.revision=d.entity_revision),
source_refs(source_id, version) AS (
 SELECT source_id, source_version FROM atlas.decision_features WHERE revision = %(revision)s
 UNION
 SELECT source_id, source_version FROM atlas.decision_list1_entry_evidence_sources WHERE revision = %(revision)s
 UNION
 SELECT source_id, source_version FROM atlas.decision_ecoregion_source_refs WHERE revision = %(revision)s
 UNION
 SELECT dep.parent_source_id, dep.parent_version FROM atlas.source_asset_dependencies dep
 JOIN source_refs r ON (dep.source_id,dep.version)=(r.source_id,r.version)
)
SELECT jsonb_build_object(
 'schema','worldatlas-geography-decision-draft-evidence-v3',
 'serialization','worldatlas-canonical-json-v1', 'source','neon-export',
 'decision_revision',(SELECT jsonb_build_object('id',revision,'entity_revision',entity_revision,'status','draft','evidence',evidence,'reviewed_by',NULL,'reviewed_at',NULL) FROM rev),
 'entity_revision',(SELECT jsonb_build_object('id',revision,'status','draft','reviewed_by',NULL,'reviewed_at',NULL) FROM ent),
 'sources',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.source_id,s.version) FROM (SELECT a.source_id,a.version,a.sha256,a.size_bytes,a.r2_bucket,a.r2_key FROM atlas.source_assets a WHERE EXISTS (SELECT 1 FROM atlas.decision_features f WHERE f.revision=%(revision)s AND (f.source_id,f.source_version)=(a.source_id,a.version)) OR EXISTS (SELECT 1 FROM atlas.decision_list1_entry_evidence_sources e WHERE e.revision=%(revision)s AND (e.source_id,e.source_version)=(a.source_id,a.version)) OR EXISTS (SELECT 1 FROM atlas.decision_ecoregion_source_refs e WHERE e.revision=%(revision)s AND (e.source_id,e.source_version)=(a.source_id,a.version))) s),'[]'::jsonb),
 'source_lineage_assets',COALESCE((SELECT jsonb_agg((to_jsonb(a) - 'created_at') ORDER BY a.source_id,a.version) FROM atlas.source_assets a JOIN source_refs r USING (source_id,version)),'[]'::jsonb),
 'source_lineage_dependencies',COALESCE((SELECT jsonb_agg(to_jsonb(dep) ORDER BY dep.source_id,dep.version,dep.parent_source_id,dep.parent_version) FROM atlas.source_asset_dependencies dep JOIN source_refs r ON (dep.source_id,dep.version)=(r.source_id,r.version)),'[]'::jsonb),
 'entities',COALESCE((SELECT jsonb_agg(to_jsonb(g)-'revision' ORDER BY g.id) FROM atlas.geographic_entities g JOIN ent e USING (revision)),'[]'::jsonb),
 'category_bindings',COALESCE((SELECT jsonb_agg(to_jsonb(b)-'revision' ORDER BY b.code) FROM atlas.review_category_bindings b JOIN ent e USING (revision)),'[]'::jsonb),
 'features',COALESCE((SELECT jsonb_agg(jsonb_build_object('feature_id',f.feature_id,'source_id',f.source_id,'source_version',f.source_version,'source_feature_id',f.source_feature_id,'geometry_sha256',f.geometry_sha256,'coordinate_reference',f.coordinate_reference,'evidence',f.evidence) ORDER BY f.feature_id) FROM atlas.decision_features f JOIN rev d USING (revision)),'[]'::jsonb),
 'endpoints',COALESCE((SELECT jsonb_agg((to_jsonb(p)-'revision') || jsonb_build_object('longitude',p.longitude::text,'latitude',p.latitude::text) ORDER BY p.endpoint_id) FROM atlas.decision_endpoints p JOIN rev d USING (revision)),'[]'::jsonb),
 'routes',COALESCE((SELECT jsonb_agg((to_jsonb(r)-'revision') || jsonb_build_object('points',COALESCE((SELECT jsonb_agg(to_jsonb(p)-'revision'-'route_id' ORDER BY p.ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id),'[]'::jsonb)) ORDER BY r.route_id) FROM atlas.decision_routes r JOIN rev d USING (revision)),'[]'::jsonb),
 'basins',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',b.basin_id,'feature_id',b.feature_id,'source_id',f.source_id,'source_version',f.source_version,'source_feature_id',f.source_feature_id,'geometry_sha256',f.geometry_sha256,'assignment_method',b.method,'tie_rules',b.tie_rules,'evidence',b.evidence,'participant_entity_ids',COALESCE((SELECT jsonb_agg(p.entity_id ORDER BY p.entity_id) FROM atlas.decision_basin_participants p WHERE p.revision=b.revision AND p.basin_id=b.basin_id),'[]'::jsonb)) ORDER BY b.basin_id) FROM atlas.decision_basins b JOIN rev d USING (revision) LEFT JOIN atlas.decision_features f ON (f.revision,f.feature_id)=(b.revision,b.feature_id)),'[]'::jsonb),
 'affiliations',COALESCE((SELECT jsonb_agg((to_jsonb(a)-'revision'-'entity_revision')||jsonb_build_object('decision_revision',a.revision) ORDER BY a.affiliation_id) FROM atlas.decision_affiliations a JOIN rev d USING (revision)),'[]'::jsonb),
 'land_component_witness_rules',COALESCE((SELECT jsonb_agg(to_jsonb(w)-'revision'-'entity_revision' ORDER BY w.rule_id) FROM atlas.decision_land_component_witness_rules w JOIN rev d USING (revision)),'[]'::jsonb),
 'ocean_seeds',COALESCE((SELECT jsonb_agg(to_jsonb(s)-'revision'-'entity_revision' ORDER BY s.seed_id) FROM atlas.decision_ocean_seeds s JOIN rev d USING (revision)),'[]'::jsonb),
 'policies',COALESCE((SELECT jsonb_agg(p.obj ORDER BY p.id) FROM (SELECT policy_id id, jsonb_build_object('id',policy_id,'kind',kind,'definition',definition,'evidence',evidence) obj FROM atlas.decision_policies WHERE revision=%(revision)s UNION ALL SELECT policy_id id,jsonb_build_object('id',policy_id,'kind','ocean_fill','definition',definition,'evidence',evidence) obj FROM atlas.decision_ocean_fill_policies WHERE revision=%(revision)s UNION ALL SELECT policy_id id,jsonb_build_object('id',policy_id,'kind',kind,'definition',definition,'evidence',evidence) obj FROM atlas.decision_water_assignment_policies WHERE revision=%(revision)s) p),'[]'::jsonb) ,
 'list1_entry_evidence_sources',COALESCE((SELECT jsonb_agg((to_jsonb(e)-'revision')||jsonb_build_object('decision_revision',e.revision) ORDER BY e.entry_id,e.role,e.source_id,e.source_version) FROM atlas.decision_list1_entry_evidence_sources e WHERE e.revision=%(revision)s),'[]'::jsonb),
 'affiliation_source_refs','[]'::jsonb,
 'unsupported_affiliation_source_ref_table_present',to_regclass('atlas.decision_affiliation_source_refs') IS NOT NULL,
 'unsupported_point_methods_present',EXISTS (SELECT 1 FROM atlas.decision_affiliations a JOIN atlas.decision_list1_policy_affiliations p ON (p.revision,p.affiliation_id)=(a.revision,a.affiliation_id) WHERE a.revision=%(revision)s AND a.method IN ('source_point_component_v1','raw_json_city_named_region_component_v1')),
 'polygon_affiliation_feature_refs',COALESCE((SELECT jsonb_agg(to_jsonb(f)-'revision' ORDER BY f.affiliation_id,f.role,f.feature_id) FROM atlas.decision_polygon_affiliation_feature_refs f WHERE f.revision=%(revision)s),'[]'::jsonb),
 'polygon_corroboration_refs',COALESCE((SELECT jsonb_agg((to_jsonb(c)-'revision')||jsonb_build_object('decision_revision',c.revision) ORDER BY c.affiliation_id,c.selected_feature_id,c.corroborating_feature_id) FROM atlas.decision_polygon_corroboration_refs c WHERE c.revision=%(revision)s),'[]'::jsonb),
 'ecoregion_source_refs',COALESCE((SELECT jsonb_agg((to_jsonb(e)-'revision')||jsonb_build_object('decision_revision',e.revision) ORDER BY e.affiliation_id,e.role) FROM atlas.decision_ecoregion_source_refs e WHERE e.revision=%(revision)s),'[]'::jsonb),
 'affiliation_feature_refs',COALESCE((SELECT jsonb_agg(to_jsonb(f)-'revision' ORDER BY f.affiliation_id,f.role) FROM atlas.decision_affiliation_feature_refs f WHERE f.revision=%(revision)s),'[]'::jsonb),
 'list1_entries',COALESCE((SELECT jsonb_agg((to_jsonb(e)-'revision'-'old_list1_refs')||jsonb_build_object('decision_revision',e.revision,'affiliation_ids',COALESCE((SELECT jsonb_agg(a.affiliation_id ORDER BY a.affiliation_id) FROM atlas.decision_list1_entry_affiliations a WHERE (a.revision,a.entry_id)=(e.revision,e.entry_id)),'[]'::jsonb)) ORDER BY e.entry_id) FROM atlas.decision_list1_entries e WHERE e.revision=%(revision)s),'[]'::jsonb),
 'list1_policy',(SELECT (to_jsonb(p)-'revision')||jsonb_build_object('decision_revision',p.revision,'entry_ids',COALESCE((SELECT jsonb_agg(e.entry_id ORDER BY e.entry_id) FROM atlas.decision_list1_policy_entries e WHERE e.revision=p.revision),'[]'::jsonb),'affiliation_ids',COALESCE((SELECT jsonb_agg(a.affiliation_id ORDER BY a.affiliation_id) FROM atlas.decision_list1_policy_affiliations a WHERE a.revision=p.revision),'[]'::jsonb)) FROM atlas.decision_list1_policies p WHERE p.revision=%(revision)s)

)::text AS snapshot;
