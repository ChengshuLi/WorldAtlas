BEGIN;
INSERT INTO atlas.geographic_entities(id,name,level) VALUES (81,'First','continent'),(42,'Second','continent');
INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
VALUES ('__partition_raw','Test','Test','test:raw','Test','test:license','Test','test','partition',repeat('a',64),1);
INSERT INTO atlas.construction_records VALUES ('__partition_recipe',
'{"method":"geodesic_trace","source_ids":["__partition_raw"],"source_feature_id":"Figure 1","feature_id":"__partition_line","basis":"Selected points","points":[[0,-1],[0,1]],"max_step_metres":1000}');
INSERT INTO atlas.source_features VALUES ('__partition_line','Figure 1','{"type":"LineString","coordinates":[[0,-1],[0,1]]}','__partition_recipe');
INSERT INTO atlas.geographic_partitions(id,method,feature_id,bounds_lon_lat,side_a_entity_id,side_a_witness,side_b_entity_id,side_b_witness,rationale)
VALUES ('__partition','land_components','__partition_line',ARRAY[-1,-1,1,1],81,ARRAY[-0.5,0],42,ARRAY[0.5,0],'A source-backed divide');
DO $$ DECLARE bounds double precision[]; BEGIN
 FOREACH bounds SLICE 1 IN ARRAY ARRAY[ARRAY[0,0,0,0],ARRAY[-181,-1,1,1],ARRAY[-1,-1,1,'NaN'::float8]] LOOP
  BEGIN
   UPDATE atlas.geographic_partitions SET bounds_lon_lat=bounds;
   RAISE EXCEPTION 'invalid partition bounds accepted';
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
 BEGIN
  UPDATE atlas.geographic_partitions SET bounds_lon_lat=ARRAY[]::float8[];
  RAISE EXCEPTION 'empty partition bounds accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.geographic_partitions SET side_a_witness=ARRAY[181,0];
  RAISE EXCEPTION 'invalid side witness accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.geographic_partitions SET side_b_entity_id=81;
  RAISE EXCEPTION 'identical partition targets accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.geographic_partitions SET method='ocean_barrier';
  RAISE EXCEPTION 'ocean barrier accepted component scope and witnesses';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.geographic_partitions SET extend_to_south_grid_edge=true;
  RAISE EXCEPTION 'land partition accepted an ocean grid extension';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.geographic_partitions SET method='mainland_seeds',feature_id=NULL,
    bounds_lon_lat=NULL,side_a_witness=NULL,side_b_witness=NULL;
  RAISE EXCEPTION 'mainland seeds accepted missing group and region';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
UPDATE atlas.geographic_partitions SET method='ocean_barrier',bounds_lon_lat=NULL,
 side_a_witness=NULL,side_b_witness=NULL,extend_to_south_grid_edge=true;
DO $$ BEGIN
 BEGIN
  UPDATE atlas.geographic_partitions SET feature_id=NULL;
  RAISE EXCEPTION 'ocean barrier accepted missing line';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
ROLLBACK;
