-- Check selection flags and source references in working land and water policies.
-- Run on a disposable database initialized with the full schema.
DO $$
DECLARE
 rev constant text := 'test-draft-guards-rollback-20261104';
 erev constant text := '__draft_guard_test_registry';
 caught boolean;
BEGIN
 BEGIN
  INSERT INTO atlas.entity_registry_revisions(revision) VALUES (erev);
  INSERT INTO atlas.geographic_entity_ids(id) VALUES (3) ON CONFLICT DO NOTHING;
  INSERT INTO atlas.geographic_entities(revision,id,name,level,parent_id)
   VALUES (erev,3,'Synthetic parent','continent',NULL);
  INSERT INTO atlas.decision_revisions(revision,entity_revision,evidence) VALUES (rev,erev,'{}');
  INSERT INTO atlas.decision_land_component_witness_rules(revision,rule_id,entity_revision,entity_id,method,selector,evidence)
   VALUES (rev,'valid',erev,3,'component_witness_list_v1','{}','{"execution_status":"selected_for_research"}');
  INSERT INTO atlas.decision_water_assignment_policies(revision,policy_id,kind,definition,evidence)
   VALUES (rev,'valid','closed_water_assignment','{}','{"execution_status":"research_only_not_selected"}');
  INSERT INTO atlas.decision_ocean_fill_policies(revision,policy_id,definition,evidence)
   VALUES (rev,'valid','{}','{"execution_status":"research_only_not_selected"}');
  caught:=false;
  BEGIN INSERT INTO atlas.decision_land_component_witness_rules(revision,rule_id,entity_revision,entity_id,method,selector,evidence)
   VALUES(rev,'missing',erev,3,'component_witness_list_v1','{}','{}'); EXCEPTION WHEN check_violation THEN caught:=true; END;
  IF NOT caught THEN RAISE EXCEPTION 'missing witness selection allowed'; END IF;
  caught:=false;
  BEGIN INSERT INTO atlas.decision_land_component_witness_rules(revision,rule_id,entity_revision,entity_id,method,selector,evidence)
   VALUES(rev,'unknown',erev,3,'component_witness_list_v1','{}','{"execution_status":"unknown"}'); EXCEPTION WHEN check_violation THEN caught:=true; END;
  IF NOT caught THEN RAISE EXCEPTION 'unknown witness selection allowed'; END IF;
  caught:=false;
  BEGIN INSERT INTO atlas.decision_land_component_witness_rules(revision,rule_id,entity_revision,entity_id,method,selector,evidence)
   VALUES(rev,'bad-entity',erev,-9223372036854775807,'component_witness_list_v1','{}','{"execution_status":"selected_for_research"}'); EXCEPTION WHEN foreign_key_violation THEN caught:=true; END;
  IF NOT caught THEN RAISE EXCEPTION 'orphan witness entity allowed'; END IF;
  INSERT INTO atlas.decision_water_assignment_policies(revision,policy_id,kind,definition,evidence)
   VALUES(rev,'plain-policy','closed_water_assignment','{}','{}');
  caught:=false;
  BEGIN INSERT INTO atlas.decision_water_assignment_policies(revision,policy_id,kind,definition,evidence)
   VALUES(rev,'unknown-kind','unknown','{}','{}'); EXCEPTION WHEN check_violation THEN caught:=true; END;
  IF NOT caught THEN RAISE EXCEPTION 'unknown water policy kind allowed'; END IF;
  caught:=false;
  BEGIN INSERT INTO atlas.decision_ocean_fill_policies(revision,policy_id,definition,evidence)
   VALUES(rev,'unknown','{}','{"execution_status":"unknown"}'); EXCEPTION WHEN check_violation THEN caught:=true; END;
  IF NOT caught THEN RAISE EXCEPTION 'unknown ocean selection allowed'; END IF;
  UPDATE atlas.decision_water_assignment_policies
    SET evidence='{"execution_status":"selected_for_research"}'
    WHERE revision=rev AND policy_id='valid';
  IF NOT FOUND THEN RAISE EXCEPTION 'working water policy could not be edited'; END IF;
  RAISE EXCEPTION '__draft_guards_success_rollback__';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM <> '__draft_guards_success_rollback__' THEN RAISE; END IF;
 END;
END $$;
