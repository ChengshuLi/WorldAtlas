-- Stable IDs, valid hierarchy links and unique grid-code meanings.
BEGIN;
DO $$
DECLARE first_id bigint; second_id bigint;
BEGIN
 INSERT INTO atlas.geographic_entities(name,level) VALUES ('Generated first','continent') RETURNING id INTO first_id;
 INSERT INTO atlas.geographic_entities(name,level) VALUES ('Generated second','continent') RETURNING id INTO second_id;
 IF first_id IS NULL OR second_id<=first_id THEN RAISE EXCEPTION 'generated entity IDs did not advance'; END IF;
 INSERT INTO atlas.geographic_entities(id,name,level,parent_id) VALUES
 (4294967294,'Subcontinent','subcontinent',4294967293),(4294967293,'Continent','continent',NULL);
 SET CONSTRAINTS ALL IMMEDIATE;
 SET CONSTRAINTS ALL DEFERRED;
 INSERT INTO atlas.map_category_bindings VALUES (17,4294967294,'land'),(4294967295,4294967294,'water');
 BEGIN
  INSERT INTO atlas.map_category_bindings VALUES (4294967296,4294967293,'water');
  RAISE EXCEPTION 'category exceeded uint32';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.map_category_bindings VALUES (123,4294967294,'land');
  RAISE EXCEPTION 'an entity/class had two map codes';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.map_category_bindings VALUES (123,4294967295,'land');
  RAISE EXCEPTION 'missing entity accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.geographic_entities(id,name,level,parent_id) VALUES (4294967295,'Region','region',4294967293);
  SET CONSTRAINTS atlas.geographic_entity_parent_check IMMEDIATE;
  RAISE EXCEPTION 'region skipped its parent level';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'invalid parent level for entity 4294967295' THEN RAISE; END IF;
 END;
 BEGIN
  DELETE FROM atlas.geographic_entities WHERE id=4294967293;
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'continent with a child was deleted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 UPDATE atlas.geographic_entities SET name='Subcontinent renamed' WHERE id=4294967294;
 IF NOT EXISTS (SELECT FROM atlas.map_category_bindings b JOIN atlas.geographic_entities e ON e.id=b.entity_id
 WHERE b.code=17 AND e.name='Subcontinent renamed') THEN RAISE EXCEPTION 'rename lost its map code'; END IF;
 -- Deferred validation must check the final row, not an earlier edit's values.
 INSERT INTO atlas.geographic_entities(id,name,level,parent_id)
 VALUES (4294967295,'Region','region',4294967294);
 SET CONSTRAINTS ALL IMMEDIATE;
 SET CONSTRAINTS ALL DEFERRED;
 UPDATE atlas.geographic_entities SET level='continent',parent_id=NULL WHERE id=4294967294;
 UPDATE atlas.geographic_entities SET level='subcontinent',parent_id=4294967293 WHERE id=4294967294;
 SET CONSTRAINTS ALL IMMEDIATE;
 SET CONSTRAINTS ALL DEFERRED;
 -- A temporary row removed before commit must not leave a failing deferred event.
 INSERT INTO atlas.geographic_entities(id,name,level,parent_id)
 VALUES (4294967292,'Temporary region','region',4294967293);
 DELETE FROM atlas.geographic_entities WHERE id=4294967292;
 SET CONSTRAINTS ALL IMMEDIATE;
 SET CONSTRAINTS ALL DEFERRED;
END $$;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
