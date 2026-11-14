-- Raw-file identity is fixed; source descriptions can be corrected.
BEGIN;
DO $$
DECLARE field text;
BEGIN
 INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,
 license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__source','Test','Provider','test:source','Terms','test:terms','Credit','test','file',repeat('a',64),1);
 FOREACH field IN ARRAY ARRAY['source_id','r2_bucket','r2_key','sha256','size_bytes','created_at'] LOOP
  BEGIN
   EXECUTE CASE field
    WHEN 'size_bytes' THEN 'UPDATE atlas.source_assets SET size_bytes=2'
    WHEN 'created_at' THEN 'UPDATE atlas.source_assets SET created_at=created_at + interval ''1 second'''
    WHEN 'sha256' THEN 'UPDATE atlas.source_assets SET sha256=repeat(''b'',64)'
    ELSE format('UPDATE atlas.source_assets SET %I=%I || ''-changed''',field,field)
   END || ' WHERE source_id=''__source''';
   RAISE EXCEPTION 'protected source field was changed: %',field;
  EXCEPTION WHEN raise_exception THEN
   IF SQLERRM<>'source identity and captured bytes are immutable; use a new source ID' THEN RAISE; END IF;
  END;
 END LOOP;
 UPDATE atlas.source_assets SET title='Corrected title',provider='Corrected provider',
 source_uri='test:corrected',license_name='Corrected terms',license_uri='test:terms-corrected',attribution='Corrected credit'
 WHERE source_id='__source';
 BEGIN
  INSERT INTO atlas.source_assets SELECT '__duplicate',title,provider,source_uri,license_name,
   license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,created_at FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'one R2 object was registered twice';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.source_assets SELECT '__invalid',title,provider,source_uri,license_name,
   license_uri,attribution,r2_bucket,'invalid','bad',size_bytes,created_at FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'malformed hash accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 INSERT INTO atlas.construction_records VALUES ('__feature_recipe',
 '{"method":"selected_vector_features","source_id":"__source","basis":"Selected point","id_field":"id","selections":[{"feature_id":"__feature","source_feature_id":"provider"}]}');
 INSERT INTO atlas.source_features(feature_id,source_id,source_feature_id,geometry,construction_id)
 VALUES ('__feature','__source','provider-id','{"type":"Point","coordinates":[0,0]}','__feature_recipe');
 BEGIN
  DELETE FROM atlas.source_assets WHERE source_id='__source';
  RAISE EXCEPTION 'contributing raw source deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
END $$;
ROLLBACK;
