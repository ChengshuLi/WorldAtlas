-- Check valid and invalid parent levels without retaining synthetic entities.
DO $$
BEGIN
  BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision,status) VALUES ('__registry_parent_test','draft');
    INSERT INTO atlas.geographic_entity_ids(id) VALUES (1) ON CONFLICT DO NOTHING;
    INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
      VALUES ('__registry_parent_test',1,'Synthetic parent','continent',NULL);
    INSERT INTO atlas.geographic_entity_ids (id) VALUES (4294967294), (4294967295);
    INSERT INTO atlas.geographic_entities (revision,id,name,level,parent_id)
      VALUES ('__registry_parent_test',4294967294,'test subcontinent','subcontinent',1);
    SET CONSTRAINTS atlas.geographic_entity_parent_check IMMEDIATE;
    SET CONSTRAINTS atlas.geographic_entity_parent_check DEFERRED;
    BEGIN
      INSERT INTO atlas.geographic_entities (revision,id,name,level,parent_id)
        VALUES ('__registry_parent_test',4294967295,'test region','region',1);
      SET CONSTRAINTS atlas.geographic_entity_parent_check IMMEDIATE;
      RAISE EXCEPTION 'invalid parent accepted';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'invalid parent level for entity 4294967295' THEN RAISE; END IF;
    END;
    RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'rollback test data';
  EXCEPTION WHEN SQLSTATE 'ZX001' THEN NULL; END;
END; $$;
