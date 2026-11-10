BEGIN;
DO $$
BEGIN
    INSERT INTO atlas.geographic_entity_ids (id) VALUES (101);
    INSERT INTO atlas.geographic_entity_colors VALUES (101, 0, 120, 255);

    BEGIN
        INSERT INTO atlas.geographic_entity_colors VALUES (101, 100, 120, 255);
        RAISE EXCEPTION 'a second color was accepted for one entity';
    EXCEPTION WHEN unique_violation THEN NULL; END;

    BEGIN
        INSERT INTO atlas.geographic_entity_colors VALUES (102, 0, 120, 255);
        RAISE EXCEPTION 'a color was accepted for a missing entity';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;

    BEGIN
        UPDATE atlas.geographic_entity_colors SET blue = 256 WHERE entity_id = 101;
        RAISE EXCEPTION 'an RGB channel exceeded its range';
    EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
ROLLBACK;
