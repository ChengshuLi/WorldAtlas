-- A working boundary keeps its source links when its notes or geometry change.
BEGIN;
DO $$
DECLARE
    line jsonb := '{"type":"LineString","coordinates":[[0,0],[1,1]]}';
    edited_line jsonb := '{"type":"LineString","coordinates":[[0,0],[1,1],[2,2]]}';
    line_hash text := repeat('a',64);
BEGIN
    INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__boundary_entities');
    INSERT INTO atlas.decision_revisions(revision,entity_revision,evidence)
      VALUES ('__boundary_decisions','__boundary_entities','{}');
    INSERT INTO atlas.source_assets
      (source_id,version,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,provenance)
      VALUES ('__boundary_source','1','Test','Test','test:source','Test','test:license','Test','test','boundary',repeat('b',64),1,'{}');
    INSERT INTO atlas.decision_mainland_boundaries(revision,boundary_id,geometry,geometry_sha256,coordinate_reference,provenance) VALUES
      ('__boundary_decisions','line',line,line_hash,'OGC:CRS84','{}');
    BEGIN
        INSERT INTO atlas.decision_mainland_boundary_sources VALUES
          ('__boundary_decisions','line','missing','1','construction');
        RAISE EXCEPTION 'missing source accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    INSERT INTO atlas.decision_mainland_boundary_sources VALUES
      ('__boundary_decisions','line','__boundary_source','1','construction');
    UPDATE atlas.decision_mainland_boundaries SET provenance='{"review":"checked"}'
    WHERE revision='__boundary_decisions' AND boundary_id='line';
    IF NOT EXISTS (
        SELECT 1 FROM atlas.decision_mainland_boundaries b JOIN atlas.decision_mainland_boundary_sources s USING (revision,boundary_id)
        WHERE b.revision='__boundary_decisions' AND b.geometry=line AND b.geometry_sha256=line_hash
          AND b.provenance->>'review'='checked' AND s.source_id='__boundary_source' AND s.source_version='1'
    ) THEN RAISE EXCEPTION 'the notes, geometry, or source links changed unexpectedly'; END IF;

    UPDATE atlas.decision_mainland_boundaries SET geometry=edited_line, geometry_sha256=repeat('c',64)
    WHERE revision='__boundary_decisions' AND boundary_id='line';
    IF NOT EXISTS (
        SELECT FROM atlas.decision_mainland_boundaries b JOIN atlas.decision_mainland_boundary_sources s USING (revision,boundary_id)
        WHERE b.revision='__boundary_decisions' AND b.geometry=edited_line AND b.geometry_sha256=repeat('c',64)
          AND s.source_id='__boundary_source' AND s.source_version='1'
    ) THEN RAISE EXCEPTION 'editing a boundary lost its geometry or source'; END IF;

    BEGIN
        UPDATE atlas.decision_mainland_boundaries SET geometry='{"type":"Point","coordinates":[0,0]}'
        WHERE revision='__boundary_decisions';
        RAISE EXCEPTION 'a boundary accepted a point instead of a line';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.decision_mainland_boundaries SET geometry='{}'
        WHERE revision='__boundary_decisions';
        RAISE EXCEPTION 'a boundary accepted missing geometry fields';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.decision_mainland_boundaries SET construction_id='missing'
        WHERE revision='__boundary_decisions';
        RAISE EXCEPTION 'a boundary accepted an incomplete construction reference';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        UPDATE atlas.decision_mainland_boundaries SET construction_id='missing',construction_version='1'
        WHERE revision='__boundary_decisions';
        RAISE EXCEPTION 'a boundary accepted a missing construction';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
END $$;
ROLLBACK;
