-- Historical UI presentation only; never an executable geography decision.
-- Install only after separately cataloging the three exact R2 source artifacts.
-- Export must verify source keys/hashes and deterministic records bytes against
-- an independently authenticated manifest. Constraints do not authenticate data.
-- Privileged owners can disable triggers or change schema; restrict privileges.
CREATE TABLE atlas.review_presentation_releases (
  release_id text PRIMARY KEY CHECK (length(trim(release_id)) > 0),
  release_kind text NOT NULL CHECK (release_kind = 'historical_review_presentation'),
  proposal_source_id text NOT NULL,
  proposal_source_version text NOT NULL,
  reference_source_id text NOT NULL,
  reference_source_version text NOT NULL,
  water_source_id text NOT NULL,
  water_source_version text NOT NULL,
  manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  records_sha256 text NOT NULL CHECK (records_sha256 ~ '^[0-9a-f]{64}$'),
  source_pins jsonb NOT NULL CHECK (jsonb_typeof(source_pins) = 'object'),
  records jsonb NOT NULL CHECK ((
    jsonb_typeof(records) = 'object'
    AND records ->> 'schema' = 'worldatlas-island-presentation-v1'
    AND jsonb_typeof(records -> 'source') = 'object'
    AND jsonb_typeof(records -> 'groups') = 'array'
    AND jsonb_typeof(records -> 'leaves') = 'array'
  ) IS TRUE),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (proposal_source_id,proposal_source_version) REFERENCES atlas.source_assets(source_id,version),
  FOREIGN KEY (reference_source_id,reference_source_version) REFERENCES atlas.source_assets(source_id,version),
  FOREIGN KEY (water_source_id,water_source_version) REFERENCES atlas.source_assets(source_id,version)
);

-- Immutable release rows ensure a correction creates a distinct release.
CREATE FUNCTION atlas.guard_review_presentation_release() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'historical presentation releases are immutable; create a new release';
END; $$;
CREATE TRIGGER review_presentation_release_immutable
  BEFORE UPDATE OR DELETE ON atlas.review_presentation_releases
  FOR EACH ROW EXECUTE FUNCTION atlas.guard_review_presentation_release();
CREATE TRIGGER review_presentation_release_no_truncate
  BEFORE TRUNCATE ON atlas.review_presentation_releases
  FOR EACH STATEMENT EXECUTE FUNCTION atlas.guard_review_presentation_release();

