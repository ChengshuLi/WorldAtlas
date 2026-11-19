-- Immutable raw-file identities and editable construction settings.

CREATE TABLE atlas.source_assets (
    id text,
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
    CONSTRAINT source_assets_attribution_check CHECK (atlas.nonblank(attribution)),
    CONSTRAINT source_assets_license_name_check CHECK (atlas.nonblank(license_name)),
    CONSTRAINT source_assets_license_uri_check CHECK (atlas.nonblank(license_uri)),
    CONSTRAINT source_assets_provider_check CHECK (atlas.nonblank(provider)),
    CONSTRAINT source_assets_r2_bucket_check CHECK (atlas.nonblank(r2_bucket)),
    CONSTRAINT source_assets_r2_key_check CHECK (atlas.nonblank(r2_key)),
    CONSTRAINT source_assets_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT source_assets_size_bytes_check CHECK ((size_bytes >= 0)),
    CONSTRAINT source_assets_id_check CHECK (atlas.nonblank(id)),
    CONSTRAINT source_assets_source_uri_check CHECK (atlas.nonblank(source_uri)),
    CONSTRAINT source_assets_title_check CHECK (atlas.nonblank(title)),
    CONSTRAINT source_assets_pkey PRIMARY KEY (id),
    CONSTRAINT source_assets_r2_bucket_r2_key_key UNIQUE (r2_bucket, r2_key)
);

CREATE FUNCTION atlas.guard_source_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF (NEW.id,NEW.r2_bucket,NEW.r2_key,NEW.sha256,NEW.size_bytes,NEW.created_at) IS DISTINCT FROM
    (OLD.id,OLD.r2_bucket,OLD.r2_key,OLD.sha256,OLD.size_bytes,OLD.created_at) THEN
  RAISE EXCEPTION 'source identity and captured bytes are immutable; use a new source ID';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER source_asset_immutable BEFORE UPDATE ON atlas.source_assets FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_identity();

CREATE TABLE atlas.construction_records (
    id text,
    method text NOT NULL,
    arguments jsonb NOT NULL,
    CONSTRAINT construction_records_id_check CHECK (atlas.nonblank(id)),
    CONSTRAINT construction_records_pkey PRIMARY KEY (id)
);

CREATE TABLE atlas.construction_sources (
    construction_id text NOT NULL REFERENCES atlas.construction_records(id) ON DELETE CASCADE,
    source_id text NOT NULL REFERENCES atlas.source_assets(id),
    PRIMARY KEY (construction_id, source_id)
);

-- Source paths are generated from typed Python arguments in construction_contracts.sql.
CREATE FUNCTION atlas.sync_construction_sources() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE sources text[];
BEGIN
 SELECT coalesce(array_agg(source_id), ARRAY[]::text[]) INTO sources
 FROM atlas.construction_source_ids(NEW.method, NEW.arguments) AS refs(source_id);
 DELETE FROM atlas.construction_sources
 WHERE construction_id=NEW.id AND NOT source_id=ANY(sources);
 INSERT INTO atlas.construction_sources(construction_id,source_id)
 SELECT NEW.id,source_id FROM unnest(sources) AS refs(source_id)
 ON CONFLICT DO NOTHING;
 RETURN NULL;
END $$;

CREATE TRIGGER construction_sources_sync AFTER INSERT OR UPDATE OF method, arguments
ON atlas.construction_records FOR EACH ROW EXECUTE FUNCTION atlas.sync_construction_sources();

CREATE FUNCTION atlas.check_construction_source_link() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
  SELECT FROM (VALUES (OLD.construction_id,OLD.source_id),
                      (NEW.construction_id,NEW.source_id)) AS changed(construction_id,source_id)
  JOIN atlas.construction_records c ON c.id=changed.construction_id
  WHERE EXISTS (
   SELECT FROM atlas.construction_sources s
   WHERE s.construction_id=c.id AND s.source_id=changed.source_id
  ) IS DISTINCT FROM EXISTS (
   SELECT FROM atlas.construction_source_ids(c.method,c.arguments) AS expected(source_id)
   WHERE expected.source_id=changed.source_id
  )
 ) THEN RAISE EXCEPTION 'construction source links must match the construction arguments'; END IF;
 RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER construction_source_link_check AFTER INSERT OR UPDATE OR DELETE
ON atlas.construction_sources DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION atlas.check_construction_source_link();
