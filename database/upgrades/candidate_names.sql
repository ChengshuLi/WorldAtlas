-- Accept v8.3-rc1 while keeping existing immutable -rc.1 candidate IDs valid.
ALTER TABLE atlas.map_release_candidates
    DROP CONSTRAINT IF EXISTS map_release_candidates_candidate_id_check;
ALTER TABLE atlas.map_release_candidates
    DROP CONSTRAINT IF EXISTS map_release_candidate_name;
ALTER TABLE atlas.map_release_candidates ADD CONSTRAINT map_release_candidate_name
    CHECK (candidate_id ~ '^v[0-9]+[.][0-9]+-rc[.]?[1-9][0-9]*$');
ALTER TABLE atlas.map_release_candidates ALTER COLUMN map_version
    SET EXPRESSION AS (split_part(candidate_id, '-rc', 1));
