-- Research-only water policy values; no acceptance or source-catalog assertion.
CREATE TABLE atlas.decision_water_assignment_policies (
 revision text NOT NULL REFERENCES atlas.decision_revisions(revision),
 policy_id text NOT NULL CHECK (length(trim(policy_id)) > 0),
 kind text NOT NULL CHECK (kind IN ('coastline_assignment','closed_water_assignment')),
 definition jsonb NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,policy_id)
);
CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_water_assignment_policies
 FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
