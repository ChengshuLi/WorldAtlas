-- Representative rows from the pre-release-candidate schema.
INSERT INTO atlas.entity_registry_revisions (revision,status) VALUES ('entities','draft');
INSERT INTO atlas.geographic_entity_ids (id) VALUES (1);
INSERT INTO atlas.geographic_entities (revision,id,name,level) VALUES ('entities',1,'Africa','continent');
INSERT INTO atlas.decision_revisions (revision,entity_revision,evidence)
VALUES ('working','entities','{"note":"keep"}');

INSERT INTO atlas.map_release_objects
    (map_version,stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256)
VALUES ('v8.0','rows','worldatlas','review/v8.0/rows.u32le.gz',123,repeat('a',64),repeat('b',64)),
       ('v8.0','runs','worldatlas','review/v8.0/runs.u32le.gz',456,repeat('c',64),repeat('d',64));

CREATE TABLE expected_v8 AS TABLE atlas.map_release_objects;
