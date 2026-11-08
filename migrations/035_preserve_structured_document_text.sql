-- Preserve the JSON text for inputs whose original byte order is pinned.
ALTER TABLE atlas.structured_documents
    DROP CONSTRAINT structured_documents_document_check,
    ALTER COLUMN document TYPE json USING document::text::json,
    ADD CONSTRAINT structured_documents_document_check
        CHECK (json_typeof(document) = 'object');
