-- Computational seed-region closures, ordered regions and physical-component witnesses.

CREATE TABLE atlas.decision_mainland_closure_routes (
    id text NOT NULL,
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
    CONSTRAINT decision_mainland_closure_routes_pkey PRIMARY KEY (id),
    CONSTRAINT decision_mainland_closure_route_start_boundary_id_fkey FOREIGN KEY (start_boundary_id) REFERENCES atlas.source_features(id),
    CONSTRAINT decision_mainland_closure_routes_end_boundary_id_fkey FOREIGN KEY (end_boundary_id) REFERENCES atlas.source_features(id)
);

CREATE TABLE atlas.decision_mainland_seed_regions (
    id text NOT NULL,
    witnesses jsonb NOT NULL,
    CONSTRAINT decision_mainland_seed_regions_witnesses_check CHECK ((jsonb_typeof(witnesses) = 'array'::text)),
    CONSTRAINT decision_mainland_seed_regions_pkey PRIMARY KEY (id)
);

CREATE TABLE atlas.decision_mainland_region_segments (
    region_id text NOT NULL,
    ordinal integer NOT NULL,
    kind text NOT NULL,
    boundary_id text,
    route_id text,
    reverse boolean NOT NULL,
    CONSTRAINT decision_mainland_region_segments_check1 CHECK ((((kind = 'boundary'::text) AND (boundary_id IS NOT NULL) AND (route_id IS NULL)) OR ((kind = 'route'::text) AND (route_id IS NOT NULL) AND (boundary_id IS NULL)))),
    CONSTRAINT decision_mainland_region_segments_kind_check CHECK ((kind = ANY (ARRAY['boundary'::text, 'route'::text]))),
    CONSTRAINT decision_mainland_region_segments_ordinal_check CHECK ((ordinal >= 0)),
    CONSTRAINT decision_mainland_region_segments_pkey PRIMARY KEY (region_id, ordinal),
    CONSTRAINT decision_mainland_region_segments_boundary_id_fkey FOREIGN KEY (boundary_id) REFERENCES atlas.source_features(id),
    CONSTRAINT decision_mainland_region_segments_region_id_fkey FOREIGN KEY (region_id) REFERENCES atlas.decision_mainland_seed_regions(id),
    CONSTRAINT decision_mainland_region_segments_route_id_fkey FOREIGN KEY (route_id) REFERENCES atlas.decision_mainland_closure_routes(id)
);

CREATE TABLE atlas.decision_mainland_witnesses (
    id text NOT NULL,
    point_feature_id text NOT NULL,
    identity_feature_id text NOT NULL,
    radius_cells integer NOT NULL,
    max_water_cells integer NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witnesses_check CHECK ((point_feature_id <> identity_feature_id)),
    CONSTRAINT decision_mainland_witnesses_max_water_cells_check CHECK ((max_water_cells >= 0)),
    CONSTRAINT decision_mainland_witnesses_radius_cells_check CHECK (((radius_cells >= 0) AND (radius_cells <= 100))),
    CONSTRAINT decision_mainland_witnesses_pkey PRIMARY KEY (id),
    CONSTRAINT decision_mainland_witnesses_identity_feature_id_fkey FOREIGN KEY (identity_feature_id) REFERENCES atlas.source_features(id),
    CONSTRAINT decision_mainland_witnesses_point_feature_id_fkey FOREIGN KEY (point_feature_id) REFERENCES atlas.source_features(id)
);

CREATE TABLE atlas.decision_mainland_witness_groups (
    id text NOT NULL,
    role text NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witness_groups_role_check CHECK ((role = ANY (ARRAY['mainland'::text, 'sentinel'::text]))),
    CONSTRAINT decision_mainland_witness_groups_pkey PRIMARY KEY (id)
);

CREATE TABLE atlas.decision_mainland_witness_group_members (
    group_id text NOT NULL,
    witness_id text NOT NULL,
    CONSTRAINT decision_mainland_witness_group_member_witness_id_key1 UNIQUE (witness_id),
    CONSTRAINT decision_mainland_witness_group_members_pkey PRIMARY KEY (group_id, witness_id),
    CONSTRAINT decision_mainland_witness_group_member_witness_id_fkey FOREIGN KEY (witness_id) REFERENCES atlas.decision_mainland_witnesses(id),
    CONSTRAINT decision_mainland_witness_group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES atlas.decision_mainland_witness_groups(id)
);


CREATE TABLE atlas.decision_mainland_witness_group_targets (
    group_id text NOT NULL,
    entity_id bigint NOT NULL,
    CONSTRAINT decision_mainland_witness_group_targets_pkey PRIMARY KEY (group_id, entity_id),
    CONSTRAINT decision_mainland_witness_group_targets_entity_id_key UNIQUE (entity_id),
    CONSTRAINT decision_mainland_witness_group__entity_id_fkey FOREIGN KEY (entity_id) REFERENCES atlas.geographic_entities(id),
    CONSTRAINT decision_mainland_witness_group_targets_group_id_fkey FOREIGN KEY (group_id) REFERENCES atlas.decision_mainland_witness_groups(id)
);

CREATE TABLE atlas.decision_mainland_distinct_groups (
    group_a text NOT NULL,
    group_b text NOT NULL,
    CONSTRAINT decision_mainland_distinct_groups_check CHECK ((group_a < group_b)),
    CONSTRAINT decision_mainland_distinct_groups_pkey PRIMARY KEY (group_a, group_b),
    CONSTRAINT decision_mainland_distinct_groups_group_a_fkey FOREIGN KEY (group_a) REFERENCES atlas.decision_mainland_witness_groups(id),
    CONSTRAINT decision_mainland_distinct_groups_group_b_fkey FOREIGN KEY (group_b) REFERENCES atlas.decision_mainland_witness_groups(id)
);
