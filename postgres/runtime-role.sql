-- Technical-maintainer operation, executed by the schema owner in one transaction.
-- scripts/provision-postgres-runtime-role.mjs supplies the password with a bound,
-- transaction-local set_config call. Never paste a credential into this file.
-- Existing roles keep their password unless explicit rotation was requested.
-- PostgreSQL 16+ gives a non-superuser creator ADMIN OPTION on a new role.
-- Allow only the reviewed table owner's administrative edge into this role,
-- with INHERIT and SET both false. It grants the application no owner privileges.
-- The application itself must belong to no roles. Other incoming edges fail.
DO $atlas_runtime_role$
DECLARE
 app_name constant text := 'worldatlas_app';
 app_oid oid;
 owner_oid oid := (SELECT oid FROM pg_roles WHERE rolname=current_user);
 app pg_roles%ROWTYPE;
 password text := current_setting('worldatlas.runtime_password',true);
 rotate boolean := coalesce(current_setting('worldatlas.rotate_password',true),'false')='true';
 app_table text;
 app_schema text;
 field_name text;
 all_tables constant text[] := ARRAY['atlas_sources','atlas_entity_types','atlas_entities','atlas_categories','atlas_attribute_records','atlas_names','atlas_relationships','atlas_media','atlas_media_links','atlas_evidence_retirements','atlas_ingestions','atlas_geographic_releases','atlas_geographic_memberships','atlas_geographic_changes'];
BEGIN
 IF current_schema()<>'public' THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Runtime provisioning requires the reviewed public schema'; END IF;
 IF EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY(all_tables) AND c.relowner<>(SELECT oid FROM pg_roles WHERE rolname=current_user)) OR (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY(all_tables) AND c.relkind='r')<>14 THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Runtime provisioning requires the owner of all fourteen reviewed tables'; END IF;
 SELECT * INTO app FROM pg_roles WHERE rolname=app_name;
 IF FOUND THEN
  app_oid:=app.oid;
  IF NOT app.rolcanlogin OR app.rolsuper OR app.rolinherit OR app.rolcreatedb OR app.rolcreaterole OR app.rolreplication OR app.rolbypassrls OR coalesce(array_length(app.rolconfig,1),0)>0 THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has unreviewed attributes'; END IF;
  IF EXISTS(SELECT 1 FROM pg_auth_members WHERE member=app_oid OR (roleid=app_oid AND NOT(member=owner_oid AND admin_option AND NOT inherit_option AND NOT set_option))) OR EXISTS(SELECT 1 FROM pg_shdepend WHERE refclassid='pg_authid'::regclass AND refobjid=app_oid AND deptype='o') THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has membership or ownership'; END IF;
  IF EXISTS(SELECT 1 FROM pg_db_role_setting WHERE setrole=app_oid AND coalesce(array_length(setconfig,1),0)>0) OR has_parameter_privilege(app_oid,'session_replication_role','SET') THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has unreviewed settings or trigger-bypass privilege'; END IF;
  IF EXISTS(SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' AND has_schema_privilege(app_oid,oid,'CREATE')) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Application role can create persistent schema objects'; END IF;
  FOR app_schema,app_table IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','v','m','f') LOOP
   IF NOT(app_schema='public' AND app_table=ANY(all_tables)) AND (has_table_privilege(app_oid,format('%I.%I',app_schema,app_table),'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege(app_oid,format('%I.%I',app_schema,app_table),'SELECT,INSERT,UPDATE,REFERENCES')) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has unrelated table privileges'; END IF;
  END LOOP;
  FOREACH app_table IN ARRAY all_tables LOOP
   IF has_table_privilege(app_oid,format('public.%I',app_table),'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR (app_table='atlas_ingestions' AND has_table_privilege(app_oid,'public.atlas_ingestions','INSERT')) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has excessive table privileges'; END IF;
   FOR field_name IN SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND information_schema.columns.table_name=app_table LOOP
    IF has_column_privilege(app_oid,format('public.%I',app_table),field_name,'REFERENCES') OR (has_column_privilege(app_oid,format('public.%I',app_table),field_name,'UPDATE') AND NOT(app_table='atlas_geographic_releases' AND field_name IN ('status','published_at'))) OR (app_table='atlas_ingestions' AND field_name='rowid' AND has_column_privilege(app_oid,'public.atlas_ingestions',field_name,'INSERT')) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role has excessive column privileges'; END IF;
   END LOOP;
  END LOOP;
  IF has_sequence_privilege(app_oid,'public.atlas_ingestions_rowid_seq','SELECT,UPDATE') THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Existing application role can inspect or reset the ingestion sequence'; END IF;
  IF rotate THEN
   IF password IS NULL OR length(password)<24 THEN RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Explicit password rotation requires a strong private credential'; END IF;
   EXECUTE format('ALTER ROLE %I PASSWORD %L',app_name,password);
  END IF;
 ELSE
  IF password IS NULL OR length(password)<24 THEN RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Fresh application LOGIN requires a strong private credential'; END IF;
  EXECUTE format('CREATE ROLE %I LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',app_name,password);
 END IF;
 EXECUTE format('GRANT USAGE ON SCHEMA public TO %I',app_name);
 FOREACH app_table IN ARRAY all_tables LOOP
  EXECUTE format('GRANT SELECT ON TABLE public.%I TO %I',app_table,app_name);
  IF app_table<>'atlas_ingestions' THEN EXECUTE format('GRANT INSERT ON TABLE public.%I TO %I',app_table,app_name); END IF;
 END LOOP;
 EXECUTE format('GRANT INSERT(id,fingerprint,counts,created_at) ON TABLE public.atlas_ingestions TO %I',app_name);
 EXECUTE format('GRANT UPDATE(status,published_at) ON TABLE public.atlas_geographic_releases TO %I',app_name);
 EXECUTE format('GRANT USAGE ON SEQUENCE public.atlas_ingestions_rowid_seq TO %I',app_name);
 IF EXISTS(SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' AND has_schema_privilege(app_name,oid,'CREATE')) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='Schema permits persistent object creation; do not reopen imports'; END IF;
END
$atlas_runtime_role$;
