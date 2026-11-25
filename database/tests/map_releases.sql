-- Official bundles are permanent, with at most one per version and one current.
BEGIN;
INSERT INTO atlas.map_releases(id,r2_bucket,manifest_sha256) VALUES
 ('v8.2-rc.5','test',repeat('a',64)),
 ('v8.3-rc.1','test',repeat('b',64)),
 ('v8.3-rc.2','test',repeat('c',64));
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
  INSERT INTO atlas.map_releases(id,r2_bucket,manifest_sha256)
  VALUES ('v8.3-rc3','test',repeat('e',64));
  RAISE EXCEPTION 'inconsistent candidate spelling accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE atlas.map_releases SET is_current=false WHERE is_current;
 UPDATE atlas.map_releases SET is_current=true WHERE id='v8.3-rc.1';
 BEGIN
  UPDATE atlas.map_releases SET is_official=false WHERE id='v8.2-rc.5';
  RAISE EXCEPTION 'a previously published release was demoted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'official release status is permanent' THEN RAISE; END IF;
 END;
 BEGIN
  DELETE FROM atlas.map_releases WHERE id='v8.2-rc.5';
  RAISE EXCEPTION 'a previously published release was deleted';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'official release cannot be deleted' THEN RAISE; END IF;
 END;
 DELETE FROM atlas.map_releases WHERE id='v8.3-rc.2';
 IF NOT FOUND THEN RAISE EXCEPTION 'the preview could not be deleted'; END IF;
END $$;
ROLLBACK;
