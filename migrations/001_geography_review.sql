-- Initial research records. A review preview is not an accepted geography release.
CREATE SCHEMA IF NOT EXISTS atlas;

CREATE TABLE IF NOT EXISTS atlas.geography_proposals (
    proposal_id text PRIMARY KEY,
    parent_scope text NOT NULL,
    hierarchy_level text NOT NULL CHECK (hierarchy_level IN
        ('continent', 'subcontinent', 'region', 'area', 'province', 'location')),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'rejected')),
    base_revision text,
    grid_width integer NOT NULL CHECK (grid_width > 0),
    grid_height integer NOT NULL CHECK (grid_height > 0),
    grid_sha256 text NOT NULL CHECK (grid_sha256 ~ '^[0-9a-f]{64}$'),
    grid_uri text NOT NULL,
    metadata jsonb NOT NULL,
    evidence jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    approved_at timestamptz,
    CHECK ((status = 'approved') = (approved_at IS NOT NULL))
);

CREATE VIEW atlas.accepted_geography_proposals AS
    SELECT * FROM atlas.geography_proposals WHERE status = 'approved';
