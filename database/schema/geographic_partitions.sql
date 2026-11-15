-- A source-backed divider assigns complete land components on each side.
CREATE TABLE atlas.geographic_partitions (
    id text PRIMARY KEY CHECK (length(trim(id)) > 0),
    feature_id text NOT NULL REFERENCES atlas.source_features(id),
    bounds_lon_lat double precision[] NOT NULL,
    side_a_entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    side_a_witness double precision[] NOT NULL,
    side_b_entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    side_b_witness double precision[] NOT NULL,
    rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
    mainland_group_id text UNIQUE REFERENCES atlas.decision_mainland_witness_groups(id),
    mainland_region_id text REFERENCES atlas.decision_mainland_seed_regions(id),
    CHECK (side_a_entity_id <> side_b_entity_id),
    CHECK (atlas.valid_source_coordinates(to_jsonb(side_a_witness),'Point')),
    CHECK (atlas.valid_source_coordinates(to_jsonb(side_b_witness),'Point')),
    CONSTRAINT geographic_partitions_bounds_check CHECK (coalesce(array_ndims(bounds_lon_lat)=1 AND array_length(bounds_lon_lat,1)=4
           AND array_position(bounds_lon_lat,NULL) IS NULL
           AND -180 <= bounds_lon_lat[1] AND bounds_lon_lat[1] < bounds_lon_lat[3]
           AND bounds_lon_lat[3] <= 180
           AND -90 <= bounds_lon_lat[2] AND bounds_lon_lat[2] < bounds_lon_lat[4]
           AND bounds_lon_lat[4] <= 90, false)),
    CHECK ((mainland_group_id IS NULL) = (mainland_region_id IS NULL))
);
