-- One editable recipe per construction ID; structural checks apply to edits too.
BEGIN;
DO $$
DECLARE
 input jsonb := '{"method":"osm_way_chain","source_id":"raw","boundary_id":"boundary","basis":"Join source segments"}';
 invalid jsonb;
BEGIN
 INSERT INTO atlas.construction_records VALUES ('__construction',input);
 UPDATE atlas.construction_records SET document=input || '{"basis":"Updated explanation"}' WHERE source_id='__construction';
 IF (SELECT document->>'basis' FROM atlas.construction_records WHERE source_id='__construction') <> 'Updated explanation' THEN
  RAISE EXCEPTION 'construction edit was not saved'; END IF;
 BEGIN
  INSERT INTO atlas.construction_records VALUES ('__construction',input);
  RAISE EXCEPTION 'duplicate construction ID accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 FOREACH invalid IN ARRAY ARRAY['[]'::jsonb,'{}'::jsonb,input-'method',input-'boundary_id',
 input || '{"method":"unknown"}',input || '{"basis":null}',input || '{"basis":42}',
 input || '{"basis":""}',input || jsonb_build_object('basis',E' \t\n'),input || '{"extra":true}'] LOOP
  BEGIN
   UPDATE atlas.construction_records SET document=invalid WHERE source_id='__construction';
   RAISE EXCEPTION 'invalid construction edit accepted: %',invalid;
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
END $$;
ROLLBACK;
