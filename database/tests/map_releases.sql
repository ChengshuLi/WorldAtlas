-- One official bundle per version and exactly one current bundle at most.
BEGIN;
INSERT INTO atlas.map_releases(id,r2_bucket,r2_prefix,manifest_sha256) VALUES
 ('v8.2-rc.5','test','releases/v8.2-rc.5/',repeat('a',64)),
 ('v8.3-rc.1','test','releases/v8.3-rc.1/',repeat('b',64)),
 ('v8.3-rc.2','test','releases/v8.3-rc.2/',repeat('c',64));
UPDATE atlas.map_releases SET is_official=true,is_current=true WHERE id='v8.2-rc.5';
DO $$ BEGIN
 IF (SELECT map_version FROM atlas.map_releases WHERE id='v8.3-rc.1')<>'v8.3' THEN
  RAISE EXCEPTION 'candidate version extraction failed'; END IF;
 BEGIN
  UPDATE atlas.map_releases SET is_current=true WHERE id='v8.3-rc.1';
  RAISE EXCEPTION 'an unofficial candidate became current';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.map_releases SET is_official=true,is_current=true WHERE id='v8.3-rc.1';
  RAISE EXCEPTION 'two current releases accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 UPDATE atlas.map_releases SET is_official=true WHERE id='v8.3-rc.1';
 BEGIN
  UPDATE atlas.map_releases SET is_official=true WHERE id='v8.3-rc.2';
  RAISE EXCEPTION 'two official releases for the same version accepted';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  UPDATE atlas.map_releases SET manifest_sha256=repeat('d',64) WHERE id='v8.3-rc.1';
  RAISE EXCEPTION 'immutable bundle changed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'release bundle identity is immutable' THEN RAISE; END IF;
 END;
 BEGIN
  INSERT INTO atlas.map_releases(id,r2_bucket,r2_prefix,manifest_sha256)
  VALUES ('v8.3-rc3','test','releases/v8.3-rc3/',repeat('e',64));
  RAISE EXCEPTION 'inconsistent candidate spelling accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE atlas.map_releases SET is_current=false WHERE is_current;
 UPDATE atlas.map_releases SET is_current=true WHERE id='v8.3-rc.1';
END $$;
ROLLBACK;
