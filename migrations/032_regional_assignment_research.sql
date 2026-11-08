-- Source geometry referenced by a selected regional rule.
CREATE TABLE IF NOT EXISTS atlas.geographic_line_observations (
    line_id text PRIMARY KEY,
    source_id text NOT NULL,
    source_version text NOT NULL,
    geometry jsonb NOT NULL CHECK (geometry ->> 'type' IN ('LineString', 'MultiLineString')),
    geometry_sha256 text NOT NULL CHECK (geometry_sha256 ~ '^[0-9a-f]{64}$'),
    coordinate_reference text NOT NULL,
    provenance jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('research', 'selected', 'retired')),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (source_id, source_version) REFERENCES atlas.source_assets(source_id, version)
);

-- Selected research policy data only. No accepted geography or map is changed.
CREATE TABLE IF NOT EXISTS atlas.regional_island_rule_sets (
    revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
    rule_set_id text NOT NULL CHECK (length(btrim(rule_set_id)) > 0),
    selection_status text NOT NULL CHECK (selection_status IN ('selected_for_research', 'withdrawn')),
    line_id text NOT NULL REFERENCES atlas.geographic_line_observations(line_id),
    definition jsonb NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
    evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (revision, rule_set_id)
);
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'atlas.regional_island_rule_sets'::regclass AND tgname = 'decision_row_guard' AND NOT tgisinternal) THEN
    CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.regional_island_rule_sets FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
  END IF;
END $$;
