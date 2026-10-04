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

-- Bounded owner-only copy; one round trip per page, never one per record.
-- Evidence remains a TEXT value inside the transport JSON, including spelling.
CREATE FUNCTION public.worldatlas_membership_copy_batch(payload json) RETURNS integer
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE copied integer;
BEGIN
 IF json_typeof(payload)<>'array' OR json_array_length(payload)>200 OR octet_length(payload::text)>8388608 THEN
  RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Owner membership copy exceeds bounded page';
 END IF;
 INSERT INTO public.worldatlas_membership_release_keys(id)
  SELECT DISTINCT x.release_id FROM json_to_recordset(payload) x(release_id text) ON CONFLICT DO NOTHING;
 INSERT INTO public.worldatlas_membership_entity_keys(id)
  SELECT x.entity_id FROM json_to_recordset(payload) x(entity_id text)
  UNION SELECT x.parent_id FROM json_to_recordset(payload) x(parent_id text) WHERE x.parent_id IS NOT NULL
  ON CONFLICT DO NOTHING;
 INSERT INTO public.worldatlas_membership_source_keys(id)
  SELECT DISTINCT x.source_id FROM json_to_recordset(payload) x(source_id text) ON CONFLICT DO NOTHING;
 INSERT INTO public.worldatlas_membership_evidence(digest,raw)
  SELECT DISTINCT sha256(convert_to(x.evidence,'UTF8')),x.evidence FROM json_to_recordset(payload) x(evidence text)
  ON CONFLICT DO NOTHING;
 IF EXISTS(SELECT 1 FROM json_to_recordset(payload) x(evidence text)
  JOIN public.worldatlas_membership_evidence e ON e.digest=sha256(convert_to(x.evidence,'UTF8'))
  WHERE e.raw IS DISTINCT FROM x.evidence COLLATE "C") THEN
  RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Evidence digest collision or changed original bytes';
 END IF;
 INSERT INTO public.worldatlas_membership_rows
 SELECT r.key,e.key,p.key,x.reference_name,x.active,s.key,v.key
 FROM json_to_recordset(payload) x(release_id text,entity_id text,parent_id text,reference_name text,active integer,source_id text,evidence text)
 JOIN public.worldatlas_membership_release_keys r ON r.id=x.release_id
 JOIN public.worldatlas_membership_entity_keys e ON e.id=x.entity_id
 LEFT JOIN public.worldatlas_membership_entity_keys p ON p.id=x.parent_id
 JOIN public.worldatlas_membership_source_keys s ON s.id=x.source_id
 JOIN public.worldatlas_membership_evidence v ON v.digest=sha256(convert_to(x.evidence,'UTF8'));
 GET DIAGNOSTICS copied=ROW_COUNT;
 IF copied<>json_array_length(payload) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Incomplete owner membership copy'; END IF;
 RETURN copied;
END $$;
REVOKE ALL ON FUNCTION public.worldatlas_membership_copy_batch(json) FROM PUBLIC;

-- Server-side page reader avoids sending all evidence to the client and back.
CREATE FUNCTION public.worldatlas_membership_copy_next(after_release text,after_entity text)
 RETURNS TABLE(copied integer,last_release text,last_entity text)
 LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
DECLARE payload json; page_count integer;
BEGIN
 IF (SELECT relkind FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass)<>'r' THEN
  RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Original physical membership source required';
 END IF;
 WITH candidates AS MATERIALIZED(SELECT release_id,entity_id,parent_id,reference_name,active,source_id,evidence
  FROM public.atlas_geographic_memberships WHERE (release_id,entity_id)>(after_release COLLATE "C",after_entity COLLATE "C")
  ORDER BY release_id,entity_id LIMIT 200),
 bounded AS(SELECT *,sum(256+6*(octet_length(release_id)::bigint+octet_length(entity_id)+coalesce(octet_length(parent_id),0)+coalesce(octet_length(reference_name),0)+octet_length(source_id)+octet_length(evidence)))
  OVER(ORDER BY release_id,entity_id) budget FROM candidates),
 page AS(SELECT release_id,entity_id,parent_id,reference_name,active,source_id,evidence FROM bounded WHERE budget<=8388608)
 SELECT json_agg(row_to_json(page) ORDER BY release_id,entity_id),
  (SELECT count(*)::integer FROM candidates),
  (SELECT release_id FROM page ORDER BY release_id DESC,entity_id DESC LIMIT 1),
  (SELECT entity_id FROM page ORDER BY release_id DESC,entity_id DESC LIMIT 1)
 INTO payload,page_count,last_release,last_entity FROM page;
 IF page_count>0 AND payload IS NULL THEN RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='Original membership row exceeds bounded copy'; END IF;
 copied:=CASE WHEN payload IS NULL THEN 0 ELSE public.worldatlas_membership_copy_batch(payload) END;
 RETURN NEXT;
END $$;
REVOKE ALL ON FUNCTION public.worldatlas_membership_copy_next(text,text) FROM PUBLIC;

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
