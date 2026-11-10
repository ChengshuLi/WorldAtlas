DO $$
BEGIN
    IF EXISTS (
        (SELECT * FROM expected_v8 EXCEPT SELECT map_version,stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256 FROM atlas.map_release_objects WHERE candidate_id IS NULL)
        UNION ALL
        (SELECT map_version,stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256 FROM atlas.map_release_objects WHERE candidate_id IS NULL EXCEPT SELECT * FROM expected_v8)
    ) THEN RAISE EXCEPTION 'upgrading changed the published V8 records'; END IF;
    IF EXISTS (
        SELECT FROM information_schema.columns WHERE table_schema='atlas'
        AND table_name IN ('decision_revisions','entity_registry_revisions')
        AND column_name IN ('status','reviewed_by','reviewed_at')
    ) THEN RAISE EXCEPTION 'obsolete review columns remain'; END IF;
    IF NOT EXISTS (
        SELECT FROM atlas.decision_revisions d JOIN atlas.geographic_entities e ON e.revision=d.entity_revision
        WHERE d.revision='working' AND d.evidence='{"note":"keep"}' AND e.id=1 AND e.name='Africa'
    ) THEN RAISE EXCEPTION 'upgrading lost working geography'; END IF;
    UPDATE atlas.geographic_entities SET name='Africa updated' WHERE revision='entities' AND id=1;
    UPDATE atlas.decision_revisions SET evidence='{"note":"updated"}' WHERE revision='working';
END $$;
