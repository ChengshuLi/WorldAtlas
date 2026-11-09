-- Check that a working decision links its basin participants to real sources and entities.
BEGIN;
DO $$
BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__decision_test_registry');
    INSERT INTO atlas.geographic_entity_ids(id) VALUES (7),(8) ON CONFLICT DO NOTHING;
    INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
      SELECT '__decision_test_registry', n, 'Synthetic entity ' || n, 'continent', NULL
      FROM generate_series(7,8) n;
    INSERT INTO atlas.source_assets(source_id,version,title,kind,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,provenance)
      VALUES ('__decision_source','1','test','raw','test','test','test','test','test','test','decision',repeat('a',64),1,'{}');
    INSERT INTO atlas.decision_revisions(revision,entity_revision,evidence)
      VALUES ('__decision','__decision_test_registry','{}');
    BEGIN
        INSERT INTO atlas.decision_features VALUES ('__decision','feature','missing','1','raw-f',repeat('b',64),'{}');
        RAISE EXCEPTION 'decision feature without its source was stored';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    INSERT INTO atlas.decision_features VALUES ('__decision','feature','__decision_source','1','raw-f',repeat('b',64),'{}');
    INSERT INTO atlas.decision_basins VALUES ('__decision','basin','feature','shared_nearest_assigned_shore','{}','{}');
    INSERT INTO atlas.decision_basin_participants VALUES ('__decision','basin','__decision_test_registry',7);
    BEGIN
        INSERT INTO atlas.decision_basin_participants VALUES ('__decision','basin','__decision_test_registry',9);
        RAISE EXCEPTION 'basin participant without an entity was stored';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    INSERT INTO atlas.decision_basin_participants VALUES ('__decision','basin','__decision_test_registry',8);
    BEGIN
        INSERT INTO atlas.decision_basin_participants VALUES ('__decision','basin','__decision_test_registry',8);
        RAISE EXCEPTION 'duplicate basin participant was stored';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    UPDATE atlas.decision_revisions SET evidence='{"checked":true}' WHERE revision='__decision';
    IF NOT FOUND THEN RAISE EXCEPTION 'working decision could not be edited'; END IF;
END $$;
ROLLBACK;
