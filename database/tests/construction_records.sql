-- One editable recipe per construction ID; structural checks apply to edits too.
BEGIN;
INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
VALUES ('raw','Test','Test','test:raw','Test','test:license','Test','test','raw',repeat('a',64),1);
DO $$
DECLARE
 input jsonb := '{"method":"osm_way_chain","source_id":"raw","feature_id":"boundary","source_feature_id":"manifest.json","basis":"Join source segments"}';
 invalid jsonb;
BEGIN
 INSERT INTO atlas.construction_records VALUES ('__construction',input);
 UPDATE atlas.construction_records SET document=input || '{"basis":"Updated explanation"}' WHERE id='__construction';
 IF (SELECT document->>'basis' FROM atlas.construction_records WHERE id='__construction') <> 'Updated explanation' THEN
  RAISE EXCEPTION 'construction edit was not saved'; END IF;
 BEGIN
  INSERT INTO atlas.construction_records VALUES ('__construction',input);
  RAISE EXCEPTION 'duplicate construction ID accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 FOREACH invalid IN ARRAY ARRAY['[]'::jsonb,'{}'::jsonb,input-'method',input-'feature_id',
 input || '{"method":"unknown"}',input || '{"basis":null}',input || '{"basis":42}',
 input || '{"basis":""}',input || jsonb_build_object('basis',E' \t\n'),input || '{"extra":true}'] LOOP
  BEGIN
   UPDATE atlas.construction_records SET document=invalid WHERE id='__construction';
   RAISE EXCEPTION 'invalid construction edit accepted: %',invalid;
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
END $$;
DO $$
DECLARE input jsonb := '{"method":"selected_vector_features","source_id":"raw","basis":"Select a polygon part","id_field":"id","selections":[{"feature_id":"part","source_feature_id":"provider","polygon_containing":[1,2]}]}';
 invalid jsonb;
BEGIN
 INSERT INTO atlas.construction_records VALUES ('__polygon_part',input);
 FOREACH invalid IN ARRAY ARRAY['null'::jsonb,'[1]'::jsonb,'[1,2,3]'::jsonb,'[1,"2"]'::jsonb] LOOP
  BEGIN
   UPDATE atlas.construction_records SET document=jsonb_set(input,'{selections,0,polygon_containing}',invalid)
   WHERE id='__polygon_part';
   RAISE EXCEPTION 'invalid polygon selection point accepted';
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
END $$;
ROLLBACK;
