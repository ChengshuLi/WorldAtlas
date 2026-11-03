-- Review-only schema. No revisions are accepted by this migration.
-- All writers and acceptance transitions serialize on one transaction lock.
CREATE TABLE atlas.decision_revisions (
 revision text PRIMARY KEY CHECK (length(trim(revision)) > 0),
 entity_revision text NOT NULL REFERENCES atlas.entity_registry_revisions(revision),
 status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','accepted','rejected')),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 reviewed_by text, reviewed_at timestamptz,
 UNIQUE (revision, entity_revision),
 CHECK ((status = 'accepted') = (reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0 AND reviewed_at IS NOT NULL))
);
CREATE TABLE atlas.decision_features (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 feature_id text NOT NULL CHECK (length(trim(feature_id)) > 0),
 source_id text NOT NULL, source_version text NOT NULL,
 source_feature_id text NOT NULL CHECK (length(trim(source_feature_id)) > 0),
 geometry_sha256 text NOT NULL CHECK (geometry_sha256 ~ '^[0-9a-f]{64}$'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision, feature_id),
 FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version)
);
CREATE TABLE atlas.decision_endpoints (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 endpoint_id text NOT NULL CHECK (length(trim(endpoint_id)) > 0),
 name text NOT NULL CHECK (length(trim(name)) > 0),
 longitude numeric NOT NULL CHECK (longitude BETWEEN -180 AND 180),
 latitude numeric NOT NULL CHECK (latitude BETWEEN -90 AND 90),
 derivation jsonb NOT NULL CHECK (jsonb_typeof(derivation) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision, endpoint_id)
);
CREATE TABLE atlas.decision_routes (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 route_id text NOT NULL CHECK (length(trim(route_id)) > 0),
 route_type text NOT NULL CHECK (length(trim(route_type)) > 0),
 parameters jsonb NOT NULL CHECK (jsonb_typeof(parameters) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision, route_id)
);
CREATE TABLE atlas.decision_route_points (
 revision text NOT NULL, route_id text NOT NULL, ordinal integer NOT NULL CHECK (ordinal >= 0),
 endpoint_id text NOT NULL,
 PRIMARY KEY (revision,route_id,ordinal),
 FOREIGN KEY (revision,route_id) REFERENCES atlas.decision_routes(revision,route_id),
 FOREIGN KEY (revision,endpoint_id) REFERENCES atlas.decision_endpoints(revision,endpoint_id)
);
CREATE TABLE atlas.decision_basins (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 basin_id text NOT NULL CHECK (length(trim(basin_id)) > 0),
 feature_id text NOT NULL, method text NOT NULL CHECK (length(trim(method)) > 0),
 tie_rules jsonb NOT NULL CHECK (jsonb_typeof(tie_rules) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,basin_id),
 FOREIGN KEY (revision,feature_id) REFERENCES atlas.decision_features(revision,feature_id)
);
CREATE TABLE atlas.decision_basin_participants (
 revision text NOT NULL, basin_id text NOT NULL, entity_revision text NOT NULL, entity_id bigint NOT NULL,
 PRIMARY KEY (revision,basin_id,entity_id),
 FOREIGN KEY (revision,basin_id) REFERENCES atlas.decision_basins(revision,basin_id),
 FOREIGN KEY (revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),
 FOREIGN KEY (entity_revision,entity_id) REFERENCES atlas.geographic_entities(revision,id)
);
-- Relationship kinds retain provenance and distinguish group membership from overrides.
CREATE TABLE atlas.decision_affiliations (
 revision text NOT NULL, affiliation_id text NOT NULL CHECK (length(trim(affiliation_id)) > 0),
 feature_id text NOT NULL, entity_revision text NOT NULL, entity_id bigint NOT NULL,
 relationship text NOT NULL CHECK (relationship IN ('affiliation','group_membership','override')),
 scope text NOT NULL CHECK (length(trim(scope)) > 0), method text NOT NULL CHECK (length(trim(method)) > 0),
 rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,affiliation_id),
 FOREIGN KEY (revision,feature_id) REFERENCES atlas.decision_features(revision,feature_id),
 FOREIGN KEY (revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),
 FOREIGN KEY (entity_revision,entity_id) REFERENCES atlas.geographic_entities(revision,id)
);
CREATE TABLE atlas.decision_ocean_seeds (
 revision text NOT NULL, seed_id text NOT NULL CHECK (length(trim(seed_id)) > 0), endpoint_id text NOT NULL,
 entity_revision text NOT NULL, entity_id bigint NOT NULL,
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,seed_id),
 FOREIGN KEY (revision,endpoint_id) REFERENCES atlas.decision_endpoints(revision,endpoint_id),
 FOREIGN KEY (revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),
 FOREIGN KEY (entity_revision,entity_id) REFERENCES atlas.geographic_entities(revision,id)
);
CREATE FUNCTION atlas.guard_decision_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP = 'INSERT' THEN
   IF NEW.status <> 'draft' THEN RAISE EXCEPTION 'decision revision must start as draft'; END IF;
   RETURN NEW;
 END IF;
 IF OLD.status <> 'draft' THEN RAISE EXCEPTION 'closed decision revisions are immutable'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 IF NEW.status = 'accepted' THEN
   IF NOT EXISTS (SELECT 1 FROM atlas.entity_registry_revisions WHERE revision = NEW.entity_revision AND status = 'accepted') THEN
     RAISE EXCEPTION 'accepted decisions require an accepted entity registry';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_basins b WHERE b.revision = NEW.revision AND
     (SELECT count(*) FROM atlas.decision_basin_participants p WHERE p.revision=b.revision AND p.basin_id=b.basin_id) < 2) THEN
     RAISE EXCEPTION 'each basin requires at least two participants';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_basin_participants p WHERE p.revision=NEW.revision AND
     (SELECT count(*) FROM atlas.review_category_bindings b WHERE b.revision=p.entity_revision AND b.entity_id=p.entity_id AND b.physical_class='water') <> 1) THEN
     RAISE EXCEPTION 'basin participant requires one water binding';
   END IF;
   IF EXISTS (SELECT 1 FROM atlas.decision_routes r WHERE r.revision = NEW.revision AND
     ((SELECT count(*) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) < 2 OR
      (SELECT min(ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) <> 0 OR
      (SELECT max(ordinal) FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id) <>
      (SELECT count(*) - 1 FROM atlas.decision_route_points p WHERE p.revision=r.revision AND p.route_id=r.route_id))) THEN
     RAISE EXCEPTION 'each route requires contiguous points starting at zero';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER decision_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_revisions FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_revision();
CREATE FUNCTION atlas.guard_decision_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP <> 'INSERT' AND EXISTS (SELECT 1 FROM atlas.decision_revisions WHERE revision=OLD.revision AND status <> 'draft') THEN RAISE EXCEPTION 'closed decision rows are immutable'; END IF;
 IF TG_OP <> 'DELETE' AND EXISTS (SELECT 1 FROM atlas.decision_revisions WHERE revision=NEW.revision AND status <> 'draft') THEN RAISE EXCEPTION 'closed decision rows are immutable'; END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['decision_features','decision_endpoints','decision_routes','decision_route_points','decision_basins','decision_basin_participants','decision_affiliations','decision_ocean_seeds'] LOOP
  EXECUTE format('CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.%I FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row()',t);
 END LOOP;
END $$;
-- Policy values are reviewed data. Consumers must reject unknown/missing policy kinds.
CREATE TABLE atlas.decision_policies (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 policy_id text NOT NULL CHECK (length(trim(policy_id)) > 0),
 kind text NOT NULL CHECK (kind IN ('layer_precedence','overlap','coastline_assignment')),
 definition jsonb NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,policy_id)
);
CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_policies FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
-- Existing entity records must also be frozen for accepted snapshots to be reproducible.
ALTER TABLE atlas.entity_registry_revisions ADD COLUMN reviewed_by text;
ALTER TABLE atlas.entity_registry_revisions ADD COLUMN reviewed_at timestamptz;
ALTER TABLE atlas.entity_registry_revisions ADD CONSTRAINT entity_review_required CHECK
 ((status = 'accepted') = (reviewed_by IS NOT NULL AND length(trim(reviewed_by)) > 0 AND reviewed_at IS NOT NULL));
CREATE FUNCTION atlas.guard_entity_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP='INSERT' THEN
  IF NEW.status <> 'draft' THEN RAISE EXCEPTION 'entity revision must start as draft'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.status <> 'draft' THEN RAISE EXCEPTION 'closed entity revisions are immutable'; END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER entity_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.entity_registry_revisions FOR EACH ROW EXECUTE FUNCTION atlas.guard_entity_revision();
CREATE FUNCTION atlas.guard_entity_revision_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF TG_OP <> 'INSERT' AND EXISTS (SELECT 1 FROM atlas.entity_registry_revisions WHERE revision=OLD.revision AND status <> 'draft') THEN RAISE EXCEPTION 'closed entity rows are immutable'; END IF;
 IF TG_OP <> 'DELETE' AND EXISTS (SELECT 1 FROM atlas.entity_registry_revisions WHERE revision=NEW.revision AND status <> 'draft') THEN RAISE EXCEPTION 'closed entity rows are immutable'; END IF;
 RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER entity_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.geographic_entities FOR EACH ROW EXECUTE FUNCTION atlas.guard_entity_revision_row();
CREATE TRIGGER entity_binding_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.review_category_bindings FOR EACH ROW EXECUTE FUNCTION atlas.guard_entity_revision_row();
-- These fields are mandatory only at lock time, so existing drafts remain valid.
ALTER TABLE atlas.source_builds ADD COLUMN decision_revision text;
ALTER TABLE atlas.source_builds ADD COLUMN decision_snapshot_sha256 text CHECK (decision_snapshot_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE atlas.source_builds ADD COLUMN physical_grid_revision text;
ALTER TABLE atlas.source_builds ADD COLUMN physical_grid_sha256 text CHECK (physical_grid_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE atlas.source_builds ADD COLUMN software_versions jsonb CHECK (jsonb_typeof(software_versions) = 'object');
ALTER TABLE atlas.source_builds ADD FOREIGN KEY (decision_revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision);
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
  IF NOT EXISTS (SELECT 1 FROM atlas.decision_revisions d JOIN atlas.entity_registry_revisions e ON e.revision=d.entity_revision WHERE d.revision=NEW.decision_revision AND d.entity_revision=NEW.entity_revision AND d.status='accepted' AND e.status='accepted') THEN RAISE EXCEPTION 'locked build requires matching accepted revisions'; END IF;
  IF EXISTS (SELECT 1 FROM atlas.decision_features f WHERE f.revision=NEW.decision_revision AND NOT EXISTS (SELECT 1 FROM atlas.source_build_inputs i WHERE i.build_id=NEW.build_id AND i.source_id=f.source_id AND i.version=f.source_version)) THEN RAISE EXCEPTION 'locked build must select every decision source'; END IF;
 END IF;
 RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
