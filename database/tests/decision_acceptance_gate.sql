-- Run on a disposable database initialized with the full schema. Synthetic writes roll back.
DO $$ BEGIN
 BEGIN
  INSERT INTO atlas.entity_registry_revisions(revision,status) VALUES ('__gate_entity','draft');
  BEGIN
   INSERT INTO atlas.decision_revisions(revision,entity_revision,status,evidence,reviewed_by,reviewed_at)
    VALUES ('__gate_direct','__gate_entity','accepted','{}','synthetic',now());
   RAISE EXCEPTION 'unexpected accepted insert';
  EXCEPTION WHEN raise_exception THEN
   IF SQLERRM <> 'decision revision must start as draft' THEN RAISE; END IF;
  END;
  INSERT INTO atlas.decision_revisions(revision,entity_revision,evidence) VALUES ('__gate_decision','__gate_entity','{}');
  BEGIN
   UPDATE atlas.decision_revisions SET status='accepted',reviewed_by='synthetic',reviewed_at=now() WHERE revision='__gate_decision';
   RAISE EXCEPTION 'unexpected acceptance';
  EXCEPTION WHEN raise_exception THEN
   IF SQLERRM <> 'decision acceptance disabled until source-backed land and sea completeness can be verified' THEN RAISE; END IF;
  END;
  IF (SELECT status FROM atlas.decision_revisions WHERE revision='__gate_decision') <> 'draft' THEN
   RAISE EXCEPTION 'blocked transition changed the draft';
  END IF;
  UPDATE atlas.decision_revisions SET evidence='{"candidate":"still draft"}' WHERE revision='__gate_decision';
  IF (SELECT evidence->>'candidate' FROM atlas.decision_revisions WHERE revision='__gate_decision') <> 'still draft' THEN
   RAISE EXCEPTION 'draft edits should remain possible';
  END IF;
  UPDATE atlas.decision_revisions SET status='rejected' WHERE revision='__gate_decision';
  IF (SELECT status FROM atlas.decision_revisions WHERE revision='__gate_decision') <> 'rejected' THEN
   RAISE EXCEPTION 'draft rejection should remain possible';
  END IF;
  RAISE EXCEPTION USING ERRCODE='ZX001',MESSAGE='rollback synthetic test';
 EXCEPTION WHEN SQLSTATE 'ZX001' THEN NULL; END;
END $$;
