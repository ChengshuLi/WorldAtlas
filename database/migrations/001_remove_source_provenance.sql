-- Remove unused raw-source metadata; construction settings remain in their own records.
BEGIN;

CREATE OR REPLACE FUNCTION atlas.guard_source_identity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF (NEW.source_id,NEW.version,NEW.r2_bucket,NEW.r2_key,NEW.sha256,NEW.size_bytes,
     NEW.source_uri,NEW.created_at) IS DISTINCT FROM
    (OLD.source_id,OLD.version,OLD.r2_bucket,OLD.r2_key,OLD.sha256,OLD.size_bytes,
     OLD.source_uri,OLD.created_at) THEN
  RAISE EXCEPTION 'source identity and captured bytes are immutable; use a new source version';
 END IF;
 RETURN NEW;
END $$;

ALTER TABLE atlas.source_assets DROP COLUMN provenance;

COMMIT;
