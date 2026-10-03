-- Additive typed evidence storage. Empty schema only; no factual rows or legacy rewrites.
-- Applying this migration is an explicit owner operation, never a normal merge.
BEGIN;
CREATE TABLE atlas_typed_observations (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 subject_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(subject_id))>0),
 subject_kind TEXT COLLATE "C" NOT NULL CHECK(length(trim(subject_kind))>0),
 field_id TEXT COLLATE "C" NOT NULL CHECK(length(trim(field_id))>0),
 value TEXT COLLATE "C" NOT NULL CHECK(json_valid(value)),
 contract_version BIGINT NOT NULL CHECK(contract_version=1),
 registry_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(registry_sha256)=64 AND registry_sha256 ~ '^[a-f0-9]{64}$'),
 valid_from atlas_year_start NOT NULL,
 valid_to atlas_year_end NOT NULL,
 method TEXT COLLATE "C" NOT NULL CHECK(method IN ('direct','derived','reference','estimate')),
 status TEXT COLLATE "C" NOT NULL CHECK(status IN ('sourced','derived','reference','estimate','example','unknown','unresolved','disputed','no-majority')),
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 is_example BIGINT NOT NULL CHECK(is_example IN (0,1)),
 metadata TEXT COLLATE "C" NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(valid_to>valid_from),
 CHECK((status IN ('unknown','unresolved','disputed','no-majority'))=(json_type(value)='null'))
);
CREATE INDEX atlas_typed_observations_subject_id_dates ON atlas_typed_observations(subject_id,valid_from,valid_to);
CREATE FUNCTION atlas_typed_observations_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (s.status<>'example' OR NEW.is_example=1) AND (NEW.is_example=1 OR NEW.status IN ('unknown','unresolved','disputed','no-majority') OR ((s.status<>'reference' OR (NEW.method='reference' AND NEW.status='reference')) AND (s.status<>'estimate' OR NEW.status='estimate')))) THEN RAISE EXCEPTION 'Typed evidence exceeds source support or changes source class' USING ERRCODE='23514'; END IF;
 IF (NEW.status='example' AND NEW.is_example=0) OR (NEW.is_example=0 AND NEW.status NOT IN ('unknown','unresolved','disputed','no-majority') AND ((NEW.status='sourced' AND NEW.method<>'direct') OR (NEW.status='derived' AND NEW.method<>'derived') OR (NEW.status='reference' AND NEW.method<>'reference') OR (NEW.method='reference' AND NEW.status<>'reference'))) THEN RAISE EXCEPTION 'Typed evidence method/status mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.subject_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0) AND e.kind=NEW.subject_kind) THEN RAISE EXCEPTION 'Typed endpoint identity, lifetime or example mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER atlas_typed_observations_guard BEFORE INSERT ON atlas_typed_observations FOR EACH ROW EXECUTE FUNCTION atlas_typed_observations_guard();
CREATE TABLE atlas_typed_feature_links (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 source_entity_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(source_entity_id))>0),
 target_entity_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(target_entity_id))>0),
 relationship_type TEXT COLLATE "C" NOT NULL CHECK(length(trim(relationship_type))>0),
 contract_version BIGINT NOT NULL CHECK(contract_version=1),
 registry_sha256 TEXT COLLATE "C" NOT NULL CHECK(length(registry_sha256)=64 AND registry_sha256 ~ '^[a-f0-9]{64}$'),
 valid_from atlas_year_start NOT NULL,
 valid_to atlas_year_end NOT NULL,
 method TEXT COLLATE "C" NOT NULL CHECK(method IN ('direct','derived','reference','estimate')),
 status TEXT COLLATE "C" NOT NULL CHECK(status IN ('sourced','derived','reference','estimate','example','unknown','unresolved','disputed','no-majority')),
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 is_example BIGINT NOT NULL CHECK(is_example IN (0,1)),
 metadata TEXT COLLATE "C" NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(valid_to>valid_from)
);
CREATE INDEX atlas_typed_feature_links_source_entity_id_dates ON atlas_typed_feature_links(source_entity_id,valid_from,valid_to);
CREATE INDEX atlas_typed_feature_links_target_entity_id_dates ON atlas_typed_feature_links(target_entity_id,valid_from,valid_to);
CREATE FUNCTION atlas_typed_feature_links_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (s.status<>'example' OR NEW.is_example=1) AND (NEW.is_example=1 OR NEW.status IN ('unknown','unresolved','disputed','no-majority') OR ((s.status<>'reference' OR (NEW.method='reference' AND NEW.status='reference')) AND (s.status<>'estimate' OR NEW.status='estimate')))) THEN RAISE EXCEPTION 'Typed evidence exceeds source support or changes source class' USING ERRCODE='23514'; END IF;
 IF (NEW.status='example' AND NEW.is_example=0) OR (NEW.is_example=0 AND NEW.status NOT IN ('unknown','unresolved','disputed','no-majority') AND ((NEW.status='sourced' AND NEW.method<>'direct') OR (NEW.status='derived' AND NEW.method<>'derived') OR (NEW.status='reference' AND NEW.method<>'reference') OR (NEW.method='reference' AND NEW.status<>'reference'))) THEN RAISE EXCEPTION 'Typed evidence method/status mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.source_entity_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0)) THEN RAISE EXCEPTION 'Typed endpoint identity, lifetime or example mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.target_entity_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0)) THEN RAISE EXCEPTION 'Typed endpoint identity, lifetime or example mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER atlas_typed_feature_links_guard BEFORE INSERT ON atlas_typed_feature_links FOR EACH ROW EXECUTE FUNCTION atlas_typed_feature_links_guard();
CREATE TABLE atlas_typed_retirements (
 id TEXT COLLATE "C" PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 collection TEXT COLLATE "C" NOT NULL CHECK(collection IN ('observations','feature_links')),
 target_id TEXT COLLATE "C" NOT NULL CHECK(length(trim(target_id))>0),
 source_id TEXT COLLATE "C" NOT NULL REFERENCES atlas_sources(id),
 reason TEXT COLLATE "C" NOT NULL CHECK(length(trim(reason))>0),
 replacement_id TEXT COLLATE "C" CHECK(replacement_id IS NULL OR (length(trim(replacement_id))>0 AND replacement_id<>target_id)),
 metadata TEXT COLLATE "C" NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 UNIQUE(collection,target_id)
);
CREATE FUNCTION atlas_typed_retirements_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NOT EXISTS (SELECT 1 FROM atlas_sources WHERE id=NEW.source_id) OR (NEW.collection='observations' AND (NOT EXISTS(SELECT 1 FROM atlas_typed_observations WHERE id=NEW.target_id))) OR (NEW.collection='feature_links' AND (NOT EXISTS(SELECT 1 FROM atlas_typed_feature_links WHERE id=NEW.target_id))) THEN RAISE EXCEPTION 'Missing typed retirement target/source/replacement' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_retirements_guard BEFORE INSERT ON atlas_typed_retirements FOR EACH ROW EXECUTE FUNCTION atlas_typed_retirements_guard();
CREATE FUNCTION atlas_typed_observations_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF TG_OP<>'INSERT' OR EXISTS (SELECT 1 FROM atlas_typed_observations prior_claim WHERE prior_claim.id=NEW.id AND (prior_claim.id IS DISTINCT FROM NEW.id OR prior_claim.subject_id IS DISTINCT FROM NEW.subject_id OR prior_claim.subject_kind IS DISTINCT FROM NEW.subject_kind OR prior_claim.field_id IS DISTINCT FROM NEW.field_id OR prior_claim.value IS DISTINCT FROM NEW.value OR prior_claim.contract_version IS DISTINCT FROM NEW.contract_version OR prior_claim.registry_sha256 IS DISTINCT FROM NEW.registry_sha256 OR prior_claim.valid_from IS DISTINCT FROM NEW.valid_from OR prior_claim.valid_to IS DISTINCT FROM NEW.valid_to OR prior_claim.method IS DISTINCT FROM NEW.method OR prior_claim.status IS DISTINCT FROM NEW.status OR prior_claim.source_id IS DISTINCT FROM NEW.source_id OR prior_claim.is_example IS DISTINCT FROM NEW.is_example OR prior_claim.metadata IS DISTINCT FROM NEW.metadata)) THEN RAISE EXCEPTION 'Typed evidence is immutable; append a retirement/correction' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_observations_immutable BEFORE INSERT OR UPDATE OR DELETE ON atlas_typed_observations FOR EACH ROW EXECUTE FUNCTION atlas_typed_observations_immutable();
CREATE FUNCTION atlas_typed_feature_links_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF TG_OP<>'INSERT' OR EXISTS (SELECT 1 FROM atlas_typed_feature_links prior_claim WHERE prior_claim.id=NEW.id AND (prior_claim.id IS DISTINCT FROM NEW.id OR prior_claim.source_entity_id IS DISTINCT FROM NEW.source_entity_id OR prior_claim.target_entity_id IS DISTINCT FROM NEW.target_entity_id OR prior_claim.relationship_type IS DISTINCT FROM NEW.relationship_type OR prior_claim.contract_version IS DISTINCT FROM NEW.contract_version OR prior_claim.registry_sha256 IS DISTINCT FROM NEW.registry_sha256 OR prior_claim.valid_from IS DISTINCT FROM NEW.valid_from OR prior_claim.valid_to IS DISTINCT FROM NEW.valid_to OR prior_claim.method IS DISTINCT FROM NEW.method OR prior_claim.status IS DISTINCT FROM NEW.status OR prior_claim.source_id IS DISTINCT FROM NEW.source_id OR prior_claim.is_example IS DISTINCT FROM NEW.is_example OR prior_claim.metadata IS DISTINCT FROM NEW.metadata)) THEN RAISE EXCEPTION 'Typed evidence is immutable; append a retirement/correction' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_feature_links_immutable BEFORE INSERT OR UPDATE OR DELETE ON atlas_typed_feature_links FOR EACH ROW EXECUTE FUNCTION atlas_typed_feature_links_immutable();
CREATE FUNCTION atlas_typed_retirements_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF TG_OP<>'INSERT' OR EXISTS (SELECT 1 FROM atlas_typed_retirements prior_claim WHERE (prior_claim.id=NEW.id OR (prior_claim.collection=NEW.collection AND prior_claim.target_id=NEW.target_id)) AND (prior_claim.id IS DISTINCT FROM NEW.id OR prior_claim.collection IS DISTINCT FROM NEW.collection OR prior_claim.target_id IS DISTINCT FROM NEW.target_id OR prior_claim.source_id IS DISTINCT FROM NEW.source_id OR prior_claim.reason IS DISTINCT FROM NEW.reason OR prior_claim.replacement_id IS DISTINCT FROM NEW.replacement_id OR prior_claim.metadata IS DISTINCT FROM NEW.metadata)) THEN RAISE EXCEPTION 'Typed evidence is immutable; append a retirement/correction' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_retirements_immutable BEFORE INSERT OR UPDATE OR DELETE ON atlas_typed_retirements FOR EACH ROW EXECUTE FUNCTION atlas_typed_retirements_immutable();
REVOKE ALL ON FUNCTION atlas_typed_observations_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION atlas_typed_feature_links_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION atlas_typed_retirements_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION atlas_typed_observations_immutable() FROM PUBLIC;
REVOKE ALL ON FUNCTION atlas_typed_feature_links_immutable() FROM PUBLIC;
REVOKE ALL ON FUNCTION atlas_typed_retirements_immutable() FROM PUBLIC;
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_typed_observations FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_typed_feature_links FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();
CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON atlas_typed_retirements FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard();
CREATE FUNCTION atlas_typed_overlap_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NOT EXISTS (SELECT 1 FROM atlas_typed_retirements WHERE collection='observations' AND target_id=NEW.id) AND EXISTS (SELECT 1 FROM atlas_typed_observations c WHERE c.id<>NEW.id AND c.subject_id=NEW.subject_id AND c.field_id=NEW.field_id AND c.method=NEW.method AND c.is_example=NEW.is_example AND c.valid_from<NEW.valid_to AND c.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_typed_retirements r WHERE r.collection='observations' AND r.target_id=c.id)) THEN RAISE EXCEPTION 'Overlapping typed observations' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_overlap_guard BEFORE INSERT ON atlas_typed_observations FOR EACH ROW EXECUTE FUNCTION atlas_typed_overlap_guard();
REVOKE ALL ON FUNCTION atlas_typed_overlap_guard() FROM PUBLIC;
CREATE FUNCTION atlas_typed_retirement_source_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example') AND ((NEW.collection='observations' AND EXISTS(SELECT 1 FROM atlas_typed_observations c WHERE c.id=NEW.target_id AND c.is_example=0)) OR (NEW.collection='feature_links' AND EXISTS(SELECT 1 FROM atlas_typed_feature_links c WHERE c.id=NEW.target_id AND c.is_example=0))) THEN RAISE EXCEPTION 'Example sources cannot retire factual typed claims' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_retirement_source_guard BEFORE INSERT ON atlas_typed_retirements FOR EACH ROW EXECUTE FUNCTION atlas_typed_retirement_source_guard();
REVOKE ALL ON FUNCTION atlas_typed_retirement_source_guard() FROM PUBLIC;
CREATE FUNCTION atlas_typed_ingestion_complete_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS (SELECT 1 FROM atlas_typed_retirements r WHERE r.replacement_id IS NOT NULL AND ((r.collection='observations' AND NOT EXISTS(SELECT 1 FROM atlas_typed_observations c WHERE c.id=r.replacement_id)) OR (r.collection='feature_links' AND NOT EXISTS(SELECT 1 FROM atlas_typed_feature_links c WHERE c.id=r.replacement_id)))) THEN RAISE EXCEPTION 'Typed replacement claim is missing' USING ERRCODE='23514'; END IF; RETURN NEW; END;
$$;
CREATE TRIGGER atlas_typed_ingestion_complete_guard BEFORE INSERT ON atlas_ingestions FOR EACH ROW EXECUTE FUNCTION atlas_typed_ingestion_complete_guard();
REVOKE ALL ON FUNCTION atlas_typed_ingestion_complete_guard() FROM PUBLIC;
COMMIT;
