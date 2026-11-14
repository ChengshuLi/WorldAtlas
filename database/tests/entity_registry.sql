-- Stable IDs, valid hierarchy links and unique grid-code meanings.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.geographic_entity_ids(id) VALUES (4294967293),(4294967294),(4294967295);
 INSERT INTO atlas.geographic_entities(id,name,level,parent_id) VALUES
 (4294967294,'Subcontinent','subcontinent',4294967293),(4294967293,'Continent','continent',NULL);
 SET CONSTRAINTS ALL IMMEDIATE;
 SET CONSTRAINTS ALL DEFERRED;
 INSERT INTO atlas.review_category_bindings VALUES (17,4294967294,'land'),(4294967295,4294967294,'water');
 BEGIN
  INSERT INTO atlas.review_category_bindings VALUES (4294967296,4294967293,'water');
  RAISE EXCEPTION 'category exceeded uint32';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.review_category_bindings VALUES (123,4294967294,'land');
  RAISE EXCEPTION 'an entity/class had two map codes';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.review_category_bindings VALUES (123,4294967295,'land');
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
 IF NOT EXISTS (SELECT FROM atlas.review_category_bindings b JOIN atlas.geographic_entities e ON e.id=b.entity_id
 WHERE b.code=17 AND e.name='Subcontinent renamed') THEN RAISE EXCEPTION 'rename lost its map code'; END IF;
END $$;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
