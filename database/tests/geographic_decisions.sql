-- Check that a working decision links its basin participants to real sources and entities.
BEGIN;
DO $$
BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__decision_test_registry'), ('__other_registry');
    INSERT INTO atlas.geographic_entity_ids(id) VALUES (7),(8) ON CONFLICT DO NOTHING;
    INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
      SELECT '__decision_test_registry', n, 'Synthetic entity ' || n, 'continent', NULL
      FROM generate_series(7,8) n;
    INSERT INTO atlas.geographic_entities(revision,id,name,level) VALUES ('__other_registry',7,'Other version','continent');
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
        UPDATE atlas.decision_basin_participants SET entity_revision='__other_registry'
        WHERE revision='__decision' AND basin_id='basin' AND entity_id=7;
        RAISE EXCEPTION 'basin participant used the same entity ID from an unrelated registry';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    BEGIN
        INSERT INTO atlas.decision_basin_participants VALUES ('__decision','basin','__decision_test_registry',8);
        RAISE EXCEPTION 'duplicate basin participant was stored';
    EXCEPTION WHEN unique_violation THEN NULL; END;

    INSERT INTO atlas.decision_basin_source_selections VALUES
      ('__decision','basin','raw-f','__decision_source','1',repeat('a',64),repeat('b',64),'catalog_archive','selected_for_research','{}');
    BEGIN
        UPDATE atlas.decision_basin_source_selections SET source_feature_id='other-feature' WHERE revision='__decision';
        RAISE EXCEPTION 'basin selection accepted a different source feature';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'source feature does not match decision basin' THEN RAISE; END IF;
    END;
    BEGIN
        UPDATE atlas.decision_basin_source_selections SET source_file_sha256=repeat('c',64) WHERE revision='__decision';
        RAISE EXCEPTION 'basin selection accepted a different source checksum';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'selected file hash does not match source catalog' THEN RAISE; END IF;
    END;
    UPDATE atlas.decision_revisions SET evidence='{"checked":true}' WHERE revision='__decision';
    IF NOT FOUND THEN RAISE EXCEPTION 'working decision could not be edited'; END IF;
END $$;
ROLLBACK;
