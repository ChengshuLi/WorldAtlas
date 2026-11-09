-- Verify that only the approved bundle can be registered as a new release.
BEGIN;
DO $$
DECLARE
    bundle jsonb := jsonb_build_object(
        'inputs', '{"snapshot":"exact input pins"}'::jsonb,
        'objects', jsonb_build_object(
            'index.html', jsonb_build_object('sha256', repeat('a',64), 'size_bytes', 1),
            'rows.u32le.gz', jsonb_build_object('sha256', repeat('b',64), 'size_bytes', 2),
            'runs.u32le.gz', jsonb_build_object('sha256', repeat('c',64), 'size_bytes', 3)),
        'decoded_sha256', jsonb_build_object('rows', repeat('d',64), 'runs', repeat('e',64)));
BEGIN
    BEGIN
        INSERT INTO atlas.map_release_candidates(candidate_id,r2_bucket,manifest)
        VALUES ('v99.0-rc.1','test','{}');
        RAISE EXCEPTION 'incomplete candidate manifest accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    INSERT INTO atlas.map_release_candidates(candidate_id,r2_bucket,manifest)
    VALUES ('v99.0-rc.1','test',bundle), ('v99.0-rc.2','test',bundle);
    BEGIN
        UPDATE atlas.map_release_candidates SET manifest=bundle||'{"changed":true}'
        WHERE candidate_id='v99.0-rc.1';
        RAISE EXCEPTION 'candidate contents changed';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'only an unapproved candidate can receive approval' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('d',64),'v99.0-rc.1');
        RAISE EXCEPTION 'unapproved candidate published';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'release object must match an approved candidate' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','unlinked',2,repeat('b',64),repeat('d',64),NULL);
        RAISE EXCEPTION 'new release without a candidate accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;

    UPDATE atlas.map_release_candidates SET approved_by='reviewer', approved_at=now()
    WHERE candidate_id IN ('v99.0-rc.1','v99.0-rc.2');
    BEGIN
        UPDATE atlas.map_release_candidates SET approved_by='other' WHERE candidate_id='v99.0-rc.1';
        RAISE EXCEPTION 'approval changed';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'only an unapproved candidate can receive approval' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('f',64),'v99.0-rc.1');
        RAISE EXCEPTION 'different decoded bytes accepted';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'release object must match an approved candidate' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('d',64),'v99.0-rc.1');
        SET CONSTRAINTS atlas.map_release_pair IMMEDIATE;
        RAISE EXCEPTION 'incomplete release accepted';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'publish both streams from one approved candidate together' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('d',64),'v99.0-rc.1'),
          ('v99.0','runs','test','review/releases/v99.0-rc.2/runs.u32le.gz',3,repeat('c',64),repeat('e',64),'v99.0-rc.2');
        SET CONSTRAINTS atlas.map_release_pair IMMEDIATE;
        RAISE EXCEPTION 'mixed release accepted';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'publish both streams from one approved candidate together' THEN RAISE; END IF;
    END;

    INSERT INTO atlas.map_release_objects VALUES
      ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('d',64),'v99.0-rc.1'),
      ('v99.0','runs','test','review/releases/v99.0-rc.1/runs.u32le.gz',3,repeat('c',64),repeat('e',64),'v99.0-rc.1');
    SET CONSTRAINTS atlas.map_release_pair IMMEDIATE;
    BEGIN
        DELETE FROM atlas.map_release_objects WHERE map_version='v99.0' AND stream='rows';
        RAISE EXCEPTION 'one stream removed from a release';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'publish both streams from one approved candidate together' THEN RAISE; END IF;
    END;
    BEGIN
        INSERT INTO atlas.map_release_objects VALUES
          ('v99.0','rows','test','review/releases/v99.0-rc.1/rows.u32le.gz',2,repeat('b',64),repeat('d',64),'v99.0-rc.1');
        RAISE EXCEPTION 'duplicate release stream accepted';
    EXCEPTION WHEN unique_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.map_release_objects SET r2_key='different' WHERE map_version='v99.0';
        RAISE EXCEPTION 'published release edited';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'published release objects are immutable' THEN RAISE; END IF;
    END;
END $$;
-- The original release can still be restored without candidate metadata.
INSERT INTO atlas.map_release_objects VALUES
  ('v8.0','rows','test','legacy/rows',1,repeat('a',64),repeat('b',64),NULL),
  ('v8.0','runs','test','legacy/runs',1,repeat('a',64),repeat('b',64),NULL);
ROLLBACK;
