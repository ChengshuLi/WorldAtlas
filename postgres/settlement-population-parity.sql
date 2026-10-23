-- Read-only campaign parity, after migration/import on an authorized target.
-- $1: exact authenticated data/settlement-estimates.json text; $2: prepared source ID;
-- $3: prepared registry SHA256; $4: complete prepared source catalog JSON.
-- Never interpolate JSON into SQL. A count alone does not establish parity.
WITH expected AS (
 SELECT h->>'id' id, h->>'entity_id' entity_id, h->>'field' field,
        (h->>'valid_from')::integer valid_from, (h->>'valid_to')::integer valid_to,
        h->>'source' source, h->'value' value, 'und' language,
        'preferred' name_role, 0 is_example, h original_record
 FROM jsonb_array_elements(($1::jsonb)->'entity_history') h
), scope AS (
 SELECT * FROM atlas_typed_observations
 WHERE id LIKE 'ne-pop:settlement:ne:%' OR source_id=$2
), actual AS (
 SELECT id, subject_id entity_id, metadata::jsonb #>> '{original_record,field}' field,
        valid_from, valid_to, metadata::jsonb #>> '{original_record,source}' source,
        jsonb_build_object('population',value::jsonb) value,
        metadata::jsonb->>'language' language, metadata::jsonb->>'name_role' name_role,
        is_example, metadata::jsonb->'original_record' original_record
 FROM scope
), missing_or_changed AS (
 SELECT * FROM expected EXCEPT ALL SELECT * FROM actual
), extra_or_changed AS (
 SELECT * FROM actual EXCEPT ALL SELECT * FROM expected
), bad_contract AS (
 SELECT id FROM scope
 WHERE subject_kind IS DISTINCT FROM 'settlement'
    OR field_id IS DISTINCT FROM 'settlement.population'
    OR contract_version IS DISTINCT FROM 1 OR source_id IS DISTINCT FROM $2
    OR registry_sha256 IS DISTINCT FROM $3 OR method IS DISTINCT FROM 'estimate'
    OR status IS DISTINCT FROM 'estimate' OR is_example IS DISTINCT FROM 0
    OR metadata::jsonb->>'estimate_or_projection' IS DISTINCT FROM 'not_disambiguated_by_retained_source'
    OR metadata::jsonb->'un_edition' IS DISTINCT FROM 'null'::jsonb
    OR metadata::jsonb->'estimate_projection_cutoff' IS DISTINCT FROM 'null'::jsonb
    OR metadata::jsonb #>> '{measurement,unit}' IS DISTINCT FROM 'persons'
    OR metadata::jsonb #> '{measurement,period}' IS DISTINCT FROM jsonb_build_object('from',valid_from,'to',valid_to)
), source_difference AS (
 SELECT $4::jsonb AS body EXCEPT ALL
 SELECT jsonb_build_object('id',id,'name',name,'url',url,'license',license,'vintage',vintage,
   'supported_from',supported_from,'supported_to',supported_to,'status',status,'metadata',metadata::jsonb)
 FROM atlas_sources WHERE id=$2
)
SELECT jsonb_build_object(
 'expected_rows',(SELECT count(*) FROM expected),
 'actual_rows',(SELECT count(*) FROM actual),
 'distinct_subjects',(SELECT count(DISTINCT entity_id) FROM actual),
 'missing_or_changed',(SELECT count(*) FROM missing_or_changed),
 'extra_or_changed',(SELECT count(*) FROM extra_or_changed),
 'contract_mismatches',(SELECT count(*) FROM bad_contract),
 'source_mismatches',(SELECT count(*) FROM source_difference),
 'unexpected_retirements',(SELECT count(*) FROM atlas_typed_retirements r JOIN expected e ON e.id=r.target_id WHERE r.collection='observations')
) parity;
-- Required initial-import result: 9301 expected/actual, 582 subjects, all other
-- counts zero. Identity parity is checked separately before any import. Preserve
-- original receipts and before/after entities, links, geography and legacy tables.
