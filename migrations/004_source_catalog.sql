-- Source bytes live in R2. Only register verified inputs selected for the rebuild;
-- this migration deliberately inserts no source records or inferred R2 keys.
CREATE TABLE atlas.source_assets (
    source_id text NOT NULL CHECK (length(trim(source_id)) > 0),
    version text NOT NULL CHECK (length(trim(version)) > 0),
    title text NOT NULL CHECK (length(trim(title)) > 0),
    kind text NOT NULL CHECK (kind IN ('raw','derived')),
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    source_uri text NOT NULL CHECK (length(trim(source_uri)) > 0),
    license_name text NOT NULL CHECK (length(trim(license_name)) > 0),
    license_uri text NOT NULL CHECK (length(trim(license_uri)) > 0),
    attribution text NOT NULL CHECK (length(trim(attribution)) > 0),
    r2_bucket text NOT NULL CHECK (length(trim(r2_bucket)) > 0),
    r2_key text NOT NULL CHECK (length(trim(r2_key)) > 0),
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    provenance jsonb NOT NULL CHECK (jsonb_typeof(provenance) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, version),
    UNIQUE (r2_bucket, r2_key)
);

-- Derived files retain immutable lineage to exact parent versions.
CREATE TABLE atlas.source_asset_dependencies (
    source_id text NOT NULL, version text NOT NULL,
    parent_source_id text NOT NULL, parent_version text NOT NULL,
    relationship text NOT NULL CHECK (length(trim(relationship)) > 0),
    PRIMARY KEY (source_id, version, parent_source_id, parent_version),
    FOREIGN KEY (source_id, version) REFERENCES atlas.source_assets(source_id, version),
    FOREIGN KEY (parent_source_id, parent_version) REFERENCES atlas.source_assets(source_id, version),
    CHECK (source_id <> parent_source_id OR version <> parent_version)
);

CREATE TABLE atlas.source_builds (
    build_id text PRIMARY KEY CHECK (length(trim(build_id)) > 0),
    entity_revision text NOT NULL REFERENCES atlas.entity_registry_revisions(revision),
    code_revision text NOT NULL CHECK (length(trim(code_revision)) > 0),
    git_paths jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(git_paths) = 'array'),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'locked')),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- A build selects exact source versions, with their use and pipeline stage.
CREATE TABLE atlas.source_build_inputs (
    build_id text NOT NULL REFERENCES atlas.source_builds(build_id),
    source_id text NOT NULL,
    version text NOT NULL,
    stage text NOT NULL CHECK (length(trim(stage)) > 0),
    role text NOT NULL CHECK (length(trim(role)) > 0),
    PRIMARY KEY (build_id, source_id, version, stage, role),
    FOREIGN KEY (source_id, version) REFERENCES atlas.source_assets(source_id, version)
);

CREATE TABLE atlas.source_entity_links (
    source_id text NOT NULL,
    version text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    relationship text NOT NULL CHECK (length(trim(relationship)) > 0),
    PRIMARY KEY (source_id, version, entity_revision, entity_id, relationship),
    FOREIGN KEY (source_id, version) REFERENCES atlas.source_assets(source_id, version),
    FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id)
);

-- A source version identifies exact bytes and metadata; correct errors with a new
-- version. A foreign key prevents deletion of an asset referenced by a build.
CREATE FUNCTION atlas.reject_source_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'source records are immutable; use a new source version';
END; $$;
CREATE TRIGGER source_asset_immutable BEFORE UPDATE ON atlas.source_assets
  FOR EACH ROW EXECUTE FUNCTION atlas.reject_source_change();
CREATE FUNCTION atlas.guard_source_build() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('atlas.source_graph'));
  IF TG_OP = 'INSERT' THEN
    IF NEW.status = 'locked' THEN RAISE EXCEPTION 'create a build as draft first'; END IF;
    RETURN NEW;
  END IF;
  IF OLD.status = 'locked' THEN
    RAISE EXCEPTION 'locked builds are immutable';
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.status = 'locked' AND NOT EXISTS
      (SELECT 1 FROM atlas.source_build_inputs WHERE build_id = NEW.build_id) THEN
    RAISE EXCEPTION 'a locked build requires at least one input';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END; $$;
CREATE TRIGGER source_build_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.source_builds
  FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_build();

CREATE FUNCTION atlas.guard_source_build_input() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE old_locked boolean := false; new_locked boolean := false;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('atlas.source_graph'));
  IF TG_OP <> 'INSERT' THEN
    SELECT status = 'locked' INTO old_locked FROM atlas.source_builds WHERE build_id = OLD.build_id;
  END IF;
  IF TG_OP <> 'DELETE' THEN
    SELECT status = 'locked' INTO new_locked FROM atlas.source_builds WHERE build_id = NEW.build_id;
  END IF;
  IF old_locked OR new_locked THEN RAISE EXCEPTION 'locked build inputs are immutable'; END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END; $$;
CREATE TRIGGER source_build_input_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.source_build_inputs
  FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_build_input();

CREATE FUNCTION atlas.guard_source_dependency() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('atlas.source_graph'));
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'source dependencies are immutable; use a new source version';
  END IF;
  IF EXISTS (
    WITH RECURSIVE pinned(source_id, version) AS (
      SELECT i.source_id, i.version FROM atlas.source_build_inputs i
        JOIN atlas.source_builds b USING (build_id) WHERE b.status = 'locked'
      UNION
      SELECT d.parent_source_id, d.parent_version FROM atlas.source_asset_dependencies d
        JOIN pinned p ON (d.source_id, d.version) = (p.source_id, p.version)
    ) SELECT 1 FROM pinned WHERE (source_id, version) = (NEW.source_id, NEW.version)
  ) THEN RAISE EXCEPTION 'locked build lineage is immutable'; END IF;
  IF EXISTS (
    WITH RECURSIVE ancestors(source_id, version) AS (
      SELECT NEW.parent_source_id, NEW.parent_version
      UNION
      SELECT d.parent_source_id, d.parent_version FROM atlas.source_asset_dependencies d
        JOIN ancestors a ON (d.source_id, d.version) = (a.source_id, a.version)
    ) SELECT 1 FROM ancestors WHERE (source_id, version) = (NEW.source_id, NEW.version)
  ) THEN RAISE EXCEPTION 'source dependency cycle'; END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER source_dependency_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.source_asset_dependencies
  FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_dependency();
