-- Imported geographic geometry and its producing construction.

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
    id text PRIMARY KEY CHECK (atlas.nonblank(id)),
    geometry jsonb NOT NULL,
    construction_id text NOT NULL REFERENCES atlas.construction_records(id),
    CONSTRAINT source_features_geometry_check CHECK (atlas.valid_source_geometry(geometry))
);

