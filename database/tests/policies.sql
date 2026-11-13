-- Working geographic policies can be edited directly.
BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.entity_registry_revisions(revision) VALUES ('__policies');
 INSERT INTO atlas.decision_revisions VALUES ('__policies','__policies','{}');
 INSERT INTO atlas.decision_policies VALUES
 ('__policies','coast','coastline_assignment','{}','{}'),
 ('__policies','ocean','ocean_fill','{}','{}'),
 ('__policies','land','mainland_assignment','{"tie_tolerance_metres":0.00001}','{}');
 UPDATE atlas.decision_policies SET evidence='{"note":"editable"}' WHERE revision='__policies';
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__policies','unknown','unknown','{}','{}');
  RAISE EXCEPTION 'unknown policy operation accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__policies','invalid','ocean_fill','[]','{}');
  RAISE EXCEPTION 'non-object policy definition accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__policies','coast','ocean_fill','{}','{}');
  RAISE EXCEPTION 'duplicate policy identity accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
ROLLBACK;
