-- Deterministic identities for the existing V7 review only. Draft is not approval.
BEGIN;
INSERT INTO atlas.entity_registry_revisions (revision,status) VALUES ('v7-category-bootstrap-v1','draft');
INSERT INTO atlas.geographic_entity_ids (id) SELECT n FROM generate_series(1,10) n;
SELECT setval(pg_get_serial_sequence('atlas.geographic_entity_ids','id'), 10, true);
INSERT INTO atlas.geographic_entities (revision,id,name,level,parent_id) VALUES
 ('v7-category-bootstrap-v1',1,'Africa','continent',NULL),
 ('v7-category-bootstrap-v1',2,'Asia','continent',NULL),
 ('v7-category-bootstrap-v1',3,'Europe','continent',NULL),
 ('v7-category-bootstrap-v1',4,'North America','continent',NULL),
 ('v7-category-bootstrap-v1',5,'South America','continent',NULL),
 ('v7-category-bootstrap-v1',6,'Oceania','continent',NULL),
 ('v7-category-bootstrap-v1',7,'Atlantic Ocean','continent',NULL),
 ('v7-category-bootstrap-v1',8,'Pacific Ocean','continent',NULL),
 ('v7-category-bootstrap-v1',9,'Indian Ocean','continent',NULL),
 ('v7-category-bootstrap-v1',10,'Arctic Ocean','continent',NULL);
INSERT INTO atlas.review_category_bindings (revision,code,entity_id,physical_class)
SELECT 'v7-category-bootstrap-v1', n, n, 'water' FROM generate_series(1,10) n
UNION ALL SELECT 'v7-category-bootstrap-v1', n+16, n, 'land' FROM generate_series(1,6) n;
COMMIT;
