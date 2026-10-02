-- Forward complete footprint catalog and dated selections. No geometry bytes in SQL.
-- Catalog writes are maintainer-only; ordinary runtime can only select published products.


BEGIN;

CREATE TABLE atlas_footprint_versions (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id), source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 supported_from atlas_year_start NOT NULL,
 supported_to atlas_year_end NOT NULL,
 manifest_media_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_media(id), receipt_media_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_media(id),
 footprints_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(footprints_sha256)=64 AND footprints_sha256 ~ '^[a-f0-9]{64}$'), location_ids_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(location_ids_sha256)=64 AND location_ids_sha256 ~ '^[a-f0-9]{64}$'), dictionary_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(dictionary_sha256)=64 AND dictionary_sha256 ~ '^[a-f0-9]{64}$'), grid_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(grid_sha256)=64 AND grid_sha256 ~ '^[a-f0-9]{64}$'),
 footprint_hash_algorithm TEXT COLLATE "C" NOT NULL CHECK(footprint_hash_algorithm='sha256-canonical-json-location-geometry-sha256-v1'),
 grid_size BIGINT NOT NULL CHECK(grid_size>=256 AND grid_size<=1048576), location_count BIGINT NOT NULL CHECK(location_count BETWEEN 1 AND 1000000),
 object_count BIGINT NOT NULL CHECK(object_count BETWEEN 5 AND 512), producer_key_id TEXT COLLATE "C" NOT NULL CHECK(length(trim(producer_key_id))>0),
 status TEXT COLLATE "C" NOT NULL CHECK(status IN ('staged','published')), verified_receipt_sha256 TEXT COLLATE "C", published_at BIGINT,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(supported_from<supported_to), CHECK(manifest_media_id<>receipt_media_id),
 CHECK((status='staged' AND verified_receipt_sha256 IS NULL AND published_at IS NULL) OR (status='published' AND verified_receipt_sha256 IS NOT NULL AND length(verified_receipt_sha256)=64 AND published_at IS NOT NULL))
);

CREATE TABLE atlas_footprint_version_objects (
 version_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_footprint_versions(id), media_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_media(id),
 role TEXT COLLATE "C" NOT NULL CHECK(role IN ('source_archive','reconciled_geometry','coverage_mask','rows','runs')),
 sha256 TEXT COLLATE "C" NOT NULL CHECK(length(sha256)=64 AND sha256 ~ '^[a-f0-9]{64}$'), bytes BIGINT NOT NULL CHECK(bytes BETWEEN 1 AND 20971520),
 "offset" BIGINT, words BIGINT, encoding TEXT COLLATE "C", decoded_sha256 TEXT COLLATE "C", decoded_bytes BIGINT,
 PRIMARY KEY(version_id,media_id),
 CHECK((role IN ('rows','runs') AND "offset" IS NOT NULL AND words IS NOT NULL AND encoding IS NOT NULL AND decoded_sha256 IS NOT NULL AND decoded_bytes IS NOT NULL AND "offset">=0 AND words>0 AND words<=4194304 AND encoding='gzip-u32le' AND length(decoded_sha256)=64 AND decoded_bytes=words*4) OR (role NOT IN ('rows','runs') AND "offset" IS NULL AND words IS NULL AND encoding IS NULL AND decoded_sha256 IS NULL AND decoded_bytes IS NULL))
);

CREATE TABLE atlas_footprint_selection_validations (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), ingestion_id TEXT COLLATE "C" NOT NULL UNIQUE REFERENCES atlas_ingestions(id) DEFERRABLE INITIALLY DEFERRED,
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id), hierarchy_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(hierarchy_sha256)=64 AND hierarchy_sha256 ~ '^[a-f0-9]{64}$'), footprints_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(footprints_sha256)=64 AND footprints_sha256 ~ '^[a-f0-9]{64}$'), fingerprint TEXT COLLATE "C" NOT NULL CHECK(length(fingerprint)=64 AND fingerprint ~ '^[a-f0-9]{64}$'), created_at BIGINT NOT NULL,
 CHECK(id=ingestion_id)
);

CREATE TABLE atlas_geographic_footprint_records (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), version_id TEXT COLLATE "C" REFERENCES atlas_footprint_versions(id), release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id),
 valid_from atlas_year_start NOT NULL, valid_to atlas_year_end NOT NULL, source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 method TEXT COLLATE "C" NOT NULL CHECK(method IN ('direct','derived','reference')), status TEXT COLLATE "C" NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)), validation_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_footprint_selection_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'), CHECK(valid_from<valid_to), CHECK(status NOT IN ('unknown','disputed') OR version_id IS NULL)
);

CREATE TABLE atlas_footprint_retirements (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), target_id TEXT COLLATE "C" NOT NULL UNIQUE REFERENCES atlas_geographic_footprint_records(id),
 replacement_id TEXT COLLATE "C" REFERENCES atlas_geographic_footprint_records(id) DEFERRABLE INITIALLY DEFERRED, source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id), reason TEXT COLLATE "C" NOT NULL CHECK(length(trim(reason))>0),
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id), validation_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_footprint_selection_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'), CHECK(replacement_id IS NULL OR replacement_id<>target_id)
);

CREATE INDEX footprint_version_release ON atlas_footprint_versions(release_id,status,id);

CREATE INDEX footprint_selection_dates ON atlas_geographic_footprint_records(release_id,valid_from,valid_to,id);

CREATE INDEX footprint_selection_validation ON atlas_geographic_footprint_records(validation_id,id);

CREATE INDEX footprint_retirement_validation ON atlas_footprint_retirements(validation_id,id);

CREATE FUNCTION atlas_footprint_versions_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE retained atlas_footprint_versions%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 IF TG_OP='INSERT' THEN
  SELECT * INTO retained FROM atlas_footprint_versions WHERE id=NEW.id;
  IF FOUND THEN IF to_jsonb(retained)=to_jsonb(NEW) THEN RETURN NULL; ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Immutable footprint identity collision'; END IF; END IF;
  RETURN NEW;
 END IF;
 IF TG_OP='UPDATE' AND (OLD.status='staged' AND NEW.status='published' AND NEW.verified_receipt_sha256=(SELECT sha256 FROM atlas_media WHERE id=OLD.receipt_media_id) AND NEW.published_at IS NOT NULL AND (SELECT count(*) FROM atlas_footprint_version_objects WHERE version_id=OLD.id)=OLD.object_count) AND NEW."id" IS NOT DISTINCT FROM OLD."id" AND NEW."release_id" IS NOT DISTINCT FROM OLD."release_id" AND NEW."source_id" IS NOT DISTINCT FROM OLD."source_id" AND NEW."supported_from" IS NOT DISTINCT FROM OLD."supported_from" AND NEW."supported_to" IS NOT DISTINCT FROM OLD."supported_to" AND NEW."manifest_media_id" IS NOT DISTINCT FROM OLD."manifest_media_id" AND NEW."receipt_media_id" IS NOT DISTINCT FROM OLD."receipt_media_id" AND NEW."footprints_sha256" IS NOT DISTINCT FROM OLD."footprints_sha256" AND NEW."location_ids_sha256" IS NOT DISTINCT FROM OLD."location_ids_sha256" AND NEW."dictionary_sha256" IS NOT DISTINCT FROM OLD."dictionary_sha256" AND NEW."grid_sha256" IS NOT DISTINCT FROM OLD."grid_sha256" AND NEW."footprint_hash_algorithm" IS NOT DISTINCT FROM OLD."footprint_hash_algorithm" AND NEW."grid_size" IS NOT DISTINCT FROM OLD."grid_size" AND NEW."location_count" IS NOT DISTINCT FROM OLD."location_count" AND NEW."object_count" IS NOT DISTINCT FROM OLD."object_count" AND NEW."producer_key_id" IS NOT DISTINCT FROM OLD."producer_key_id" AND NEW."metadata" IS NOT DISTINCT FROM OLD."metadata" THEN RETURN NEW; END IF;
 RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint evidence and published catalog are immutable';
END $$;
CREATE TRIGGER atlas_00_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_footprint_versions FOR EACH ROW EXECUTE FUNCTION atlas_footprint_versions_identity_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_footprint_versions FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_footprint_version_objects_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE retained atlas_footprint_version_objects%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 IF TG_OP='INSERT' THEN
  SELECT * INTO retained FROM atlas_footprint_version_objects WHERE version_id=NEW.version_id AND media_id=NEW.media_id;
  IF FOUND THEN IF to_jsonb(retained)=to_jsonb(NEW) THEN RETURN NULL; ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Immutable footprint identity collision'; END IF; END IF;
  RETURN NEW;
 END IF;
 
 RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint evidence and published catalog are immutable';
END $$;
CREATE TRIGGER atlas_00_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_footprint_version_objects FOR EACH ROW EXECUTE FUNCTION atlas_footprint_version_objects_identity_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_footprint_version_objects FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_footprint_selection_validations_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE retained atlas_footprint_selection_validations%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 IF TG_OP='INSERT' THEN
  SELECT * INTO retained FROM atlas_footprint_selection_validations WHERE id=NEW.id;
  IF FOUND THEN IF to_jsonb(retained)=to_jsonb(NEW) THEN RETURN NULL; ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Immutable footprint identity collision'; END IF; END IF;
  RETURN NEW;
 END IF;
 
 RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint evidence and published catalog are immutable';
END $$;
CREATE TRIGGER atlas_00_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_footprint_selection_validations FOR EACH ROW EXECUTE FUNCTION atlas_footprint_selection_validations_identity_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_footprint_selection_validations FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_geographic_footprint_records_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE retained atlas_geographic_footprint_records%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 IF TG_OP='INSERT' THEN
  SELECT * INTO retained FROM atlas_geographic_footprint_records WHERE id=NEW.id;
  IF FOUND THEN IF to_jsonb(retained)=to_jsonb(NEW) THEN RETURN NULL; ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Immutable footprint identity collision'; END IF; END IF;
  RETURN NEW;
 END IF;
 
 RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint evidence and published catalog are immutable';
END $$;
CREATE TRIGGER atlas_00_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_geographic_footprint_records FOR EACH ROW EXECUTE FUNCTION atlas_geographic_footprint_records_identity_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_geographic_footprint_records FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_footprint_retirements_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE retained atlas_footprint_retirements%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 IF TG_OP='INSERT' THEN
  SELECT * INTO retained FROM atlas_footprint_retirements WHERE id=NEW.id;
  IF FOUND THEN IF to_jsonb(retained)=to_jsonb(NEW) THEN RETURN NULL; ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Immutable footprint identity collision'; END IF; END IF;
  RETURN NEW;
 END IF;
 
 RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint evidence and published catalog are immutable';
END $$;
CREATE TRIGGER atlas_00_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_footprint_retirements FOR EACH ROW EXECUTE FUNCTION atlas_footprint_retirements_identity_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_footprint_retirements FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_footprint_guard_0() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS(SELECT 1 FROM atlas_sources s JOIN atlas_geographic_releases r ON r.id=NEW.release_id WHERE s.id=NEW.source_id AND s.status<>'example' AND r.status='published' AND NEW.supported_from>=s.supported_from AND NEW.supported_to<=s.supported_to) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint source interval or published release is unsupported'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_0 BEFORE INSERT ON atlas_footprint_versions FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_0();

CREATE FUNCTION atlas_footprint_guard_1() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS(SELECT 1 FROM atlas_media m JOIN atlas_footprint_versions v ON v.id=NEW.version_id WHERE m.id=NEW.media_id AND m.sha256=NEW.sha256 AND m.bytes=NEW.bytes AND m.object_key='media/'||m.sha256 AND m.status IN ('ready','published') AND v.status='staged') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint object registry or staging context is invalid'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_1 BEFORE INSERT ON atlas_footprint_version_objects FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_1();

CREATE FUNCTION atlas_footprint_guard_2() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (NEW.is_example=1 OR s.status<>'example') AND (s.status<>'reference' OR NEW.method='reference') AND (NEW.status<>'reference' OR NEW.method='reference') AND (NEW.is_example=1 OR NEW.status<>'example')) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint claim source bounds or class invalid'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_2 BEFORE INSERT ON atlas_geographic_footprint_records FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_2();

CREATE FUNCTION atlas_footprint_guard_3() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_footprint_versions v WHERE v.id=NEW.version_id AND v.release_id=NEW.release_id AND v.status='published' AND NEW.valid_from>=v.supported_from AND NEW.valid_to<=v.supported_to) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Unpublished or unsupported footprint version'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_3 BEFORE INSERT ON atlas_geographic_footprint_records FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_3();

CREATE FUNCTION atlas_footprint_guard_4() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.id=NEW.validation_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint validation receipt is already sealed'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_4 BEFORE INSERT ON atlas_geographic_footprint_records FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_4();

CREATE FUNCTION atlas_footprint_guard_5() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_footprint_retirements t WHERE t.target_id=r.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Equal-precedence footprint intervals overlap'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_5 BEFORE INSERT ON atlas_geographic_footprint_records FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_5();

CREATE FUNCTION atlas_footprint_guard_6() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.id=NEW.validation_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint validation receipt is already sealed'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_6 BEFORE INSERT ON atlas_footprint_retirements FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_6();

CREATE FUNCTION atlas_footprint_guard_7() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r JOIN atlas_sources s ON s.id=NEW.source_id WHERE r.id=NEW.target_id AND r.release_id=NEW.release_id AND (r.is_example=1 OR s.status<>'example') AND (r.is_example=1 OR s.status<>'reference' OR r.method='reference') AND s.supported_from<=r.valid_from AND s.supported_to>=r.valid_to) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint withdrawal must have supported retained target'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_7 BEFORE INSERT ON atlas_footprint_retirements FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_7();

CREATE FUNCTION atlas_footprint_guard_8() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS(SELECT 1 FROM atlas_geographic_releases r WHERE r.id=NEW.release_id AND r.status='published' AND r.hierarchy_sha256=NEW.hierarchy_sha256 AND r.footprints_sha256=NEW.footprints_sha256 AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases n WHERE n.status='published' AND n.version>r.version)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint selection geographic pins changed'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_8 BEFORE INSERT ON atlas_footprint_selection_validations FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_8();

CREATE FUNCTION atlas_footprint_guard_9() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_ingestions i WHERE i.id=NEW.ingestion_id AND (i.fingerprint<>NEW.fingerprint OR coalesce(json_extract(i.counts,'$._footprint_validation_id'),'')<>NEW.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint ingestion identity mismatch'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_9 BEFORE INSERT ON atlas_footprint_selection_validations FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_9();

CREATE FUNCTION atlas_footprint_guard_10() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r WHERE r.validation_id=NEW.id AND r.release_id<>NEW.release_id) OR EXISTS(SELECT 1 FROM atlas_footprint_retirements r WHERE r.validation_id=NEW.id AND r.release_id<>NEW.release_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint validation release mismatch'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_10 BEFORE INSERT ON atlas_footprint_selection_validations FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_10();

CREATE FUNCTION atlas_footprint_guard_11() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_footprint_retirements t LEFT JOIN atlas_geographic_footprint_records retained_claim ON retained_claim.id=t.target_id LEFT JOIN atlas_geographic_footprint_records n ON n.id=t.replacement_id WHERE t.validation_id=NEW.id AND t.replacement_id IS NOT NULL AND (n.id IS NULL OR n.release_id<>retained_claim.release_id OR n.is_example<>retained_claim.is_example OR EXISTS(SELECT 1 FROM atlas_footprint_retirements w WHERE w.target_id=n.id))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint replacement is missing or invalid'; END IF; RETURN NEW; END $$;
CREATE TRIGGER atlas_10_guard_11 BEFORE INSERT ON atlas_footprint_selection_validations FOR EACH ROW EXECUTE FUNCTION atlas_footprint_guard_11();

CREATE FUNCTION atlas_footprint_ingestion_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.ingestion_id=NEW.id AND (v.fingerprint<>NEW.fingerprint OR coalesce(json_extract(NEW.counts,'$._footprint_validation_id'),'')<>v.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Footprint ingestion receipt mismatch'; END IF; RETURN NEW; END $$; CREATE TRIGGER atlas_footprint_ingestion_guard BEFORE INSERT ON atlas_ingestions FOR EACH ROW EXECUTE FUNCTION atlas_footprint_ingestion_guard();

DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='worldatlas_app') THEN GRANT SELECT ON atlas_footprint_versions,atlas_footprint_version_objects TO worldatlas_app; GRANT SELECT,INSERT ON atlas_footprint_selection_validations,atlas_geographic_footprint_records,atlas_footprint_retirements TO worldatlas_app; END IF; END $$;

COMMIT;
