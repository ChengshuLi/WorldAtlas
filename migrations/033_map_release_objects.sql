CREATE TABLE atlas.map_release_objects (
    map_version text NOT NULL CHECK (length(btrim(map_version)) > 0),
    stream text NOT NULL CHECK (stream IN ('rows', 'runs')),
    r2_bucket text NOT NULL CHECK (length(btrim(r2_bucket)) > 0),
    r2_key text NOT NULL CHECK (length(btrim(r2_key)) > 0),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    stored_sha256 text NOT NULL CHECK (stored_sha256 ~ '^[0-9a-f]{64}$'),
    decoded_sha256 text NOT NULL CHECK (decoded_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (map_version, stream),
    UNIQUE (r2_bucket, r2_key)
);

COMMENT ON TABLE atlas.map_release_objects IS
    'Versioned row-run map outputs in R2. Recording an object does not approve its geography.';
COMMENT ON COLUMN atlas.map_release_objects.size_bytes IS
    'Byte length of the stored R2 object before gzip decompression.';
COMMENT ON COLUMN atlas.map_release_objects.stored_sha256 IS
    'SHA-256 of the stored R2 object.';
COMMENT ON COLUMN atlas.map_release_objects.decoded_sha256 IS
    'SHA-256 of the uncompressed little-endian u32 stream.';
