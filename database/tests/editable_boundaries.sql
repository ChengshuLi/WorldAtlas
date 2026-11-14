BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__source','Test','Provider','test:source','Terms','test:terms','Credit','test','source',repeat('a',64),1);
 INSERT INTO atlas.decision_mainland_boundaries VALUES ('__line','{"type":"LineString","coordinates":[[0,0],[1,1]]}',repeat('b',64),'OGC:CRS84','{"note":"retain"}',NULL);
 INSERT INTO atlas.decision_mainland_boundary_sources VALUES ('__line','__source','construction_input');
 UPDATE atlas.decision_mainland_boundaries SET geometry='{"type":"LineString","coordinates":[[0,0],[2,2]]}',geometry_sha256=repeat('c',64);
 IF NOT EXISTS (SELECT FROM atlas.decision_mainland_boundaries b JOIN atlas.decision_mainland_boundary_sources s USING(boundary_id)
 WHERE b.geometry_sha256=repeat('c',64) AND b.provenance->>'note'='retain' AND s.source_id='__source') THEN
 RAISE EXCEPTION 'boundary edit lost source links or notes'; END IF;
 BEGIN
  UPDATE atlas.decision_mainland_boundaries SET geometry='{"type":"Point","coordinates":[0,0]}';
  RAISE EXCEPTION 'point accepted as boundary';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.decision_mainland_boundaries SET geometry='{}';
  RAISE EXCEPTION 'missing coordinates accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.decision_mainland_boundaries SET construction_id='missing';
  RAISE EXCEPTION 'missing construction accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
END $$;
ROLLBACK;
