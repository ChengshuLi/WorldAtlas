-- Read-only. $1 is the complete, byte-authenticated settlement-estimates.json text.
-- Execute with a parameterized SELECT, never concatenate untrusted JSON into SQL.
WITH expected AS (
  SELECT id, kind, name, parent_id
  FROM jsonb_to_recordset(($1::jsonb)->'entities')
    AS e(id text, kind text, name text, parent_id text)
), actual AS (
  SELECT id, kind, name, parent_id
  FROM atlas_entities
  WHERE id LIKE 'settlement:ne:%'
), missing_or_changed AS (
  SELECT * FROM expected EXCEPT ALL SELECT * FROM actual
), extra_or_changed AS (
  SELECT * FROM actual EXCEPT ALL SELECT * FROM expected
)
SELECT jsonb_build_object(
 'expected_subjects',(SELECT count(*) FROM expected),
 'actual_subjects',(SELECT count(*) FROM actual),
 'missing_or_changed',(SELECT count(*) FROM missing_or_changed),
 'extra_or_changed',(SELECT count(*) FROM extra_or_changed),
 'wrong_example_or_active',(SELECT count(*) FROM atlas_entities WHERE id LIKE 'settlement:ne:%' AND (is_example<>0 OR active<>1)),
 'missing_or_wrong_parent_kind',(SELECT count(*) FROM expected e LEFT JOIN atlas_entities p ON p.id=e.parent_id WHERE p.id IS NULL OR p.kind<>'location'),
 'missing_details',(SELECT coalesce(jsonb_agg(to_jsonb(x)),'[]'::jsonb) FROM missing_or_changed x),
 'extra_details',(SELECT coalesce(jsonb_agg(to_jsonb(x)),'[]'::jsonb) FROM extra_or_changed x)
);
-- Required: 582 / 582 and zero differences. This does not approve current
-- geographic membership or dated parent claims; it verifies retained identity.
