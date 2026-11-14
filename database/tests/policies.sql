BEGIN;
DO $$ BEGIN
 INSERT INTO atlas.decision_policies VALUES
 ('__coast','coastline_assignment','{}','{}'),('__ocean','ocean_fill','{}','{}'),
 ('__land','mainland_assignment','{"tie_tolerance_metres":0.00001}','{}');
 UPDATE atlas.decision_policies SET evidence='{"note":"editable"}';
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__unknown','unknown','{}','{}');
  RAISE EXCEPTION 'unknown policy operation accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__invalid','scoped_land_partition','[]','{}');
  RAISE EXCEPTION 'non-object policy definition accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  INSERT INTO atlas.decision_policies VALUES ('__other_ocean','ocean_fill','{}','{}');
  RAISE EXCEPTION 'two active ocean policies accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
ROLLBACK;
