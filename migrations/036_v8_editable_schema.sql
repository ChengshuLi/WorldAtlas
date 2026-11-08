-- Definitions for the editable decision tables already present on continent-review-v1.
-- Apply to a fresh database after the preceding schema migrations.
BEGIN;

CREATE FUNCTION atlas.guard_basin_source_selection_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

BEGIN

 IF NOT EXISTS (SELECT 1 FROM atlas.decision_basins b

  JOIN atlas.decision_features f ON (f.revision,f.feature_id)=(b.revision,b.feature_id)

  WHERE (b.revision,b.basin_id)=(NEW.revision,NEW.decision_id)

    AND f.source_feature_id=NEW.source_feature_id) THEN

  RAISE EXCEPTION 'source feature does not match decision basin';

 END IF;

 IF NEW.source_id IS NOT NULL AND NOT EXISTS (

   SELECT 1 FROM atlas.source_assets a

   WHERE (a.source_id,a.version)=(NEW.source_id,NEW.source_version)

     AND a.sha256=NEW.source_file_sha256) THEN

  RAISE EXCEPTION 'selected file hash does not match source catalog';

 END IF;

 RETURN NEW;

END $$;

-- Editable decision records
CREATE TABLE atlas.decision_affiliation_feature_refs (
    revision text NOT NULL,
    affiliation_id text NOT NULL,
    role text NOT NULL,
    feature_id text NOT NULL,
    CONSTRAINT decision_affiliation_feature_refs_role_check CHECK ((role = 'identity_polygon'::text))
);

CREATE TABLE atlas.decision_basin_source_selections (
    revision text NOT NULL,
    decision_id text NOT NULL,
    source_feature_id text NOT NULL,
    source_id text,
    source_version text,
    source_file_sha256 text NOT NULL,
    geometry_sha256 text NOT NULL,
    extraction_method text NOT NULL,
    selection_status text NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_basin_source_selections_check
        CHECK (((selection_status <> 'selected_for_research'::text)
            OR ((source_id IS NOT NULL)
            AND (source_version IS NOT NULL)))),
    CONSTRAINT decision_basin_source_selections_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_basin_source_selections_extraction_method_check
        CHECK ((extraction_method = ANY (ARRAY['historical_source'::text, 'catalog_archive'::text]))),
    CONSTRAINT decision_basin_source_selections_geometry_sha256_check
        CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_basin_source_selections_selection_status_check
        CHECK ((selection_status = ANY (ARRAY['pending_source_registration'::text, 'selected_for_research'::text, 'research_only_not_selected'::text]))),
    CONSTRAINT decision_basin_source_selections_source_file_sha256_check
        CHECK ((source_file_sha256 ~ '^[0-9a-f]{64}$'::text))
);

CREATE TABLE atlas.decision_distance_policy_selections (
    revision text NOT NULL,
    policy_id text NOT NULL,
    version text NOT NULL,
    execution_status text NOT NULL,
    CONSTRAINT decision_distance_policy_selections_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text))
);

CREATE TABLE atlas.decision_ecoregion_source_refs (
    revision text NOT NULL,
    affiliation_id text NOT NULL,
    role text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    contract jsonb NOT NULL,
    CONSTRAINT decision_ecoregion_source_refs_contract_check CHECK ((jsonb_typeof(contract) = 'object'::text)),
    CONSTRAINT decision_ecoregion_source_refs_role_check CHECK ((role = 'ecoregion'::text))
);

CREATE TABLE atlas.decision_land_baseline_boundaries (
    revision text NOT NULL,
    boundary_id text NOT NULL
);

CREATE TABLE atlas.decision_land_baseline_policies (
    revision text NOT NULL,
    policy_id text NOT NULL,
    version text NOT NULL,
    execution_status text NOT NULL,
    distance_policy_id text NOT NULL,
    distance_policy_version text CONSTRAINT decision_land_baseline_policie_distance_policy_version_not_null NOT NULL,
    connectivity text NOT NULL,
    endpoints text NOT NULL,
    aggregation text NOT NULL,
    island_overrides text NOT NULL,
    tie text NOT NULL,
    tie_tolerance_metres text NOT NULL,
    grid jsonb NOT NULL,
    physical_rows_sha256 text NOT NULL,
    physical_runs_sha256 text NOT NULL,
    physical_report_sha256 text NOT NULL,
    CONSTRAINT decision_land_baseline_policies_aggregation_check
        CHECK ((aggregation = 'minimum_over_component_and_mainland_cells'::text)),
    CONSTRAINT decision_land_baseline_policies_connectivity_check
        CHECK ((connectivity = 'four_neighbor_longitude_wrapped'::text)),
    CONSTRAINT decision_land_baseline_policies_endpoints_check CHECK ((endpoints = 'physical_land_cell_centers'::text)),
    CONSTRAINT decision_land_baseline_policies_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_land_baseline_policies_grid_check CHECK ((jsonb_typeof(grid) = 'object'::text)),
    CONSTRAINT decision_land_baseline_policies_island_overrides_check CHECK ((island_overrides = 'none'::text)),
    CONSTRAINT decision_land_baseline_policies_physical_report_sha256_check
        CHECK ((physical_report_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_land_baseline_policies_physical_rows_sha256_check
        CHECK ((physical_rows_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_land_baseline_policies_physical_runs_sha256_check
        CHECK ((physical_runs_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_land_baseline_policies_tie_check CHECK ((tie = 'lowest_category_code'::text)),
    CONSTRAINT decision_land_baseline_policies_tie_tolerance_metres_check
        CHECK ((tie_tolerance_metres = '0.00001'::text))
);

CREATE TABLE atlas.decision_land_baseline_regions (
    revision text NOT NULL,
    region_id text NOT NULL
);

CREATE TABLE atlas.decision_land_baseline_routes (
    revision text NOT NULL,
    route_id text NOT NULL
);

CREATE TABLE atlas.decision_land_baseline_rules (
    revision text NOT NULL,
    rule_id text NOT NULL
);

CREATE TABLE atlas.decision_list1_entries (
    revision text NOT NULL,
    entry_id text NOT NULL,
    title text NOT NULL,
    reason text NOT NULL,
    execution_status text NOT NULL,
    old_list1_refs jsonb NOT NULL,
    CONSTRAINT decision_list1_entries_entry_id_check CHECK ((length(TRIM(BOTH FROM entry_id)) > 0)),
    CONSTRAINT decision_list1_entries_execution_status_check CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_list1_entries_old_list1_refs_check CHECK ((jsonb_typeof(old_list1_refs) = 'array'::text)),
    CONSTRAINT decision_list1_entries_reason_check CHECK ((length(TRIM(BOTH FROM reason)) > 0)),
    CONSTRAINT decision_list1_entries_title_check CHECK ((length(TRIM(BOTH FROM title)) > 0))
);

CREATE TABLE atlas.decision_list1_entry_affiliations (
    revision text NOT NULL,
    entry_id text NOT NULL,
    affiliation_id text NOT NULL
);

CREATE TABLE atlas.decision_list1_entry_evidence_sources (
    revision text NOT NULL,
    entry_id text NOT NULL,
    role text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    citation_section text NOT NULL,
    interpretation text NOT NULL,
    limitations jsonb NOT NULL,
    CONSTRAINT decision_list1_entry_evidence_sources_citation_section_check
        CHECK ((length(TRIM(BOTH FROM citation_section)) > 0)),
    CONSTRAINT decision_list1_entry_evidence_sources_interpretation_check
        CHECK ((length(TRIM(BOTH FROM interpretation)) > 0)),
    CONSTRAINT decision_list1_entry_evidence_sources_limitations_check
        CHECK (((jsonb_typeof(limitations) = 'array'::text)
            AND (jsonb_array_length(limitations) > 0))),
    CONSTRAINT decision_list1_entry_evidence_sources_role_check CHECK ((role = 'geographic_membership_evidence'::text))
);

CREATE TABLE atlas.decision_list1_policies (
    revision text NOT NULL,
    execution_status text NOT NULL,
    baseline_revision text NOT NULL,
    baseline_report_sha256 text NOT NULL,
    baseline_rows_sha256 text NOT NULL,
    baseline_runs_sha256 text NOT NULL,
    baseline_decision_snapshot_sha256 text CONSTRAINT decision_list1_policies_baseline_decision_snapshot_sha_not_null NOT NULL,
    physical_rows_sha256 text NOT NULL,
    physical_runs_sha256 text NOT NULL,
    component_rows_sha256 text NOT NULL,
    component_runs_sha256 text NOT NULL,
    conflict_policy text NOT NULL,
    unclaimed_policy text NOT NULL,
    physical_water_policy text NOT NULL,
    CONSTRAINT decision_list1_policies_baseline_decision_snapshot_sha256_check
        CHECK ((baseline_decision_snapshot_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_baseline_report_sha256_check
        CHECK ((baseline_report_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_baseline_rows_sha256_check
        CHECK ((baseline_rows_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_baseline_runs_sha256_check
        CHECK ((baseline_runs_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_component_rows_sha256_check
        CHECK ((component_rows_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_component_runs_sha256_check
        CHECK ((component_runs_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_conflict_policy_check
        CHECK ((conflict_policy = 'error_on_different_target'::text)),
    CONSTRAINT decision_list1_policies_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_list1_policies_physical_rows_sha256_check
        CHECK ((physical_rows_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_physical_runs_sha256_check
        CHECK ((physical_runs_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_list1_policies_physical_water_policy_check
        CHECK ((physical_water_policy = 'preserve_unassigned'::text)),
    CONSTRAINT decision_list1_policies_unclaimed_policy_check CHECK ((unclaimed_policy = 'preserve_baseline'::text))
);

CREATE TABLE atlas.decision_list1_policy_affiliations (
    revision text NOT NULL,
    affiliation_id text NOT NULL
);

CREATE TABLE atlas.decision_list1_policy_entries (
    revision text NOT NULL,
    entry_id text NOT NULL
);

CREATE TABLE atlas.decision_list1_records (
    revision text NOT NULL,
    item_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    reference text NOT NULL,
    name text NOT NULL,
    geographic_group text NOT NULL,
    rationale text NOT NULL,
    source_group_id text NOT NULL,
    rule_ids jsonb NOT NULL,
    source_evidence jsonb NOT NULL,
    basis_status text NOT NULL,
    selection_status text NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_list1_records_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_list1_records_item_id_check CHECK ((length(TRIM(BOTH FROM item_id)) > 0)),
    CONSTRAINT decision_list1_records_rule_ids_check CHECK ((jsonb_typeof(rule_ids) = 'array'::text)),
    CONSTRAINT decision_list1_records_selection_status_check
        CHECK ((selection_status = 'recorded_pending_selector'::text)),
    CONSTRAINT decision_list1_records_source_evidence_check CHECK ((jsonb_typeof(source_evidence) = 'array'::text))
);

CREATE TABLE atlas.decision_mainland_boundaries (
    revision text NOT NULL,
    boundary_id text NOT NULL,
    method text NOT NULL,
    execution_status text NOT NULL,
    geometry jsonb NOT NULL,
    geometry_sha256 text NOT NULL,
    geometry_hash_method text NOT NULL,
    coordinate_reference text NOT NULL,
    provenance jsonb NOT NULL,
    CONSTRAINT decision_mainland_boundaries_boundary_id_check CHECK ((length(TRIM(BOTH FROM boundary_id)) > 0)),
    CONSTRAINT decision_mainland_boundaries_coordinate_reference_check
        CHECK ((coordinate_reference = 'OGC:CRS84'::text)),
    CONSTRAINT decision_mainland_boundaries_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_boundaries_geometry_check
        CHECK (((jsonb_typeof(geometry) = 'object'::text)
            AND ((geometry ->> 'type'::text) = 'LineString'::text)
            AND (jsonb_typeof((geometry -> 'coordinates'::text)) = 'array'::text)
            AND (jsonb_array_length((geometry -> 'coordinates'::text)) >= 2))),
    CONSTRAINT decision_mainland_boundaries_geometry_hash_method_check
        CHECK ((geometry_hash_method = 'binary64-sorted-compact-geojson-v1'::text)),
    CONSTRAINT decision_mainland_boundaries_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_mainland_boundaries_method_check CHECK ((method = 'stored_linestring_v1'::text)),
    CONSTRAINT decision_mainland_boundaries_provenance_check CHECK ((jsonb_typeof(provenance) = 'object'::text))
);

CREATE TABLE atlas.decision_mainland_boundary_sources (
    revision text NOT NULL,
    boundary_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    relationship text NOT NULL,
    CONSTRAINT decision_mainland_boundary_sources_relationship_check CHECK ((length(TRIM(BOTH FROM relationship)) > 0))
);

CREATE TABLE atlas.decision_mainland_closure_routes (
    revision text NOT NULL,
    route_id text NOT NULL,
    route_type text NOT NULL,
    role text NOT NULL,
    execution_status text NOT NULL,
    geometry jsonb NOT NULL,
    geometry_sha256 text NOT NULL,
    geometry_hash_method text NOT NULL,
    coordinate_reference text NOT NULL,
    closure_method text NOT NULL,
    start_boundary_id text NOT NULL,
    start_endpoint text NOT NULL,
    end_boundary_id text NOT NULL,
    end_endpoint text NOT NULL,
    provenance jsonb NOT NULL,
    CONSTRAINT decision_mainland_closure_routes_closure_method_check
        CHECK ((closure_method = 'physical_terminal_closure_v1'::text)),
    CONSTRAINT decision_mainland_closure_routes_coordinate_reference_check
        CHECK ((coordinate_reference = 'OGC:CRS84'::text)),
    CONSTRAINT decision_mainland_closure_routes_end_endpoint_check
        CHECK ((end_endpoint = ANY (ARRAY['start'::text, 'end'::text]))),
    CONSTRAINT decision_mainland_closure_routes_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_closure_routes_geometry_check
        CHECK (((jsonb_typeof(geometry) = 'object'::text)
            AND ((geometry ->> 'type'::text) = 'LineString'::text)
            AND (jsonb_typeof((geometry -> 'coordinates'::text)) = 'array'::text)
            AND (jsonb_array_length((geometry -> 'coordinates'::text)) >= 2))),
    CONSTRAINT decision_mainland_closure_routes_geometry_hash_method_check
        CHECK ((geometry_hash_method = 'binary64-sorted-compact-geojson-v1'::text)),
    CONSTRAINT decision_mainland_closure_routes_geometry_sha256_check
        CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_mainland_closure_routes_provenance_check CHECK ((jsonb_typeof(provenance) = 'object'::text)),
    CONSTRAINT decision_mainland_closure_routes_role_check CHECK ((role = 'water_closure'::text)),
    CONSTRAINT decision_mainland_closure_routes_route_type_check CHECK ((route_type = 'stored_linestring_v1'::text)),
    CONSTRAINT decision_mainland_closure_routes_start_endpoint_check
        CHECK ((start_endpoint = ANY (ARRAY['start'::text, 'end'::text])))
);

CREATE TABLE atlas.decision_mainland_closure_sources (
    revision text NOT NULL,
    route_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL
);

CREATE TABLE atlas.decision_mainland_component_rules (
    revision text NOT NULL,
    rule_id text NOT NULL,
    execution_status text NOT NULL,
    group_id text NOT NULL,
    region_id text,
    entity_revision text NOT NULL,
    inside_entity_id bigint NOT NULL,
    outside_entity_id bigint NOT NULL,
    CONSTRAINT decision_mainland_component_rules_check
        CHECK ((((region_id IS NULL)
            AND (inside_entity_id = outside_entity_id))
            OR ((region_id IS NOT NULL)
            AND (inside_entity_id <> outside_entity_id)))),
    CONSTRAINT decision_mainland_component_rules_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text))
);

CREATE TABLE atlas.decision_mainland_group_relations (
    revision text NOT NULL,
    relation_id text NOT NULL,
    execution_status text NOT NULL,
    relation text NOT NULL,
    group_a text NOT NULL,
    group_b text NOT NULL,
    CONSTRAINT decision_mainland_group_relations_check CHECK ((group_a <> group_b)),
    CONSTRAINT decision_mainland_group_relations_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_group_relations_relation_check CHECK ((relation = 'different'::text))
);

CREATE TABLE atlas.decision_mainland_region_segments (
    revision text NOT NULL,
    region_id text NOT NULL,
    ordinal integer NOT NULL,
    kind text NOT NULL,
    boundary_id text,
    route_id text,
    start_index integer NOT NULL,
    end_index integer NOT NULL,
    reverse boolean NOT NULL,
    CONSTRAINT decision_mainland_region_segments_check CHECK ((end_index > start_index)),
    CONSTRAINT decision_mainland_region_segments_check1
        CHECK ((((kind = 'boundary'::text)
            AND (boundary_id IS NOT NULL)
            AND (route_id IS NULL))
            OR ((kind = 'route'::text)
            AND (route_id IS NOT NULL)
            AND (boundary_id IS NULL)))),
    CONSTRAINT decision_mainland_region_segments_kind_check
        CHECK ((kind = ANY (ARRAY['boundary'::text, 'route'::text]))),
    CONSTRAINT decision_mainland_region_segments_ordinal_check CHECK ((ordinal >= 0)),
    CONSTRAINT decision_mainland_region_segments_start_index_check CHECK ((start_index >= 0))
);

CREATE TABLE atlas.decision_mainland_seed_regions (
    revision text NOT NULL,
    region_id text NOT NULL,
    execution_status text NOT NULL,
    geometry_sha256 text NOT NULL,
    geometry_hash_method text NOT NULL,
    witnesses jsonb NOT NULL,
    CONSTRAINT decision_mainland_seed_regions_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_seed_regions_geometry_hash_method_check
        CHECK ((geometry_hash_method = 'binary64-sorted-compact-geojson-v1'::text)),
    CONSTRAINT decision_mainland_seed_regions_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_mainland_seed_regions_witnesses_check CHECK ((jsonb_typeof(witnesses) = 'array'::text))
);

CREATE TABLE atlas.decision_mainland_witness_group_members (
    revision text NOT NULL,
    group_id text NOT NULL,
    witness_id text NOT NULL,
    ordinal integer NOT NULL,
    CONSTRAINT decision_mainland_witness_group_members_ordinal_check CHECK ((ordinal >= 0))
);

CREATE TABLE atlas.decision_mainland_witness_group_targets (
    revision text NOT NULL,
    group_id text NOT NULL,
    entity_revision text CONSTRAINT decision_mainland_witness_group_target_entity_revision_not_null NOT NULL,
    entity_id bigint NOT NULL
);

CREATE TABLE atlas.decision_mainland_witness_groups (
    revision text NOT NULL,
    group_id text NOT NULL,
    role text NOT NULL,
    execution_status text NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witness_groups_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_witness_groups_role_check
        CHECK ((role = ANY (ARRAY['mainland'::text, 'sentinel'::text])))
);

CREATE TABLE atlas.decision_mainland_witnesses (
    revision text NOT NULL,
    witness_id text NOT NULL,
    method text NOT NULL,
    execution_status text NOT NULL,
    point_feature_id text NOT NULL,
    identity_feature_id text NOT NULL,
    point_name text NOT NULL,
    identity_name text NOT NULL,
    identity_class text NOT NULL,
    id_property text NOT NULL,
    identity_id_property text NOT NULL,
    identity_name_property text NOT NULL,
    identity_class_property text NOT NULL,
    radius_cells integer NOT NULL,
    max_water_cells integer NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witnesses_check CHECK ((point_feature_id <> identity_feature_id)),
    CONSTRAINT decision_mainland_witnesses_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_mainland_witnesses_max_water_cells_check CHECK ((max_water_cells >= 0)),
    CONSTRAINT decision_mainland_witnesses_method_check CHECK ((method = 'source_point_named_region_v1'::text)),
    CONSTRAINT decision_mainland_witnesses_radius_cells_check CHECK (((radius_cells >= 0) AND (radius_cells <= 100)))
);

CREATE TABLE atlas.decision_polygon_affiliation_feature_refs (
    revision text NOT NULL,
    affiliation_id text CONSTRAINT decision_polygon_affiliation_feature_re_affiliation_id_not_null NOT NULL,
    role text NOT NULL,
    feature_id text NOT NULL,
    CONSTRAINT decision_polygon_affiliation_feature_refs_role_check CHECK ((role = 'additional_polygon'::text))
);

CREATE TABLE atlas.decision_polygon_corroboration_refs (
    revision text NOT NULL,
    affiliation_id text NOT NULL,
    selected_feature_id text CONSTRAINT decision_polygon_corroboration_ref_selected_feature_id_not_null NOT NULL,
    corroborating_feature_id text CONSTRAINT decision_polygon_corroboratio_corroborating_feature_id_not_null NOT NULL,
    CONSTRAINT decision_polygon_corroboration_refs_check CHECK ((selected_feature_id <> corroborating_feature_id))
);

CREATE TABLE atlas.decision_stage1_source_inputs (
    revision text NOT NULL,
    role text NOT NULL,
    ordinal integer NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    execution_status text NOT NULL,
    CONSTRAINT decision_stage1_source_inputs_execution_status_check
        CHECK ((execution_status = 'selected_for_research'::text)),
    CONSTRAINT decision_stage1_source_inputs_ordinal_check CHECK ((ordinal >= 0)),
    CONSTRAINT decision_stage1_source_inputs_role_check
        CHECK ((role = ANY (ARRAY['physical_land'::text, 'inland_water'::text])))
);

CREATE TABLE atlas.distance_policy_versions (
    policy_id text NOT NULL,
    version text NOT NULL,
    algorithm text NOT NULL,
    units text NOT NULL,
    semi_major_axis_m text NOT NULL,
    inverse_flattening text NOT NULL
);

-- Primary keys and uniqueness constraints
ALTER TABLE ONLY atlas.decision_affiliation_feature_refs
    ADD CONSTRAINT decision_affiliation_feature_refs_pkey PRIMARY KEY (revision, affiliation_id, role);

ALTER TABLE ONLY atlas.decision_basin_source_selections
    ADD CONSTRAINT decision_basin_source_selections_pkey PRIMARY KEY (revision, decision_id);

ALTER TABLE ONLY atlas.decision_distance_policy_selections
    ADD CONSTRAINT decision_distance_policy_selections_pkey PRIMARY KEY (revision, policy_id);

ALTER TABLE ONLY atlas.decision_ecoregion_source_refs
    ADD CONSTRAINT decision_ecoregion_source_refs_pkey PRIMARY KEY (revision, affiliation_id, role);

ALTER TABLE ONLY atlas.decision_land_baseline_boundaries
    ADD CONSTRAINT decision_land_baseline_boundaries_pkey PRIMARY KEY (revision, boundary_id);

ALTER TABLE ONLY atlas.decision_land_baseline_policies
    ADD CONSTRAINT decision_land_baseline_policies_pkey PRIMARY KEY (revision);

ALTER TABLE ONLY atlas.decision_land_baseline_regions
    ADD CONSTRAINT decision_land_baseline_regions_pkey PRIMARY KEY (revision, region_id);

ALTER TABLE ONLY atlas.decision_land_baseline_routes
    ADD CONSTRAINT decision_land_baseline_routes_pkey PRIMARY KEY (revision, route_id);

ALTER TABLE ONLY atlas.decision_land_baseline_rules
    ADD CONSTRAINT decision_land_baseline_rules_pkey PRIMARY KEY (revision, rule_id);

ALTER TABLE ONLY atlas.decision_list1_entries
    ADD CONSTRAINT decision_list1_entries_pkey PRIMARY KEY (revision, entry_id);

ALTER TABLE ONLY atlas.decision_list1_entry_affiliations
    ADD CONSTRAINT decision_list1_entry_affiliations_pkey PRIMARY KEY (revision, entry_id, affiliation_id);

ALTER TABLE ONLY atlas.decision_list1_entry_evidence_sources
    ADD CONSTRAINT decision_list1_entry_evidence_sources_pkey
    PRIMARY KEY (revision, entry_id, role, source_id, source_version);

ALTER TABLE ONLY atlas.decision_list1_policies
    ADD CONSTRAINT decision_list1_policies_pkey PRIMARY KEY (revision);

ALTER TABLE ONLY atlas.decision_list1_policy_affiliations
    ADD CONSTRAINT decision_list1_policy_affiliations_pkey PRIMARY KEY (revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_list1_policy_entries
    ADD CONSTRAINT decision_list1_policy_entries_pkey PRIMARY KEY (revision, entry_id);

ALTER TABLE ONLY atlas.decision_list1_records
    ADD CONSTRAINT decision_list1_records_pkey PRIMARY KEY (revision, item_id);

ALTER TABLE ONLY atlas.decision_mainland_boundaries
    ADD CONSTRAINT decision_mainland_boundaries_pkey PRIMARY KEY (revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_sources_pkey
    PRIMARY KEY (revision, boundary_id, source_id, source_version);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_pkey PRIMARY KEY (revision, route_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_sources
    ADD CONSTRAINT decision_mainland_closure_sources_pkey PRIMARY KEY (revision, route_id, source_id, source_version);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_pkey PRIMARY KEY (revision, rule_id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_group_id_key UNIQUE (revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_group_relations
    ADD CONSTRAINT decision_mainland_group_relations_pkey PRIMARY KEY (revision, relation_id);

ALTER TABLE ONLY atlas.decision_mainland_group_relations
    ADD CONSTRAINT decision_mainland_group_relations_revision_group_a_group_b_key UNIQUE (revision, group_a, group_b);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_pkey PRIMARY KEY (revision, region_id, ordinal);

ALTER TABLE ONLY atlas.decision_mainland_seed_regions
    ADD CONSTRAINT decision_mainland_seed_regions_pkey PRIMARY KEY (revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_m_revision_group_id_ordinal_key UNIQUE (revision, group_id, ordinal);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_members_pkey PRIMARY KEY (revision, group_id, witness_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_members_revision_witness_id_key UNIQUE (revision, witness_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_targets_pkey PRIMARY KEY (revision, group_id, entity_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_targets_revision_entity_id_key UNIQUE (revision, entity_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_groups
    ADD CONSTRAINT decision_mainland_witness_groups_pkey PRIMARY KEY (revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_pkey PRIMARY KEY (revision, witness_id);

ALTER TABLE ONLY atlas.decision_polygon_affiliation_feature_refs
    ADD CONSTRAINT decision_polygon_affiliation_feature_refs_pkey
    PRIMARY KEY (revision, affiliation_id, role, feature_id);

ALTER TABLE ONLY atlas.decision_polygon_corroboration_refs
    ADD CONSTRAINT decision_polygon_corroboration_refs_pkey
    PRIMARY KEY (revision, affiliation_id, selected_feature_id, corroborating_feature_id);

ALTER TABLE ONLY atlas.decision_stage1_source_inputs
    ADD CONSTRAINT decision_stage1_source_inputs_pkey PRIMARY KEY (revision, role, ordinal);

ALTER TABLE ONLY atlas.decision_stage1_source_inputs
    ADD CONSTRAINT decision_stage1_source_inputs_revision_source_id_source_ver_key
    UNIQUE (revision, source_id, source_version);

ALTER TABLE ONLY atlas.distance_policy_versions
    ADD CONSTRAINT distance_policy_versions_pkey PRIMARY KEY (policy_id, version);

-- Draft and source identity guards
CREATE TRIGGER basin_source_selection_identity BEFORE INSERT OR UPDATE ON atlas.decision_basin_source_selections FOR EACH ROW EXECUTE FUNCTION atlas.guard_basin_source_selection_identity();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_affiliation_feature_refs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_basin_source_selections FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_distance_policy_selections FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_ecoregion_source_refs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_land_baseline_boundaries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_land_baseline_policies FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_land_baseline_regions FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_land_baseline_routes FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_land_baseline_rules FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_entries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_entry_affiliations FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_entry_evidence_sources FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_policies FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_policy_affiliations FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_policy_entries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_list1_records FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_boundaries FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_boundary_sources FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_closure_routes FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_closure_sources FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_component_rules FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_group_relations FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_region_segments FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_seed_regions FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_witness_group_members FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_witness_group_targets FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_witness_groups FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_mainland_witnesses FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_polygon_affiliation_feature_refs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_polygon_corroboration_refs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER decision_row_guard BEFORE INSERT OR DELETE OR UPDATE ON atlas.decision_stage1_source_inputs FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();

CREATE TRIGGER version_immutable BEFORE DELETE OR UPDATE ON atlas.distance_policy_versions FOR EACH ROW EXECUTE FUNCTION atlas.reject_source_change();

ALTER TABLE ONLY atlas.decision_affiliation_feature_refs
    ADD CONSTRAINT decision_affiliation_feature_refs_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_affiliation_feature_refs
    ADD CONSTRAINT decision_affiliation_feature_refs_revision_feature_id_fkey
    FOREIGN KEY (revision, feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_basin_source_selections
    ADD CONSTRAINT decision_basin_source_selections_revision_decision_id_fkey
    FOREIGN KEY (revision, decision_id)
    REFERENCES atlas.decision_basins(revision, basin_id);

ALTER TABLE ONLY atlas.decision_basin_source_selections
    ADD CONSTRAINT decision_basin_source_selections_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version) MATCH FULL;

ALTER TABLE ONLY atlas.decision_distance_policy_selections
    ADD CONSTRAINT decision_distance_policy_selections_policy_id_version_fkey
    FOREIGN KEY (policy_id, version)
    REFERENCES atlas.distance_policy_versions(policy_id, version);

ALTER TABLE ONLY atlas.decision_distance_policy_selections
    ADD CONSTRAINT decision_distance_policy_selections_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_ecoregion_source_refs
    ADD CONSTRAINT decision_ecoregion_source_refs_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_ecoregion_source_refs
    ADD CONSTRAINT decision_ecoregion_source_refs_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_land_baseline_boundaries
    ADD CONSTRAINT decision_land_baseline_boundaries_revision_boundary_id_fkey
    FOREIGN KEY (revision, boundary_id)
    REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_land_baseline_boundaries
    ADD CONSTRAINT decision_land_baseline_boundaries_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_land_baseline_policies(revision);

ALTER TABLE ONLY atlas.decision_land_baseline_policies
    ADD CONSTRAINT decision_land_baseline_polici_distance_policy_id_distance__fkey
    FOREIGN KEY (distance_policy_id, distance_policy_version)
    REFERENCES atlas.distance_policy_versions(policy_id, version);

ALTER TABLE ONLY atlas.decision_land_baseline_policies
    ADD CONSTRAINT decision_land_baseline_policie_revision_distance_policy_id_fkey
    FOREIGN KEY (revision, distance_policy_id)
    REFERENCES atlas.decision_distance_policy_selections(revision, policy_id);

ALTER TABLE ONLY atlas.decision_land_baseline_policies
    ADD CONSTRAINT decision_land_baseline_policies_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_land_baseline_regions
    ADD CONSTRAINT decision_land_baseline_regions_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_land_baseline_policies(revision);

ALTER TABLE ONLY atlas.decision_land_baseline_regions
    ADD CONSTRAINT decision_land_baseline_regions_revision_region_id_fkey
    FOREIGN KEY (revision, region_id)
    REFERENCES atlas.decision_mainland_seed_regions(revision, region_id);

ALTER TABLE ONLY atlas.decision_land_baseline_routes
    ADD CONSTRAINT decision_land_baseline_routes_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_land_baseline_policies(revision);

ALTER TABLE ONLY atlas.decision_land_baseline_routes
    ADD CONSTRAINT decision_land_baseline_routes_revision_route_id_fkey
    FOREIGN KEY (revision, route_id)
    REFERENCES atlas.decision_mainland_closure_routes(revision, route_id);

ALTER TABLE ONLY atlas.decision_land_baseline_rules
    ADD CONSTRAINT decision_land_baseline_rules_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_land_baseline_policies(revision);

ALTER TABLE ONLY atlas.decision_land_baseline_rules
    ADD CONSTRAINT decision_land_baseline_rules_revision_rule_id_fkey
    FOREIGN KEY (revision, rule_id)
    REFERENCES atlas.decision_mainland_component_rules(revision, rule_id);

ALTER TABLE ONLY atlas.decision_list1_entries
    ADD CONSTRAINT decision_list1_entries_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_list1_entry_affiliations
    ADD CONSTRAINT decision_list1_entry_affiliations_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_list1_entry_affiliations
    ADD CONSTRAINT decision_list1_entry_affiliations_revision_entry_id_fkey
    FOREIGN KEY (revision, entry_id)
    REFERENCES atlas.decision_list1_entries(revision, entry_id);

ALTER TABLE ONLY atlas.decision_list1_entry_evidence_sources
    ADD CONSTRAINT decision_list1_entry_evidence_sou_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_list1_entry_evidence_sources
    ADD CONSTRAINT decision_list1_entry_evidence_sources_revision_entry_id_fkey
    FOREIGN KEY (revision, entry_id)
    REFERENCES atlas.decision_list1_entries(revision, entry_id);

ALTER TABLE ONLY atlas.decision_list1_policies
    ADD CONSTRAINT decision_list1_policies_baseline_revision_fkey
    FOREIGN KEY (baseline_revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_list1_policies
    ADD CONSTRAINT decision_list1_policies_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_list1_policy_affiliations
    ADD CONSTRAINT decision_list1_policy_affiliations_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_list1_policy_affiliations
    ADD CONSTRAINT decision_list1_policy_affiliations_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_list1_policies(revision);

ALTER TABLE ONLY atlas.decision_list1_policy_entries
    ADD CONSTRAINT decision_list1_policy_entries_revision_entry_id_fkey
    FOREIGN KEY (revision, entry_id)
    REFERENCES atlas.decision_list1_entries(revision, entry_id);

ALTER TABLE ONLY atlas.decision_list1_policy_entries
    ADD CONSTRAINT decision_list1_policy_entries_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_list1_policies(revision);

ALTER TABLE ONLY atlas.decision_list1_records
    ADD CONSTRAINT decision_list1_records_entity_revision_entity_id_fkey
    FOREIGN KEY (entity_revision, entity_id)
    REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_list1_records
    ADD CONSTRAINT decision_list1_records_revision_entity_revision_fkey
    FOREIGN KEY (revision, entity_revision)
    REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_mainland_boundaries
    ADD CONSTRAINT decision_mainland_boundaries_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_source_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_sources_revision_boundary_id_fkey
    FOREIGN KEY (revision, boundary_id)
    REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_route_revision_start_boundary_id_fkey
    FOREIGN KEY (revision, start_boundary_id)
    REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_revision_end_boundary_id_fkey
    FOREIGN KEY (revision, end_boundary_id)
    REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_closure_sources
    ADD CONSTRAINT decision_mainland_closure_sources_revision_route_id_fkey
    FOREIGN KEY (revision, route_id)
    REFERENCES atlas.decision_mainland_closure_routes(revision, route_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_sources
    ADD CONSTRAINT decision_mainland_closure_sources_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_r_entity_revision_inside_entit_fkey
    FOREIGN KEY (entity_revision, inside_entity_id)
    REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_r_entity_revision_outside_enti_fkey
    FOREIGN KEY (entity_revision, outside_entity_id)
    REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_entity_revision_fkey
    FOREIGN KEY (revision, entity_revision)
    REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_group_id_fkey
    FOREIGN KEY (revision, group_id)
    REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_region_id_fkey
    FOREIGN KEY (revision, region_id)
    REFERENCES atlas.decision_mainland_seed_regions(revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_group_relations
    ADD CONSTRAINT decision_mainland_group_relations_revision_group_a_fkey
    FOREIGN KEY (revision, group_a)
    REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_group_relations
    ADD CONSTRAINT decision_mainland_group_relations_revision_group_b_fkey
    FOREIGN KEY (revision, group_b)
    REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_boundary_id_fkey
    FOREIGN KEY (revision, boundary_id)
    REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_region_id_fkey
    FOREIGN KEY (revision, region_id)
    REFERENCES atlas.decision_mainland_seed_regions(revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_route_id_fkey
    FOREIGN KEY (revision, route_id)
    REFERENCES atlas.decision_mainland_closure_routes(revision, route_id);

ALTER TABLE ONLY atlas.decision_mainland_seed_regions
    ADD CONSTRAINT decision_mainland_seed_regions_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group__entity_revision_entity_id_fkey
    FOREIGN KEY (entity_revision, entity_id)
    REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_member_revision_witness_id_fkey
    FOREIGN KEY (revision, witness_id)
    REFERENCES atlas.decision_mainland_witnesses(revision, witness_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_members_revision_group_id_fkey
    FOREIGN KEY (revision, group_id)
    REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_t_revision_entity_revision_fkey
    FOREIGN KEY (revision, entity_revision)
    REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_targets_revision_group_id_fkey
    FOREIGN KEY (revision, group_id)
    REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_groups
    ADD CONSTRAINT decision_mainland_witness_groups_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_identity_feature_id_fkey
    FOREIGN KEY (revision, identity_feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_point_feature_id_fkey
    FOREIGN KEY (revision, point_feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_polygon_affiliation_feature_refs
    ADD CONSTRAINT decision_polygon_affiliation_featu_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_polygon_affiliation_feature_refs
    ADD CONSTRAINT decision_polygon_affiliation_feature_r_revision_feature_id_fkey
    FOREIGN KEY (revision, feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_polygon_corroboration_refs
    ADD CONSTRAINT decision_polygon_corroboratio_revision_corroborating_featu_fkey
    FOREIGN KEY (revision, corroborating_feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_polygon_corroboration_refs
    ADD CONSTRAINT decision_polygon_corroboratio_revision_selected_feature_id_fkey
    FOREIGN KEY (revision, selected_feature_id)
    REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_polygon_corroboration_refs
    ADD CONSTRAINT decision_polygon_corroboration_ref_revision_affiliation_id_fkey
    FOREIGN KEY (revision, affiliation_id)
    REFERENCES atlas.decision_affiliations(revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_stage1_source_inputs
    ADD CONSTRAINT decision_stage1_source_inputs_revision_fkey
    FOREIGN KEY (revision)
    REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_stage1_source_inputs
    ADD CONSTRAINT decision_stage1_source_inputs_source_id_source_version_fkey
    FOREIGN KEY (source_id, source_version)
    REFERENCES atlas.source_assets(source_id, version);

COMMIT;
