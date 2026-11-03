-- Run only in a disposable namespace after 001–005. Synthetic writes roll back.
DO $$ BEGIN
 BEGIN
  INSERT INTO atlas.source_assets(source_id,version,title,kind,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,provenance)
    VALUES ('__s','1','test','raw','test','test','test','test','test','test','__decision_test',repeat('a',64),1,'{}');
  INSERT INTO atlas.decision_revisions(revision,entity_revision,evidence) VALUES ('__d','v7-category-bootstrap-v1','{}');
  INSERT INTO atlas.decision_features VALUES ('__d','f','__s','1','raw-f',repeat('b',64),'{}');
  INSERT INTO atlas.decision_basins VALUES ('__d','b','f','shared_nearest_assigned_shore','{}','{}');
  INSERT INTO atlas.decision_basin_participants VALUES ('__d','b','v7-category-bootstrap-v1',7);
  BEGIN
   UPDATE atlas.decision_revisions SET status='accepted',reviewed_by='test',reviewed_at=now() WHERE revision='__d';
   RAISE EXCEPTION 'accepted with draft registry';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'accepted decisions require an accepted entity registry' THEN RAISE; END IF; END;
  UPDATE atlas.entity_registry_revisions SET status='accepted',reviewed_by='test',reviewed_at=now() WHERE revision='v7-category-bootstrap-v1';
  BEGIN
   UPDATE atlas.decision_revisions SET status='accepted',reviewed_by='test',reviewed_at=now() WHERE revision='__d';
   RAISE EXCEPTION 'accepted with one participant';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'basin has too few participants for its method' THEN RAISE; END IF; END;
  INSERT INTO atlas.decision_basin_participants VALUES ('__d','b','v7-category-bootstrap-v1',8);
  INSERT INTO atlas.decision_basins VALUES ('__d','single','f','single_continent_named_basin','{}','{}');
  INSERT INTO atlas.decision_basin_participants VALUES ('__d','single','v7-category-bootstrap-v1',9);
  UPDATE atlas.decision_revisions SET status='accepted',reviewed_by='test',reviewed_at=now() WHERE revision='__d';
  BEGIN
   DELETE FROM atlas.decision_basin_participants WHERE revision='__d' AND entity_id=8;
   RAISE EXCEPTION 'accepted rows changed';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'closed decision rows are immutable' THEN RAISE; END IF; END;
  BEGIN
   UPDATE atlas.review_category_bindings SET code=100 WHERE revision='v7-category-bootstrap-v1' AND code=7;
   RAISE EXCEPTION 'accepted entity binding changed';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'closed entity rows are immutable' THEN RAISE; END IF; END;
  INSERT INTO atlas.source_builds(build_id,entity_revision,code_revision,decision_revision,decision_snapshot_sha256,physical_grid_revision,physical_grid_sha256,software_versions)
  VALUES ('__b','v7-category-bootstrap-v1','test','__d',repeat('c',64),'grid-1',repeat('d',64),'{}');
  INSERT INTO atlas.source_build_inputs VALUES ('__b','__s','1','raw','basin');
  BEGIN
   UPDATE atlas.source_builds SET decision_snapshot_sha256=NULL, status='locked' WHERE build_id='__b';
   RAISE EXCEPTION 'build locked without snapshot hash';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'locked build requires decision, grid, hash and software pins' THEN RAISE; END IF; END;
  UPDATE atlas.source_builds SET status='locked' WHERE build_id='__b';
  BEGIN
   UPDATE atlas.source_builds SET decision_snapshot_sha256=repeat('e',64) WHERE build_id='__b';
   RAISE EXCEPTION 'locked build changed';
  EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'locked builds are immutable' THEN RAISE; END IF; END;
  RAISE EXCEPTION USING ERRCODE='ZX001',MESSAGE='rollback synthetic test';
 EXCEPTION WHEN SQLSTATE 'ZX001' THEN NULL; END;
END $$;
