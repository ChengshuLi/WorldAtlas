-- Geographic records link to existing sources, entities and explanations.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.geographic_entities(id,name,level) VALUES (7,'Entity','continent');
 INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__source','Test','Provider','test:source','Terms','test:terms','Credit','test','source',repeat('a',64),1);
 INSERT INTO atlas.construction_records VALUES ('__feature_recipe',
 '{"method":"selected_vector_features","source_id":"__source","basis":"Selected point","id_field":"id","selections":[{"feature_id":"__feature","source_feature_id":"provider"}]}');
 BEGIN
  INSERT INTO atlas.source_features(feature_id,source_id,source_feature_id,geometry,construction_id)
  VALUES ('__missing','absent','provider','{"type":"Point","coordinates":[0,0]}','__feature_recipe');
  RAISE EXCEPTION 'missing feature source accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 INSERT INTO atlas.source_features(feature_id,source_id,source_feature_id,geometry,construction_id)
 VALUES ('__feature','__source','provider','{"type":"Point","coordinates":[0,0]}','__feature_recipe');
 INSERT INTO atlas.decision_basins VALUES ('__basin','__feature','nearest_participating_shore','{}','{}');
 INSERT INTO atlas.geographic_assignments VALUES ('__assignment',7,'Geographic reasoning',
 '{"feature_id":"__feature","relation":"point_component"}');
 INSERT INTO atlas.geographic_assignment_sources VALUES ('__assignment','__source','Section 1','Interpretation and its limitations');
 BEGIN
  UPDATE atlas.geographic_assignments SET entity_id=8;
  RAISE EXCEPTION 'missing entity accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  DELETE FROM atlas.geographic_assignments;
  RAISE EXCEPTION 'referenced assignment deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 UPDATE atlas.geographic_assignments SET rationale='Revised explanation';
 IF (SELECT citation_section FROM atlas.geographic_assignment_sources)<>'Section 1' THEN RAISE EXCEPTION 'editing a rule changed its citation'; END IF;
END $$;
DO $$ DECLARE invalid jsonb; BEGIN
 FOREACH invalid IN ARRAY ARRAY[
  'null'::jsonb, '[]'::jsonb, '{}'::jsonb,
  '{"feature_id":"__feature"}'::jsonb,
  '{"feature_id":"__feature","relation":null}'::jsonb,
  '{"feature_id":42,"relation":"point_component"}'::jsonb,
  '{"feature_id":" ","relation":"point_component"}'::jsonb,
  '{"feature_id":"__feature","relation":"unknown"}'::jsonb,
  '{"feature_id":"__feature","relation":"point_component","combine":"all"}'::jsonb,
  '{"combine":"all","conditions":[{"feature_id":"__feature","relation":"point_component"}]}'::jsonb
 ] LOOP
  BEGIN
   UPDATE atlas.geographic_assignments SET selection=invalid;
   RAISE EXCEPTION 'malformed selection accepted: %', invalid;
  EXCEPTION WHEN check_violation THEN NULL; END;
 END LOOP;
 FOREACH invalid IN ARRAY ARRAY[
  '{"feature_id":"__feature","relation":"point_component"}'::jsonb,
  '{"feature_id":"__feature","relation":"contains_component"}'::jsonb,
  '{"feature_id":"__feature","relation":"intersects_component"}'::jsonb,
  '{"feature_id":"__feature","relation":"majority_component"}'::jsonb
 ] LOOP
  UPDATE atlas.geographic_assignments SET selection=invalid;
 END LOOP;
END $$;
ROLLBACK;
