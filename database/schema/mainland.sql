-- Editable boundaries, assembled regions and physical-component witnesses.

CREATE TABLE atlas.decision_mainland_boundaries (
    revision text NOT NULL,
    boundary_id text NOT NULL,
    geometry jsonb NOT NULL,
    geometry_sha256 text NOT NULL,
    coordinate_reference text NOT NULL,
    provenance jsonb NOT NULL,
    construction_id text,
    construction_version text,
    CONSTRAINT decision_mainland_boundaries_boundary_id_check CHECK ((length(TRIM(BOTH FROM boundary_id)) > 0)),
    CONSTRAINT decision_mainland_boundaries_check CHECK (((construction_id IS NULL) = (construction_version IS NULL))),
    CONSTRAINT decision_mainland_boundaries_coordinate_reference_check CHECK ((coordinate_reference = 'OGC:CRS84'::text)),
    CONSTRAINT decision_mainland_boundaries_geometry_check CHECK (COALESCE(((jsonb_typeof(geometry) = 'object'::text) AND ((geometry ->> 'type'::text) = 'LineString'::text) AND (jsonb_typeof((geometry -> 'coordinates'::text)) = 'array'::text) AND (jsonb_array_length((geometry -> 'coordinates'::text)) >= 2)), false)),
    CONSTRAINT decision_mainland_boundaries_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_mainland_boundaries_provenance_check CHECK ((jsonb_typeof(provenance) = 'object'::text)),
    CONSTRAINT decision_mainland_boundaries_pkey PRIMARY KEY (revision, boundary_id),
    CONSTRAINT decision_mainland_boundaries_construction_id_construction__fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version),
    CONSTRAINT decision_mainland_boundaries_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_mainland_boundary_sources (
    revision text NOT NULL,
    boundary_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    relationship text NOT NULL,
    CONSTRAINT decision_mainland_boundary_sources_relationship_check CHECK ((length(TRIM(BOTH FROM relationship)) > 0)),
    CONSTRAINT decision_mainland_boundary_sources_pkey PRIMARY KEY (revision, boundary_id, source_id, source_version),
    CONSTRAINT decision_mainland_boundary_source_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version),
    CONSTRAINT decision_mainland_boundary_sources_revision_boundary_id_fkey FOREIGN KEY (revision, boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id)
);

CREATE TABLE atlas.decision_mainland_closure_routes (
    revision text NOT NULL,
    route_id text NOT NULL,
    geometry jsonb NOT NULL,
    geometry_sha256 text NOT NULL,
    coordinate_reference text NOT NULL,
    closure_method text NOT NULL,
    start_boundary_id text NOT NULL,
    start_endpoint text NOT NULL,
    end_boundary_id text NOT NULL,
    end_endpoint text NOT NULL,
    provenance jsonb NOT NULL,
    CONSTRAINT decision_mainland_closure_routes_closure_method_check CHECK ((closure_method = 'physical_terminal_closure_v1'::text)),
    CONSTRAINT decision_mainland_closure_routes_coordinate_reference_check CHECK ((coordinate_reference = 'OGC:CRS84'::text)),
    CONSTRAINT decision_mainland_closure_routes_end_endpoint_check CHECK ((end_endpoint = ANY (ARRAY['start'::text, 'end'::text]))),
    CONSTRAINT decision_mainland_closure_routes_geometry_check CHECK (COALESCE(((jsonb_typeof(geometry) = 'object'::text) AND ((geometry ->> 'type'::text) = 'LineString'::text) AND (jsonb_typeof((geometry -> 'coordinates'::text)) = 'array'::text) AND (jsonb_array_length((geometry -> 'coordinates'::text)) >= 2)), false)),
    CONSTRAINT decision_mainland_closure_routes_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_mainland_closure_routes_provenance_check CHECK ((jsonb_typeof(provenance) = 'object'::text)),
    CONSTRAINT decision_mainland_closure_routes_start_endpoint_check CHECK ((start_endpoint = ANY (ARRAY['start'::text, 'end'::text]))),
    CONSTRAINT decision_mainland_closure_routes_pkey PRIMARY KEY (revision, route_id),
    CONSTRAINT decision_mainland_closure_route_revision_start_boundary_id_fkey FOREIGN KEY (revision, start_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id),
    CONSTRAINT decision_mainland_closure_routes_revision_end_boundary_id_fkey FOREIGN KEY (revision, end_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id),
    CONSTRAINT decision_mainland_closure_routes_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_mainland_seed_regions (
    revision text NOT NULL,
    region_id text NOT NULL,
    witnesses jsonb NOT NULL,
    CONSTRAINT decision_mainland_seed_regions_witnesses_check CHECK ((jsonb_typeof(witnesses) = 'array'::text)),
    CONSTRAINT decision_mainland_seed_regions_pkey PRIMARY KEY (revision, region_id),
    CONSTRAINT decision_mainland_seed_regions_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_mainland_region_segments (
    revision text NOT NULL,
    region_id text NOT NULL,
    ordinal integer NOT NULL,
    kind text NOT NULL,
    boundary_id text,
    route_id text,
    reverse boolean NOT NULL,
    CONSTRAINT decision_mainland_region_segments_check1 CHECK ((((kind = 'boundary'::text) AND (boundary_id IS NOT NULL) AND (route_id IS NULL)) OR ((kind = 'route'::text) AND (route_id IS NOT NULL) AND (boundary_id IS NULL)))),
    CONSTRAINT decision_mainland_region_segments_kind_check CHECK ((kind = ANY (ARRAY['boundary'::text, 'route'::text]))),
    CONSTRAINT decision_mainland_region_segments_ordinal_check CHECK ((ordinal >= 0)),
    CONSTRAINT decision_mainland_region_segments_pkey PRIMARY KEY (revision, region_id, ordinal),
    CONSTRAINT decision_mainland_region_segments_revision_boundary_id_fkey FOREIGN KEY (revision, boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id),
    CONSTRAINT decision_mainland_region_segments_revision_region_id_fkey FOREIGN KEY (revision, region_id) REFERENCES atlas.decision_mainland_seed_regions(revision, region_id),
    CONSTRAINT decision_mainland_region_segments_revision_route_id_fkey FOREIGN KEY (revision, route_id) REFERENCES atlas.decision_mainland_closure_routes(revision, route_id)
);

CREATE TABLE atlas.decision_mainland_witnesses (
    revision text NOT NULL,
    witness_id text NOT NULL,
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
    CONSTRAINT decision_mainland_witnesses_max_water_cells_check CHECK ((max_water_cells >= 0)),
    CONSTRAINT decision_mainland_witnesses_radius_cells_check CHECK (((radius_cells >= 0) AND (radius_cells <= 100))),
    CONSTRAINT decision_mainland_witnesses_pkey PRIMARY KEY (revision, witness_id),
    CONSTRAINT decision_mainland_witnesses_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision),
    CONSTRAINT decision_mainland_witnesses_revision_identity_feature_id_fkey FOREIGN KEY (revision, identity_feature_id) REFERENCES atlas.decision_features(revision, feature_id),
    CONSTRAINT decision_mainland_witnesses_revision_point_feature_id_fkey FOREIGN KEY (revision, point_feature_id) REFERENCES atlas.decision_features(revision, feature_id)
);

CREATE TABLE atlas.decision_mainland_witness_groups (
    revision text NOT NULL,
    group_id text NOT NULL,
    role text NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witness_groups_role_check CHECK ((role = ANY (ARRAY['mainland'::text, 'sentinel'::text]))),
    CONSTRAINT decision_mainland_witness_groups_pkey PRIMARY KEY (revision, group_id),
    CONSTRAINT decision_mainland_witness_groups_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_mainland_witness_group_members (
    revision text NOT NULL,
    group_id text NOT NULL,
    witness_id text NOT NULL,
    CONSTRAINT decision_mainland_witness_group_member_revision_witness_id_key1 UNIQUE (revision, witness_id),
    CONSTRAINT decision_mainland_witness_group_members_pkey PRIMARY KEY (revision, group_id, witness_id),
    CONSTRAINT decision_mainland_witness_group_member_revision_witness_id_fkey FOREIGN KEY (revision, witness_id) REFERENCES atlas.decision_mainland_witnesses(revision, witness_id),
    CONSTRAINT decision_mainland_witness_group_members_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id)
);


ALTER TABLE atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_members_revision_witness_id_key UNIQUE (revision, witness_id);
CREATE TABLE atlas.decision_mainland_witness_group_targets (
    revision text NOT NULL,
    group_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    CONSTRAINT decision_mainland_witness_group_targets_pkey PRIMARY KEY (revision, group_id, entity_id),
    CONSTRAINT decision_mainland_witness_group_targets_revision_entity_id_key UNIQUE (revision, entity_id),
    CONSTRAINT decision_mainland_witness_group__entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id),
    CONSTRAINT decision_mainland_witness_group_t_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision),
    CONSTRAINT decision_mainland_witness_group_targets_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id)
);

CREATE TABLE atlas.decision_mainland_distinct_groups (
    revision text NOT NULL,
    group_a text NOT NULL,
    group_b text NOT NULL,
    CONSTRAINT decision_mainland_distinct_groups_check CHECK ((group_a < group_b)),
    CONSTRAINT decision_mainland_distinct_groups_pkey PRIMARY KEY (revision, group_a, group_b),
    CONSTRAINT decision_mainland_distinct_groups_revision_group_a_fkey FOREIGN KEY (revision, group_a) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id),
    CONSTRAINT decision_mainland_distinct_groups_revision_group_b_fkey FOREIGN KEY (revision, group_b) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id)
);

CREATE TABLE atlas.decision_mainland_component_rules (
    revision text NOT NULL,
    rule_id text NOT NULL,
    group_id text NOT NULL,
    region_id text,
    entity_revision text NOT NULL,
    inside_entity_id bigint NOT NULL,
    outside_entity_id bigint NOT NULL,
    CONSTRAINT decision_mainland_component_rules_check CHECK ((((region_id IS NULL) AND (inside_entity_id = outside_entity_id)) OR ((region_id IS NOT NULL) AND (inside_entity_id <> outside_entity_id)))),
    CONSTRAINT decision_mainland_component_rules_pkey PRIMARY KEY (revision, rule_id),
    CONSTRAINT decision_mainland_component_rules_revision_group_id_key UNIQUE (revision, group_id),
    CONSTRAINT decision_mainland_component_r_entity_revision_inside_entit_fkey FOREIGN KEY (entity_revision, inside_entity_id) REFERENCES atlas.geographic_entities(revision, id),
    CONSTRAINT decision_mainland_component_r_entity_revision_outside_enti_fkey FOREIGN KEY (entity_revision, outside_entity_id) REFERENCES atlas.geographic_entities(revision, id),
    CONSTRAINT decision_mainland_component_rules_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision),
    CONSTRAINT decision_mainland_component_rules_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id),
    CONSTRAINT decision_mainland_component_rules_revision_region_id_fkey FOREIGN KEY (revision, region_id) REFERENCES atlas.decision_mainland_seed_regions(revision, region_id)
);
