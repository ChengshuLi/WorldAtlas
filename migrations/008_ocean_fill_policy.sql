-- Distinct table avoids rewriting the existing policy-kind constraint on the review branch.
CREATE TABLE atlas.decision_ocean_fill_policies (
 revision text PRIMARY KEY REFERENCES atlas.decision_revisions(revision),
 policy_id text NOT NULL CHECK (length(trim(policy_id)) > 0),
 definition jsonb NOT NULL CHECK (jsonb_typeof(definition) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object')
);
CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE ON atlas.decision_ocean_fill_policies FOR EACH ROW EXECUTE FUNCTION atlas.guard_decision_row();
