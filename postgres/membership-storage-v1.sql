-- Owner-only forward representation. Applied by the bounded maintenance helper;
-- never run through the original immutable deployment migrations.
CREATE TABLE public.worldatlas_membership_release_keys (
 key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id text COLLATE "C" UNIQUE NOT NULL REFERENCES public.atlas_geographic_releases(id));
CREATE TABLE public.worldatlas_membership_entity_keys (
 key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id text COLLATE "C" UNIQUE NOT NULL REFERENCES public.atlas_entities(id));
CREATE TABLE public.worldatlas_membership_source_keys (
 key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id text COLLATE "C" UNIQUE NOT NULL REFERENCES public.atlas_sources(id));
CREATE TABLE public.worldatlas_membership_evidence (
 key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 digest bytea UNIQUE NOT NULL,
 raw text COLLATE "C" NOT NULL,
 CHECK(public.json_valid(raw) AND public.json_type(raw)='object'),
 CHECK(digest=pg_catalog.sha256(pg_catalog.convert_to(raw,'UTF8'))));
CREATE TABLE public.worldatlas_membership_rows (
 release_key integer NOT NULL REFERENCES public.worldatlas_membership_release_keys(key),
 entity_key integer NOT NULL REFERENCES public.worldatlas_membership_entity_keys(key),
 parent_key integer REFERENCES public.worldatlas_membership_entity_keys(key),
 reference_name text COLLATE "C",active integer NOT NULL CHECK(active IN (0,1)),
 source_key integer NOT NULL REFERENCES public.worldatlas_membership_source_keys(key),
 evidence_key integer NOT NULL REFERENCES public.worldatlas_membership_evidence(key),
 PRIMARY KEY(release_key,entity_key),
 CHECK(reference_name IS NULL OR length(trim(reference_name))>0));
CREATE INDEX worldatlas_membership_parent ON public.worldatlas_membership_rows(release_key,active,parent_key,entity_key);
CREATE INDEX worldatlas_membership_page ON public.worldatlas_membership_rows(release_key,active,entity_key);

CREATE FUNCTION public.worldatlas_membership_append_only() RETURNS trigger
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
 BEGIN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Compact membership storage is append-only'; END $$;
DO $$ DECLARE relation text; BEGIN
 FOREACH relation IN ARRAY ARRAY['worldatlas_membership_release_keys','worldatlas_membership_entity_keys',
 'worldatlas_membership_source_keys','worldatlas_membership_evidence','worldatlas_membership_rows'] LOOP
  EXECUTE format('CREATE TRIGGER worldatlas_membership_immutable BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.worldatlas_membership_append_only()',relation);
  EXECUTE format('CREATE TRIGGER worldatlas_membership_no_truncate BEFORE TRUNCATE ON public.%I FOR EACH STATEMENT EXECUTE FUNCTION public.worldatlas_membership_append_only()',relation);
  EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC',relation);
  IF relation<>'worldatlas_membership_rows' THEN
   EXECUTE format('REVOKE ALL ON SEQUENCE public.%I FROM PUBLIC',relation||'_key_seq');
  END IF;
 END LOOP;
END $$;

-- The schema owner uses this for bounded original-row copy. The application
-- cannot call it directly; only the view trigger calls it after original guards.
CREATE FUNCTION public.worldatlas_membership_save(release_id text,entity_id text,parent_id text,
 reference_name text,active integer,source_id text,evidence text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE release_key integer; entity_key integer; parent_key integer; source_key integer;
 evidence_key integer; raw_original text; evidence_digest bytea;
BEGIN
 INSERT INTO public.worldatlas_membership_release_keys(id) VALUES(release_id) ON CONFLICT DO NOTHING;
 SELECT k.key INTO release_key FROM public.worldatlas_membership_release_keys k WHERE k.id=release_id;
 INSERT INTO public.worldatlas_membership_entity_keys(id) VALUES(entity_id) ON CONFLICT DO NOTHING;
 SELECT k.key INTO entity_key FROM public.worldatlas_membership_entity_keys k WHERE k.id=entity_id;
 IF parent_id IS NOT NULL THEN
  INSERT INTO public.worldatlas_membership_entity_keys(id) VALUES(parent_id) ON CONFLICT DO NOTHING;
  SELECT k.key INTO parent_key FROM public.worldatlas_membership_entity_keys k WHERE k.id=parent_id;
 END IF;
 INSERT INTO public.worldatlas_membership_source_keys(id) VALUES(source_id) ON CONFLICT DO NOTHING;
 SELECT k.key INTO source_key FROM public.worldatlas_membership_source_keys k WHERE k.id=source_id;
 evidence_digest:=pg_catalog.sha256(pg_catalog.convert_to(evidence,'UTF8'));
 INSERT INTO public.worldatlas_membership_evidence(digest,raw) VALUES(evidence_digest,evidence) ON CONFLICT DO NOTHING;
 SELECT k.key,k.raw INTO evidence_key,raw_original FROM public.worldatlas_membership_evidence k WHERE k.digest=evidence_digest;
 IF raw_original IS DISTINCT FROM evidence COLLATE "C" THEN
  RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Evidence digest collision or changed original bytes';
 END IF;
 INSERT INTO public.worldatlas_membership_rows VALUES(release_key,entity_key,parent_key,reference_name,active,source_key,evidence_key);
END $$;
REVOKE ALL ON FUNCTION public.worldatlas_membership_save(text,text,text,text,integer,text,text) FROM PUBLIC;

CREATE FUNCTION public.worldatlas_membership_insert() RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 PERFORM public.worldatlas_membership_save(NEW.release_id,NEW.entity_id,NEW.parent_id,
 NEW.reference_name,NEW.active,NEW.source_id,NEW.evidence);
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION public.worldatlas_membership_insert() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.worldatlas_membership_append_only() FROM PUBLIC;

CREATE VIEW public.worldatlas_membership_projection AS
 SELECT r.id AS release_id,e.id AS entity_id,p.id AS parent_id,m.reference_name,m.active,s.id AS source_id,v.raw AS evidence
 FROM public.worldatlas_membership_rows m
 JOIN public.worldatlas_membership_release_keys r ON r.key=m.release_key
 JOIN public.worldatlas_membership_entity_keys e ON e.key=m.entity_key
 LEFT JOIN public.worldatlas_membership_entity_keys p ON p.key=m.parent_key
 JOIN public.worldatlas_membership_source_keys s ON s.key=m.source_key
 JOIN public.worldatlas_membership_evidence v ON v.key=m.evidence_key;
REVOKE ALL ON public.worldatlas_membership_projection FROM PUBLIC;
