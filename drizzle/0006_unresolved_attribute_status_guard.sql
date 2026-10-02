-- Preserve existing claims and all original schema identities. Reject only new
-- contradictory unresolved evidence; readers suppress malformed retained claims.
CREATE TRIGGER atlas_attribute_unresolved_status BEFORE INSERT ON atlas_attribute_records
WHEN NEW.status IN ('unknown','disputed','no-majority') AND (json_type(NEW.value)!='null' OR NEW.category_id IS NOT NULL)
BEGIN SELECT RAISE(ABORT,'Unresolved attribute status requires null value and category_id'); END;
