-- Additive typed evidence storage. Empty schema only; no factual rows or legacy rewrites.
-- Applying this migration is an explicit owner operation, never a normal merge.
PRAGMA foreign_keys=ON;
CREATE TABLE atlas_typed_observations (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 subject_id TEXT NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(subject_id))>0),
 subject_kind TEXT NOT NULL CHECK(length(trim(subject_kind))>0),
 field_id TEXT NOT NULL CHECK(length(trim(field_id))>0),
 value TEXT NOT NULL CHECK(json_valid(value)),
 contract_version INTEGER NOT NULL CHECK(contract_version=1),
 registry_sha256 TEXT NOT NULL CHECK(length(registry_sha256)=64 AND registry_sha256 NOT GLOB '*[^0-9a-f]*'),
 valid_from INTEGER NOT NULL,
 valid_to INTEGER NOT NULL,
 method TEXT NOT NULL CHECK(method IN ('direct','derived','reference','estimate')),
 status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','estimate','example','unknown','unresolved','disputed','no-majority')),
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 metadata TEXT NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(valid_to>valid_from),
 CHECK(typeof(valid_from)='integer' AND typeof(valid_to)='integer' AND valid_from BETWEEN -3000 AND 2026 AND valid_from<>0 AND valid_to BETWEEN -3000 AND 2027 AND valid_to<>0),
 CHECK((status IN ('unknown','unresolved','disputed','no-majority'))=(json_type(value)='null'))
);
CREATE INDEX atlas_typed_observations_subject_id_dates ON atlas_typed_observations(subject_id,valid_from,valid_to);
CREATE TRIGGER atlas_typed_observations_guard_0 BEFORE INSERT ON atlas_typed_observations
WHEN NOT EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (s.status<>'example' OR NEW.is_example=1) AND (NEW.is_example=1 OR NEW.status IN ('unknown','unresolved','disputed','no-majority') OR ((s.status<>'reference' OR (NEW.method='reference' AND NEW.status='reference')) AND (s.status<>'estimate' OR NEW.status='estimate'))))
BEGIN SELECT RAISE(ABORT,'Typed evidence exceeds source support or changes source class'); END;
CREATE TRIGGER atlas_typed_observations_guard_1 BEFORE INSERT ON atlas_typed_observations
WHEN (NEW.status='example' AND NEW.is_example=0) OR (NEW.is_example=0 AND NEW.status NOT IN ('unknown','unresolved','disputed','no-majority') AND ((NEW.status='sourced' AND NEW.method<>'direct') OR (NEW.status='derived' AND NEW.method<>'derived') OR (NEW.status='reference' AND NEW.method<>'reference') OR (NEW.method='reference' AND NEW.status<>'reference')))
BEGIN SELECT RAISE(ABORT,'Typed evidence method/status mismatch'); END;
CREATE TRIGGER atlas_typed_observations_guard_2 BEFORE INSERT ON atlas_typed_observations
WHEN NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.subject_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0) AND e.kind=NEW.subject_kind)
BEGIN SELECT RAISE(ABORT,'Typed endpoint identity, lifetime or example mismatch'); END;
CREATE TABLE atlas_typed_feature_links (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 source_entity_id TEXT NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(source_entity_id))>0),
 target_entity_id TEXT NOT NULL REFERENCES atlas_entities(id) CHECK(length(trim(target_entity_id))>0),
 relationship_type TEXT NOT NULL CHECK(length(trim(relationship_type))>0),
 contract_version INTEGER NOT NULL CHECK(contract_version=1),
 registry_sha256 TEXT NOT NULL CHECK(length(registry_sha256)=64 AND registry_sha256 NOT GLOB '*[^0-9a-f]*'),
 valid_from INTEGER NOT NULL,
 valid_to INTEGER NOT NULL,
 method TEXT NOT NULL CHECK(method IN ('direct','derived','reference','estimate')),
 status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','estimate','example','unknown','unresolved','disputed','no-majority')),
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 metadata TEXT NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(valid_to>valid_from),
 CHECK(typeof(valid_from)='integer' AND typeof(valid_to)='integer' AND valid_from BETWEEN -3000 AND 2026 AND valid_from<>0 AND valid_to BETWEEN -3000 AND 2027 AND valid_to<>0)
);
CREATE INDEX atlas_typed_feature_links_source_entity_id_dates ON atlas_typed_feature_links(source_entity_id,valid_from,valid_to);
CREATE INDEX atlas_typed_feature_links_target_entity_id_dates ON atlas_typed_feature_links(target_entity_id,valid_from,valid_to);
CREATE TRIGGER atlas_typed_feature_links_guard_0 BEFORE INSERT ON atlas_typed_feature_links
WHEN NOT EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (s.status<>'example' OR NEW.is_example=1) AND (NEW.is_example=1 OR NEW.status IN ('unknown','unresolved','disputed','no-majority') OR ((s.status<>'reference' OR (NEW.method='reference' AND NEW.status='reference')) AND (s.status<>'estimate' OR NEW.status='estimate'))))
BEGIN SELECT RAISE(ABORT,'Typed evidence exceeds source support or changes source class'); END;
CREATE TRIGGER atlas_typed_feature_links_guard_1 BEFORE INSERT ON atlas_typed_feature_links
WHEN (NEW.status='example' AND NEW.is_example=0) OR (NEW.is_example=0 AND NEW.status NOT IN ('unknown','unresolved','disputed','no-majority') AND ((NEW.status='sourced' AND NEW.method<>'direct') OR (NEW.status='derived' AND NEW.method<>'derived') OR (NEW.status='reference' AND NEW.method<>'reference') OR (NEW.method='reference' AND NEW.status<>'reference')))
BEGIN SELECT RAISE(ABORT,'Typed evidence method/status mismatch'); END;
CREATE TRIGGER atlas_typed_feature_links_guard_2 BEFORE INSERT ON atlas_typed_feature_links
WHEN NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.source_entity_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0))
BEGIN SELECT RAISE(ABORT,'Typed endpoint identity, lifetime or example mismatch'); END;
CREATE TRIGGER atlas_typed_feature_links_guard_3 BEFORE INSERT ON atlas_typed_feature_links
WHEN NOT EXISTS (SELECT 1 FROM atlas_entities e WHERE e.id=NEW.target_entity_id AND (e.valid_from IS NULL OR NEW.valid_from>=e.valid_from) AND (e.valid_to IS NULL OR NEW.valid_to<=e.valid_to) AND (NEW.is_example=1 OR e.is_example=0))
BEGIN SELECT RAISE(ABORT,'Typed endpoint identity, lifetime or example mismatch'); END;
CREATE TABLE atlas_typed_retirements (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 collection TEXT NOT NULL CHECK(collection IN ('observations','feature_links')),
 target_id TEXT NOT NULL CHECK(length(trim(target_id))>0),
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 replacement_id TEXT CHECK(replacement_id IS NULL OR (length(trim(replacement_id))>0 AND replacement_id<>target_id)),
 metadata TEXT NOT NULL CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 UNIQUE(collection,target_id)
);
CREATE TRIGGER atlas_typed_retirements_guard BEFORE INSERT ON atlas_typed_retirements
WHEN NOT EXISTS (SELECT 1 FROM atlas_sources WHERE id=NEW.source_id) OR (NEW.collection='observations' AND (NOT EXISTS(SELECT 1 FROM atlas_typed_observations WHERE id=NEW.target_id))) OR (NEW.collection='feature_links' AND (NOT EXISTS(SELECT 1 FROM atlas_typed_feature_links WHERE id=NEW.target_id)))
BEGIN SELECT RAISE(ABORT,'Missing typed retirement target/source/replacement'); END;
CREATE TRIGGER atlas_typed_observations_collision BEFORE INSERT ON atlas_typed_observations WHEN EXISTS (SELECT 1 FROM atlas_typed_observations old WHERE old.id=NEW.id AND (old.id IS NOT NEW.id OR old.subject_id IS NOT NEW.subject_id OR old.subject_kind IS NOT NEW.subject_kind OR old.field_id IS NOT NEW.field_id OR old.value IS NOT NEW.value OR old.contract_version IS NOT NEW.contract_version OR old.registry_sha256 IS NOT NEW.registry_sha256 OR old.valid_from IS NOT NEW.valid_from OR old.valid_to IS NOT NEW.valid_to OR old.method IS NOT NEW.method OR old.status IS NOT NEW.status OR old.source_id IS NOT NEW.source_id OR old.is_example IS NOT NEW.is_example OR old.metadata IS NOT NEW.metadata))
BEGIN SELECT RAISE(ABORT,'Typed identity already identifies different evidence'); END;
CREATE TRIGGER atlas_typed_observations_no_update BEFORE UPDATE ON atlas_typed_observations
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_observations_no_delete BEFORE DELETE ON atlas_typed_observations
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_feature_links_collision BEFORE INSERT ON atlas_typed_feature_links WHEN EXISTS (SELECT 1 FROM atlas_typed_feature_links old WHERE old.id=NEW.id AND (old.id IS NOT NEW.id OR old.source_entity_id IS NOT NEW.source_entity_id OR old.target_entity_id IS NOT NEW.target_entity_id OR old.relationship_type IS NOT NEW.relationship_type OR old.contract_version IS NOT NEW.contract_version OR old.registry_sha256 IS NOT NEW.registry_sha256 OR old.valid_from IS NOT NEW.valid_from OR old.valid_to IS NOT NEW.valid_to OR old.method IS NOT NEW.method OR old.status IS NOT NEW.status OR old.source_id IS NOT NEW.source_id OR old.is_example IS NOT NEW.is_example OR old.metadata IS NOT NEW.metadata))
BEGIN SELECT RAISE(ABORT,'Typed identity already identifies different evidence'); END;
CREATE TRIGGER atlas_typed_feature_links_no_update BEFORE UPDATE ON atlas_typed_feature_links
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_feature_links_no_delete BEFORE DELETE ON atlas_typed_feature_links
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_retirements_collision BEFORE INSERT ON atlas_typed_retirements WHEN EXISTS (SELECT 1 FROM atlas_typed_retirements old WHERE (old.id=NEW.id OR (old.collection=NEW.collection AND old.target_id=NEW.target_id)) AND (old.id IS NOT NEW.id OR old.collection IS NOT NEW.collection OR old.target_id IS NOT NEW.target_id OR old.source_id IS NOT NEW.source_id OR old.reason IS NOT NEW.reason OR old.replacement_id IS NOT NEW.replacement_id OR old.metadata IS NOT NEW.metadata))
BEGIN SELECT RAISE(ABORT,'Typed identity already identifies different evidence'); END;
CREATE TRIGGER atlas_typed_retirements_no_update BEFORE UPDATE ON atlas_typed_retirements
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_retirements_no_delete BEFORE DELETE ON atlas_typed_retirements
BEGIN SELECT RAISE(ABORT,'Typed evidence is immutable; append a retirement/correction'); END;
CREATE TRIGGER atlas_typed_overlap_guard BEFORE INSERT ON atlas_typed_observations WHEN NOT EXISTS (SELECT 1 FROM atlas_typed_retirements WHERE collection='observations' AND target_id=NEW.id) AND EXISTS (SELECT 1 FROM atlas_typed_observations c WHERE c.id<>NEW.id AND c.subject_id=NEW.subject_id AND c.field_id=NEW.field_id AND c.method=NEW.method AND c.is_example=NEW.is_example AND c.valid_from<NEW.valid_to AND c.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_typed_retirements r WHERE r.collection='observations' AND r.target_id=c.id))
BEGIN SELECT RAISE(ABORT,'Overlapping typed observations'); END;
CREATE TRIGGER atlas_typed_retirement_source_guard BEFORE INSERT ON atlas_typed_retirements WHEN EXISTS (SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example') AND ((NEW.collection='observations' AND EXISTS(SELECT 1 FROM atlas_typed_observations c WHERE c.id=NEW.target_id AND c.is_example=0)) OR (NEW.collection='feature_links' AND EXISTS(SELECT 1 FROM atlas_typed_feature_links c WHERE c.id=NEW.target_id AND c.is_example=0)))
BEGIN SELECT RAISE(ABORT,'Example sources cannot retire factual typed claims'); END;
CREATE TRIGGER atlas_typed_ingestion_complete_guard BEFORE INSERT ON atlas_ingestions WHEN EXISTS (SELECT 1 FROM atlas_typed_retirements r WHERE r.replacement_id IS NOT NULL AND ((r.collection='observations' AND NOT EXISTS(SELECT 1 FROM atlas_typed_observations c WHERE c.id=r.replacement_id)) OR (r.collection='feature_links' AND NOT EXISTS(SELECT 1 FROM atlas_typed_feature_links c WHERE c.id=r.replacement_id))))
BEGIN SELECT RAISE(ABORT,'Typed replacement claim is missing'); END;
