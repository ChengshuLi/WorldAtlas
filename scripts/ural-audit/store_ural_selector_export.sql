-- psql --set=selector_base64="$(base64 ... | tr -d '\n')"; input must
-- be the deterministic gzip of the exact selector export. This preserves the
-- bytes needed by replay in the same Neon Ural decision, without R2 or GitHub.
\set ON_ERROR_STOP on
BEGIN;
UPDATE atlas.decision_mainland_boundaries
 SET provenance=jsonb_set(provenance,'{selector_pinned_export}',jsonb_build_object(
 'encoding','gzip-base64','source','Neon selected-stage2 export from v2-land-mainland-boundary-draft-1',
 'uncompressed_sha256','615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc',
 'gzip_sha256','756e518fd7dc73a392b860bab5f7c52cc1a8b7c00989e3b151e525fec947b785',
 'base64',:'selector_base64'))
 WHERE revision='ural-spring-geodesic-20261106' AND boundary_id='ural_kara_coast_to_caspian'
 AND geometry_sha256='746e6a85b05e40994e451e49e7df6333b8816dfe1d6624d9c20f9c669e953b32'
 AND NOT (provenance ? 'selector_pinned_export')
 AND encode(sha256(decode(:'selector_base64','base64')),'hex')='756e518fd7dc73a392b860bab5f7c52cc1a8b7c00989e3b151e525fec947b785';
DO $$ BEGIN
 IF (SELECT count(*) FROM atlas.decision_mainland_boundaries
 WHERE revision='ural-spring-geodesic-20261106' AND boundary_id='ural_kara_coast_to_caspian'
 AND encode(sha256(decode(provenance->'selector_pinned_export'->>'base64','base64')),'hex')='756e518fd7dc73a392b860bab5f7c52cc1a8b7c00989e3b151e525fec947b785') <> 1
 THEN RAISE EXCEPTION 'pinned selector export missing or invalid'; END IF;
END $$;
COMMIT;
