-- Create an empty database schema. Run with psql; geographic records are loaded separately.
\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA atlas;

\ir schema/sources.sql
\ir schema/construction_contracts.sql
\ir schema/entities.sql
\ir schema/geographic_decisions.sql
\ir schema/mainland.sql
\ir schema/releases.sql

COMMIT;
