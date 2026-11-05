-- Bind parameters from the authenticated Neon connection; this is read-only.
-- Origin values are attestations supplied by the orchestrator, not authentication.
SELECT jsonb_build_object(
  'schema', 'worldatlas-neon-presentation-export-v1',
  'origin', jsonb_build_object('project_id', %(project_id)s, 'branch_id', %(branch_id)s, 'database', current_database()),
  'release', to_jsonb(r),
  'assets', jsonb_build_object('proposal', to_jsonb(p), 'water_presentation', to_jsonb(w), 'references', to_jsonb(f), 'manifest', to_jsonb(m))
) AS snapshot
FROM atlas.review_presentation_releases r
JOIN atlas.source_assets p ON (p.source_id,p.version) = (r.proposal_source_id,r.proposal_source_version)
JOIN atlas.source_assets w ON (w.source_id,w.version) = (r.water_source_id,r.water_source_version)
JOIN atlas.source_assets f ON (f.source_id,f.version) = (r.reference_source_id,r.reference_source_version)
JOIN atlas.source_assets m ON (m.source_id,m.version) = (r.manifest_source_id,r.manifest_source_version)
WHERE r.release_id = %(release_id)s;

