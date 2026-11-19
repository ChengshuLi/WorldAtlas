-- Hierarchy, physical eligibility, colors and stable encoding are independent.
BEGIN;
INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world');
DO $$ BEGIN
 BEGIN
  INSERT INTO atlas.geographic_entities(id,name,level_id,physical_class)
  VALUES (1,'World','world','mixed');
  RAISE EXCEPTION 'a nonzero root ID was accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class)
VALUES (0,'World','world',NULL,'mixed'),(2,'Asia','continent',0,'mixed'),
       (7,'Atlantic','continent',0,'water'),(8,'Dry region','continent',0,'land');
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
DO $$
DECLARE land_code bigint;
        dry_land_code bigint;
BEGIN
 IF (SELECT array_agg(entity_id || ':' || physical_class ORDER BY entity_id,physical_class)
     FROM atlas.map_category_bindings) IS DISTINCT FROM ARRAY['2:land','2:water','7:water','8:land'] THEN
  RAISE EXCEPTION 'new entities received incorrect map bindings'; END IF;
 SELECT id INTO land_code FROM atlas.map_category_bindings WHERE entity_id=2 AND physical_class='land';
 SELECT id INTO dry_land_code FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='land';
 UPDATE atlas.geographic_entities SET physical_class='mixed' WHERE id=8;
 IF (SELECT id FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='land') IS DISTINCT FROM dry_land_code
   OR NOT EXISTS (SELECT FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='water') THEN
  RAISE EXCEPTION 'class expansion failed to preserve land and add water'; END IF;
 UPDATE atlas.geographic_entities SET physical_class='land' WHERE id=8;
 IF (SELECT id FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='land') IS DISTINCT FROM dry_land_code
   OR EXISTS (SELECT FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='water') THEN
  RAISE EXCEPTION 'class reduction failed to preserve land and remove water'; END IF;
 IF (SELECT color_rgb FROM atlas.geographic_entities WHERE id=2) IS NOT NULL THEN
  RAISE EXCEPTION 'new entities must not receive an invented color'; END IF;
 UPDATE atlas.geographic_entities SET color_rgb='#0078FF',name='Asia renamed' WHERE id=2;
 IF (SELECT id FROM atlas.map_category_bindings WHERE entity_id=2 AND physical_class='land') IS DISTINCT FROM land_code THEN
  RAISE EXCEPTION 'renaming an entity changed its encoding'; END IF;
 BEGIN
  UPDATE atlas.geographic_entities SET color_rgb='#0078GG' WHERE id=2;
  RAISE EXCEPTION 'invalid RGB accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.map_category_bindings VALUES (42,2,'land');
  RAISE EXCEPTION 'duplicate entity/class encoding accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.map_category_bindings VALUES (42,7,'land');
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'a water-only entity received a land encoding';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'map bindings do not match entity 7' THEN RAISE; END IF;
 END;
 BEGIN
  DELETE FROM atlas.map_category_bindings WHERE entity_id=2 AND physical_class='water';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'an entity lost its required water code';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'map bindings do not match entity 2' THEN RAISE; END IF;
 END;
 BEGIN
  DELETE FROM atlas.map_category_bindings WHERE entity_id=8 AND physical_class='land';
  UPDATE atlas.map_category_bindings SET entity_id=8 WHERE entity_id=2 AND physical_class='land';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'an entity lost its required land code when it was moved';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> 'map bindings do not match entity 2' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.geographic_entities SET level_id='world' WHERE id=2;
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'invalid parent level accepted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'invalid parent for entity%' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.geographic_levels SET parent_id='continent' WHERE id='continent';
  SET CONSTRAINTS atlas.geographic_level_check IMMEDIATE;
  RAISE EXCEPTION 'level accepted itself as its parent';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'geographic levels contain a cycle' THEN RAISE; END IF;
 END;
 BEGIN
  UPDATE atlas.geographic_levels SET parent_id='continent' WHERE id='world';
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE EXCEPTION 'hierarchy cycle accepted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'geographic levels contain a cycle' THEN RAISE; END IF;
 END;
 -- Deferred events inspect final rows, including an edit that was undone.
 UPDATE atlas.geographic_entities SET level_id='world' WHERE id=2;
 UPDATE atlas.geographic_entities SET level_id='continent' WHERE id=2;
 DELETE FROM atlas.geographic_entities WHERE id=8;
 SET CONSTRAINTS ALL IMMEDIATE;
 IF EXISTS (SELECT FROM atlas.map_category_bindings WHERE entity_id=8)
    OR NOT EXISTS (SELECT FROM atlas.map_category_bindings WHERE id=land_code AND entity_id=2)
 THEN RAISE EXCEPTION 'deleting an entity must remove only its own map bindings'; END IF;
END $$;
ROLLBACK;
