-- Raw byte identity is immutable; descriptive corrections do not duplicate files.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.source_assets(source_id,version,title,provider,source_uri,license_name,
 license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__source','1','Test','Provider','test:source','Terms','test:terms','Credit','test','file',repeat('a',64),1);
 BEGIN
  UPDATE atlas.source_assets SET sha256=repeat('b',64) WHERE source_id='__source';
  RAISE EXCEPTION 'source byte identity was changed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'source identity and captured bytes are immutable; use a new source version' THEN RAISE; END IF;
 END;
 UPDATE atlas.source_assets SET title='Corrected title',license_name='Corrected terms',attribution='Corrected credit'
 WHERE source_id='__source';
 IF NOT EXISTS (SELECT FROM atlas.source_assets WHERE source_id='__source' AND title='Corrected title'
 AND r2_key='file' AND sha256=repeat('a',64)) THEN RAISE EXCEPTION 'metadata correction changed source bytes'; END IF;
 BEGIN
  INSERT INTO atlas.source_assets SELECT '__duplicate',version,title,provider,source_uri,license_name,
   license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,created_at FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'one R2 object was registered twice';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.source_assets SELECT '__invalid',version,title,provider,source_uri,license_name,
   license_uri,attribution,r2_bucket,'invalid','bad',size_bytes,created_at FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'malformed hash accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__sources');
 INSERT INTO atlas.decision_revisions VALUES ('__sources','__sources','{}');
 INSERT INTO atlas.decision_features(revision,feature_id,source_id,source_version,source_feature_id,geometry_sha256,evidence)
 VALUES ('__sources','feature','__source','1','provider-id',repeat('b',64),'{}');
 BEGIN
  DELETE FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'contributing raw source deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
END $$;
ROLLBACK;
