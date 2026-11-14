-- Immutable raw-file identities and editable construction settings.

CREATE TABLE atlas.source_assets (
    source_id text NOT NULL,
    title text NOT NULL,
    provider text NOT NULL,
    source_uri text NOT NULL,
    license_name text NOT NULL,
    license_uri text NOT NULL,
    attribution text NOT NULL,
    r2_bucket text NOT NULL,
    r2_key text NOT NULL,
    sha256 text NOT NULL,
    size_bytes bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_assets_attribution_check CHECK ((length(TRIM(BOTH FROM attribution)) > 0)),
    CONSTRAINT source_assets_license_name_check CHECK ((length(TRIM(BOTH FROM license_name)) > 0)),
    CONSTRAINT source_assets_license_uri_check CHECK ((length(TRIM(BOTH FROM license_uri)) > 0)),
    CONSTRAINT source_assets_provider_check CHECK ((length(TRIM(BOTH FROM provider)) > 0)),
    CONSTRAINT source_assets_r2_bucket_check CHECK ((length(TRIM(BOTH FROM r2_bucket)) > 0)),
    CONSTRAINT source_assets_r2_key_check CHECK ((length(TRIM(BOTH FROM r2_key)) > 0)),
    CONSTRAINT source_assets_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT source_assets_size_bytes_check CHECK ((size_bytes >= 0)),
    CONSTRAINT source_assets_source_id_check CHECK ((length(TRIM(BOTH FROM source_id)) > 0)),
    CONSTRAINT source_assets_source_uri_check CHECK ((length(TRIM(BOTH FROM source_uri)) > 0)),
    CONSTRAINT source_assets_title_check CHECK ((length(TRIM(BOTH FROM title)) > 0)),
    CONSTRAINT source_assets_pkey PRIMARY KEY (source_id),
    CONSTRAINT source_assets_r2_bucket_r2_key_key UNIQUE (r2_bucket, r2_key)
);

CREATE FUNCTION atlas.guard_source_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF (NEW.source_id,NEW.r2_bucket,NEW.r2_key,NEW.sha256,NEW.size_bytes,NEW.created_at) IS DISTINCT FROM
    (OLD.source_id,OLD.r2_bucket,OLD.r2_key,OLD.sha256,OLD.size_bytes,OLD.created_at) THEN
  RAISE EXCEPTION 'source identity and captured bytes are immutable; use a new source ID';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER source_asset_immutable BEFORE UPDATE ON atlas.source_assets FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_identity();

CREATE TABLE atlas.construction_records (
    source_id text NOT NULL,
    document jsonb NOT NULL,
    CONSTRAINT construction_records_source_id_check CHECK ((length(btrim(source_id)) > 0)),
    CONSTRAINT construction_records_pkey PRIMARY KEY (source_id)
);
