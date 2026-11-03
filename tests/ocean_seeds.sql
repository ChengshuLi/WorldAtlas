-- Read-only verification of the imported candidate seed grid coordinates.
DO $$
DECLARE n integer;
BEGIN
 SELECT count(*) INTO n FROM atlas.decision_ocean_seeds s
 JOIN atlas.decision_endpoints e USING (revision)
 JOIN atlas.decision_revisions d ON d.revision=s.revision
 WHERE s.revision='v7-ocean-seed-recovery-draft-1' AND e.endpoint_id=s.endpoint_id
 AND d.status='draft' AND d.entity_revision='v7-category-bootstrap-v1'
 AND e.longitude = -180 + ((e.derivation->>'x')::numeric + 0.5) * 360 / 131072
 AND e.latitude = 90 - ((e.derivation->>'y')::numeric + 0.5) * 360 / 131072
 AND (s.seed_id,s.entity_id) IN (('atlantic',7),('pacific',8),('indian',9),('arctic',10));
 IF n <> 4 THEN RAISE EXCEPTION 'candidate seed import does not match source grid'; END IF;
END $$;
