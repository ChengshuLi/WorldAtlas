-- Schema-only; no geometry, source data or decisions. Apply only on an authorized draft branch.
 CREATE TABLE atlas.decision_mainland_boundaries (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
  boundary_id text NOT NULL CHECK(length(trim(boundary_id))>0),
  method text NOT NULL CHECK(method='stored_linestring_v1'),
  execution_status text NOT NULL CHECK(execution_status='selected_for_research'),
  geometry jsonb NOT NULL CHECK(jsonb_typeof(geometry)='object' AND geometry->>'type'='LineString' AND jsonb_typeof(geometry->'coordinates')='array' AND jsonb_array_length(geometry->'coordinates')>=2),
  geometry_sha256 text NOT NULL CHECK(geometry_sha256 ~ '^[0-9a-f]{64}$'),
  geometry_hash_method text NOT NULL CHECK(geometry_hash_method='binary64-sorted-compact-geojson-v1'),
  coordinate_reference text NOT NULL CHECK(coordinate_reference='OGC:CRS84'),
  provenance jsonb NOT NULL CHECK(jsonb_typeof(provenance)='object'),PRIMARY KEY(revision,boundary_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_boundaries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_boundary_sources (
  revision text NOT NULL,boundary_id text NOT NULL,source_id text NOT NULL,source_version text NOT NULL,
  relationship text NOT NULL CHECK(length(trim(relationship))>0),
  PRIMARY KEY(revision,boundary_id,source_id,source_version),
  FOREIGN KEY(revision,boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision,boundary_id),
  FOREIGN KEY(source_id,source_version) REFERENCES atlas.source_assets(source_id,version));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_boundary_sources FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.distance_policy_versions (
  policy_id text NOT NULL,version text NOT NULL,algorithm text NOT NULL,units text NOT NULL,
  semi_major_axis_m text NOT NULL,inverse_flattening text NOT NULL,PRIMARY KEY(policy_id,version));
 CREATE TRIGGER version_immutable BEFORE UPDATE OR DELETE ON atlas.distance_policy_versions FOR EACH ROW EXECUTE FUNCTION atlas.reject_source_change();
 CREATE TABLE atlas.decision_distance_policy_selections (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),policy_id text NOT NULL,version text NOT NULL,
  execution_status text NOT NULL CHECK(execution_status='selected_for_research'),PRIMARY KEY(revision,policy_id),
  FOREIGN KEY(policy_id,version) REFERENCES atlas.distance_policy_versions(policy_id,version));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_distance_policy_selections FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
