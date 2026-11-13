-- Initial schema for an empty database. Load constructions, geography and releases separately.
BEGIN;
CREATE SCHEMA atlas;

CREATE FUNCTION atlas.check_geographic_entity_parent() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE parent_level text;
BEGIN
  IF NEW.parent_id IS NOT NULL THEN
    SELECT level INTO parent_level FROM atlas.geographic_entities
      WHERE revision = NEW.revision AND id = NEW.parent_id;
    IF parent_level IS DISTINCT FROM (CASE NEW.level
      WHEN 'subcontinent' THEN 'continent' WHEN 'region' THEN 'subcontinent'
      WHEN 'area' THEN 'region' WHEN 'province' THEN 'area'
      WHEN 'location' THEN 'province' END) THEN
      RAISE EXCEPTION 'invalid parent level for entity %', NEW.id;
    END IF;
  END IF;
  -- A parent's level change must not invalidate existing children.
  IF EXISTS (SELECT 1 FROM atlas.geographic_entities c
    WHERE c.revision = NEW.revision AND c.parent_id = NEW.id
      AND NEW.level IS DISTINCT FROM (CASE c.level
        WHEN 'subcontinent' THEN 'continent' WHEN 'region' THEN 'subcontinent'
        WHEN 'area' THEN 'region' WHEN 'province' THEN 'area'
        WHEN 'location' THEN 'province' END)) THEN
    RAISE EXCEPTION 'invalid child level for entity %', NEW.id;
  END IF;
  RETURN NULL;
END; $$;

CREATE FUNCTION atlas.guard_map_publication() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF TG_OP='UPDATE' AND (NEW.map_version,NEW.release_id) IS DISTINCT FROM (OLD.map_version,OLD.release_id) THEN
  RAISE EXCEPTION 'published versions are immutable';
 END IF;
 IF TG_OP='INSERT' AND NOT EXISTS (
  SELECT 1 FROM atlas.map_releases WHERE release_id=NEW.release_id AND approved_at IS NOT NULL) THEN
  RAISE EXCEPTION 'approve the exact release before publishing';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas.guard_map_release() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.approved_at IS NOT NULL THEN RAISE EXCEPTION 'stage the release before approving it'; END IF;
 ELSIF OLD.approved_at IS NOT NULL OR NEW.approved_at IS NULL
  OR (NEW.release_id,NEW.r2_bucket,NEW.manifest) IS DISTINCT FROM (OLD.release_id,OLD.r2_bucket,OLD.manifest) THEN
  RAISE EXCEPTION 'only an unapproved release can receive approval';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas.guard_source_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF (NEW.source_id,NEW.version,NEW.r2_bucket,NEW.r2_key,NEW.sha256,NEW.size_bytes,
     NEW.source_uri,NEW.provenance,NEW.created_at) IS DISTINCT FROM
    (OLD.source_id,OLD.version,OLD.r2_bucket,OLD.r2_key,OLD.sha256,OLD.size_bytes,
     OLD.source_uri,OLD.provenance,OLD.created_at) THEN
  RAISE EXCEPTION 'source identity and captured bytes are immutable; use a new source version';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas.reject_source_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  RAISE EXCEPTION 'source records are immutable; use a new source version';
END; $$;

CREATE FUNCTION atlas.valid_release_assets(objects jsonb) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
 SELECT jsonb_typeof(objects)='object' AND NOT EXISTS (
  SELECT 1 FROM jsonb_each(CASE WHEN jsonb_typeof(objects)='object' THEN objects ELSE '{}'::jsonb END) o
  WHERE NOT COALESCE(jsonb_typeof(value)='object'
   AND jsonb_typeof(value->'r2_key')='string' AND length(value->>'r2_key')>0
   AND value->>'sha256' ~ '^[0-9a-f]{64}$'
   AND jsonb_typeof(value->'content_type')='string' AND length(value->>'content_type')>0
   AND CASE WHEN jsonb_typeof(value->'size_bytes')='number' THEN
    (value->>'size_bytes')::numeric>=0 AND trunc((value->>'size_bytes')::numeric)=(value->>'size_bytes')::numeric
    ELSE false END,false))
$_$;

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
    CONSTRAINT decision_affiliations_rationale_check CHECK ((length(TRIM(BOTH FROM rationale)) > 0))
);

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
    CONSTRAINT decision_basins_tie_rules_check CHECK ((jsonb_typeof(tie_rules) = 'object'::text))
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
    CONSTRAINT decision_case_sources_interpretation_check CHECK ((length(TRIM(BOTH FROM interpretation)) > 0))
);

CREATE TABLE atlas.decision_cases (
    revision text NOT NULL,
    case_id text NOT NULL,
    title text NOT NULL,
    reason text NOT NULL,
    CONSTRAINT decision_cases_case_id_check CHECK ((length(TRIM(BOTH FROM case_id)) > 0)),
    CONSTRAINT decision_cases_reason_check CHECK ((length(TRIM(BOTH FROM reason)) > 0)),
    CONSTRAINT decision_cases_title_check CHECK ((length(TRIM(BOTH FROM title)) > 0))
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
    CONSTRAINT decision_endpoints_name_check CHECK ((length(TRIM(BOTH FROM name)) > 0))
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
    CONSTRAINT decision_features_source_feature_id_check CHECK ((length(TRIM(BOTH FROM source_feature_id)) > 0))
);

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
    CONSTRAINT decision_mainland_closure_routes_start_endpoint_check CHECK ((start_endpoint = ANY (ARRAY['start'::text, 'end'::text])))
);

CREATE TABLE atlas.decision_mainland_component_rules (
    revision text NOT NULL,
    rule_id text NOT NULL,
    group_id text NOT NULL,
    region_id text,
    entity_revision text NOT NULL,
    inside_entity_id bigint NOT NULL,
    outside_entity_id bigint NOT NULL,
    CONSTRAINT decision_mainland_component_rules_check CHECK ((((region_id IS NULL) AND (inside_entity_id = outside_entity_id)) OR ((region_id IS NOT NULL) AND (inside_entity_id <> outside_entity_id))))
);

CREATE TABLE atlas.decision_mainland_distinct_groups (
    revision text NOT NULL,
    group_a text NOT NULL,
    group_b text NOT NULL,
    CONSTRAINT decision_mainland_distinct_groups_check CHECK ((group_a < group_b))
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
    CONSTRAINT decision_mainland_region_segments_ordinal_check CHECK ((ordinal >= 0))
);

CREATE TABLE atlas.decision_mainland_seed_regions (
    revision text NOT NULL,
    region_id text NOT NULL,
    witnesses jsonb NOT NULL,
    CONSTRAINT decision_mainland_seed_regions_witnesses_check CHECK ((jsonb_typeof(witnesses) = 'array'::text))
);

CREATE TABLE atlas.decision_mainland_witness_group_members (
    revision text NOT NULL,
    group_id text NOT NULL,
    witness_id text NOT NULL
);

CREATE TABLE atlas.decision_mainland_witness_group_targets (
    revision text NOT NULL,
    group_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL
);

CREATE TABLE atlas.decision_mainland_witness_groups (
    revision text NOT NULL,
    group_id text NOT NULL,
    role text NOT NULL,
    rationale text NOT NULL,
    CONSTRAINT decision_mainland_witness_groups_role_check CHECK ((role = ANY (ARRAY['mainland'::text, 'sentinel'::text])))
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
    CONSTRAINT decision_mainland_witnesses_radius_cells_check CHECK (((radius_cells >= 0) AND (radius_cells <= 100)))
);

CREATE TABLE atlas.decision_ocean_seeds (
    revision text NOT NULL,
    seed_id text NOT NULL,
    endpoint_id text NOT NULL,
    entity_revision text NOT NULL,
    entity_id bigint NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_ocean_seeds_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_ocean_seeds_seed_id_check CHECK ((length(TRIM(BOTH FROM seed_id)) > 0))
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
    CONSTRAINT decision_policies_policy_id_check CHECK ((length(TRIM(BOTH FROM policy_id)) > 0))
);

CREATE TABLE atlas.decision_revisions (
    revision text NOT NULL,
    entity_revision text NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_revisions_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_revisions_revision_check CHECK ((length(TRIM(BOTH FROM revision)) > 0))
);

CREATE TABLE atlas.decision_route_points (
    revision text NOT NULL,
    route_id text NOT NULL,
    ordinal integer NOT NULL,
    endpoint_id text NOT NULL,
    CONSTRAINT decision_route_points_ordinal_check CHECK ((ordinal >= 0))
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
    CONSTRAINT decision_routes_route_type_check CHECK ((length(TRIM(BOTH FROM route_type)) > 0))
);

CREATE TABLE atlas.entity_registry_revisions (
    revision text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT entity_registry_revisions_revision_check CHECK ((length(TRIM(BOTH FROM revision)) > 0))
);

CREATE TABLE atlas.geographic_entities (
    revision text NOT NULL,
    id bigint NOT NULL,
    name text NOT NULL,
    level text NOT NULL,
    parent_id bigint,
    physical_class text,
    CONSTRAINT geographic_entities_check CHECK (((level = 'continent'::text) = (parent_id IS NULL))),
    CONSTRAINT geographic_entities_check1 CHECK (((level = 'location'::text) = (physical_class IS NOT NULL))),
    CONSTRAINT geographic_entities_check2 CHECK ((id <> parent_id)),
    CONSTRAINT geographic_entities_level_check CHECK ((level = ANY (ARRAY['continent'::text, 'subcontinent'::text, 'region'::text, 'area'::text, 'province'::text, 'location'::text]))),
    CONSTRAINT geographic_entities_name_check CHECK ((length(TRIM(BOTH FROM name)) > 0)),
    CONSTRAINT geographic_entities_physical_class_check CHECK ((physical_class = ANY (ARRAY['land'::text, 'water'::text])))
);

COMMENT ON COLUMN atlas.geographic_entities.level IS 'Hierarchy tier; the continent tier includes the top-level oceans. Physical class is specified on location leaves and map code bindings.';

CREATE TABLE atlas.geographic_entity_ids (
    id bigint NOT NULL,
    color_rgb text,
    CONSTRAINT geographic_entity_ids_color_rgb_check CHECK ((color_rgb ~ '^#[0-9A-Fa-f]{6}$'::text)),
    CONSTRAINT geographic_entity_ids_id_check CHECK (((id >= 1) AND (id <= '4294967295'::bigint)))
);

ALTER TABLE atlas.geographic_entity_ids ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME atlas.geographic_entity_ids_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
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
    CONSTRAINT geographic_line_observations_geometry_sha256_check CHECK ((geometry_sha256 ~ '^[0-9a-f]{64}$'::text))
);

CREATE TABLE atlas.map_publications (
    map_version text NOT NULL,
    release_id text NOT NULL,
    homepage_key text,
    CONSTRAINT map_publications_homepage_key_check CHECK (((homepage_key IS NULL) OR (length(btrim(homepage_key)) > 0)))
);

CREATE TABLE atlas.map_releases (
    release_id text NOT NULL,
    map_version text GENERATED ALWAYS AS (regexp_replace(release_id, '-rc\.?[1-9][0-9]*$'::text, ''::text)) STORED,
    r2_bucket text NOT NULL,
    manifest jsonb NOT NULL,
    approved_by text,
    approved_at timestamp with time zone,
    CONSTRAINT map_releases_approved_by_check CHECK ((length(btrim(approved_by)) > 0)),
    CONSTRAINT map_releases_check CHECK (((approved_by IS NULL) = (approved_at IS NULL))),
    CONSTRAINT map_releases_manifest_check CHECK (COALESCE(((jsonb_typeof(manifest) = 'object'::text) AND atlas.valid_release_assets((manifest -> 'objects'::text)) AND ((manifest -> 'objects'::text) ?& ARRAY['rows.u32le.gz'::text, 'runs.u32le.gz'::text]) AND ((manifest #>> '{decoded_sha256,rows}'::text[]) ~ '^[0-9a-f]{64}$'::text) AND ((manifest #>> '{decoded_sha256,runs}'::text[]) ~ '^[0-9a-f]{64}$'::text)), false)),
    CONSTRAINT map_releases_r2_bucket_check CHECK ((length(btrim(r2_bucket)) > 0)),
    CONSTRAINT map_releases_release_id_check CHECK ((release_id ~ '^v[0-9]+\.[0-9]+(-rc\.?[1-9][0-9]*)?$'::text))
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
    CONSTRAINT regional_island_rule_sets_rule_set_id_check CHECK ((length(btrim(rule_set_id)) > 0))
);

CREATE TABLE atlas.review_category_bindings (
    revision text NOT NULL,
    code bigint NOT NULL,
    entity_id bigint NOT NULL,
    physical_class text NOT NULL,
    CONSTRAINT review_category_bindings_code_check CHECK (((code >= 1) AND (code <= '4294967295'::bigint))),
    CONSTRAINT review_category_bindings_physical_class_check CHECK ((physical_class = ANY (ARRAY['land'::text, 'water'::text])))
);

CREATE TABLE atlas.source_assets (
    source_id text NOT NULL,
    version text NOT NULL,
    title text NOT NULL,
    provider text NOT NULL,
    source_uri text NOT NULL,
    license_name text NOT NULL,
    license_uri text NOT NULL,
    attribution text NOT NULL,
    r2_bucket text NOT NULL,
    r2_key text NOT NULL,
    sha256 text NOT NULL,
    size_bytes bigint NOT NULL,
    provenance jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_assets_attribution_check CHECK ((length(TRIM(BOTH FROM attribution)) > 0)),
    CONSTRAINT source_assets_license_name_check CHECK ((length(TRIM(BOTH FROM license_name)) > 0)),
    CONSTRAINT source_assets_license_uri_check CHECK ((length(TRIM(BOTH FROM license_uri)) > 0)),
    CONSTRAINT source_assets_provenance_check CHECK ((jsonb_typeof(provenance) = 'object'::text)),
    CONSTRAINT source_assets_provider_check CHECK ((length(TRIM(BOTH FROM provider)) > 0)),
    CONSTRAINT source_assets_r2_bucket_check CHECK ((length(TRIM(BOTH FROM r2_bucket)) > 0)),
    CONSTRAINT source_assets_r2_key_check CHECK ((length(TRIM(BOTH FROM r2_key)) > 0)),
    CONSTRAINT source_assets_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT source_assets_size_bytes_check CHECK ((size_bytes >= 0)),
    CONSTRAINT source_assets_source_id_check CHECK ((length(TRIM(BOTH FROM source_id)) > 0)),
    CONSTRAINT source_assets_source_uri_check CHECK ((length(TRIM(BOTH FROM source_uri)) > 0)),
    CONSTRAINT source_assets_title_check CHECK ((length(TRIM(BOTH FROM title)) > 0)),
    CONSTRAINT source_assets_version_check CHECK ((length(TRIM(BOTH FROM version)) > 0))
);

CREATE TABLE atlas.structured_documents (
    source_id text NOT NULL,
    version text NOT NULL,
    sha256 text NOT NULL,
    size_bytes bigint NOT NULL,
    document json NOT NULL,
    CONSTRAINT structured_documents_document_check CHECK ((json_typeof(document) = 'object'::text)),
    CONSTRAINT structured_documents_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT structured_documents_size_bytes_check CHECK ((size_bytes > 0)),
    CONSTRAINT structured_documents_source_id_check CHECK ((length(btrim(source_id)) > 0)),
    CONSTRAINT structured_documents_version_check CHECK ((length(btrim(version)) > 0))
);

COMMENT ON TABLE atlas.structured_documents IS 'Versioned pipeline inputs stored in Neon. Size and SHA-256 refer to the selected serialized document.';

ALTER TABLE ONLY atlas.decision_affiliations
    ADD CONSTRAINT decision_affiliations_pkey PRIMARY KEY (revision, affiliation_id);

ALTER TABLE ONLY atlas.decision_basins
    ADD CONSTRAINT decision_basins_pkey PRIMARY KEY (revision, basin_id);

ALTER TABLE ONLY atlas.decision_case_sources
    ADD CONSTRAINT decision_case_sources_pkey PRIMARY KEY (revision, case_id, source_id, source_version);

ALTER TABLE ONLY atlas.decision_cases
    ADD CONSTRAINT decision_cases_pkey PRIMARY KEY (revision, case_id);

ALTER TABLE ONLY atlas.decision_endpoints
    ADD CONSTRAINT decision_endpoints_pkey PRIMARY KEY (revision, endpoint_id);

ALTER TABLE ONLY atlas.decision_features
    ADD CONSTRAINT decision_features_pkey PRIMARY KEY (revision, feature_id);

ALTER TABLE ONLY atlas.decision_mainland_boundaries
    ADD CONSTRAINT decision_mainland_boundaries_pkey PRIMARY KEY (revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_sources_pkey PRIMARY KEY (revision, boundary_id, source_id, source_version);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_pkey PRIMARY KEY (revision, route_id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_pkey PRIMARY KEY (revision, rule_id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_group_id_key UNIQUE (revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_distinct_groups
    ADD CONSTRAINT decision_mainland_distinct_groups_pkey PRIMARY KEY (revision, group_a, group_b);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_pkey PRIMARY KEY (revision, region_id, ordinal);

ALTER TABLE ONLY atlas.decision_mainland_seed_regions
    ADD CONSTRAINT decision_mainland_seed_regions_pkey PRIMARY KEY (revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_member_revision_witness_id_key1 UNIQUE (revision, witness_id);

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

ALTER TABLE ONLY atlas.decision_ocean_seeds
    ADD CONSTRAINT decision_ocean_seeds_pkey PRIMARY KEY (revision, seed_id);

ALTER TABLE ONLY atlas.decision_policies
    ADD CONSTRAINT decision_policies_pkey PRIMARY KEY (revision, policy_id);

ALTER TABLE ONLY atlas.decision_revisions
    ADD CONSTRAINT decision_revisions_pkey PRIMARY KEY (revision);

ALTER TABLE ONLY atlas.decision_revisions
    ADD CONSTRAINT decision_revisions_revision_entity_revision_key UNIQUE (revision, entity_revision);

ALTER TABLE ONLY atlas.decision_route_points
    ADD CONSTRAINT decision_route_points_pkey PRIMARY KEY (revision, route_id, ordinal);

ALTER TABLE ONLY atlas.decision_routes
    ADD CONSTRAINT decision_routes_pkey PRIMARY KEY (revision, route_id);

ALTER TABLE ONLY atlas.entity_registry_revisions
    ADD CONSTRAINT entity_registry_revisions_pkey PRIMARY KEY (revision);

ALTER TABLE ONLY atlas.geographic_entities
    ADD CONSTRAINT geographic_entities_pkey PRIMARY KEY (revision, id);

ALTER TABLE ONLY atlas.geographic_entity_ids
    ADD CONSTRAINT geographic_entity_ids_pkey PRIMARY KEY (id);

ALTER TABLE ONLY atlas.geographic_line_observations
    ADD CONSTRAINT geographic_line_observations_pkey PRIMARY KEY (line_id);

ALTER TABLE ONLY atlas.map_publications
    ADD CONSTRAINT map_publications_homepage_key_key UNIQUE (homepage_key);

ALTER TABLE ONLY atlas.map_publications
    ADD CONSTRAINT map_publications_pkey PRIMARY KEY (map_version);

ALTER TABLE ONLY atlas.map_releases
    ADD CONSTRAINT map_releases_pkey PRIMARY KEY (release_id);

ALTER TABLE ONLY atlas.map_releases
    ADD CONSTRAINT map_releases_release_id_map_version_key UNIQUE (release_id, map_version);

ALTER TABLE ONLY atlas.regional_island_rule_sets
    ADD CONSTRAINT regional_island_rule_sets_pkey PRIMARY KEY (revision, rule_set_id);

ALTER TABLE ONLY atlas.review_category_bindings
    ADD CONSTRAINT review_category_bindings_pkey PRIMARY KEY (revision, code);

ALTER TABLE ONLY atlas.review_category_bindings
    ADD CONSTRAINT review_category_bindings_revision_entity_id_physical_class_key UNIQUE (revision, entity_id, physical_class);

ALTER TABLE ONLY atlas.source_assets
    ADD CONSTRAINT source_assets_pkey PRIMARY KEY (source_id, version);

ALTER TABLE ONLY atlas.source_assets
    ADD CONSTRAINT source_assets_r2_bucket_r2_key_key UNIQUE (r2_bucket, r2_key);

ALTER TABLE ONLY atlas.structured_documents
    ADD CONSTRAINT structured_documents_pkey PRIMARY KEY (source_id, version);

CREATE UNIQUE INDEX decision_single_assignment_policy ON atlas.decision_policies USING btree (revision, kind) WHERE (kind = ANY (ARRAY['mainland_assignment'::text, 'ocean_fill'::text, 'coastline_assignment'::text, 'closed_water_assignment'::text, 'layer_precedence'::text]));

CREATE CONSTRAINT TRIGGER geographic_entity_parent_check AFTER INSERT OR UPDATE ON atlas.geographic_entities DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas.check_geographic_entity_parent();

CREATE TRIGGER map_publication_guard BEFORE INSERT OR UPDATE ON atlas.map_publications FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_publication();

CREATE TRIGGER map_release_guard BEFORE INSERT OR UPDATE ON atlas.map_releases FOR EACH ROW EXECUTE FUNCTION atlas.guard_map_release();

CREATE TRIGGER source_asset_immutable BEFORE UPDATE ON atlas.source_assets FOR EACH ROW EXECUTE FUNCTION atlas.guard_source_identity();

CREATE TRIGGER structured_document_immutable BEFORE UPDATE ON atlas.structured_documents FOR EACH ROW EXECUTE FUNCTION atlas.reject_source_change();

ALTER TABLE ONLY atlas.decision_affiliations
    ADD CONSTRAINT decision_affiliations_entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_affiliations
    ADD CONSTRAINT decision_affiliations_revision_case_id_fkey FOREIGN KEY (revision, case_id) REFERENCES atlas.decision_cases(revision, case_id);

ALTER TABLE ONLY atlas.decision_affiliations
    ADD CONSTRAINT decision_affiliations_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_basins
    ADD CONSTRAINT decision_basins_revision_feature_id_fkey FOREIGN KEY (revision, feature_id) REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_basins
    ADD CONSTRAINT decision_basins_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_case_sources
    ADD CONSTRAINT decision_case_sources_revision_case_id_fkey FOREIGN KEY (revision, case_id) REFERENCES atlas.decision_cases(revision, case_id);

ALTER TABLE ONLY atlas.decision_cases
    ADD CONSTRAINT decision_cases_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_endpoints
    ADD CONSTRAINT decision_endpoints_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version);

ALTER TABLE ONLY atlas.decision_endpoints
    ADD CONSTRAINT decision_endpoints_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_features
    ADD CONSTRAINT decision_features_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version);

ALTER TABLE ONLY atlas.decision_features
    ADD CONSTRAINT decision_features_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_features
    ADD CONSTRAINT decision_features_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_case_sources
    ADD CONSTRAINT decision_case_sources_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_mainland_boundaries
    ADD CONSTRAINT decision_mainland_boundaries_construction_id_construction__fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version);

ALTER TABLE ONLY atlas.decision_mainland_boundaries
    ADD CONSTRAINT decision_mainland_boundaries_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_source_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.decision_mainland_boundary_sources
    ADD CONSTRAINT decision_mainland_boundary_sources_revision_boundary_id_fkey FOREIGN KEY (revision, boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_route_revision_start_boundary_id_fkey FOREIGN KEY (revision, start_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_revision_end_boundary_id_fkey FOREIGN KEY (revision, end_boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_closure_routes
    ADD CONSTRAINT decision_mainland_closure_routes_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_r_entity_revision_inside_entit_fkey FOREIGN KEY (entity_revision, inside_entity_id) REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_r_entity_revision_outside_enti_fkey FOREIGN KEY (entity_revision, outside_entity_id) REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_component_rules
    ADD CONSTRAINT decision_mainland_component_rules_revision_region_id_fkey FOREIGN KEY (revision, region_id) REFERENCES atlas.decision_mainland_seed_regions(revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_distinct_groups
    ADD CONSTRAINT decision_mainland_distinct_groups_revision_group_a_fkey FOREIGN KEY (revision, group_a) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_distinct_groups
    ADD CONSTRAINT decision_mainland_distinct_groups_revision_group_b_fkey FOREIGN KEY (revision, group_b) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_boundary_id_fkey FOREIGN KEY (revision, boundary_id) REFERENCES atlas.decision_mainland_boundaries(revision, boundary_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_region_id_fkey FOREIGN KEY (revision, region_id) REFERENCES atlas.decision_mainland_seed_regions(revision, region_id);

ALTER TABLE ONLY atlas.decision_mainland_region_segments
    ADD CONSTRAINT decision_mainland_region_segments_revision_route_id_fkey FOREIGN KEY (revision, route_id) REFERENCES atlas.decision_mainland_closure_routes(revision, route_id);

ALTER TABLE ONLY atlas.decision_mainland_seed_regions
    ADD CONSTRAINT decision_mainland_seed_regions_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group__entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_member_revision_witness_id_fkey FOREIGN KEY (revision, witness_id) REFERENCES atlas.decision_mainland_witnesses(revision, witness_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_members
    ADD CONSTRAINT decision_mainland_witness_group_members_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_t_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_mainland_witness_group_targets
    ADD CONSTRAINT decision_mainland_witness_group_targets_revision_group_id_fkey FOREIGN KEY (revision, group_id) REFERENCES atlas.decision_mainland_witness_groups(revision, group_id);

ALTER TABLE ONLY atlas.decision_mainland_witness_groups
    ADD CONSTRAINT decision_mainland_witness_groups_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_identity_feature_id_fkey FOREIGN KEY (revision, identity_feature_id) REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_mainland_witnesses
    ADD CONSTRAINT decision_mainland_witnesses_revision_point_feature_id_fkey FOREIGN KEY (revision, point_feature_id) REFERENCES atlas.decision_features(revision, feature_id);

ALTER TABLE ONLY atlas.decision_ocean_seeds
    ADD CONSTRAINT decision_ocean_seeds_entity_revision_entity_id_fkey FOREIGN KEY (entity_revision, entity_id) REFERENCES atlas.geographic_entities(revision, id);

ALTER TABLE ONLY atlas.decision_ocean_seeds
    ADD CONSTRAINT decision_ocean_seeds_revision_endpoint_id_fkey FOREIGN KEY (revision, endpoint_id) REFERENCES atlas.decision_endpoints(revision, endpoint_id);

ALTER TABLE ONLY atlas.decision_ocean_seeds
    ADD CONSTRAINT decision_ocean_seeds_revision_entity_revision_fkey FOREIGN KEY (revision, entity_revision) REFERENCES atlas.decision_revisions(revision, entity_revision);

ALTER TABLE ONLY atlas.decision_policies
    ADD CONSTRAINT decision_policies_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.decision_revisions
    ADD CONSTRAINT decision_revisions_entity_revision_fkey FOREIGN KEY (entity_revision) REFERENCES atlas.entity_registry_revisions(revision);

ALTER TABLE ONLY atlas.decision_route_points
    ADD CONSTRAINT decision_route_points_revision_endpoint_id_fkey FOREIGN KEY (revision, endpoint_id) REFERENCES atlas.decision_endpoints(revision, endpoint_id);

ALTER TABLE ONLY atlas.decision_route_points
    ADD CONSTRAINT decision_route_points_revision_route_id_fkey FOREIGN KEY (revision, route_id) REFERENCES atlas.decision_routes(revision, route_id);

ALTER TABLE ONLY atlas.decision_routes
    ADD CONSTRAINT decision_routes_construction_id_construction_version_fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version);

ALTER TABLE ONLY atlas.decision_routes
    ADD CONSTRAINT decision_routes_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.geographic_entities
    ADD CONSTRAINT geographic_entities_id_fkey FOREIGN KEY (id) REFERENCES atlas.geographic_entity_ids(id);

ALTER TABLE ONLY atlas.geographic_entities
    ADD CONSTRAINT geographic_entities_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.entity_registry_revisions(revision);

ALTER TABLE ONLY atlas.geographic_entities
    ADD CONSTRAINT geographic_entities_revision_parent_id_fkey FOREIGN KEY (revision, parent_id) REFERENCES atlas.geographic_entities(revision, id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY atlas.geographic_line_observations
    ADD CONSTRAINT geographic_line_observations_construction_id_construction__fkey FOREIGN KEY (construction_id, construction_version) REFERENCES atlas.structured_documents(source_id, version);

ALTER TABLE ONLY atlas.geographic_line_observations
    ADD CONSTRAINT geographic_line_observations_source_id_source_version_fkey FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version);

ALTER TABLE ONLY atlas.map_publications
    ADD CONSTRAINT map_publications_release_id_map_version_fkey FOREIGN KEY (release_id, map_version) REFERENCES atlas.map_releases(release_id, map_version);

ALTER TABLE ONLY atlas.regional_island_rule_sets
    ADD CONSTRAINT regional_island_rule_sets_line_id_fkey FOREIGN KEY (line_id) REFERENCES atlas.geographic_line_observations(line_id);

ALTER TABLE ONLY atlas.regional_island_rule_sets
    ADD CONSTRAINT regional_island_rule_sets_revision_fkey FOREIGN KEY (revision) REFERENCES atlas.decision_revisions(revision);

ALTER TABLE ONLY atlas.review_category_bindings
    ADD CONSTRAINT review_category_bindings_revision_entity_id_fkey FOREIGN KEY (revision, entity_id) REFERENCES atlas.geographic_entities(revision, id);
COMMIT;
