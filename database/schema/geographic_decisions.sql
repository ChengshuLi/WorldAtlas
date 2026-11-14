-- Source-backed geometry, geographic choices, citations and assignment policies.

CREATE TABLE atlas.decision_revisions (
    revision text NOT NULL,
    entity_revision text NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_revisions_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_revisions_revision_check CHECK ((length(TRIM(BOTH FROM revision)) > 0)),
    CONSTRAINT decision_revisions_pkey PRIMARY KEY (revision),
    CONSTRAINT decision_revisions_revision_entity_revision_key UNIQUE (revision, entity_revision),
    CONSTRAINT decision_revisions_entity_revision_fkey FOREIGN KEY (entity_revision) REFERENCES atlas.entity_registry_revisions(revision)
);

CREATE TABLE atlas.decision_features (
    revision text NOT NULL,
    feature_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    source_feature_id text NOT NULL,
    geometry_sha256 text NOT NULL,
    evidence jsonb NOT NULL,
    geometry jsonb,
    coordinate_reference text,
    construction_id text,
    construction_version text,
    CONSTRAINT decision_features_check CHECK (((construction_id IS NULL) = (construction_version IS NULL))),
    CONSTRAINT decision_features_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_features_feature_id_check CHECK ((length(TRIM(BOTH FROM feature_id)) > 0)),
    CONSTRAINT decision_features_geometry CHECK (COALESCE((((geometry IS NULL) AND (coordinate_reference IS NULL)) OR ((geometry IS NOT NULL) AND (jsonb_typeof(geometry) = 'object'::text) AND (geometry ? 'type'::text) AND (geometry ? 'coordinates'::text) AND (coordinate_reference IS NOT NULL) AND (length(TRIM(BOTH FROM coordinate_reference)) > 0))), false)),
    CONSTRAINT decision_features_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT decision_features_source_feature_id_check CHECK ((length(TRIM(BOTH FROM source_feature_id)) > 0)),
    CONSTRAINT decision_features_pkey PRIMARY KEY (revision, feature_id),
    CONSTRAINT decision_features_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.construction_records(source_id, version),
    CONSTRAINT decision_features_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision),
    CONSTRAINT decision_features_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version)
);

CREATE TABLE atlas.geographic_line_observations (
    line_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    geometry jsonb NOT NULL,
    geometry_sha256 text NOT NULL,
    coordinate_reference text NOT NULL,
    provenance jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    construction_id text,
    construction_version text,
    CONSTRAINT geographic_line_observations_check CHECK (((construction_id IS NULL) = (construction_version IS NULL))),
    CONSTRAINT geographic_line_observations_geometry_check CHECK (((geometry ->> 'type'::text) = ANY (ARRAY['LineString'::text, 'MultiLineString'::text]))),
    CONSTRAINT geographic_line_observations_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT geographic_line_observations_pkey PRIMARY KEY (line_id),
    CONSTRAINT geographic_line_observations_construction_id_construction__fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.construction_records(source_id, version),
    CONSTRAINT geographic_line_observations_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version)
);

CREATE TABLE atlas.decision_cases (
    revision text NOT NULL,
    case_id text NOT NULL,
    title text NOT NULL,
    reason text NOT NULL,
    CONSTRAINT decision_cases_case_id_check CHECK ((length(TRIM(BOTH FROM case_id)) > 0)),
    CONSTRAINT decision_cases_reason_check CHECK ((length(TRIM(BOTH FROM reason)) > 0)),
    CONSTRAINT decision_cases_title_check CHECK ((length(TRIM(BOTH FROM title)) > 0)),
    CONSTRAINT decision_cases_pkey PRIMARY KEY (revision, case_id),
    CONSTRAINT decision_cases_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_case_sources (
    revision text NOT NULL,
    case_id text NOT NULL,
    source_id text NOT NULL,
    source_version text NOT NULL,
    citation_section text NOT NULL,
    interpretation text NOT NULL,
    limitations text[] DEFAULT '{}'::text[] NOT NULL,
    CONSTRAINT decision_case_sources_citation_section_check CHECK ((length(TRIM(BOTH FROM citation_section)) > 0)),
    CONSTRAINT decision_case_sources_interpretation_check CHECK ((length(TRIM(BOTH FROM interpretation)) > 0)),
    CONSTRAINT decision_case_sources_pkey PRIMARY KEY (revision, case_id, source_id, source_version),
    CONSTRAINT decision_case_sources_revision_case_id_fkey FOREIGN KEY (revision, case_id) REFERENCES atlas.decision_cases(revision, case_id),
    CONSTRAINT decision_case_sources_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version)
);

CREATE TABLE atlas.decision_affiliations (
    revision text NOT NULL,
    affiliation_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    rationale text NOT NULL,
    evidence jsonb NOT NULL,
    case_id text,
    component_selection jsonb NOT NULL,
    CONSTRAINT decision_affiliations_affiliation_id_check CHECK ((length(TRIM(BOTH FROM affiliation_id)) > 0)),
    CONSTRAINT decision_affiliations_component_selection_check CHECK ((jsonb_typeof(component_selection) = 'object'::text)),
    CONSTRAINT decision_affiliations_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_affiliations_rationale_check CHECK ((length(TRIM(BOTH FROM rationale)) > 0)),
    CONSTRAINT decision_affiliations_pkey PRIMARY KEY (revision, affiliation_id),
    CONSTRAINT decision_affiliations_entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id),
    CONSTRAINT decision_affiliations_revision_case_id_fkey FOREIGN KEY (revision, case_id) REFERENCES atlas.decision_cases(revision, case_id),
    CONSTRAINT decision_affiliations_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision)
);

CREATE TABLE atlas.regional_island_rule_sets (
    revision text NOT NULL,
    rule_set_id text NOT NULL,
    line_id text NOT NULL,
    definition jsonb NOT NULL,
    evidence jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    CONSTRAINT regional_island_rule_sets_definition_check CHECK ((jsonb_typeof(definition) = 'object'::text)),
    CONSTRAINT regional_island_rule_sets_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT regional_island_rule_sets_rule_set_id_check CHECK ((length(btrim(rule_set_id)) > 0)),
    CONSTRAINT regional_island_rule_sets_pkey PRIMARY KEY (revision, rule_set_id),
    CONSTRAINT regional_island_rule_sets_line_id_fkey FOREIGN KEY (line_id) REFERENCES atlas.geographic_line_observations(line_id),
    CONSTRAINT regional_island_rule_sets_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_endpoints (
    revision text NOT NULL,
    endpoint_id text NOT NULL,
    name text NOT NULL,
    longitude numeric NOT NULL,
    latitude numeric NOT NULL,
    derivation jsonb NOT NULL,
    evidence jsonb NOT NULL,
    construction_id text,
    construction_version text,
    CONSTRAINT decision_endpoints_check CHECK (((construction_id IS NULL) = (construction_version IS NULL))),
    CONSTRAINT decision_endpoints_derivation_check CHECK ((jsonb_typeof(derivation) = 'object'::text)),
    CONSTRAINT decision_endpoints_endpoint_id_check CHECK ((length(TRIM(BOTH FROM endpoint_id)) > 0)),
    CONSTRAINT decision_endpoints_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_endpoints_latitude_check CHECK (((latitude >= ('-90'::integer)::numeric) AND (latitude <= (90)::numeric))),
    CONSTRAINT decision_endpoints_longitude_check CHECK (((longitude >= ('-180'::integer)::numeric) AND (longitude <= (180)::numeric))),
    CONSTRAINT decision_endpoints_name_check CHECK ((length(TRIM(BOTH FROM name)) > 0)),
    CONSTRAINT decision_endpoints_pkey PRIMARY KEY (revision, endpoint_id),
    CONSTRAINT decision_endpoints_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.construction_records(source_id, version),
    CONSTRAINT decision_endpoints_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_routes (
    revision text NOT NULL,
    route_id text NOT NULL,
    route_type text NOT NULL,
    parameters jsonb NOT NULL,
    evidence jsonb NOT NULL,
    construction_id text,
    construction_version text,
    CONSTRAINT decision_routes_check CHECK (((construction_id IS NULL) = (construction_version IS NULL))),
    CONSTRAINT decision_routes_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_routes_parameters_check CHECK ((jsonb_typeof(parameters) = 'object'::text)),
    CONSTRAINT decision_routes_route_id_check CHECK ((length(TRIM(BOTH FROM route_id)) > 0)),
    CONSTRAINT decision_routes_route_type_check CHECK ((length(TRIM(BOTH FROM route_type)) > 0)),
    CONSTRAINT decision_routes_pkey PRIMARY KEY (revision, route_id),
    CONSTRAINT decision_routes_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.construction_records(source_id, version),
    CONSTRAINT decision_routes_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE TABLE atlas.decision_route_points (
    revision text NOT NULL,
    route_id text NOT NULL,
    ordinal integer NOT NULL,
    endpoint_id text NOT NULL,
    CONSTRAINT decision_route_points_ordinal_check CHECK ((ordinal >= 0)),
    CONSTRAINT decision_route_points_pkey PRIMARY KEY (revision, route_id, ordinal),
    CONSTRAINT decision_route_points_revision_endpoint_id_fkey FOREIGN KEY (revision, endpoint_id) REFERENCES atlas.decision_endpoints(revision, endpoint_id),
    CONSTRAINT decision_route_points_revision_route_id_fkey FOREIGN KEY (revision, route_id) REFERENCES atlas.decision_routes(revision, route_id)
);

CREATE TABLE atlas.decision_ocean_seeds (
    revision text NOT NULL,
    seed_id text NOT NULL,
    endpoint_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_ocean_seeds_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_ocean_seeds_seed_id_check CHECK ((length(TRIM(BOTH FROM seed_id)) > 0)),
    CONSTRAINT decision_ocean_seeds_pkey PRIMARY KEY (revision, seed_id),
    CONSTRAINT decision_ocean_seeds_entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id),
    CONSTRAINT decision_ocean_seeds_revision_endpoint_id_fkey FOREIGN KEY (revision, endpoint_id) REFERENCES atlas.decision_endpoints(revision, endpoint_id),
    CONSTRAINT decision_ocean_seeds_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision)
);

CREATE TABLE atlas.decision_policies (
    revision text NOT NULL,
    policy_id text NOT NULL,
    kind text NOT NULL,
    definition jsonb NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_policies_definition_check CHECK ((jsonb_typeof(definition) = 'object'::text)),
    CONSTRAINT decision_policies_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_policies_kind_check CHECK ((kind = ANY (ARRAY['layer_precedence'::text, 'coastline_assignment'::text, 'scoped_land_partition'::text, 'ocean_fill'::text, 'closed_water_assignment'::text, 'mainland_assignment'::text]))),
    CONSTRAINT decision_policies_policy_id_check CHECK ((length(TRIM(BOTH FROM policy_id)) > 0)),
    CONSTRAINT decision_policies_pkey PRIMARY KEY (revision, policy_id),
    CONSTRAINT decision_policies_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);

CREATE UNIQUE INDEX decision_single_assignment_policy ON atlas.decision_policies USING btree (revision, kind) WHERE (kind = ANY (ARRAY['mainland_assignment'::text, 'ocean_fill'::text, 'coastline_assignment'::text, 'closed_water_assignment'::text, 'layer_precedence'::text]));

CREATE TABLE atlas.decision_basins (
    revision text NOT NULL,
    basin_id text NOT NULL,
    feature_id text NOT NULL,
    method text NOT NULL,
    tie_rules jsonb NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_basins_basin_id_check CHECK ((length(TRIM(BOTH FROM basin_id)) > 0)),
    CONSTRAINT decision_basins_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_basins_method_check CHECK ((length(TRIM(BOTH FROM method)) > 0)),
    CONSTRAINT decision_basins_tie_rules_check CHECK ((jsonb_typeof(tie_rules) = 'object'::text)),
    CONSTRAINT decision_basins_pkey PRIMARY KEY (revision, basin_id),
    CONSTRAINT decision_basins_revision_feature_id_fkey FOREIGN KEY (revision, feature_id) REFERENCES atlas.decision_features(revision, feature_id),
    CONSTRAINT decision_basins_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision)
);
