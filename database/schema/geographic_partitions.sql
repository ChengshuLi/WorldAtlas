-- Explicit dividers share geometry references and two entity targets.
CREATE TABLE atlas.geographic_partitions (
    id text PRIMARY KEY CHECK (length(trim(id)) > 0),
    method text NOT NULL CHECK (method IN ('land_components','land_cells','mainland_seeds','ocean_barrier')),
    feature_id text REFERENCES atlas.source_features(id),
    bounds_lon_lat double precision[],
    side_a_entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    side_a_witness double precision[],
    side_b_entity_id bigint NOT NULL REFERENCES atlas.geographic_entities(id),
    side_b_witness double precision[],
    rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
    mainland_group_id text REFERENCES atlas.decision_mainland_witness_groups(id),
    mainland_region_id text REFERENCES atlas.decision_mainland_seed_regions(id),
    extend_to_south_grid_edge boolean NOT NULL DEFAULT false,
    CHECK (side_a_entity_id <> side_b_entity_id),
    CHECK (side_a_witness IS NULL OR atlas.valid_source_coordinates(to_jsonb(side_a_witness),'Point')),
    CHECK (side_b_witness IS NULL OR atlas.valid_source_coordinates(to_jsonb(side_b_witness),'Point')),
    CONSTRAINT geographic_partitions_bounds_check CHECK (bounds_lon_lat IS NULL OR coalesce(array_ndims(bounds_lon_lat)=1 AND array_length(bounds_lon_lat,1)=4
           AND array_position(bounds_lon_lat,NULL) IS NULL
           AND -180 <= bounds_lon_lat[1] AND bounds_lon_lat[1] < bounds_lon_lat[3]
           AND bounds_lon_lat[3] <= 180
           AND -90 <= bounds_lon_lat[2] AND bounds_lon_lat[2] < bounds_lon_lat[4]
           AND bounds_lon_lat[4] <= 90, false)),
    CHECK ((method IN ('land_components','ocean_barrier')) = (feature_id IS NOT NULL)),
    CHECK ((method IN ('land_components','land_cells')) = (bounds_lon_lat IS NOT NULL)),
    CHECK ((method IN ('land_components','land_cells')) = (side_a_witness IS NOT NULL)),
    CHECK ((side_a_witness IS NULL) = (side_b_witness IS NULL)),
    CHECK (NOT extend_to_south_grid_edge OR method='ocean_barrier'),
    CHECK (CASE method
       WHEN 'land_components' THEN (mainland_group_id IS NULL) = (mainland_region_id IS NULL)
       WHEN 'mainland_seeds' THEN mainland_group_id IS NOT NULL AND mainland_region_id IS NOT NULL
       WHEN 'land_cells' THEN mainland_group_id IS NULL AND mainland_region_id IS NOT NULL
       WHEN 'ocean_barrier' THEN mainland_group_id IS NULL AND mainland_region_id IS NULL END),
    CHECK ((method IN ('mainland_seeds','land_cells')) = (feature_id IS NULL AND mainland_region_id IS NOT NULL))
);

CREATE UNIQUE INDEX geographic_partition_mainland_group ON atlas.geographic_partitions(mainland_group_id)
WHERE mainland_group_id IS NOT NULL;
