-- Source-backed geometry, geographic choices, citations and assignment policies.

-- Geometry uses WGS84 [longitude, latitude] in degrees. Imports also check validity with GEOS.
CREATE FUNCTION atlas.valid_source_coordinates(value jsonb, kind text)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
DECLARE child jsonb; child_kind text; minimum integer; x numeric; y numeric;
BEGIN
  IF jsonb_typeof(value) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
  IF kind = 'Point' THEN
    IF jsonb_array_length(value) <> 2
       OR jsonb_typeof(value->0) IS DISTINCT FROM 'number'
       OR jsonb_typeof(value->1) IS DISTINCT FROM 'number' THEN RETURN false; END IF;
    x := (value->>0)::numeric; y := (value->>1)::numeric;
    RETURN x BETWEEN -180 AND 180 AND y BETWEEN -90 AND 90;
  END IF;
  CASE kind
    WHEN 'MultiPoint' THEN child_kind := 'Point'; minimum := 1;
    WHEN 'LineString' THEN child_kind := 'Point'; minimum := 2;
    WHEN 'Ring' THEN child_kind := 'Point'; minimum := 4;
    WHEN 'MultiLineString' THEN child_kind := 'LineString'; minimum := 1;
    WHEN 'Polygon' THEN child_kind := 'Ring'; minimum := 1;
    WHEN 'MultiPolygon' THEN child_kind := 'Polygon'; minimum := 1;
    ELSE RETURN false;
  END CASE;
  IF jsonb_array_length(value) < minimum THEN RETURN false; END IF;
  IF kind = 'Ring' AND value->0 <> value->-1 THEN RETURN false; END IF;
  FOR child IN SELECT jsonb_array_elements(value) LOOP
    IF NOT atlas.valid_source_coordinates(child, child_kind) THEN RETURN false; END IF;
  END LOOP;
  RETURN true;
END; $$;

CREATE FUNCTION atlas.valid_source_geometry(geometry jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT CASE WHEN jsonb_typeof(geometry) = 'object' THEN COALESCE(
    geometry ?& ARRAY['type','coordinates']
    AND geometry - ARRAY['type','coordinates'] = '{}'::jsonb
    AND geometry->>'type' IN ('Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon')
    AND atlas.valid_source_coordinates(geometry->'coordinates', geometry->>'type'),
    false) ELSE false END;
$$;

CREATE TABLE atlas.source_features (
    id text PRIMARY KEY CHECK (length(trim(id)) > 0),
    source_feature_id text NOT NULL CHECK (length(trim(source_feature_id)) > 0),
    geometry jsonb NOT NULL,
    construction_id text NOT NULL REFERENCES atlas.construction_records(id),
    CONSTRAINT source_features_geometry_check CHECK (atlas.valid_source_geometry(geometry))
);

-- An assignment selects whole components using the union of imported features.
CREATE FUNCTION atlas.valid_feature_ids(identifiers text[])
RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT COALESCE(
        array_ndims(identifiers) = 1 AND cardinality(identifiers) > 0
        AND NOT EXISTS (SELECT FROM unnest(identifiers) ident
                        WHERE ident IS NULL OR ident !~ '[^[:space:]]')
        AND cardinality(identifiers) = (SELECT count(DISTINCT ident) FROM unnest(identifiers) ident),
        false);
$$;

CREATE TABLE atlas.geographic_assignments (
    id text PRIMARY KEY CHECK (length(trim(id)) > 0),
    entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
    feature_ids text[] NOT NULL CHECK (atlas.valid_feature_ids(feature_ids))
);

CREATE TABLE atlas.geographic_assignment_sources (
    assignment_id text NOT NULL REFERENCES atlas.geographic_assignments(id),
    source_id text NOT NULL REFERENCES atlas.source_assets(id),
    citation_section text NOT NULL CHECK (length(trim(citation_section)) > 0),
    interpretation text NOT NULL CHECK (length(trim(interpretation)) > 0),
    PRIMARY KEY (assignment_id, source_id)
);

-- Interior witnesses seed ocean fill; the selected source polygon establishes identity.
CREATE TABLE atlas.ocean_seeds (
    id bigint PRIMARY KEY REFERENCES atlas.geographic_entities(id),
    feature_id text NOT NULL REFERENCES atlas.source_features(id),
    witness double precision[] NOT NULL,
    CHECK (atlas.valid_source_coordinates(to_jsonb(witness),'Point'))
);

CREATE TABLE atlas.decision_policies (
    id text NOT NULL,
    kind text NOT NULL,
    definition jsonb NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_policies_definition_check CHECK ((jsonb_typeof(definition) = 'object'::text)),
    CONSTRAINT decision_policies_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_policies_kind_check CHECK ((kind = ANY (ARRAY['layer_precedence'::text, 'coastline_assignment'::text, 'ocean_fill'::text, 'closed_water_assignment'::text]))),
    CONSTRAINT decision_policies_id_check CHECK ((length(TRIM(BOTH FROM id)) > 0)),
    CONSTRAINT decision_policies_pkey PRIMARY KEY (id)
);

CREATE UNIQUE INDEX decision_single_assignment_policy ON atlas.decision_policies USING btree (kind) WHERE (kind = ANY (ARRAY['ocean_fill'::text, 'coastline_assignment'::text, 'closed_water_assignment'::text, 'layer_precedence'::text]));

CREATE TABLE atlas.decision_basins (
    id text NOT NULL,
    feature_id text NOT NULL,
    method text NOT NULL,
    tie_rules jsonb NOT NULL,
    evidence jsonb NOT NULL,
    CONSTRAINT decision_basins_id_check CHECK ((length(TRIM(BOTH FROM id)) > 0)),
    CONSTRAINT decision_basins_evidence_check CHECK ((jsonb_typeof(evidence) = 'object'::text)),
    CONSTRAINT decision_basins_method_check CHECK ((length(TRIM(BOTH FROM method)) > 0)),
    CONSTRAINT decision_basins_tie_rules_check CHECK ((jsonb_typeof(tie_rules) = 'object'::text)),
    CONSTRAINT decision_basins_pkey PRIMARY KEY (id),
    CONSTRAINT decision_basins_feature_id_fkey FOREIGN KEY (feature_id) REFERENCES atlas.source_features(id)
);
