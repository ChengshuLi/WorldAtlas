-- Rename the construction table; historical documents are archived before removal.
BEGIN;

ALTER TABLE atlas.structured_documents RENAME TO construction_records;
ALTER TABLE atlas.construction_records RENAME CONSTRAINT structured_documents_document_check TO construction_records_document_check;
ALTER TABLE atlas.construction_records RENAME CONSTRAINT structured_documents_source_id_check TO construction_records_source_id_check;
ALTER TABLE atlas.construction_records RENAME CONSTRAINT structured_documents_version_check TO construction_records_version_check;
ALTER TABLE atlas.construction_records RENAME CONSTRAINT structured_documents_pkey TO construction_records_pkey;
ALTER TRIGGER structured_document_immutable ON atlas.construction_records RENAME TO construction_record_immutable;
ALTER FUNCTION atlas.reject_source_change() RENAME TO reject_construction_change;
CREATE OR REPLACE FUNCTION atlas.reject_construction_change() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'construction records are immutable; use a new version';
END; $$;
COMMENT ON TABLE atlas.construction_records IS 'Immutable versioned construction settings identified by source_id and version.';

COMMIT;
