-- Forward dated membership/existence contract. Original fourteen tables and source bytes remain unchanged.
-- New claims require a sealed SQL-validated receipt; no caller-supplied success flag.
--> statement-breakpoint
CREATE TABLE atlas_temporal_geography_validations (
 id TEXT COLLATE BINARY PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 ingestion_id TEXT NOT NULL UNIQUE REFERENCES atlas_ingestions(id) DEFERRABLE INITIALLY DEFERRED,
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id),
 hierarchy_sha256 TEXT NOT NULL CHECK(length(hierarchy_sha256)=64),
 footprints_sha256 TEXT NOT NULL CHECK(length(footprints_sha256)=64),
 fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64),
 created_at INTEGER NOT NULL,
 CHECK(id=ingestion_id)
);
--> statement-breakpoint
CREATE TABLE atlas_geographic_membership_records (
 id TEXT COLLATE BINARY PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 entity_id TEXT NOT NULL REFERENCES atlas_entities(id),
 valid_from INTEGER NOT NULL,
 valid_to INTEGER NOT NULL,
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 method TEXT NOT NULL CHECK(method IN ('direct','derived','reference')),
 status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 parent_id TEXT REFERENCES atlas_entities(id),
 CHECK(status NOT IN ('unknown','disputed') OR parent_id IS NULL),
 CHECK(valid_from<valid_to),
 CHECK(typeof(valid_from)='integer' AND typeof(valid_to)='integer' AND valid_from BETWEEN -3000 AND 2026 AND valid_to BETWEEN -2999 AND 2027 AND valid_from<>0 AND valid_to<>0)
);
--> statement-breakpoint
CREATE INDEX temporal_memberships_dates ON atlas_geographic_membership_records(release_id,entity_id,valid_from,valid_to,id);
CREATE INDEX temporal_memberships_validation ON atlas_geographic_membership_records(validation_id,entity_id);
--> statement-breakpoint
CREATE TABLE atlas_geographic_existence_records (
 id TEXT COLLATE BINARY PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 entity_id TEXT NOT NULL REFERENCES atlas_entities(id),
 valid_from INTEGER NOT NULL,
 valid_to INTEGER NOT NULL,
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 method TEXT NOT NULL CHECK(method IN ('direct','derived','reference')),
 status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)),
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 value TEXT NOT NULL CHECK(value IN ('exists','not_exists','unknown')),
 CHECK(status NOT IN ('unknown','disputed') OR value='unknown'),
 CHECK(valid_from<valid_to),
 CHECK(typeof(valid_from)='integer' AND typeof(valid_to)='integer' AND valid_from BETWEEN -3000 AND 2026 AND valid_to BETWEEN -2999 AND 2027 AND valid_from<>0 AND valid_to<>0)
);
--> statement-breakpoint
CREATE INDEX temporal_existence_dates ON atlas_geographic_existence_records(release_id,entity_id,valid_from,valid_to,id);
CREATE INDEX temporal_existence_validation ON atlas_geographic_existence_records(validation_id,entity_id);
--> statement-breakpoint
CREATE TABLE atlas_temporal_geography_retirements (
 id TEXT COLLATE BINARY PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 collection TEXT NOT NULL CHECK(collection IN ('memberships','existence')),
 target_id TEXT NOT NULL CHECK(length(trim(target_id))>0),
 replacement_id TEXT CHECK(replacement_id IS NULL OR (length(trim(replacement_id))>0 AND replacement_id<>target_id)),
 source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id),
 validation_id TEXT NOT NULL REFERENCES atlas_temporal_geography_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 UNIQUE(collection,target_id)
);
--> statement-breakpoint
CREATE INDEX temporal_retirement_release ON atlas_temporal_geography_retirements(release_id,id);
CREATE INDEX temporal_retirement_validation ON atlas_temporal_geography_retirements(validation_id,collection,target_id);
--> statement-breakpoint
CREATE TRIGGER temporal_memberships_contract BEFORE INSERT ON atlas_geographic_membership_records BEGIN
 SELECT RAISE(ABORT,'Stable temporal identity collision') WHERE EXISTS(SELECT 1 FROM atlas_geographic_membership_records x WHERE x.id=NEW.id AND (x.id IS NOT NEW.id OR x.entity_id IS NOT NEW.entity_id OR x.valid_from IS NOT NEW.valid_from OR x.valid_to IS NOT NEW.valid_to OR x.source_id IS NOT NEW.source_id OR x.method IS NOT NEW.method OR x.status IS NOT NEW.status OR x.is_example IS NOT NEW.is_example OR x.release_id IS NOT NEW.release_id OR x.validation_id IS NOT NEW.validation_id OR x.metadata IS NOT NEW.metadata OR x.parent_id IS NOT NEW.parent_id));
 SELECT RAISE(ABORT,'Temporal validation receipt is sealed') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_membership_records WHERE id=NEW.id);
 SELECT RAISE(ABORT,'Claim requires an approved geographic identity') WHERE NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id JOIN atlas_entity_types t ON t.id=e.kind WHERE m.release_id=NEW.release_id AND m.entity_id=NEW.entity_id AND m.active=1 AND t.geographic_level IS NOT NULL);
 SELECT RAISE(ABORT,'Unsupported geographic source interval/class') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to OR (s.status='example' AND NEW.is_example=0) OR s.status='estimate' OR (s.status='reference' AND NEW.method<>'reference')));
 SELECT RAISE(ABORT,'Claim exceeds identity lifetime/example isolation') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to) OR (e.is_example=1 AND NEW.is_example=0)));
 SELECT RAISE(ABORT,'Overlapping equal-precedence geographic claims') WHERE NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE collection='memberships' AND target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_geographic_membership_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.entity_id=NEW.entity_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='memberships' AND t.target_id=r.id));
 SELECT RAISE(ABORT,'Parent must be an approved adjacent-tier identity within its lifetime') WHERE NEW.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_entities e JOIN atlas_entity_types et ON et.id=e.kind JOIN atlas_geographic_memberships p ON p.release_id=NEW.release_id AND p.entity_id=NEW.parent_id AND p.active=1 JOIN atlas_entities pe ON pe.id=p.entity_id JOIN atlas_entity_types pt ON pt.id=pe.kind WHERE e.id=NEW.entity_id AND pt.geographic_level=et.geographic_level+1 AND (NEW.is_example=1 OR pe.is_example=0) AND (pe.valid_from IS NULL OR NEW.valid_from>=pe.valid_from) AND (pe.valid_to IS NULL OR NEW.valid_to<=pe.valid_to));
 SELECT RAISE(ABORT,'Continents cannot acquire dated parents') WHERE EXISTS(SELECT 1 FROM atlas_entities WHERE id=NEW.entity_id AND kind='continent');
END;
--> statement-breakpoint
CREATE TRIGGER temporal_memberships_immutable BEFORE UPDATE ON atlas_geographic_membership_records BEGIN SELECT RAISE(ABORT,'Temporal evidence is append-only'); END;
CREATE TRIGGER temporal_memberships_retain BEFORE DELETE ON atlas_geographic_membership_records BEGIN SELECT RAISE(ABORT,'Temporal evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER temporal_existence_contract BEFORE INSERT ON atlas_geographic_existence_records BEGIN
 SELECT RAISE(ABORT,'Stable temporal identity collision') WHERE EXISTS(SELECT 1 FROM atlas_geographic_existence_records x WHERE x.id=NEW.id AND (x.id IS NOT NEW.id OR x.entity_id IS NOT NEW.entity_id OR x.valid_from IS NOT NEW.valid_from OR x.valid_to IS NOT NEW.valid_to OR x.source_id IS NOT NEW.source_id OR x.method IS NOT NEW.method OR x.status IS NOT NEW.status OR x.is_example IS NOT NEW.is_example OR x.release_id IS NOT NEW.release_id OR x.validation_id IS NOT NEW.validation_id OR x.metadata IS NOT NEW.metadata OR x.value IS NOT NEW.value));
 SELECT RAISE(ABORT,'Temporal validation receipt is sealed') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_existence_records WHERE id=NEW.id);
 SELECT RAISE(ABORT,'Claim requires an approved geographic identity') WHERE NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id JOIN atlas_entity_types t ON t.id=e.kind WHERE m.release_id=NEW.release_id AND m.entity_id=NEW.entity_id AND m.active=1 AND t.geographic_level IS NOT NULL);
 SELECT RAISE(ABORT,'Unsupported geographic source interval/class') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to OR (s.status='example' AND NEW.is_example=0) OR s.status='estimate' OR (s.status='reference' AND NEW.method<>'reference')));
 SELECT RAISE(ABORT,'Claim exceeds identity lifetime/example isolation') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to) OR (e.is_example=1 AND NEW.is_example=0)));
 SELECT RAISE(ABORT,'Overlapping equal-precedence geographic claims') WHERE NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE collection='existence' AND target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_geographic_existence_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.entity_id=NEW.entity_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.collection='existence' AND t.target_id=r.id));
END;
--> statement-breakpoint
CREATE TRIGGER temporal_existence_immutable BEFORE UPDATE ON atlas_geographic_existence_records BEGIN SELECT RAISE(ABORT,'Temporal evidence is append-only'); END;
CREATE TRIGGER temporal_existence_retain BEFORE DELETE ON atlas_geographic_existence_records BEGIN SELECT RAISE(ABORT,'Temporal evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER temporal_retirements_contract BEFORE INSERT ON atlas_temporal_geography_retirements BEGIN
 SELECT RAISE(ABORT,'Stable temporal identity collision') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements x WHERE x.id=NEW.id AND (x.id IS NOT NEW.id OR x.collection IS NOT NEW.collection OR x.target_id IS NOT NEW.target_id OR x.replacement_id IS NOT NEW.replacement_id OR x.source_id IS NOT NEW.source_id OR x.reason IS NOT NEW.reason OR x.release_id IS NOT NEW.release_id OR x.validation_id IS NOT NEW.validation_id OR x.metadata IS NOT NEW.metadata));
 SELECT RAISE(ABORT,'Temporal validation receipt is sealed') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements WHERE id=NEW.id);
 SELECT RAISE(ABORT,'Retired geographic claim must exist in the same release') WHERE NOT EXISTS(SELECT 1 FROM (SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_membership_records WHERE NEW.collection='memberships' UNION ALL SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_existence_records WHERE NEW.collection='existence') c WHERE c.id=NEW.target_id AND c.release_id=NEW.release_id);
 SELECT RAISE(ABORT,'Withdrawal source must support the target interval and factual status') WHERE EXISTS(SELECT 1 FROM (SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_membership_records WHERE NEW.collection='memberships' UNION ALL SELECT id,entity_id,release_id,valid_from,valid_to,is_example FROM atlas_geographic_existence_records WHERE NEW.collection='existence') c JOIN atlas_sources s ON s.id=NEW.source_id WHERE c.id=NEW.target_id AND ((s.status='example' AND c.is_example=0) OR s.supported_from>c.valid_from OR s.supported_to<c.valid_to));
 SELECT RAISE(ABORT,'Geographic supersession cycle') WHERE EXISTS(WITH RECURSIVE chain(id) AS (SELECT NEW.replacement_id WHERE NEW.replacement_id IS NOT NULL UNION SELECT t.replacement_id FROM atlas_temporal_geography_retirements t JOIN chain c ON t.target_id=c.id WHERE t.collection=NEW.collection AND t.replacement_id IS NOT NULL) SELECT 1 FROM chain WHERE id=NEW.target_id);
END;
--> statement-breakpoint
CREATE TRIGGER temporal_retirements_immutable BEFORE UPDATE ON atlas_temporal_geography_retirements BEGIN SELECT RAISE(ABORT,'Temporal evidence is append-only'); END;
CREATE TRIGGER temporal_retirements_retain BEFORE DELETE ON atlas_temporal_geography_retirements BEGIN SELECT RAISE(ABORT,'Temporal evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER temporal_validations_contract BEFORE INSERT ON atlas_temporal_geography_validations BEGIN
 SELECT RAISE(ABORT,'Stable temporal identity collision') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations x WHERE x.id=NEW.id AND (x.id IS NOT NEW.id OR x.ingestion_id IS NOT NEW.ingestion_id OR x.release_id IS NOT NEW.release_id OR x.hierarchy_sha256 IS NOT NEW.hierarchy_sha256 OR x.footprints_sha256 IS NOT NEW.footprints_sha256 OR x.fingerprint IS NOT NEW.fingerprint));
 SELECT RAISE(IGNORE) WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations WHERE id=NEW.id);
 SELECT RAISE(ABORT,'Temporal validation must precede a new tracked ingestion') WHERE EXISTS(SELECT 1 FROM atlas_ingestions WHERE id=NEW.ingestion_id);
 SELECT RAISE(ABORT,'Published geography does not match transaction pins') WHERE NOT EXISTS(SELECT 1 FROM atlas_geographic_releases r WHERE r.id=NEW.release_id AND r.status='published' AND r.hierarchy_sha256=NEW.hierarchy_sha256 AND r.footprints_sha256=NEW.footprints_sha256 AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases newer WHERE newer.status='published' AND newer.version>r.version));
 SELECT RAISE(ABORT,'Replacement geographic claim is missing') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_retirements t WHERE t.validation_id=NEW.id AND t.replacement_id IS NOT NULL AND ((t.collection='memberships' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_membership_records r WHERE r.id=t.replacement_id AND r.release_id=t.release_id)) OR (t.collection='existence' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_existence_records r WHERE r.id=t.replacement_id AND r.release_id=t.release_id))));
END;
--> statement-breakpoint
CREATE TRIGGER temporal_validations_immutable BEFORE UPDATE ON atlas_temporal_geography_validations BEGIN SELECT RAISE(ABORT,'Temporal evidence is append-only'); END;
CREATE TRIGGER temporal_validations_retain BEFORE DELETE ON atlas_temporal_geography_validations BEGIN SELECT RAISE(ABORT,'Temporal evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER temporal_chain_validate AFTER INSERT ON atlas_temporal_geography_validations BEGIN
 SELECT RAISE(ABORT,'Temporal geography has a disconnected present chain at an affected transition') WHERE EXISTS(WITH RECURSIVE
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
SELECT 1 FROM resolved r LEFT JOIN resolved p ON p.entity_id=r.parent_id AND p.year=r.year AND p.examples=r.examples WHERE r.present=1 AND ((r.level=5 AND r.parent_id IS NOT NULL) OR (r.level<5 AND (p.entity_id IS NULL OR p.present<>1 OR p.level<>r.level+1))) LIMIT 1);
END;
--> statement-breakpoint
CREATE TRIGGER temporal_ingestion_complete BEFORE INSERT ON atlas_ingestions BEGIN
 SELECT RAISE(ABORT,'Temporal ingestion does not match its SQL validation receipt') WHERE EXISTS(SELECT 1 FROM atlas_temporal_geography_validations v WHERE v.ingestion_id=NEW.id AND (v.fingerprint<>NEW.fingerprint OR json_extract(NEW.counts,'$._temporal_geography_validation_id') IS NOT v.id));
END;
