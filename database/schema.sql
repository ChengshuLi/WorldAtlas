-- Create an empty database schema. Run with psql; geographic records are loaded separately.
\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA atlas;
CREATE EXTENSION pg_jsonschema WITH SCHEMA public;

CREATE FUNCTION atlas.nonblank(value text) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
 SELECT value COLLATE "C" ~ '[^[:space:]]';
$$;

\ir schema/sources.sql
\ir schema/construction_contracts.sql
\ir schema/geographic_entities.sql
\ir schema/source_features.sql
\ir schema/geographic_rules.sql
\ir schema/releases.sql

COMMIT;
