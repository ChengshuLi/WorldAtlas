-- Each operation requires precise relational geometry and child-target inputs.
BEGIN;
INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes)
VALUES ('raw','Test','Test','test:raw','Test','test:license','Test','test','raw',repeat('a',64),1);
INSERT INTO atlas.construction_records(id,method,arguments) VALUES
 ('context','interpreted_geometry','{"source_ids":["raw"],"basis":"Selected context","selections":[{"feature_id":"point","geometry":{"type":"Point","coordinates":[1,1]}}]}');
INSERT INTO atlas.source_features VALUES
 ('point','{"type":"Point","coordinates":[1,1]}','context'),
 ('line','{"type":"LineString","coordinates":[[0,0],[2,2]]}','context'),
 ('area','{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,0]]]}','context');
INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world');
INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class)
VALUES (0,'World','world',NULL,'mixed'),(2,'Asia','continent',0,'mixed'),(3,'Europe','continent',0,'mixed');
INSERT INTO atlas.geographic_rules VALUES
 ('divide',0,'divide_area','land','cell',false,'Selected physical boundary'),
 ('group',0,'assign_area','land','component',false,'Whole island group'),
 ('remaining',0,'nearest_land','land','component',true,'Nearest mainland shores'),
 ('basin',0,'nearest_basin_water','water','cell',false,'Nearest bordering shores'),
 ('coastal',0,'nearest_coastal_water','water','cell',false,'Shared coastal distance'),
 ('water',0,'nearest_water','water','cell',true,'Complete remaining water');
INSERT INTO atlas.geographic_rule_features VALUES
 ('divide','line','boundary_line'),('divide','point','scope_component'),
 ('group','area','scope_area'),('remaining','point','distance_reference'),('basin','area','scope_area');
INSERT INTO atlas.geographic_rule_features VALUES
 ('group','point','connected_to'),('water','point','connected_to');
INSERT INTO atlas.geographic_rule_targets VALUES ('divide-asia','divide',2,'point'),('group-asia','group',2,NULL);
INSERT INTO atlas.geographic_rule_sources VALUES ('group','raw','Section 1','Geographic affiliation');
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
-- A mixed query filter may feed a water-only owner. Actual emitted cells are
-- checked against that owner's physical class during claim consolidation.
INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class)
VALUES (7,'Water child','continent',0,'water');
INSERT INTO atlas.geographic_rules VALUES
 ('mixed-filter',0,'assign_area','mixed','cell',false,'Query both physical classes');
INSERT INTO atlas.geographic_rule_targets VALUES ('water-target','mixed-filter',7,NULL);
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
DO $$ DECLARE feature text;
BEGIN
 FOREACH feature IN ARRAY ARRAY['line','area'] LOOP
  BEGIN
   INSERT INTO atlas.geographic_rule_features VALUES ('water',feature,'connected_to');
   SET CONSTRAINTS ALL IMMEDIATE;
   RAISE EXCEPTION 'a non-point feature was accepted as a connectivity reference';
  EXCEPTION WHEN raise_exception THEN
   IF SQLERRM NOT LIKE 'invalid feature geometry%' THEN RAISE; END IF;
  END;
 END LOOP;
 BEGIN
  INSERT INTO atlas.geographic_rule_targets VALUES ('divide-europe','divide',3,'point');
  SET CONSTRAINTS atlas.geographic_rule_targets_unique_label IMMEDIATE;
  RAISE EXCEPTION 'a divided-face label point was assigned twice';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  DELETE FROM atlas.geographic_rule_features WHERE rule_id='divide' AND role='boundary_line';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'a division without boundaries was accepted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid feature role counts%' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.source_features SET geometry='{"type":"Point","coordinates":[1,1]}' WHERE id='area';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'a scope-area feature changed into a point';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid feature geometry%' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.geographic_rule_targets SET label_point_id='line' WHERE rule_id='divide';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'a line was accepted as a face label';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid child target or label point%' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.geographic_rule_targets SET entity_id=0 WHERE rule_id='group';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'a parent was accepted as its own target';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid child target or label point%' THEN RAISE; END IF;
 END;
 BEGIN
  INSERT INTO atlas.geographic_rule_features VALUES ('coastal','point','distance_reference');
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'coastal reference override was accepted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid feature role counts%' THEN RAISE; END IF;
 END;
 UPDATE atlas.geographic_rules SET rationale='Clearer explanation' WHERE id='group';
 IF (SELECT citation_section FROM atlas.geographic_rule_sources WHERE rule_id='group')<>'Section 1' THEN
  RAISE EXCEPTION 'a rationale edit changed its citation'; END IF;
 DELETE FROM atlas.geographic_rules WHERE id='group';
 IF EXISTS (SELECT FROM atlas.geographic_rule_features WHERE rule_id='group')
    OR EXISTS (SELECT FROM atlas.geographic_rule_sources WHERE rule_id='group') THEN
  RAISE EXCEPTION 'deleted rule left orphaned links'; END IF;
 SET CONSTRAINTS ALL IMMEDIATE;
END $$;
ROLLBACK;
