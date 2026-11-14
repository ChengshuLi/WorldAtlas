-- Preserve JSON values and freeze each stored version; formatting is not identity.
BEGIN;
DO $$
DECLARE
    input text := E'{ "z": 1,\n "a": 2 }\n';
BEGIN
    INSERT INTO atlas.construction_records VALUES
        ('__document_test','1',input::jsonb);
    IF (SELECT document FROM atlas.construction_records
        WHERE source_id='__document_test' AND version='1') IS DISTINCT FROM '{"a":2,"z":1}'::jsonb THEN
        RAISE EXCEPTION 'stored input JSON values changed';
    END IF;
    BEGIN
        INSERT INTO atlas.construction_records VALUES
            ('__document_test','1',input::jsonb);
        RAISE EXCEPTION 'duplicate version accepted';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.construction_records SET document='{}'
        WHERE source_id='__document_test';
        RAISE EXCEPTION 'stored version was edited';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'construction records are immutable; use a new version' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.construction_records VALUES ('__document_test','2','[]');
        RAISE EXCEPTION 'a non-object document was accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    INSERT INTO atlas.construction_records VALUES
        ('__document_test','2',input::jsonb);
END $$;
ROLLBACK;
