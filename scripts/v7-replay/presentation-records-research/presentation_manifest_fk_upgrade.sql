-- Upgrade only an empty table created by the earlier research schema.
-- Fresh installations should use presentation_release_schema.sql instead.
ALTER TABLE atlas.review_presentation_releases
  ADD COLUMN manifest_source_id text NOT NULL,
  ADD COLUMN manifest_source_version text NOT NULL,
  ADD COLUMN code_revision text NOT NULL CHECK (code_revision ~ '^[0-9a-f]{40}$'),
  ADD CONSTRAINT review_presentation_manifest_source_fk
    FOREIGN KEY (manifest_source_id,manifest_source_version)
    REFERENCES atlas.source_assets(source_id,version);

