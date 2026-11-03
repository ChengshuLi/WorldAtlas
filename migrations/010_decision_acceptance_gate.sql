-- Migration 009 is a review-branch-only research data import and is not a
-- schema prerequisite. This migration depends on 005; keep the numbering distinct.
-- Fail closed: the current model cannot prove complete source-backed land and
-- sea coverage. Draft records and research evidence are not build authority.
-- A future reviewed migration may replace this gate only after implementing and
-- testing completeness, source-byte verification, and review controls.
CREATE FUNCTION atlas.block_decision_acceptance_pending_readiness() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(hashtext('atlas.decision_graph'));
 IF NEW.status='accepted' THEN
  RAISE EXCEPTION 'decision acceptance disabled until source-backed land and sea completeness can be verified';
 END IF;
 RETURN NEW;
END $$;
-- SPLIT
CREATE TRIGGER decision_acceptance_gate BEFORE UPDATE OF status ON atlas.decision_revisions
 FOR EACH ROW EXECUTE FUNCTION atlas.block_decision_acceptance_pending_readiness();
