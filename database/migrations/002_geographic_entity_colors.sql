BEGIN;

CREATE TABLE atlas.geographic_entity_colors (
    entity_id bigint PRIMARY KEY REFERENCES atlas.geographic_entity_ids(id),
    red smallint NOT NULL CHECK (red BETWEEN 0 AND 255),
    green smallint NOT NULL CHECK (green BETWEEN 0 AND 255),
    blue smallint NOT NULL CHECK (blue BETWEEN 0 AND 255)
);

-- Seed existing continent land colors when upgrading a populated registry.
INSERT INTO atlas.geographic_entity_colors (entity_id, red, green, blue)
SELECT id.id, color.red, color.green, color.blue
FROM (VALUES
    (1, 233, 180, 76),
    (2, 222, 118, 110),
    (3, 139, 145, 212),
    (4, 112, 184, 144),
    (5, 194, 139, 202),
    (6, 115, 186, 196)
) AS color(entity_id, red, green, blue)
JOIN atlas.geographic_entity_ids id ON id.id = color.entity_id
WHERE EXISTS (
    SELECT FROM atlas.review_category_bindings binding
    WHERE binding.entity_id = id.id AND binding.physical_class = 'land'
);

COMMIT;
