-- Preserve exact JSON input text and freeze each stored version.
BEGIN;
DO $$
DECLARE
    input text := E'{ "z": 1,\n "a": 2 }\n';
    input_hash text := encode(sha256(convert_to(input,'UTF8')),'hex');
BEGIN
    INSERT INTO atlas.structured_documents VALUES
        ('__document_test','1',input_hash,octet_length(input),input::json);
    IF (SELECT document::text FROM atlas.structured_documents
        WHERE source_id='__document_test' AND version='1') IS DISTINCT FROM input THEN
        RAISE EXCEPTION 'stored input JSON text changed';
    END IF;
    BEGIN
        INSERT INTO atlas.structured_documents VALUES
            ('__document_test','1',input_hash,octet_length(input),input::json);
        RAISE EXCEPTION 'duplicate version accepted';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.structured_documents SET document='{}'
        WHERE source_id='__document_test';
        RAISE EXCEPTION 'stored version was edited';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'source records are immutable; use a new source version' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.structured_documents VALUES ('__document_test','2',input_hash,2,'[]');
        RAISE EXCEPTION 'a non-object document was accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    INSERT INTO atlas.structured_documents VALUES
        ('__document_test','2',input_hash,octet_length(input),input::json);
END $$;
ROLLBACK;
