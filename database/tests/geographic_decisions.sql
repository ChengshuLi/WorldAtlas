-- Geographic records link to existing sources, entities and explanations.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.geographic_entities(id,name,level) VALUES (7,'Entity','continent');
 INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__source','Test','Provider','test:source','Terms','test:terms','Credit','test','source',repeat('a',64),1);
 BEGIN
  INSERT INTO atlas.decision_features(feature_id,source_id,source_feature_id,geometry_sha256,evidence)
  VALUES ('__missing','absent','provider',repeat('b',64),'{}');
  RAISE EXCEPTION 'missing feature source accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 INSERT INTO atlas.decision_features(feature_id,source_id,source_feature_id,geometry_sha256,evidence)
 VALUES ('__feature','__source','provider',repeat('b',64),'{}');
 INSERT INTO atlas.decision_basins VALUES ('__basin','__feature','nearest_participating_shore','{}','{}');
 INSERT INTO atlas.decision_cases VALUES ('__case','Title','Shared geographic reasoning');
 INSERT INTO atlas.decision_case_sources VALUES ('__case','__source','Section 1','Interpretation',ARRAY[]::text[]);
 INSERT INTO atlas.decision_affiliations VALUES ('__affiliation',7,'Rule-specific explanation','{}','__case',
 '{"combine":"all","conditions":[{"feature_id":"__feature","relation":"point_component"}]}');
 BEGIN
  UPDATE atlas.decision_affiliations SET entity_id=8;
  RAISE EXCEPTION 'missing entity accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  DELETE FROM atlas.decision_cases;
  RAISE EXCEPTION 'referenced explanation deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.decision_affiliations SET component_selection='[]';
  RAISE EXCEPTION 'non-object selection accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE atlas.decision_affiliations SET rationale='Revised explanation';
 IF (SELECT citation_section FROM atlas.decision_case_sources)<>'Section 1' THEN RAISE EXCEPTION 'editing a rule changed its citation'; END IF;
END $$;
ROLLBACK;
