BEGIN;

ALTER TABLE atlas.geographic_entity_ids
    ADD COLUMN color_rgb text CHECK (color_rgb ~ '^#[0-9A-Fa-f]{6}$');

COMMIT;
