WITH RECURSIVE
rev AS (SELECT * FROM atlas.decision_revisions WHERE revision = %(revision)s),
ent AS (SELECT e.* FROM atlas.entity_registry_revisions e JOIN rev d ON e.revision=d.entity_revision),
source_refs(source_id, version) AS (
 SELECT source_id, source_version FROM atlas.decision_features WHERE revision = %(revision)s
 UNION
 SELECT dep.parent_source_id, dep.parent_version FROM atlas.source_asset_dependencies dep
 JOIN source_refs r ON (dep.source_id,dep.version)=(r.source_id,r.version)
)
SELECT jsonb_build_object(
 'schema','worldatlas-geography-decision-draft-evidence-v1',
 'serialization','worldatlas-canonical-json-v1', 'source','neon-export',
 'decision_revision',(SELECT jsonb_build_object('id',revision,'entity_revision',entity_revision,'status',status,'evidence',evidence,'reviewed_by',reviewed_by,'reviewed_at',reviewed_at) FROM rev),
 'entity_revision',(SELECT jsonb_build_object('id',revision,'status',status,'reviewed_by',reviewed_by,'reviewed_at',reviewed_at) FROM ent),
 'sources',COALESCE((SELECT jsonb_agg(to_jsonb(s) ORDER BY s.source_id,s.version) FROM (SELECT a.source_id,a.version,a.sha256,a.size_bytes,a.r2_bucket,a.r2_key FROM atlas.source_assets a WHERE EXISTS (SELECT 1 FROM atlas.decision_features f WHERE f.revision=%(revision)s AND (f.source_id,f.source_version)=(a.source_id,a.version))) s),'[]'::jsonb),
 'source_lineage_assets',COALESCE((SELECT jsonb_agg(to_jsonb(a) - 'created_at' ORDER BY a.source_id,a.version) FROM atlas.source_assets a JOIN source_refs r USING (source_id,version)),'[]'::jsonb),
 'source_lineage_dependencies',COALESCE((SELECT jsonb_agg(to_jsonb(dep) ORDER BY dep.source_id,dep.version,dep.parent_source_id,dep.parent_version) FROM atlas.source_asset_dependencies dep JOIN source_refs r ON (dep.source_id,dep.version)=(r.source_id,r.version)),'[]'::jsonb),
 'entities',COALESCE((SELECT jsonb_agg(to_jsonb(g)-'revision' ORDER BY g.id) FROM atlas.geographic_entities g JOIN ent e USING (revision)),'[]'::jsonb),
 'category_bindings',COALESCE((SELECT jsonb_agg(to_jsonb(b)-'revision' ORDER BY b.code) FROM atlas.review_category_bindings b JOIN ent e USING (revision)),'[]'::jsonb),
 'features',COALESCE((SELECT jsonb_agg(to_jsonb(f)-'revision' ORDER BY f.feature_id) FROM atlas.decision_features f JOIN rev d USING (revision)),'[]'::jsonb),
 'endpoints',COALESCE((SELECT jsonb_agg(to_jsonb(p)-'revision' ORDER BY p.endpoint_id) FROM atlas.decision_endpoints p JOIN rev d USING (revision)),'[]'::jsonb),
 'routes',COALESCE((SELECT jsonb_agg((to_jsonb(r)-'revision') || jsonb_build_object('points',COALESCE((SELECT jsonb_agg(to_jsonb(p)-'revision'-'route_id' ORDER BY p.ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id),'[]'::jsonb)) ORDER BY r.route_id) FROM atlas.decision_routes r JOIN rev d USING (revision)),'[]'::jsonb),
 'basins',COALESCE((SELECT jsonb_agg(jsonb_build_object('id',b.basin_id,'feature_id',b.feature_id,'source_id',f.source_id,'source_version',f.source_version,'source_feature_id',f.source_feature_id,'geometry_sha256',f.geometry_sha256,'assignment_method',b.method,'tie_rules',b.tie_rules,'evidence',b.evidence,'participant_entity_ids',COALESCE((SELECT jsonb_agg(p.entity_id ORDER BY p.entity_id) FROM atlas.decision_basin_participants p WHERE p.revision=b.revision AND p.basin_id=b.basin_id),'[]'::jsonb)) ORDER BY b.basin_id) FROM atlas.decision_basins b JOIN rev d USING (revision) LEFT JOIN atlas.decision_features f ON (f.revision,f.feature_id)=(b.revision,b.feature_id)),'[]'::jsonb),
 'affiliations',COALESCE((SELECT jsonb_agg(to_jsonb(a)-'revision'-'entity_revision' ORDER BY a.affiliation_id) FROM atlas.decision_affiliations a JOIN rev d USING (revision)),'[]'::jsonb),
 'ocean_seeds',COALESCE((SELECT jsonb_agg(to_jsonb(s)-'revision'-'entity_revision' ORDER BY s.seed_id) FROM atlas.decision_ocean_seeds s JOIN rev d USING (revision)),'[]'::jsonb),
 'policies',COALESCE((SELECT jsonb_agg(p.obj ORDER BY p.id) FROM (SELECT policy_id id, jsonb_build_object('id',policy_id,'kind',kind,'definition',definition,'evidence',evidence) obj FROM atlas.decision_policies WHERE revision=%(revision)s UNION ALL SELECT policy_id id,jsonb_build_object('id',policy_id,'kind','ocean_fill','definition',definition,'evidence',evidence) obj FROM atlas.decision_ocean_fill_policies WHERE revision=%(revision)s) p),'[]'::jsonb)
)::text AS snapshot;
