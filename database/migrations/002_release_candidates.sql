-- Approve an exact candidate bundle. Working geography stays editable.
BEGIN;

-- Preserve any historical reviews on databases that used the old lifecycle.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM atlas.decision_revisions WHERE status <> 'draft')
       OR EXISTS (SELECT 1 FROM atlas.entity_registry_revisions WHERE status <> 'draft') THEN
        RAISE EXCEPTION 'archive existing decision and entity reviews before upgrading';
    END IF;
END $$;

DROP TRIGGER decision_acceptance_gate ON atlas.decision_revisions;
DROP FUNCTION atlas.block_decision_acceptance_pending_readiness();
DROP TRIGGER decision_revision_guard ON atlas.decision_revisions;
DROP FUNCTION atlas.guard_decision_revision();
DROP TRIGGER entity_revision_guard ON atlas.entity_registry_revisions;
DROP TRIGGER entity_row_guard ON atlas.geographic_entities;
DROP TRIGGER entity_binding_guard ON atlas.review_category_bindings;
DROP FUNCTION atlas.guard_entity_revision();
DROP FUNCTION atlas.guard_entity_revision_row();

DO $$
DECLARE item record;
BEGIN
    FOR item IN
        SELECT tgname, tgrelid::regclass AS relation
        FROM pg_trigger WHERE tgfoid='atlas.guard_decision_row()'::regprocedure
    LOOP
        EXECUTE format('DROP TRIGGER %I ON %s', item.tgname, item.relation);
    END LOOP;
END $$;
DROP FUNCTION atlas.guard_decision_row();

CREATE OR REPLACE FUNCTION atlas.guard_source_build() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.source_graph'));
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP = 'INSERT' THEN
  IF NEW.status = 'locked' THEN RAISE EXCEPTION 'create a build as draft first'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.status = 'locked' THEN RAISE EXCEPTION 'locked builds are immutable'; END IF;
 IF TG_OP = 'UPDATE' AND NEW.status = 'locked' THEN
  IF NOT EXISTS (SELECT 1 FROM atlas.source_build_inputs WHERE build_id=NEW.build_id) THEN RAISE EXCEPTION 'a locked build requires at least one input'; END IF;
  IF NEW.decision_revision IS NULL OR NEW.decision_snapshot_sha256 IS NULL OR NEW.physical_grid_revision IS NULL OR length(trim(NEW.physical_grid_revision)) = 0 OR NEW.physical_grid_sha256 IS NULL OR NEW.software_versions IS NULL THEN RAISE EXCEPTION 'locked build requires decision, grid, hash and software pins'; END IF;
  IF EXISTS (SELECT 1 FROM atlas.decision_features f WHERE f.revision=NEW.decision_revision AND NOT EXISTS (SELECT 1 FROM atlas.source_build_inputs i WHERE i.build_id=NEW.build_id AND i.source_id=f.source_id AND i.version=f.source_version)) THEN RAISE EXCEPTION 'locked build must select every decision source'; END IF;
 END IF;
 RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

ALTER TABLE atlas.decision_revisions
    DROP COLUMN status, DROP COLUMN reviewed_by, DROP COLUMN reviewed_at;
ALTER TABLE atlas.entity_registry_revisions
    DROP COLUMN status, DROP COLUMN reviewed_by, DROP COLUMN reviewed_at;

CREATE TABLE atlas.map_release_candidates (
    candidate_id text PRIMARY KEY CHECK (candidate_id ~ '^v[0-9]+[.][0-9]+-rc[.][1-9][0-9]*$'),
    map_version text GENERATED ALWAYS AS (split_part(candidate_id, '-rc.', 1)) STORED,
    r2_bucket text NOT NULL CHECK (length(btrim(r2_bucket)) > 0),
    manifest jsonb NOT NULL,
    approved_by text,
    approved_at timestamptz,
    CHECK ((approved_by IS NULL AND approved_at IS NULL) OR
           (approved_by IS NOT NULL AND length(btrim(approved_by)) > 0 AND approved_at IS NOT NULL)),
    CHECK (COALESCE(jsonb_typeof(manifest->'inputs') = 'object'
                    AND jsonb_typeof(manifest->'objects') = 'object'
                    AND manifest->'objects' ?& ARRAY['index.html', 'rows.u32le.gz', 'runs.u32le.gz']
                    AND (manifest->'decoded_sha256'->>'rows') ~ '^[0-9a-f]{64}$'
                    AND (manifest->'decoded_sha256'->>'runs') ~ '^[0-9a-f]{64}$', false))
);

CREATE FUNCTION atlas.guard_map_release_candidate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.approved_at IS NOT NULL THEN
            RAISE EXCEPTION 'stage the release candidate before approving it';
        END IF;
    ELSIF OLD.approved_at IS NOT NULL OR NEW.approved_at IS NULL
          OR (NEW.candidate_id, NEW.r2_bucket, NEW.manifest)
             IS DISTINCT FROM (OLD.candidate_id, OLD.r2_bucket, OLD.manifest) THEN
        RAISE EXCEPTION 'only an unapproved candidate can receive approval';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER map_release_candidate_guard BEFORE INSERT OR UPDATE ON atlas.map_release_candidates
    FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_release_candidate();

ALTER TABLE atlas.map_release_objects
    ADD COLUMN candidate_id text REFERENCES atlas.map_release_candidates(candidate_id),
    ADD CONSTRAINT map_release_objects_candidate_required
        CHECK (map_version = 'v8.0' OR candidate_id IS NOT NULL);

CREATE FUNCTION atlas.guard_map_release_object() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    candidate atlas.map_release_candidates%ROWTYPE;
    asset jsonb;
BEGIN
    IF TG_OP = 'UPDATE' AND (OLD.candidate_id IS NOT NULL OR NEW.candidate_id IS NOT NULL) THEN
        RAISE EXCEPTION 'published release objects are immutable';
    END IF;
    IF NEW.candidate_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT * INTO candidate FROM atlas.map_release_candidates WHERE candidate_id=NEW.candidate_id;
    asset := candidate.manifest->'objects'->(NEW.stream || '.u32le.gz');
    IF candidate.approved_at IS NULL
       OR (NEW.map_version, NEW.r2_bucket, NEW.r2_key, NEW.stored_sha256, NEW.size_bytes, NEW.decoded_sha256)
          IS DISTINCT FROM
          (candidate.map_version, candidate.r2_bucket,
           'review/releases/' || candidate.candidate_id || '/' || NEW.stream || '.u32le.gz',
           asset->>'sha256', (asset->>'size_bytes')::bigint, candidate.manifest->'decoded_sha256'->>NEW.stream) THEN
        RAISE EXCEPTION 'release object must match an approved candidate';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER map_release_object_guard BEFORE INSERT OR UPDATE ON atlas.map_release_objects
    FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_release_object();

CREATE FUNCTION atlas.check_map_release_pair() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    release_version text := CASE WHEN TG_OP = 'DELETE' THEN OLD.map_version ELSE NEW.map_version END;
    objects integer;
    candidates integer;
    linked integer;
BEGIN
    SELECT count(*), count(DISTINCT candidate_id), count(candidate_id)
      INTO objects, candidates, linked FROM atlas.map_release_objects WHERE map_version=release_version;
    IF linked > 0 AND (objects <> 2 OR candidates <> 1 OR linked <> 2) THEN
        RAISE EXCEPTION 'publish both streams from one approved candidate together';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER map_release_pair AFTER INSERT OR UPDATE OR DELETE ON atlas.map_release_objects
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_map_release_pair();

COMMENT ON TABLE atlas.map_release_objects IS
    'Versioned row-run map outputs in R2, tied to the approved candidate for new releases.';

COMMIT;
