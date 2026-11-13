-- The working revision selects these policies; a research flag is unnecessary.
ALTER TABLE atlas.decision_water_assignment_policies
    DROP CONSTRAINT IF EXISTS water_policy_execution_status_required;
