-- A published version points to one complete immutable manifest and approved candidate.
BEGIN;
DO $$
DECLARE
 bundle jsonb:=jsonb_build_object('objects',jsonb_build_object(
 'index.html',jsonb_build_object('r2_key','test/index.html','sha256',repeat('a',64),'size_bytes',1,'content_type','text/html'),
 'rows.u32le.gz',jsonb_build_object('r2_key','test/rows','sha256',repeat('b',64),'size_bytes',2,'content_type','application/gzip'),
 'runs.u32le.gz',jsonb_build_object('r2_key','test/runs','sha256',repeat('c',64),'size_bytes',3,'content_type','application/gzip')),
 'decoded_sha256',jsonb_build_object('rows',repeat('d',64),'runs',repeat('e',64)));
BEGIN
 INSERT INTO atlas.map_releases(release_id,r2_bucket,manifest) VALUES
 ('v99.0-rc1','test',bundle),('v99.0-rc2','test',bundle),('v99.1-rc.1','test',bundle);
 IF (SELECT map_version FROM atlas.map_releases WHERE release_id='v99.1-rc.1')<>'v99.1' THEN
  RAISE EXCEPTION 'candidate version extraction failed'; END IF;
 BEGIN
  INSERT INTO atlas.map_releases(release_id,r2_bucket,manifest) VALUES ('v99.2-rc1','test',bundle#-'{objects,runs.u32le.gz}');
  RAISE EXCEPTION 'a release without both streams was accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.map_publications VALUES ('v99.0','v99.0-rc1',NULL);
  RAISE EXCEPTION 'unapproved release published';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'approve the exact release before publishing' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.map_releases SET manifest=manifest||'{"changed":true}' WHERE release_id='v99.0-rc1';
  RAISE EXCEPTION 'staged contents changed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'only an unapproved release can receive approval' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.map_releases SET approved_by=' ',approved_at=now() WHERE release_id='v99.0-rc1';
  RAISE EXCEPTION 'blank reviewer accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE atlas.map_releases SET approved_by='Reviewer',approved_at=now() WHERE release_id LIKE 'v99.%';
 BEGIN
  UPDATE atlas.map_releases SET approved_by='Another reviewer' WHERE release_id='v99.0-rc1';
  RAISE EXCEPTION 'approval changed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'only an unapproved release can receive approval' THEN RAISE; END IF;
 END;
 BEGIN
  INSERT INTO atlas.map_publications VALUES ('v99.2','v99.0-rc1',NULL);
  RAISE EXCEPTION 'unrelated version name accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 INSERT INTO atlas.map_publications VALUES ('v99.0','v99.0-rc1','index.html'),('v99.1','v99.1-rc.1',NULL);
 BEGIN
  UPDATE atlas.map_publications SET release_id='v99.0-rc2' WHERE map_version='v99.0';
  RAISE EXCEPTION 'official version replaced';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'published versions are immutable' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.map_publications SET homepage_key='index.html' WHERE map_version='v99.1';
  RAISE EXCEPTION 'two publications own one homepage';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  DELETE FROM atlas.map_releases WHERE release_id='v99.0-rc1';
  RAISE EXCEPTION 'published manifest deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
END $$;
ROLLBACK;
