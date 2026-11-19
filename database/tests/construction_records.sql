-- One editable recipe per construction ID; structural checks apply to edits too.
BEGIN;
INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
VALUES ('raw','Test','Test','test:raw','Test','test:license','Test','test','raw',repeat('a',64),1),
       ('other','Test','Test','test:other','Test','test:license','Test','test','other',repeat('b',64),1);
DO $$
DECLARE
 input jsonb := '{"way_source_ids":["raw"],"feature_id":"boundary"}';
 invalid jsonb;
 explanation text;
BEGIN
 INSERT INTO atlas.construction_records(id,method,arguments,basis)
 VALUES ('__construction','osm_way_chain',input,'Join source segments');
 UPDATE atlas.construction_records SET basis=U&'\00a0東京\3000' WHERE id='__construction';
 IF (SELECT basis FROM atlas.construction_records WHERE id='__construction') IS DISTINCT FROM U&'\00a0東京\3000' THEN
  RAISE EXCEPTION 'construction explanation edit was not saved'; END IF;
 FOREACH explanation IN ARRAY ARRAY[NULL::text,'',E' \t\n',U&'\0085\00a0\3000'] LOOP
  BEGIN
   UPDATE atlas.construction_records SET basis=explanation WHERE id='__construction';
   RAISE EXCEPTION 'null or blank construction explanation accepted';
  EXCEPTION WHEN check_violation OR not_null_violation THEN NULL; END;
 END LOOP;
 BEGIN
  INSERT INTO atlas.construction_records(id,method,arguments,basis)
  VALUES ('__construction','osm_way_chain',input,'Join source segments');
  RAISE EXCEPTION 'duplicate construction ID accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 FOREACH invalid IN ARRAY ARRAY['[]'::jsonb,'{}'::jsonb,input-'feature_id',input-'way_source_ids',
 input || '{"way_source_ids":[1]}',
 input || '{"method":"osm_way_chain"}',input || '{"basis":"Duplicated explanation"}',input || '{"extra":true}'] LOOP
  BEGIN
   UPDATE atlas.construction_records SET arguments=invalid WHERE id='__construction';
   RAISE EXCEPTION 'invalid construction edit accepted: %',invalid;
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
END $$;
DO $$
DECLARE input jsonb := '{"source_id":"raw","id_field":"id","selections":[{"feature_id":"part","source_feature_id":"provider","polygon_containing":[1,2]}]}';
 invalid jsonb;
BEGIN
 INSERT INTO atlas.construction_records(id,method,arguments,basis)
 VALUES ('__polygon_part','selected_vector_features',input,'Select a polygon part');
 FOREACH invalid IN ARRAY ARRAY['null'::jsonb,'[1]'::jsonb,'[1,2,3]'::jsonb,'[1,"2"]'::jsonb] LOOP
  BEGIN
   UPDATE atlas.construction_records SET arguments=jsonb_set(input,'{selections,0,polygon_containing}',invalid)
   WHERE id='__polygon_part';
   RAISE EXCEPTION 'invalid polygon selection point accepted';
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
END $$;
DO $$ BEGIN
 BEGIN
  DELETE FROM atlas.construction_sources WHERE construction_id='__construction' AND source_id='raw';
  SET CONSTRAINTS atlas.construction_source_link_check IMMEDIATE;
  RAISE EXCEPTION 'a construction lost a required raw-source link';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'construction source links must match the construction arguments' THEN RAISE; END IF;
 END;
 BEGIN
  INSERT INTO atlas.construction_sources VALUES ('__construction','other');
  SET CONSTRAINTS atlas.construction_source_link_check IMMEDIATE;
  RAISE EXCEPTION 'a construction gained an unrelated raw-source link';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'construction source links must match the construction arguments' THEN RAISE; END IF;
 END;
 UPDATE atlas.construction_records SET arguments=jsonb_set(arguments,'{way_source_ids}','["other"]')
 WHERE id='__construction';
 SET CONSTRAINTS atlas.construction_source_link_check IMMEDIATE;
 IF (SELECT array_agg(source_id) FROM atlas.construction_sources WHERE construction_id='__construction')
   IS DISTINCT FROM ARRAY['other'] THEN RAISE EXCEPTION 'editing construction arguments did not update the links'; END IF;
END $$;
ROLLBACK;
