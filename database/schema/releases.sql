-- Immutable map bundles, publication approval and official-version pointers.

CREATE FUNCTION atlas.valid_release_assets(objects jsonb) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
 SELECT jsonb_typeof(objects)='object' AND NOT EXISTS (
  SELECT 1 FROM jsonb_each(CASE WHEN jsonb_typeof(objects)='object' THEN objects ELSE '{}'::jsonb END) o
  WHERE NOT COALESCE(jsonb_typeof(value)='object'
   AND jsonb_typeof(value->'r2_key')='string' AND length(value->>'r2_key')>0
   AND value->>'sha256' ~ '^[0-9a-f]{64}$'
   AND jsonb_typeof(value->'content_type')='string' AND length(value->>'content_type')>0
   AND CASE WHEN jsonb_typeof(value->'size_bytes')='number' THEN
    (value->>'size_bytes')::numeric>=0 AND trunc((value->>'size_bytes')::numeric)=(value->>'size_bytes')::numeric
    ELSE false END,false))
$_$;

CREATE TABLE atlas.map_releases (
    release_id text NOT NULL,
    map_version text GENERATED ALWAYS AS (regexp_replace(release_id, '-rc\.?[1-9][0-9]*$'::text, ''::text)) STORED,
    r2_bucket text NOT NULL,
    manifest jsonb NOT NULL,
    approved_by text,
    approved_at timestamp with time zone,
    CONSTRAINT map_releases_approved_by_check CHECK ((length(btrim(approved_by)) > 0)),
    CONSTRAINT map_releases_check CHECK (((approved_by IS NULL) = (approved_at IS NULL))),
    CONSTRAINT map_releases_manifest_check CHECK (COALESCE(((jsonb_typeof(manifest) = 'object'::text) AND atlas.valid_release_assets((manifest -> 'objects'::text)) AND ((manifest -> 'objects'::text) ?& ARRAY['rows.u32le.gz'::text, 'runs.u32le.gz'::text]) AND ((manifest #>> '{decoded_sha256,rows}'::text[]) ~ '^[0-9a-f]{64}$'::text) AND ((manifest #>> '{decoded_sha256,runs}'::text[]) ~ '^[0-9a-f]{64}$'::text)), false)),
    CONSTRAINT map_releases_r2_bucket_check CHECK ((length(btrim(r2_bucket)) > 0)),
    CONSTRAINT map_releases_release_id_check CHECK ((release_id ~ '^v[0-9]+\.[0-9]+(-rc\.?[1-9][0-9]*)?$'::text)),
    CONSTRAINT map_releases_pkey PRIMARY KEY (release_id),
    CONSTRAINT map_releases_release_id_map_version_key UNIQUE (release_id, map_version)
);

CREATE FUNCTION atlas.guard_map_release() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.approved_at IS NOT NULL THEN RAISE EXCEPTION 'stage the release before approving it'; END IF;
 ELSIF OLD.approved_at IS NOT NULL OR NEW.approved_at IS NULL
  OR (NEW.release_id,NEW.r2_bucket,NEW.manifest) IS DISTINCT FROM (OLD.release_id,OLD.r2_bucket,OLD.manifest) THEN
  RAISE EXCEPTION 'only an unapproved release can receive approval';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER map_release_guard BEFORE INSERT OR UPDATE ON atlas.map_releases FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_release();

CREATE TABLE atlas.map_publications (
    map_version text NOT NULL,
    release_id text NOT NULL,
    homepage_key text,
    CONSTRAINT map_publications_homepage_key_check CHECK (((homepage_key IS NULL) OR (length(btrim(homepage_key)) > 0))),
    CONSTRAINT map_publications_homepage_key_key UNIQUE (homepage_key),
    CONSTRAINT map_publications_pkey PRIMARY KEY (map_version),
    CONSTRAINT map_publications_release_id_map_version_fkey FOREIGN KEY (release_id, map_version) REFERENCES atlas.map_releases(release_id, map_version)
);

CREATE FUNCTION atlas.guard_map_publication() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF TG_OP='UPDATE' AND (NEW.map_version,NEW.release_id) IS DISTINCT FROM (OLD.map_version,OLD.release_id) THEN
  RAISE EXCEPTION 'published versions are immutable';
 END IF;
 IF TG_OP='INSERT' AND NOT EXISTS (
  SELECT 1 FROM atlas.map_releases WHERE release_id=NEW.release_id AND approved_at IS NOT NULL) THEN
  RAISE EXCEPTION 'approve the exact release before publishing';
 END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER map_publication_guard BEFORE INSERT OR UPDATE ON atlas.map_publications FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_publication();
