-- Draft structural land proposals. Source geometry hashes are evidence, not
-- claims that an external file has been selected or registered in R2.
CREATE TABLE atlas.decision_land_component_witness_rules (
 revision text NOT NULL,
 rule_id text NOT NULL CHECK (length(trim(rule_id)) > 0),
 entity_revision text NOT NULL,
 entity_id bigint NOT NULL,
 method text NOT NULL CHECK (method = 'component_witness_list_v1'),
 selector jsonb NOT NULL CHECK (jsonb_typeof(selector) = 'object'),
 evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence) = 'object'),
 PRIMARY KEY (revision,rule_id),
 FOREIGN KEY (revision,entity_revision) REFERENCES atlas.decision_revisions(revision,entity_revision),
 FOREIGN KEY (entity_revision,entity_id) REFERENCES atlas.geographic_entities(revision,id)
);
CREATE TRIGGER decision_row_guard BEFORE INSERT OR UPDATE OR DELETE
 ON atlas.decision_land_component_witness_rules FOR EACH ROW
 EXECUTE FUNCTION atlas.guard_decision_row();
