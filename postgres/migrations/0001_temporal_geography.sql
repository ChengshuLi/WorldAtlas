-- Forward dated membership/existence contract. Original fourteen tables and source bytes remain unchanged.
-- New claims require a sealed SQL-validated receipt; no caller-supplied success flag.

BEGIN;

CREATE TABLE atlas_temporal_geography_validations (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 ingestion_id TEXT COLLATE "C" NOT NULL UNIQUE REFERENCES atlas_ingestions(id) DEFERRABLE INITIALLY DEFERRED,
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id),
 hierarchy_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(hierarchy_sha256)=64),
 footprints_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(footprints_sha256)=64),
 fingerprint TEXT COLLATE "C" NOT NULL CHECK(length(fingerprint)=64),
 created_at BIGINT NOT NULL,
 CHECK(id=ingestion_id)
);

CREATE TABLE atlas_geographic_membership_records (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 entity_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_entities(id),
 valid_from atlas_year_start NOT NULL,
 valid_to atlas_year_end NOT NULL,
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 method TEXT COLLATE "C" NOT NULL CHECK(method IN ('direct','derived','reference')),
 status TEXT COLLATE "C" NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 parent_id TEXT COLLATE "C" REFERENCES atlas_entities(id),
 CHECK(status NOT IN ('unknown','disputed') OR parent_id IS NULL),
 CHECK(valid_from<valid_to)
);

CREATE INDEX temporal_memberships_dates ON atlas_geographic_membership_records(release_id,entity_id,valid_from,valid_to,id);
CREATE INDEX temporal_memberships_validation ON atlas_geographic_membership_records(validation_id,entity_id);

CREATE TABLE atlas_geographic_existence_records (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 entity_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_entities(id),
 valid_from atlas_year_start NOT NULL,
 valid_to atlas_year_end NOT NULL,
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 method TEXT COLLATE "C" NOT NULL CHECK(method IN ('direct','derived','reference')),
 status TEXT COLLATE "C" NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 value TEXT COLLATE "C" NOT NULL CHECK(value IN ('exists','not_exists','unknown')),
 CHECK(status NOT IN ('unknown','disputed') OR value='unknown'),
 CHECK(valid_from<valid_to)
);

CREATE INDEX temporal_existence_dates ON atlas_geographic_existence_records(release_id,entity_id,valid_from,valid_to,id);
CREATE INDEX temporal_existence_validation ON atlas_geographic_existence_records(validation_id,entity_id);

CREATE TABLE atlas_temporal_geography_retirements (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 collection TEXT COLLATE "C" NOT NULL CHECK(collection IN ('memberships','existence')),
 target_id TEXT COLLATE "C" NOT NULL CHECK(length(trim(target_id))>0),
 replacement_id TEXT COLLATE "C" CHECK(replacement_id IS NULL OR (length(trim(replacement_id))>0 AND replacement_id<>target_id)),
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 reason TEXT COLLATE "C" NOT NULL CHECK(length(trim(reason))>0),
 release_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT COLLATE "C" NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 UNIQUE(collection,target_id)
);

CREATE INDEX temporal_retirement_release ON atlas_temporal_geography_retirements(release_id,id);
CREATE INDEX temporal_retirement_validation ON atlas_temporal_geography_retirements(validation_id,collection,target_id);

CREATE FUNCTION atlas_temporal_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previous jsonb; incoming jsonb:=to_jsonb(NEW);
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal evidence is append-only'; END IF;
 PERFORM pg_advisory_xact_lock(807245315,1);
 EXECUTE format('SELECT to_jsonb(r) FROM %I r WHERE id=$1',TG_TABLE_NAME) INTO previous USING NEW.id;
 IF TG_TABLE_NAME='atlas_temporal_geography_validations' THEN previous:=previous-'created_at'; incoming:=incoming-'created_at'; END IF;
 IF previous IS NOT NULL THEN IF previous IS DISTINCT FROM incoming THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Stable temporal identity collision'; END IF; RETURN NULL; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas_temporal_memberships_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_membership_records WHERE id=NEW.id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal validation receipt is sealed'; END IF;
 IF NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id JOIN atlas_entity_types t ON t.id=e.kind WHERE m.release_id=NEW.release_id AND m.entity_id=NEW.entity_id AND m.active=1 AND t.geographic_level IS NOT NULL) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Claim requires an approved geographic identity'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to OR (s.status='example' AND NEW.is_example=0) OR s.status='estimate' OR (s.status='reference' AND NEW.method<>'reference'))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Unsupported geographic source interval/class'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to) OR (e.is_example=1 AND NEW.is_example=0))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Claim exceeds identity lifetime/example isolation'; END IF;
 IF NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE collection='memberships' AND target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_geographic_membership_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.entity_id=NEW.entity_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Overlapping equal-precedence geographic claims'; END IF;
 IF NEW.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_entities e JOIN atlas_entity_types et ON et.id=e.kind JOIN atlas_geographic_memberships p ON p.release_id=NEW.release_id AND p.entity_id=NEW.parent_id AND p.active=1 JOIN atlas_entities pe ON pe.id=p.entity_id JOIN atlas_entity_types pt ON pt.id=pe.kind WHERE e.id=NEW.entity_id AND pt.geographic_level=et.geographic_level+1 AND (NEW.is_example=1 OR pe.is_example=0) AND (pe.valid_from IS NULL OR NEW.valid_from>=pe.valid_from) AND (pe.valid_to IS NULL OR NEW.valid_to<=pe.valid_to)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Parent must be an approved adjacent-tier identity within its lifetime'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_entities WHERE id=NEW.entity_id AND kind='continent') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Continents cannot acquire dated parents'; END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER atlas_00_temporal_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_geographic_membership_records FOR EACH ROW EXECUTE FUNCTION atlas_temporal_identity_guard();
CREATE TRIGGER atlas_10_temporal_contract BEFORE INSERT ON atlas_geographic_membership_records FOR EACH ROW EXECUTE FUNCTION atlas_temporal_memberships_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_geographic_membership_records FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_temporal_existence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_existence_records WHERE id=NEW.id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal validation receipt is sealed'; END IF;
 IF NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id JOIN atlas_entity_types t ON t.id=e.kind WHERE m.release_id=NEW.release_id AND m.entity_id=NEW.entity_id AND m.active=1 AND t.geographic_level IS NOT NULL) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Claim requires an approved geographic identity'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to OR (s.status='example' AND NEW.is_example=0) OR s.status='estimate' OR (s.status='reference' AND NEW.method<>'reference'))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Unsupported geographic source interval/class'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to) OR (e.is_example=1 AND NEW.is_example=0))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Claim exceeds identity lifetime/example isolation'; END IF;
 IF NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE collection='existence' AND target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_geographic_existence_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.entity_id=NEW.entity_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='existence' AND t.target_id=r.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Overlapping equal-precedence geographic claims'; END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER atlas_00_temporal_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_geographic_existence_records FOR EACH ROW EXECUTE FUNCTION atlas_temporal_identity_guard();
CREATE TRIGGER atlas_10_temporal_contract BEFORE INSERT ON atlas_geographic_existence_records FOR EACH ROW EXECUTE FUNCTION atlas_temporal_existence_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_geographic_existence_records FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_temporal_retirements_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE id=NEW.id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal validation receipt is sealed'; END IF;
 IF NOT EXISTS(SELECT 1 FROM (SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_membership_records WHERE NEW.collection='memberships' UNION ALL SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_existence_records WHERE NEW.collection='existence') c WHERE c.id=NEW.target_id AND c.release_id=NEW.release_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Retired geographic claim must exist in the same release'; END IF;
 IF EXISTS(SELECT 1 FROM (SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_membership_records WHERE NEW.collection='memberships' UNION ALL SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_existence_records WHERE NEW.collection='existence') c JOIN atlas_sources s ON s.id=NEW.source_id WHERE c.id=NEW.target_id AND ((s.status='example' AND c.is_example=0) OR s.supported_from>c.valid_from OR s.supported_to<c.valid_to)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Withdrawal source must support the target interval and factual status'; END IF;
 IF EXISTS(WITH RECURSIVE chain(id) AS (SELECT NEW.replacement_id WHERE NEW.replacement_id IS NOT NULL UNION SELECT t.replacement_id FROM atlas_temporal_geography_retirements t JOIN chain c ON t.target_id=c.id WHERE t.collection=NEW.collection AND t.replacement_id IS NOT NULL) SELECT 1 FROM chain WHERE id=NEW.target_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic supersession cycle'; END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER atlas_00_temporal_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_temporal_geography_retirements FOR EACH ROW EXECUTE FUNCTION atlas_temporal_identity_guard();
CREATE TRIGGER atlas_10_temporal_contract BEFORE INSERT ON atlas_temporal_geography_retirements FOR EACH ROW EXECUTE FUNCTION atlas_temporal_retirements_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_temporal_geography_retirements FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_temporal_validations_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM atlas_ingestions WHERE id=NEW.ingestion_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal validation must precede a new tracked ingestion'; END IF;
 IF NOT EXISTS(SELECT 1 FROM atlas_geographic_releases r WHERE r.id=NEW.release_id AND r.status='published' AND r.hierarchy_sha256=NEW.hierarchy_sha256 AND r.footprints_sha256=NEW.footprints_sha256 AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases newer WHERE newer.status='published' AND newer.version>r.version)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Published geography does not match transaction pins'; END IF;
 IF EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.validation_id=NEW.id AND t.replacement_id IS NOT NULL AND ((t.collection='memberships' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_membership_records r WHERE r.id=t.replacement_id AND r.release_id=t.release_id)) OR (t.collection='existence' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_existence_records r WHERE r.id=t.replacement_id AND r.release_id=t.release_id)))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Replacement geographic claim is missing'; END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER atlas_00_temporal_identity BEFORE INSERT OR UPDATE OR DELETE ON atlas_temporal_geography_validations FOR EACH ROW EXECUTE FUNCTION atlas_temporal_identity_guard();
CREATE TRIGGER atlas_10_temporal_contract BEFORE INSERT ON atlas_temporal_geography_validations FOR EACH ROW EXECUTE FUNCTION atlas_temporal_validations_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_temporal_geography_validations FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();

CREATE FUNCTION atlas_temporal_chain_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(WITH RECURSIVE
scope AS (SELECT release_id FROM atlas_temporal_geography_validations WHERE id=NEW.id),
seeds(entity_id) AS (
 SELECT entity_id FROM atlas_geographic_membership_records WHERE validation_id=NEW.id
 UNION SELECT entity_id FROM atlas_geographic_existence_records WHERE validation_id=NEW.id
 UNION SELECT r.entity_id FROM atlas_temporal_geography_retirements t JOIN atlas_geographic_membership_records r ON t.collection='memberships' AND r.id=t.target_id WHERE t.validation_id=NEW.id
 UNION SELECT r.entity_id FROM atlas_temporal_geography_retirements t JOIN atlas_geographic_existence_records r ON t.collection='existence' AND r.id=t.target_id WHERE t.validation_id=NEW.id),
edges(entity_id,parent_id) AS (
 SELECT entity_id,parent_id FROM atlas_geographic_memberships WHERE release_id=(SELECT release_id FROM scope) AND active=1 AND parent_id IS NOT NULL
 UNION SELECT r.entity_id,r.parent_id FROM atlas_geographic_membership_records r WHERE r.release_id=(SELECT release_id FROM scope) AND r.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id)),
descendants(entity_id) AS (SELECT entity_id FROM seeds UNION SELECT e.entity_id FROM edges e JOIN descendants d ON e.parent_id=d.entity_id),
ancestors(entity_id) AS (SELECT entity_id FROM descendants UNION SELECT e.parent_id FROM edges e JOIN ancestors a ON e.entity_id=a.entity_id),
refs AS (SELECT m.entity_id,m.parent_id,m.active,e.valid_from,e.valid_to,t.geographic_level AS level FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id JOIN atlas_entity_types t ON t.id=e.kind WHERE m.release_id=(SELECT release_id FROM scope) AND m.entity_id IN (SELECT entity_id FROM ancestors)),
times(year) AS (
 SELECT -3000 UNION SELECT r.valid_from FROM atlas_geographic_membership_records r WHERE r.release_id=(SELECT release_id FROM scope) AND r.entity_id IN (SELECT entity_id FROM ancestors) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id)
 UNION SELECT r.valid_to FROM atlas_geographic_membership_records r WHERE r.release_id=(SELECT release_id FROM scope) AND r.valid_to<=2026 AND r.entity_id IN (SELECT entity_id FROM ancestors) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id)
 UNION SELECT r.valid_from FROM atlas_geographic_existence_records r WHERE r.release_id=(SELECT release_id FROM scope) AND r.entity_id IN (SELECT entity_id FROM ancestors) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='existence' AND t.target_id=r.id)
 UNION SELECT r.valid_to FROM atlas_geographic_existence_records r WHERE r.release_id=(SELECT release_id FROM scope) AND r.valid_to<=2026 AND r.entity_id IN (SELECT entity_id FROM ancestors) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='existence' AND t.target_id=r.id)
 UNION SELECT valid_from FROM refs WHERE valid_from IS NOT NULL UNION SELECT valid_to FROM refs WHERE valid_to IS NOT NULL AND valid_to<=2026),
cells AS (SELECT r.entity_id,t.year,x.examples FROM refs r CROSS JOIN times t CROSS JOIN (SELECT 0 AS examples UNION ALL SELECT 1 AS examples) x),
member_candidates AS (SELECT c.*,r.parent_id,ROW_NUMBER() OVER(PARTITION BY c.entity_id,c.year,c.examples ORDER BY CASE WHEN r.id IS NULL THEN 1000 ELSE r.is_example*100+CASE r.method WHEN 'direct' THEN 0 WHEN 'derived' THEN 10 ELSE 20 END END,r.id) AS rn FROM cells c LEFT JOIN atlas_geographic_membership_records r ON r.entity_id=c.entity_id AND r.release_id=(SELECT release_id FROM scope) AND r.valid_from<=c.year AND r.valid_to>c.year AND r.is_example<=c.examples AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id)),
existence_candidates AS (SELECT c.*,r.value,ROW_NUMBER() OVER(PARTITION BY c.entity_id,c.year,c.examples ORDER BY CASE WHEN r.id IS NULL THEN 1000 ELSE r.is_example*100+CASE r.method WHEN 'direct' THEN 0 WHEN 'derived' THEN 10 ELSE 20 END END,r.id) AS rn FROM cells c LEFT JOIN atlas_geographic_existence_records r ON r.entity_id=c.entity_id AND r.release_id=(SELECT release_id FROM scope) AND r.valid_from<=c.year AND r.valid_to>c.year AND r.is_example<=c.examples AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='existence' AND t.target_id=r.id)),
resolved AS (SELECT c.entity_id,c.year,c.examples,r.level,coalesce(m.parent_id,r.parent_id) AS parent_id,CASE WHEN r.active=1 AND (r.valid_from IS NULL OR r.valid_from<=c.year) AND (r.valid_to IS NULL OR r.valid_to>c.year) AND coalesce(e.value,'unknown')<>'not_exists' THEN 1 ELSE 0 END AS present FROM cells c JOIN refs r ON r.entity_id=c.entity_id JOIN member_candidates m ON m.entity_id=c.entity_id AND m.year=c.year AND m.examples=c.examples AND m.rn=1 JOIN existence_candidates e ON e.entity_id=c.entity_id AND e.year=c.year AND e.examples=c.examples AND e.rn=1)
SELECT 1 FROM resolved r LEFT JOIN resolved p ON p.entity_id=r.parent_id AND p.year=r.year AND p.examples=r.examples WHERE r.present=1 AND ((r.level=5 AND r.parent_id IS NOT NULL) OR (r.level<5 AND (p.entity_id IS NULL OR p.present<>1 OR p.level<>r.level+1))) LIMIT 1) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal geography has a disconnected present chain at an affected transition'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER atlas_temporal_chain_validate AFTER INSERT ON atlas_temporal_geography_validations FOR EACH ROW EXECUTE FUNCTION atlas_temporal_chain_guard();

CREATE FUNCTION atlas_temporal_ingestion_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM atlas_temporal_geography_validations v WHERE v.ingestion_id=NEW.id AND (v.fingerprint<>NEW.fingerprint OR json_extract(NEW.counts,'$._temporal_geography_validation_id') IS DISTINCT FROM v.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Temporal ingestion does not match its SQL validation receipt'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER atlas_temporal_ingestion_complete BEFORE INSERT ON atlas_ingestions FOR EACH ROW EXECUTE FUNCTION atlas_temporal_ingestion_guard();

COMMIT;
