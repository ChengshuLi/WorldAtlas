-- Forward complete footprint catalog and dated selections. No geometry bytes in SQL.
-- Catalog writes are maintainer-only; ordinary runtime can only select published products.




CREATE TABLE atlas_footprint_versions (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0),
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id), source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 supported_from INTEGER NOT NULL CHECK(supported_from=CAST(supported_from AS INTEGER) AND supported_from BETWEEN -3000 AND 2026 AND supported_from<>0),
 supported_to INTEGER NOT NULL CHECK(supported_to=CAST(supported_to AS INTEGER) AND supported_to BETWEEN -2999 AND 2027 AND supported_to<>0),
 manifest_media_id TEXT NOT NULL REFERENCES atlas_media(id), receipt_media_id TEXT NOT NULL REFERENCES atlas_media(id),
 footprints_sha256 TEXT NOT NULL CHECK(length(footprints_sha256)=64 AND footprints_sha256 NOT GLOB '*[^a-f0-9]*'), location_ids_sha256 TEXT NOT NULL CHECK(length(location_ids_sha256)=64 AND location_ids_sha256 NOT GLOB '*[^a-f0-9]*'), dictionary_sha256 TEXT NOT NULL CHECK(length(dictionary_sha256)=64 AND dictionary_sha256 NOT GLOB '*[^a-f0-9]*'), grid_sha256 TEXT NOT NULL CHECK(length(grid_sha256)=64 AND grid_sha256 NOT GLOB '*[^a-f0-9]*'),
 footprint_hash_algorithm TEXT NOT NULL CHECK(footprint_hash_algorithm='sha256-canonical-json-location-geometry-sha256-v1'),
 grid_size INTEGER NOT NULL CHECK(grid_size>=256 AND grid_size<=1048576), location_count INTEGER NOT NULL CHECK(location_count BETWEEN 1 AND 1000000),
 object_count INTEGER NOT NULL CHECK(object_count BETWEEN 5 AND 512), producer_key_id TEXT NOT NULL CHECK(length(trim(producer_key_id))>0),
 status TEXT NOT NULL CHECK(status IN ('staged','published')), verified_receipt_sha256 TEXT, published_at INTEGER,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'),
 CHECK(supported_from<supported_to), CHECK(manifest_media_id<>receipt_media_id),
 CHECK((status='staged' AND verified_receipt_sha256 IS NULL AND published_at IS NULL) OR (status='published' AND verified_receipt_sha256 IS NOT NULL AND length(verified_receipt_sha256)=64 AND published_at IS NOT NULL))
);

CREATE TABLE atlas_footprint_version_objects (
 version_id TEXT NOT NULL REFERENCES atlas_footprint_versions(id), media_id TEXT NOT NULL REFERENCES atlas_media(id),
 role TEXT NOT NULL CHECK(role IN ('source_archive','reconciled_geometry','coverage_mask','rows','runs')),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64 AND sha256 NOT GLOB '*[^a-f0-9]*'), bytes INTEGER NOT NULL CHECK(bytes BETWEEN 1 AND 20971520),
 "offset" INTEGER, words INTEGER, encoding TEXT, decoded_sha256 TEXT, decoded_bytes INTEGER,
 PRIMARY KEY(version_id,media_id),
 CHECK((role IN ('rows','runs') AND "offset" IS NOT NULL AND words IS NOT NULL AND encoding IS NOT NULL AND decoded_sha256 IS NOT NULL AND decoded_bytes IS NOT NULL AND "offset">=0 AND words>0 AND words<=4194304 AND encoding='gzip-u32le' AND length(decoded_sha256)=64 AND decoded_bytes=words*4) OR (role NOT IN ('rows','runs') AND "offset" IS NULL AND words IS NULL AND encoding IS NULL AND decoded_sha256 IS NULL AND decoded_bytes IS NULL))
);

CREATE TABLE atlas_footprint_selection_validations (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), ingestion_id TEXT NOT NULL UNIQUE REFERENCES atlas_ingestions(id) DEFERRABLE INITIALLY DEFERRED,
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id), hierarchy_sha256 TEXT NOT NULL CHECK(length(hierarchy_sha256)=64 AND hierarchy_sha256 NOT GLOB '*[^a-f0-9]*'), footprints_sha256 TEXT NOT NULL CHECK(length(footprints_sha256)=64 AND footprints_sha256 NOT GLOB '*[^a-f0-9]*'), fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64 AND fingerprint NOT GLOB '*[^a-f0-9]*'), created_at INTEGER NOT NULL,
 CHECK(id=ingestion_id)
);

CREATE TABLE atlas_geographic_footprint_records (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), version_id TEXT REFERENCES atlas_footprint_versions(id), release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id),
 valid_from INTEGER CHECK(valid_from=CAST(valid_from AS INTEGER) AND valid_from BETWEEN -3000 AND 2026 AND valid_from<>0) NOT NULL, valid_to INTEGER CHECK(valid_to=CAST(valid_to AS INTEGER) AND valid_to BETWEEN -2999 AND 2027 AND valid_to<>0) NOT NULL, source_id TEXT NOT NULL REFERENCES atlas_sources(id),
 method TEXT NOT NULL CHECK(method IN ('direct','derived','reference')), status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','unknown','disputed','example')),
 is_example INTEGER NOT NULL CHECK(is_example IN (0,1)), validation_id TEXT NOT NULL REFERENCES atlas_footprint_selection_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'), CHECK(valid_from<valid_to), CHECK(status NOT IN ('unknown','disputed') OR version_id IS NULL)
);

CREATE TABLE atlas_footprint_retirements (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(trim(id))>0), target_id TEXT NOT NULL UNIQUE REFERENCES atlas_geographic_footprint_records(id),
 replacement_id TEXT REFERENCES atlas_geographic_footprint_records(id) DEFERRABLE INITIALLY DEFERRED, source_id TEXT NOT NULL REFERENCES atlas_sources(id), reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 release_id TEXT NOT NULL REFERENCES atlas_geographic_releases(id), validation_id TEXT NOT NULL REFERENCES atlas_footprint_selection_validations(id) DEFERRABLE INITIALLY DEFERRED,
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata) AND json_type(metadata)='object'), CHECK(replacement_id IS NULL OR replacement_id<>target_id)
);

CREATE INDEX footprint_version_release ON atlas_footprint_versions(release_id,status,id);

CREATE INDEX footprint_selection_dates ON atlas_geographic_footprint_records(release_id,valid_from,valid_to,id);

CREATE INDEX footprint_selection_validation ON atlas_geographic_footprint_records(validation_id,id);

CREATE INDEX footprint_retirement_validation ON atlas_footprint_retirements(validation_id,id);

CREATE TRIGGER atlas_footprint_versions_identity BEFORE INSERT ON atlas_footprint_versions WHEN EXISTS(SELECT 1 FROM atlas_footprint_versions WHERE id=NEW.id) BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM atlas_footprint_versions x WHERE id=NEW.id AND x."id" IS NEW."id" AND x."release_id" IS NEW."release_id" AND x."source_id" IS NEW."source_id" AND x."supported_from" IS NEW."supported_from" AND x."supported_to" IS NEW."supported_to" AND x."manifest_media_id" IS NEW."manifest_media_id" AND x."receipt_media_id" IS NEW."receipt_media_id" AND x."footprints_sha256" IS NEW."footprints_sha256" AND x."location_ids_sha256" IS NEW."location_ids_sha256" AND x."dictionary_sha256" IS NEW."dictionary_sha256" AND x."grid_sha256" IS NEW."grid_sha256" AND x."footprint_hash_algorithm" IS NEW."footprint_hash_algorithm" AND x."grid_size" IS NEW."grid_size" AND x."location_count" IS NEW."location_count" AND x."object_count" IS NEW."object_count" AND x."producer_key_id" IS NEW."producer_key_id" AND x."status" IS NEW."status" AND x."verified_receipt_sha256" IS NEW."verified_receipt_sha256" AND x."published_at" IS NEW."published_at" AND x."metadata" IS NEW."metadata") THEN RAISE(ABORT,'Immutable footprint identity collision') END; SELECT RAISE(IGNORE); END;

CREATE TRIGGER atlas_footprint_versions_no_delete BEFORE DELETE ON atlas_footprint_versions BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_versions_no_update BEFORE UPDATE ON atlas_footprint_versions WHEN coalesce(((OLD.status='staged' AND NEW.status='published' AND NEW.verified_receipt_sha256=(SELECT sha256 FROM atlas_media WHERE id=OLD.receipt_media_id) AND NEW.published_at IS NOT NULL AND (SELECT count(*) FROM atlas_footprint_version_objects WHERE version_id=OLD.id)=OLD.object_count) AND NEW."id" IS OLD."id" AND NEW."release_id" IS OLD."release_id" AND NEW."source_id" IS OLD."source_id" AND NEW."supported_from" IS OLD."supported_from" AND NEW."supported_to" IS OLD."supported_to" AND NEW."manifest_media_id" IS OLD."manifest_media_id" AND NEW."receipt_media_id" IS OLD."receipt_media_id" AND NEW."footprints_sha256" IS OLD."footprints_sha256" AND NEW."location_ids_sha256" IS OLD."location_ids_sha256" AND NEW."dictionary_sha256" IS OLD."dictionary_sha256" AND NEW."grid_sha256" IS OLD."grid_sha256" AND NEW."footprint_hash_algorithm" IS OLD."footprint_hash_algorithm" AND NEW."grid_size" IS OLD."grid_size" AND NEW."location_count" IS OLD."location_count" AND NEW."object_count" IS OLD."object_count" AND NEW."producer_key_id" IS OLD."producer_key_id" AND NEW."metadata" IS OLD."metadata"),0)=0 BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_version_objects_identity BEFORE INSERT ON atlas_footprint_version_objects WHEN EXISTS(SELECT 1 FROM atlas_footprint_version_objects WHERE version_id=NEW.version_id AND media_id=NEW.media_id) BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM atlas_footprint_version_objects x WHERE version_id=NEW.version_id AND media_id=NEW.media_id AND x."version_id" IS NEW."version_id" AND x."media_id" IS NEW."media_id" AND x."role" IS NEW."role" AND x."sha256" IS NEW."sha256" AND x."bytes" IS NEW."bytes" AND x."offset" IS NEW."offset" AND x."words" IS NEW."words" AND x."encoding" IS NEW."encoding" AND x."decoded_sha256" IS NEW."decoded_sha256" AND x."decoded_bytes" IS NEW."decoded_bytes") THEN RAISE(ABORT,'Immutable footprint identity collision') END; SELECT RAISE(IGNORE); END;

CREATE TRIGGER atlas_footprint_version_objects_no_delete BEFORE DELETE ON atlas_footprint_version_objects BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_version_objects_no_update BEFORE UPDATE ON atlas_footprint_version_objects WHEN 1 BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_selection_validations_identity BEFORE INSERT ON atlas_footprint_selection_validations WHEN EXISTS(SELECT 1 FROM atlas_footprint_selection_validations WHERE id=NEW.id) BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM atlas_footprint_selection_validations x WHERE id=NEW.id AND x."id" IS NEW."id" AND x."ingestion_id" IS NEW."ingestion_id" AND x."release_id" IS NEW."release_id" AND x."hierarchy_sha256" IS NEW."hierarchy_sha256" AND x."footprints_sha256" IS NEW."footprints_sha256" AND x."fingerprint" IS NEW."fingerprint" AND x."created_at" IS NEW."created_at") THEN RAISE(ABORT,'Immutable footprint identity collision') END; SELECT RAISE(IGNORE); END;

CREATE TRIGGER atlas_footprint_selection_validations_no_delete BEFORE DELETE ON atlas_footprint_selection_validations BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_selection_validations_no_update BEFORE UPDATE ON atlas_footprint_selection_validations WHEN 1 BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_geographic_footprint_records_identity BEFORE INSERT ON atlas_geographic_footprint_records WHEN EXISTS(SELECT 1 FROM atlas_geographic_footprint_records WHERE id=NEW.id) BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records x WHERE id=NEW.id AND x."id" IS NEW."id" AND x."version_id" IS NEW."version_id" AND x."release_id" IS NEW."release_id" AND x."valid_from" IS NEW."valid_from" AND x."valid_to" IS NEW."valid_to" AND x."source_id" IS NEW."source_id" AND x."method" IS NEW."method" AND x."status" IS NEW."status" AND x."is_example" IS NEW."is_example" AND x."validation_id" IS NEW."validation_id" AND x."metadata" IS NEW."metadata") THEN RAISE(ABORT,'Immutable footprint identity collision') END; SELECT RAISE(IGNORE); END;

CREATE TRIGGER atlas_geographic_footprint_records_no_delete BEFORE DELETE ON atlas_geographic_footprint_records BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_geographic_footprint_records_no_update BEFORE UPDATE ON atlas_geographic_footprint_records WHEN 1 BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_retirements_identity BEFORE INSERT ON atlas_footprint_retirements WHEN EXISTS(SELECT 1 FROM atlas_footprint_retirements WHERE id=NEW.id) BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM atlas_footprint_retirements x WHERE id=NEW.id AND x."id" IS NEW."id" AND x."target_id" IS NEW."target_id" AND x."replacement_id" IS NEW."replacement_id" AND x."source_id" IS NEW."source_id" AND x."reason" IS NEW."reason" AND x."release_id" IS NEW."release_id" AND x."validation_id" IS NEW."validation_id" AND x."metadata" IS NEW."metadata") THEN RAISE(ABORT,'Immutable footprint identity collision') END; SELECT RAISE(IGNORE); END;

CREATE TRIGGER atlas_footprint_retirements_no_delete BEFORE DELETE ON atlas_footprint_retirements BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_retirements_no_update BEFORE UPDATE ON atlas_footprint_retirements WHEN 1 BEGIN SELECT RAISE(ABORT,'Footprint evidence is immutable'); END;

CREATE TRIGGER atlas_footprint_guard_0 BEFORE INSERT ON atlas_footprint_versions WHEN NOT EXISTS(SELECT 1 FROM atlas_sources s JOIN atlas_geographic_releases r ON r.id=NEW.release_id WHERE s.id=NEW.source_id AND s.status<>'example' AND r.status='published' AND NEW.supported_from>=s.supported_from AND NEW.supported_to<=s.supported_to) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_versions WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint source interval or published release is unsupported'); END;

CREATE TRIGGER atlas_footprint_guard_1 BEFORE INSERT ON atlas_footprint_version_objects WHEN NOT EXISTS(SELECT 1 FROM atlas_media m JOIN atlas_footprint_versions v ON v.id=NEW.version_id WHERE m.id=NEW.media_id AND m.sha256=NEW.sha256 AND m.bytes=NEW.bytes AND m.object_key='media/'||m.sha256 AND m.status IN ('ready','published') AND v.status='staged') AND NOT EXISTS(SELECT 1 FROM atlas_footprint_version_objects WHERE version_id=NEW.version_id AND media_id=NEW.media_id) BEGIN SELECT RAISE(ABORT,'Footprint object registry or staging context is invalid'); END;

CREATE TRIGGER atlas_footprint_guard_2 BEFORE INSERT ON atlas_geographic_footprint_records WHEN NOT EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND NEW.valid_from>=s.supported_from AND NEW.valid_to<=s.supported_to AND (NEW.is_example=1 OR s.status<>'example') AND (s.status<>'reference' OR NEW.method='reference') AND (NEW.status<>'reference' OR NEW.method='reference') AND (NEW.is_example=1 OR NEW.status<>'example')) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint claim source bounds or class invalid'); END;

CREATE TRIGGER atlas_footprint_guard_3 BEFORE INSERT ON atlas_geographic_footprint_records WHEN NEW.version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_footprint_versions v WHERE v.id=NEW.version_id AND v.release_id=NEW.release_id AND v.status='published' AND NEW.valid_from>=v.supported_from AND NEW.valid_to<=v.supported_to) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Unpublished or unsupported footprint version'); END;

CREATE TRIGGER atlas_footprint_guard_4 BEFORE INSERT ON atlas_geographic_footprint_records WHEN EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint validation receipt is already sealed'); END;

CREATE TRIGGER atlas_footprint_guard_5 BEFORE INSERT ON atlas_geographic_footprint_records WHEN EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r WHERE r.id<>NEW.id AND r.release_id=NEW.release_id AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT EXISTS(SELECT 1 FROM atlas_footprint_retirements t WHERE t.target_id=r.id)) AND NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Equal-precedence footprint intervals overlap'); END;

CREATE TRIGGER atlas_footprint_guard_6 BEFORE INSERT ON atlas_footprint_retirements WHEN EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.id=NEW.validation_id) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_retirements WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint validation receipt is already sealed'); END;

CREATE TRIGGER atlas_footprint_guard_7 BEFORE INSERT ON atlas_footprint_retirements WHEN NOT EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r JOIN atlas_sources s ON s.id=NEW.source_id WHERE r.id=NEW.target_id AND r.release_id=NEW.release_id AND (r.is_example=1 OR s.status<>'example') AND (r.is_example=1 OR s.status<>'reference' OR r.method='reference') AND s.supported_from<=r.valid_from AND s.supported_to>=r.valid_to) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_retirements WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint withdrawal must have supported retained target'); END;

CREATE TRIGGER atlas_footprint_guard_8 BEFORE INSERT ON atlas_footprint_selection_validations WHEN NOT EXISTS(SELECT 1 FROM atlas_geographic_releases r WHERE r.id=NEW.release_id AND r.status='published' AND r.hierarchy_sha256=NEW.hierarchy_sha256 AND r.footprints_sha256=NEW.footprints_sha256 AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases n WHERE n.status='published' AND n.version>r.version)) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_selection_validations WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint selection geographic pins changed'); END;

CREATE TRIGGER atlas_footprint_guard_9 BEFORE INSERT ON atlas_footprint_selection_validations WHEN EXISTS(SELECT 1 FROM atlas_ingestions i WHERE i.id=NEW.ingestion_id AND (i.fingerprint<>NEW.fingerprint OR coalesce(json_extract(i.counts,'$._footprint_validation_id'),'')<>NEW.id)) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_selection_validations WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint ingestion identity mismatch'); END;

CREATE TRIGGER atlas_footprint_guard_10 BEFORE INSERT ON atlas_footprint_selection_validations WHEN EXISTS(SELECT 1 FROM atlas_geographic_footprint_records r WHERE r.validation_id=NEW.id AND r.release_id<>NEW.release_id) OR EXISTS(SELECT 1 FROM atlas_footprint_retirements r WHERE r.validation_id=NEW.id AND r.release_id<>NEW.release_id) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_selection_validations WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint validation release mismatch'); END;

CREATE TRIGGER atlas_footprint_guard_11 BEFORE INSERT ON atlas_footprint_selection_validations WHEN EXISTS(SELECT 1 FROM atlas_footprint_retirements t LEFT JOIN atlas_geographic_footprint_records retained_claim ON retained_claim.id=t.target_id LEFT JOIN atlas_geographic_footprint_records n ON n.id=t.replacement_id WHERE t.validation_id=NEW.id AND t.replacement_id IS NOT NULL AND (n.id IS NULL OR n.release_id<>retained_claim.release_id OR n.is_example<>retained_claim.is_example OR EXISTS(SELECT 1 FROM atlas_footprint_retirements w WHERE w.target_id=n.id))) AND NOT EXISTS(SELECT 1 FROM atlas_footprint_selection_validations WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'Footprint replacement is missing or invalid'); END;

CREATE TRIGGER atlas_footprint_ingestion_guard BEFORE INSERT ON atlas_ingestions WHEN EXISTS(SELECT 1 FROM atlas_footprint_selection_validations v WHERE v.ingestion_id=NEW.id AND (v.fingerprint<>NEW.fingerprint OR coalesce(json_extract(NEW.counts,'$._footprint_validation_id'),'')<>v.id)) BEGIN SELECT RAISE(ABORT,'Footprint ingestion receipt mismatch'); END;
