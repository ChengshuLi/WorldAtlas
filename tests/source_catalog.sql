-- Run against a disposable/test branch after migrations 002 and 004. The outer
-- exception rolls back all synthetic rows; no example source is registered.
DO $$
BEGIN
  BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision,status) VALUES ('__source_catalog_test_registry','draft');
    INSERT INTO atlas.geographic_entity_ids(id) VALUES (1) ON CONFLICT DO NOTHING;
    INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
      VALUES ('__source_catalog_test_registry',1,'Synthetic parent','continent',NULL);
    INSERT INTO atlas.source_assets
      (source_id, version, title, kind, provider, source_uri, license_name,
       license_uri, attribution, r2_bucket, r2_key, sha256, size_bytes, provenance)
    VALUES
      ('__test_a', '1', 'test', 'raw', 'test', 'test:uri', 'test', 'test:license',
       'test', '__test', 'a', repeat('a', 64), 1, '{}'),
      ('__test_b', '1', 'test', 'raw', 'test', 'test:uri', 'test', 'test:license',
       'test', '__test', 'b', repeat('b', 64), 1, '{}'),
      ('__test_c', '1', 'test', 'raw', 'test', 'test:uri', 'test', 'test:license',
       'test', '__test', 'c', repeat('c', 64), 1, '{}');
    BEGIN
      INSERT INTO atlas.source_assets SELECT '__test_bad', version, title, kind, provider,
        source_uri, license_name, license_uri, attribution, r2_bucket, 'bad',
        'bad-hash', size_bytes, provenance, created_at FROM atlas.source_assets
        WHERE source_id = '__test_a';
      RAISE EXCEPTION 'invalid hash accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
      UPDATE atlas.source_assets SET r2_key = 'changed' WHERE source_id = '__test_a';
      RAISE EXCEPTION 'source change accepted';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'source records are immutable; use a new source version' THEN RAISE; END IF;
    END;
    BEGIN
      INSERT INTO atlas.source_assets SELECT '__test_collision', version, title, kind, provider,
        source_uri, license_name, license_uri, attribution, r2_bucket, r2_key,
        sha256, size_bytes, provenance, created_at FROM atlas.source_assets
        WHERE source_id = '__test_a';
      RAISE EXCEPTION 'duplicate R2 object accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;
    BEGIN
      INSERT INTO atlas.source_builds (build_id, entity_revision, code_revision, status)
        VALUES ('__test_locked', '__source_catalog_test_registry', 'test', 'locked');
      RAISE EXCEPTION 'direct lock accepted';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'create a build as draft first' THEN RAISE; END IF;
    END;
    INSERT INTO atlas.source_builds (build_id, entity_revision, code_revision)
      VALUES ('__test_build', '__source_catalog_test_registry', 'test');
    BEGIN
      INSERT INTO atlas.source_asset_dependencies VALUES ('__test_b','1','__test_c','1','derived_from');
    BEGIN
      INSERT INTO atlas.source_asset_dependencies VALUES ('__test_c','1','__test_b','1','derived_from');
      RAISE EXCEPTION 'dependency cycle accepted';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'source dependency cycle' THEN RAISE; END IF;
    END;
    UPDATE atlas.source_builds SET status = 'locked' WHERE build_id = '__test_build';
    BEGIN
      INSERT INTO atlas.source_asset_dependencies VALUES ('__test_b','1','__test_a','1','derived_from');
      RAISE EXCEPTION 'locked lineage changed';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'locked build lineage is immutable' THEN RAISE; END IF;
    END;

      RAISE EXCEPTION 'empty build locked';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'a locked build requires at least one input' THEN RAISE; END IF;
    END;
    BEGIN
      INSERT INTO atlas.source_build_inputs VALUES ('__test_build','__missing','1','raw','mask');
      RAISE EXCEPTION 'missing input accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    INSERT INTO atlas.source_build_inputs VALUES ('__test_build','__test_b','1','raw','mask');
    INSERT INTO atlas.source_entity_links VALUES ('__test_a','1','__source_catalog_test_registry',1,'supports');
    INSERT INTO atlas.source_asset_dependencies VALUES ('__test_b','1','__test_c','1','derived_from');
    BEGIN
      INSERT INTO atlas.source_asset_dependencies VALUES ('__test_c','1','__test_b','1','derived_from');
      RAISE EXCEPTION 'dependency cycle accepted';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'source dependency cycle' THEN RAISE; END IF;
    END;
    UPDATE atlas.source_builds SET status = 'locked' WHERE build_id = '__test_build';
    BEGIN
      INSERT INTO atlas.source_asset_dependencies VALUES ('__test_b','1','__test_a','1','derived_from');
      RAISE EXCEPTION 'locked lineage changed';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'locked build lineage is immutable' THEN RAISE; END IF;
    END;

    BEGIN
      UPDATE atlas.source_build_inputs SET role = 'changed' WHERE build_id = '__test_build';
      RAISE EXCEPTION 'locked inputs changed';
    EXCEPTION WHEN raise_exception THEN
      IF SQLERRM <> 'locked build inputs are immutable' THEN RAISE; END IF;
    END;
    RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'rollback test data';
  EXCEPTION WHEN SQLSTATE 'ZX001' THEN NULL; END;
END; $$;
