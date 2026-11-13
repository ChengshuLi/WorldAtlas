-- Source-backed features, shared reasoning, citations and entity targets stay linked.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__decisions'),('__other');
 INSERT INTO atlas.geographic_entity_ids(id) VALUES(7) ON CONFLICT DO NOTHING;
 INSERT INTO atlas.geographic_entities(revision,id,name,level) VALUES ('__decisions',7,'Entity','continent'),('__other',7,'Other revision','continent');
 INSERT INTO atlas.source_assets(source_id,version,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
 VALUES ('__decision_source','1','Test','Provider','test:source','Terms','test:terms','Credit','test','source',repeat('a',64),1);
 INSERT INTO atlas.decision_revisions VALUES ('__decisions','__decisions','{}');
 BEGIN
  INSERT INTO atlas.decision_features(revision,feature_id,source_id,source_version,source_feature_id,geometry_sha256,evidence)
  VALUES ('__decisions','missing','absent','1','provider',repeat('b',64),'{}');
  RAISE EXCEPTION 'missing feature source accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 INSERT INTO atlas.decision_features(revision,feature_id,source_id,source_version,source_feature_id,geometry_sha256,evidence)
 VALUES ('__decisions','feature','__decision_source','1','provider',repeat('b',64),'{}');
 INSERT INTO atlas.decision_basins VALUES ('__decisions','basin','feature','nearest_participating_shore','{}','{}');
 INSERT INTO atlas.decision_cases(revision,case_id,title,reason) VALUES ('__decisions','case','Title','Shared geographic reasoning');
 INSERT INTO atlas.decision_case_sources(revision,case_id,source_id,source_version,citation_section,interpretation,limitations)
 VALUES ('__decisions','case','__decision_source','1','Section 1','Why it supports the decision',ARRAY[]::text[]);
 INSERT INTO atlas.decision_affiliations(revision,affiliation_id,entity_revision,entity_id,rationale,evidence,case_id,component_selection)
 VALUES ('__decisions','affiliation','__decisions',7,'Rule-specific explanation','{}','case',
 '{"combine":"all","conditions":[{"feature_id":"feature","relation":"point_component"}]}');
 BEGIN
  UPDATE atlas.decision_affiliations SET entity_revision='__other' WHERE revision='__decisions';
  RAISE EXCEPTION 'target changed to an unrelated registry';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  DELETE FROM atlas.decision_cases WHERE revision='__decisions';
  RAISE EXCEPTION 'referenced explanation deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.decision_affiliations SET component_selection='[]' WHERE revision='__decisions';
  RAISE EXCEPTION 'non-object selection accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE atlas.decision_affiliations SET rationale='Revised explanation' WHERE revision='__decisions';
 IF (SELECT citation_section FROM atlas.decision_case_sources WHERE revision='__decisions')<>'Section 1' THEN
  RAISE EXCEPTION 'editing a rule changed its citation'; END IF;
END $$;
ROLLBACK;
