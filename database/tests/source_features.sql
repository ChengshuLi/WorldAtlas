-- Imported geometry has one explicit format, even when written directly with SQL.
BEGIN;
DO $$
DECLARE candidate jsonb;
BEGIN
 INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__geometry_raw','Test','Test','test:raw','Test','test:license','Test','test','geometry',repeat('a',64),1);
 INSERT INTO atlas.construction_records VALUES ('__geometry_recipe',
 '{"method":"selected_vector_features","source_id":"__geometry_raw","basis":"Selected geometry","id_field":"id","selections":[{"feature_id":"__geometry","source_feature_id":"provider"}]}');
 FOR candidate IN SELECT jsonb_array_elements('[
  {"type":"Point","coordinates":[-180,90]},
  {"type":"MultiPoint","coordinates":[[0,0],[1,1]]},
  {"type":"LineString","coordinates":[[0,0],[1,1]]},
  {"type":"MultiLineString","coordinates":[[[0,0],[1,1]],[[2,2],[3,3]]]},
  {"type":"Polygon","coordinates":[[[0,0],[3,0],[3,3],[0,0]],[[1,1],[2,1],[2,2],[1,1]]]},
  {"type":"MultiPolygon","coordinates":[[[[0,0],[1,0],[1,1],[0,0]]]]}
 ]'::jsonb) LOOP
  INSERT INTO atlas.source_features VALUES ('__geometry','__geometry_raw','provider',candidate,'OGC:CRS84','__geometry_recipe');
  DELETE FROM atlas.source_features WHERE feature_id='__geometry';
 END LOOP;
 INSERT INTO atlas.source_features VALUES ('__geometry','__geometry_raw','provider',
  '{"type":"Point","coordinates":[1000000,-2000000]}','EPSG:3338','__geometry_recipe');
 FOR candidate IN SELECT jsonb_array_elements('[
  null, [], "point", {},
  {"type":"Point","coordinates":[0,0],"extra":true},
  {"type":"Point","coordinates":[true,0]},
  {"type":"Point","coordinates":["0",0]},
  {"type":"Point","coordinates":[0]},
  {"type":"Point","coordinates":[0,0,1]},
  {"type":"Point","coordinates":[[0,0]]},
  {"type":"Point","coordinates":[181,0]},
  {"type":"Point","coordinates":[0,-91]},
  {"type":"Point","coordinates":[1e309,0]},
  {"type":"Point"},
  {"coordinates":[0,0]},
  {"type":"MultiPoint","coordinates":[]},
  {"type":"LineString","coordinates":[[0,0]]},
  {"type":"MultiLineString","coordinates":[[]]},
  {"type":"Polygon","coordinates":[[[0,0],[1,0],[0,0]]]},
  {"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1]]]},
  {"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]],[[1,1],[2,1],[2,2],[3,3]]]},
  {"type":"MultiPolygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]},
  {"type":"GeometryCollection","coordinates":[]}
 ]'::jsonb) LOOP
  BEGIN
   UPDATE atlas.source_features SET geometry=candidate,coordinate_reference='OGC:CRS84' WHERE feature_id='__geometry';
   RAISE EXCEPTION 'invalid geometry accepted: %',candidate;
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
 -- Nulls must be rejected independently of JSON-format checks.
 BEGIN
  UPDATE atlas.source_features SET geometry=NULL;
  RAISE EXCEPTION 'null geometry accepted';
 EXCEPTION WHEN not_null_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.source_features SET construction_id=NULL;
  RAISE EXCEPTION 'null construction accepted';
 EXCEPTION WHEN not_null_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.source_features SET construction_id='missing';
  RAISE EXCEPTION 'missing construction accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.source_features SET coordinate_reference='unknown';
  RAISE EXCEPTION 'invalid coordinate reference accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
ROLLBACK;
