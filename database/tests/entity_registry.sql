-- Reuse stable IDs across registry versions while keeping hierarchies and bindings separate.
BEGIN;
DO $$
BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__registry_first'), ('__registry_second');
    INSERT INTO atlas.geographic_entity_ids(id) VALUES (4294967293),(4294967294),(4294967295);

    -- A change set can list children before their parent inside one transaction.
    INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id) VALUES
      ('__registry_first',4294967294,'Subcontinent','subcontinent',4294967293),
      ('__registry_first',4294967293,'Continent','continent',NULL),
      ('__registry_second',4294967293,'Continent renamed','continent',NULL);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    INSERT INTO atlas.review_category_bindings VALUES
      ('__registry_first',17,4294967294,'land'), ('__registry_second',17,4294967293,'land');
    BEGIN
        UPDATE atlas.review_category_bindings SET entity_id=4294967294
        WHERE revision='__registry_second' AND code=17;
        RAISE EXCEPTION 'category linked to an entity present only in another revision';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    BEGIN
        INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
        VALUES ('__registry_first',4294967295,'Region','region',4294967293);
        SET CONSTRAINTS atlas.geographic_entity_parent_check IMMEDIATE;
        RAISE EXCEPTION 'region skipped its parent level';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'invalid parent level for entity 4294967295' THEN RAISE; END IF;
    END;
    BEGIN
        DELETE FROM atlas.geographic_entities WHERE revision='__registry_first' AND id=4294967293;
        SET CONSTRAINTS ALL IMMEDIATE;
        RAISE EXCEPTION 'continent with a child was deleted';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;

    UPDATE atlas.geographic_entities SET name='Subcontinent renamed'
    WHERE revision='__registry_first' AND id=4294967294;
    IF NOT EXISTS (
        SELECT FROM atlas.review_category_bindings b JOIN atlas.geographic_entities e
        ON (e.revision,e.id)=(b.revision,b.entity_id)
        WHERE b.revision='__registry_first' AND b.code=17 AND e.name='Subcontinent renamed'
    ) THEN RAISE EXCEPTION 'renaming an entity lost its map code'; END IF;
END $$;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
