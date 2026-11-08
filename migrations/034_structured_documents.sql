CREATE TABLE atlas.structured_documents (
    source_id text NOT NULL CHECK (length(btrim(source_id)) > 0),
    version text NOT NULL CHECK (length(btrim(version)) > 0),
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    document jsonb NOT NULL CHECK (jsonb_typeof(document) = 'object'),
    PRIMARY KEY (source_id, version)
);

CREATE TRIGGER structured_document_immutable
    BEFORE UPDATE ON atlas.structured_documents
    FOR EACH ROW EXECUTE FUNCTION atlas.reject_source_change();

COMMENT ON TABLE atlas.structured_documents IS
    'Versioned pipeline inputs stored in Neon. Size and SHA-256 refer to the selected serialized document.';
