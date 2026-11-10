BEGIN;
DO $$
DECLARE
    color text;
BEGIN
    INSERT INTO atlas.geographic_entity_ids (id) VALUES (101) RETURNING color_rgb INTO color;
    IF color IS NOT NULL THEN
        RAISE EXCEPTION 'a new entity received a color by default';
    END IF;

    UPDATE atlas.geographic_entity_ids SET color_rgb = '#0078FF' WHERE id = 101
        RETURNING color_rgb INTO color;
    IF color IS DISTINCT FROM '#0078FF' THEN
        RAISE EXCEPTION 'the entity color was not saved';
    END IF;

    BEGIN
        UPDATE atlas.geographic_entity_ids SET color_rgb = '#0078GG' WHERE id = 101;
        RAISE EXCEPTION 'a nonhexadecimal RGB color was accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;

    BEGIN
        UPDATE atlas.geographic_entity_ids SET color_rgb = '#0078FF00' WHERE id = 101;
        RAISE EXCEPTION 'an RGB color with too many digits was accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
ROLLBACK;
