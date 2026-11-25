-- A record's own ID and its references have distinct names.
DO $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM pg_constraint c
  JOIN pg_class t ON t.oid=c.conrelid
  JOIN pg_namespace n ON n.oid=t.relnamespace
  JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=c.conkey[1]
  WHERE n.nspname='atlas' AND c.contype='p'
    AND cardinality(c.conkey)=1 AND a.attname<>'id'
 ) THEN RAISE EXCEPTION 'single-column primary keys must be named id'; END IF;
END $$;
