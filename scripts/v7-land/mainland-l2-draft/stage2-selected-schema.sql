-- Schema only. Apply once on an authorized draft branch after the base mainland schema.
 CREATE TABLE atlas.decision_stage1_source_inputs (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
  role text NOT NULL CHECK(role IN ('physical_land','inland_water')),
  ordinal integer NOT NULL CHECK(ordinal>=0),source_id text NOT NULL,source_version text NOT NULL,
  execution_status text NOT NULL CHECK(execution_status='selected_for_research'),
  PRIMARY KEY(revision,role,ordinal), UNIQUE(revision,source_id,source_version),
  FOREIGN KEY(source_id,source_version) REFERENCES atlas.source_assets(source_id,version));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_stage1_source_inputs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_closure_routes (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),route_id text NOT NULL,
  route_type text NOT NULL CHECK(route_type='stored_linestring_v1'),role text NOT NULL CHECK(role='water_closure'),
  execution_status text NOT NULL CHECK(execution_status='selected_for_research'),geometry jsonb NOT NULL CHECK(jsonb_typeof(geometry)='object' AND geometry->>'type'='LineString' AND jsonb_typeof(geometry->'coordinates')='array' AND jsonb_array_length(geometry->'coordinates')>=2),
  geometry_sha256 text NOT NULL CHECK(geometry_sha256 ~ '^[0-9a-f]{64}$'),geometry_hash_method text NOT NULL CHECK(geometry_hash_method='binary64-sorted-compact-geojson-v1'),coordinate_reference text NOT NULL CHECK(coordinate_reference='OGC:CRS84'),closure_method text NOT NULL CHECK(closure_method='physical_terminal_closure_v1'),
  start_boundary_id text NOT NULL,start_endpoint text NOT NULL CHECK(start_endpoint IN ('start','end')),end_boundary_id text NOT NULL,end_endpoint text NOT NULL CHECK(end_endpoint IN ('start','end')),provenance jsonb NOT NULL CHECK(jsonb_typeof(provenance)='object'),
  PRIMARY KEY(revision,route_id),FOREIGN KEY(revision,start_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision,boundary_id),FOREIGN KEY(revision,end_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision,boundary_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_closure_routes FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_closure_sources (
  revision text NOT NULL,route_id text NOT NULL,source_id text NOT NULL,source_version text NOT NULL,
  PRIMARY KEY(revision,route_id,source_id,source_version),FOREIGN KEY(revision,route_id) REFERENCES atlas.decision_mainland_closure_routes(revision,route_id),FOREIGN KEY(source_id,source_version) REFERENCES atlas.source_assets(source_id,version));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_closure_sources FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_seed_regions (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),region_id text NOT NULL,execution_status text NOT NULL CHECK(execution_status='selected_for_research'),
  geometry_sha256 text NOT NULL CHECK(geometry_sha256 ~ '^[0-9a-f]{64}$'),geometry_hash_method text NOT NULL CHECK(geometry_hash_method='binary64-sorted-compact-geojson-v1'),witnesses jsonb NOT NULL CHECK(jsonb_typeof(witnesses)='array'),PRIMARY KEY(revision,region_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_seed_regions FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_region_segments (
  revision text NOT NULL,region_id text NOT NULL,ordinal integer NOT NULL CHECK(ordinal>=0),kind text NOT NULL CHECK(kind IN ('boundary','route')),
  boundary_id text,route_id text,start_index integer NOT NULL CHECK(start_index>=0),end_index integer NOT NULL CHECK(end_index>start_index),reverse boolean NOT NULL,
  PRIMARY KEY(revision,region_id,ordinal),FOREIGN KEY(revision,region_id) REFERENCES atlas.decision_mainland_seed_regions(revision,region_id),
  FOREIGN KEY(revision,boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision,boundary_id),FOREIGN KEY(revision,route_id) REFERENCES atlas.decision_mainland_closure_routes(revision,route_id),
  CHECK((kind='boundary' AND boundary_id IS NOT NULL AND route_id IS NULL) OR (kind='route' AND route_id IS NOT NULL AND boundary_id IS NULL)));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_region_segments FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_witnesses (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),witness_id text NOT NULL,method text NOT NULL CHECK(method='source_point_named_region_v1'),execution_status text NOT NULL CHECK(execution_status='selected_for_research'),point_feature_id text NOT NULL,identity_feature_id text NOT NULL,point_name text NOT NULL,identity_name text NOT NULL,identity_class text NOT NULL,id_property text NOT NULL,identity_id_property text NOT NULL,identity_name_property text NOT NULL,identity_class_property text NOT NULL,radius_cells integer NOT NULL CHECK(radius_cells BETWEEN 0 AND 100),max_water_cells integer NOT NULL CHECK(max_water_cells>=0),rationale text NOT NULL,
  PRIMARY KEY(revision,witness_id),FOREIGN KEY(revision,point_feature_id) REFERENCES atlas.decision_features(revision,feature_id),FOREIGN KEY(revision,identity_feature_id) REFERENCES atlas.decision_features(revision,feature_id),CHECK(point_feature_id<>identity_feature_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_witnesses FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_witness_groups (
  revision text NOT NULL REFERENCES atlas.decision_revisions(revision),group_id text NOT NULL,role text NOT NULL CHECK(role IN ('mainland','sentinel')),execution_status text NOT NULL CHECK(execution_status='selected_for_research'),rationale text NOT NULL,PRIMARY KEY(revision,group_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_witness_groups FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_witness_group_members (
  revision text NOT NULL,group_id text NOT NULL,witness_id text NOT NULL,ordinal integer NOT NULL CHECK(ordinal>=0),PRIMARY KEY(revision,group_id,witness_id),UNIQUE(revision,group_id,ordinal),UNIQUE(revision,witness_id),FOREIGN KEY(revision,group_id) REFERENCES atlas.decision_mainland_witness_groups(revision,group_id),FOREIGN KEY(revision,witness_id) REFERENCES atlas.decision_mainland_witnesses(revision,witness_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_witness_group_members FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_witness_group_targets (
  revision text NOT NULL,group_id text NOT NULL,entity_revision text NOT NULL,entity_id bigint NOT NULL,PRIMARY KEY(revision,group_id,entity_id),UNIQUE(revision,entity_id),FOREIGN KEY(revision,group_id) REFERENCES atlas.decision_mainland_witness_groups(revision,group_id),FOREIGN KEY(revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),FOREIGN KEY(entity_revision,entity_id) REFERENCES atlas.geographic_entities(revision,id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_witness_group_targets FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_group_relations (
  revision text NOT NULL,relation_id text NOT NULL,execution_status text NOT NULL CHECK(execution_status='selected_for_research'),relation text NOT NULL CHECK(relation='different'),group_a text NOT NULL,group_b text NOT NULL,PRIMARY KEY(revision,relation_id),UNIQUE(revision,group_a,group_b),CHECK(group_a<>group_b),FOREIGN KEY(revision,group_a) REFERENCES atlas.decision_mainland_witness_groups(revision,group_id),FOREIGN KEY(revision,group_b) REFERENCES atlas.decision_mainland_witness_groups(revision,group_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_group_relations FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_mainland_component_rules (
  revision text NOT NULL,rule_id text NOT NULL,execution_status text NOT NULL CHECK(execution_status='selected_for_research'),group_id text NOT NULL,region_id text,entity_revision text NOT NULL,inside_entity_id bigint NOT NULL,outside_entity_id bigint NOT NULL,
  PRIMARY KEY(revision,rule_id),UNIQUE(revision,group_id),FOREIGN KEY(revision,group_id) REFERENCES atlas.decision_mainland_witness_groups(revision,group_id),FOREIGN KEY(revision,region_id) REFERENCES atlas.decision_mainland_seed_regions(revision,region_id),FOREIGN KEY(revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),FOREIGN KEY(entity_revision,inside_entity_id) REFERENCES atlas.geographic_entities(revision,id),FOREIGN KEY(entity_revision,outside_entity_id) REFERENCES atlas.geographic_entities(revision,id),CHECK((region_id IS NULL AND inside_entity_id=outside_entity_id) OR (region_id IS NOT NULL AND inside_entity_id<>outside_entity_id)));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_mainland_component_rules FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_land_baseline_policies (
 revision text PRIMARY KEY REFERENCES atlas.decision_revisions(revision),policy_id text NOT NULL,version text NOT NULL,execution_status text NOT NULL CHECK(execution_status='selected_for_research'),distance_policy_id text NOT NULL,distance_policy_version text NOT NULL,
 connectivity text NOT NULL CHECK(connectivity='four_neighbor_longitude_wrapped'),endpoints text NOT NULL CHECK(endpoints='physical_land_cell_centers'),aggregation text NOT NULL CHECK(aggregation='minimum_over_component_and_mainland_cells'),island_overrides text NOT NULL CHECK(island_overrides='none'),tie text NOT NULL CHECK(tie='lowest_category_code'),tie_tolerance_metres text NOT NULL CHECK(tie_tolerance_metres='0.00001'),
 grid jsonb NOT NULL CHECK(jsonb_typeof(grid)='object'),physical_rows_sha256 text NOT NULL CHECK(physical_rows_sha256 ~ '^[0-9a-f]{64}$'),physical_runs_sha256 text NOT NULL CHECK(physical_runs_sha256 ~ '^[0-9a-f]{64}$'),physical_report_sha256 text NOT NULL CHECK(physical_report_sha256 ~ '^[0-9a-f]{64}$'),
 FOREIGN KEY(revision,distance_policy_id) REFERENCES atlas.decision_distance_policy_selections(revision,policy_id),FOREIGN KEY(distance_policy_id,distance_policy_version) REFERENCES atlas.distance_policy_versions(policy_id,version));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_land_baseline_policies FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_land_baseline_boundaries(revision text NOT NULL REFERENCES atlas.decision_land_baseline_policies(revision),boundary_id text NOT NULL,PRIMARY KEY(revision,boundary_id),FOREIGN KEY(revision,boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision,boundary_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_land_baseline_boundaries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_land_baseline_routes(revision text NOT NULL REFERENCES atlas.decision_land_baseline_policies(revision),route_id text NOT NULL,PRIMARY KEY(revision,route_id),FOREIGN KEY(revision,route_id) REFERENCES atlas.decision_mainland_closure_routes(revision,route_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_land_baseline_routes FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_land_baseline_regions(revision text NOT NULL REFERENCES atlas.decision_land_baseline_policies(revision),region_id text NOT NULL,PRIMARY KEY(revision,region_id),FOREIGN KEY(revision,region_id) REFERENCES atlas.decision_mainland_seed_regions(revision,region_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_land_baseline_regions FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
 CREATE TABLE atlas.decision_land_baseline_rules(revision text NOT NULL REFERENCES atlas.decision_land_baseline_policies(revision),rule_id text NOT NULL,PRIMARY KEY(revision,rule_id),FOREIGN KEY(revision,rule_id) REFERENCES atlas.decision_mainland_component_rules(revision,rule_id));
 CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_land_baseline_rules FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
