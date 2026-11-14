-- Valid constructions preserve JSON values and freeze each stored version.
BEGIN;
DO $$
DECLARE
    input jsonb := '{"method":"osm_way_chain","source_id":"raw","source_version":"1","boundary_id":"boundary","basis":"Join source segments"}';
    invalid jsonb;
BEGIN
    INSERT INTO atlas.construction_records VALUES ('__document_test','1',input);
    IF (SELECT document FROM atlas.construction_records WHERE source_id='__document_test' AND version='1') IS DISTINCT FROM input THEN
        RAISE EXCEPTION 'stored input JSON values changed';
    END IF;
    BEGIN
        INSERT INTO atlas.construction_records VALUES ('__document_test','1',input);
        RAISE EXCEPTION 'duplicate version accepted';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.construction_records SET document=input || '{"basis":"Changed"}' WHERE source_id='__document_test';
        RAISE EXCEPTION 'stored version was edited';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'construction records are immutable; use a new version' THEN RAISE; END IF;
    END;
    FOREACH invalid IN ARRAY ARRAY[
        '[]'::jsonb, '{}'::jsonb, input - 'method', input - 'boundary_id',
        input || '{"method":"unknown"}', input || '{"basis":null}',
        input || '{"basis":42}', input || '{"basis":""}',
        input || jsonb_build_object('basis', E' \t\n'), input || '{"extra":true}'
    ] LOOP
        BEGIN
            INSERT INTO atlas.construction_records VALUES ('__document_test','invalid',invalid);
            RAISE EXCEPTION 'invalid construction accepted: %', invalid;
        EXCEPTION WHEN check_violation THEN NULL; END;
    END LOOP;
    INSERT INTO atlas.construction_records VALUES ('__document_test','2',input);
END $$;
ROLLBACK;
