-- Keep versioned document values, without redundant byte checks or formatting identity.
BEGIN;

ALTER TABLE atlas.structured_documents
    DROP COLUMN sha256,
    DROP COLUMN size_bytes,
    DROP CONSTRAINT structured_documents_document_check,
    ALTER COLUMN document TYPE jsonb USING document::jsonb,
    ADD CONSTRAINT structured_documents_document_check CHECK (jsonb_typeof(document) = 'object');

COMMENT ON TABLE atlas.structured_documents IS 'Immutable versioned JSON inputs identified by source_id and version.';

COMMIT;
