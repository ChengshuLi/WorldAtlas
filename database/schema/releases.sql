-- An immutable bundle pins its R2 manifest at releases/<id>/manifest.json.
CREATE TABLE atlas.map_releases (
    id text PRIMARY KEY CHECK (id ~ '^v[0-9]+\.[0-9]+(-rc\.[1-9][0-9]*)?$'),
    map_version text GENERATED ALWAYS AS (split_part(id,'-rc.',1)) STORED,
    r2_bucket text NOT NULL CHECK (atlas.nonblank(r2_bucket)),
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    is_official boolean NOT NULL DEFAULT false,
    is_current boolean NOT NULL DEFAULT false,
    CHECK (NOT is_current OR is_official)
);
CREATE UNIQUE INDEX map_release_official_version ON atlas.map_releases(map_version) WHERE is_official;
CREATE UNIQUE INDEX map_release_current ON atlas.map_releases ((true)) WHERE is_current;
CREATE FUNCTION atlas.guard_map_release() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' THEN
    IF OLD.is_official THEN
      RAISE EXCEPTION 'official release cannot be deleted';
    END IF;
    RETURN OLD;
  END IF;
  IF (NEW.id,NEW.r2_bucket,NEW.manifest_sha256) IS DISTINCT FROM
     (OLD.id,OLD.r2_bucket,OLD.manifest_sha256) THEN
    RAISE EXCEPTION 'release bundle identity is immutable';
  END IF;
  IF OLD.is_official AND NOT NEW.is_official THEN
    RAISE EXCEPTION 'official release status is permanent';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER map_release_guard BEFORE UPDATE OR DELETE ON atlas.map_releases
FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_release();
