DROP TRIGGER atlas_ingestions_retirements_complete;
--> statement-breakpoint
DROP TRIGGER atlas_retirements_contract;
--> statement-breakpoint
PRAGMA foreign_keys=OFF;--> statement-breakpoint
CREATE TABLE `__new_atlas_attribute_records` (
	`id` text PRIMARY KEY NOT NULL,
	`location_id` text NOT NULL,
	`attribute` text NOT NULL,
	`value` text NOT NULL,
	`category_id` text,
	`valid_from` integer NOT NULL,
	`valid_to` integer NOT NULL,
	`method` text NOT NULL,
	`status` text NOT NULL,
	`source_id` text NOT NULL,
	`is_example` integer DEFAULT 0 NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`location_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`category_id`) REFERENCES `atlas_categories`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "attribute_names" CHECK("__new_atlas_attribute_records"."attribute" IN ('owner','population','culture','religion','rank','topography','vegetation','climate','habitation')),
	CONSTRAINT "attribute_dates" CHECK(typeof("__new_atlas_attribute_records"."valid_from")='integer' AND "__new_atlas_attribute_records"."valid_from" BETWEEN -3000 AND 2026 AND "__new_atlas_attribute_records"."valid_from"!=0 AND typeof("__new_atlas_attribute_records"."valid_to")='integer' AND "__new_atlas_attribute_records"."valid_to" BETWEEN -2999 AND 2027 AND "__new_atlas_attribute_records"."valid_to"!=0 AND "__new_atlas_attribute_records"."valid_to">"__new_atlas_attribute_records"."valid_from"),
	CONSTRAINT "attribute_value" CHECK(json_valid("__new_atlas_attribute_records"."value") AND (json_type("__new_atlas_attribute_records"."value")='null' OR ("__new_atlas_attribute_records"."attribute"='population' AND json_type("__new_atlas_attribute_records"."value")='integer' AND json_extract("__new_atlas_attribute_records"."value",'$') BETWEEN 0 AND 9007199254740991) OR ("__new_atlas_attribute_records"."attribute"!='population' AND json_type("__new_atlas_attribute_records"."value")='text' AND length(trim(json_extract("__new_atlas_attribute_records"."value",'$')))>0))),
	CONSTRAINT "attribute_category" CHECK(("__new_atlas_attribute_records"."attribute" NOT IN ('owner','culture','religion') OR json_type("__new_atlas_attribute_records"."value")='null' OR "__new_atlas_attribute_records"."category_id" IS NOT NULL) AND ("__new_atlas_attribute_records"."category_id" IS NULL OR ("__new_atlas_attribute_records"."attribute" IN ('owner','culture','religion') AND json_type("__new_atlas_attribute_records"."value")='text'))),
	CONSTRAINT "attribute_rank" CHECK("__new_atlas_attribute_records"."attribute"!='rank' OR json_type("__new_atlas_attribute_records"."value")='null' OR json_extract("__new_atlas_attribute_records"."value",'$') IN ('unsettled','rural settlement','town','city','metropolis')),
	CONSTRAINT "attribute_habitation" CHECK("__new_atlas_attribute_records"."attribute"!='habitation' OR json_type("__new_atlas_attribute_records"."value")='null' OR json_extract("__new_atlas_attribute_records"."value",'$') IN ('inhabited','uninhabited','unknown')),
	CONSTRAINT "attribute_method" CHECK("__new_atlas_attribute_records"."method" IN ('direct','majority-area','derived','reference','estimate')),
	CONSTRAINT "attribute_status" CHECK("__new_atlas_attribute_records"."status" IN ('sourced','derived','reference','estimate','unknown','disputed','no-majority','example')),
	CONSTRAINT "attribute_example" CHECK("__new_atlas_attribute_records"."is_example" IN (0,1)),
	CONSTRAINT "attribute_metadata" CHECK(json_valid("__new_atlas_attribute_records"."metadata") AND json_type("__new_atlas_attribute_records"."metadata")='object')
);
--> statement-breakpoint
INSERT INTO `__new_atlas_attribute_records`("id", "location_id", "attribute", "value", "category_id", "valid_from", "valid_to", "method", "status", "source_id", "is_example", "metadata") SELECT "id", "location_id", "attribute", "value", "category_id", "valid_from", "valid_to", "method", "status", "source_id", "is_example", "metadata" FROM `atlas_attribute_records`;--> statement-breakpoint
DROP TABLE `atlas_attribute_records`;--> statement-breakpoint
ALTER TABLE `__new_atlas_attribute_records` RENAME TO `atlas_attribute_records`;--> statement-breakpoint
PRAGMA foreign_keys=ON;--> statement-breakpoint
CREATE INDEX `attributes_location_dates` ON `atlas_attribute_records` (`location_id`,`attribute`,`valid_from`,`valid_to`);--> statement-breakpoint
CREATE INDEX `attributes_date_id` ON `atlas_attribute_records` (`valid_from`,`valid_to`,`id`);
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_contract BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute requires a location territory') WHERE NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND e.kind='location');
 SELECT RAISE(ABORT,'Category kind mismatch') WHERE NEW.category_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_categories c WHERE c.id=NEW.category_id AND c.kind=NEW.attribute);
 SELECT RAISE(ABORT,'Overlapping attribute evidence') WHERE NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='records' AND retired.target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='records' AND retired.target_id=r.id) AND r.location_id=NEW.location_id AND r.attribute=NEW.attribute AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Attribute exceeds location lifetime') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
 SELECT RAISE(ABORT,'Uninhabited / unsettled conflicts with settlement attributes') WHERE NEW.method='direct' AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='records' AND retired.target_id=NEW.id) AND EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='records' AND retired.target_id=r.id) AND r.location_id=NEW.location_id AND r.method='direct' AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND ((((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='uninhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$')='unsettled') OR (NEW.attribute='population' AND NEW.method='direct' AND NEW.status='sourced' AND json_extract(NEW.value,'$')=0 AND coalesce(json_extract(NEW.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_attributes'),0)=0 AND (json_type(NEW.metadata,'$.rounding') IS NULL OR json_type(NEW.metadata,'$.rounding')='null') AND (json_type(NEW.metadata,'$.model') IS NULL OR json_type(NEW.metadata,'$.model')='null') AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%approx%')) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='inhabited') OR (r.attribute='rank' AND json_extract(r.value,'$') IN ('rural settlement','town','city','metropolis')) OR (r.attribute='population' AND json_extract(r.value,'$')>0))) OR (((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='inhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$') IN ('rural settlement','town','city','metropolis')) OR (NEW.attribute='population' AND json_extract(NEW.value,'$')>0)) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='uninhabited') OR (r.attribute='rank' AND json_extract(r.value,'$')='unsettled') OR (r.attribute='population' AND r.method='direct' AND r.status='sourced' AND json_extract(r.value,'$')=0 AND coalesce(json_extract(r.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(r.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(r.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(r.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(r.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_attributes'),0)=0 AND (json_type(r.metadata,'$.rounding') IS NULL OR json_type(r.metadata,'$.rounding')='null') AND (json_type(r.metadata,'$.model') IS NULL OR json_type(r.metadata,'$.model')='null') AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%approx%')))));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_example_identity BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.is_example=1 AND (e.id=NEW.location_id OR e.id=NEW.category_id));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_nonempty BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute scalar must not be blank') WHERE json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$'),char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_collision BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_attribute_records') WHERE EXISTS(SELECT 1 FROM atlas_attribute_records x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.location_id IS NEW.location_id AND x.attribute IS NEW.attribute AND x.value IS NEW.value AND x.category_id IS NEW.category_id AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.method IS NEW.method AND x.status IS NEW.status AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_example_source BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_immutable BEFORE UPDATE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_retain BEFORE DELETE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_source_interval BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_source_class BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Source class must match evidence method') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND ((s.status='reference' AND NEW.method!='reference') OR (s.status='estimate' AND NEW.method!='estimate')));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_ingestions_retirements_complete BEFORE INSERT ON atlas_ingestions BEGIN
 SELECT RAISE(ABORT,'Replacement claim is missing') WHERE EXISTS(SELECT 1 FROM atlas_evidence_retirements r JOIN json_each(NEW.counts,'$._retirement_ids') batch ON batch.value=r.id WHERE r.replacement_id IS NOT NULL AND ((r.collection='records' AND NOT EXISTS(SELECT 1 FROM atlas_attribute_records c WHERE c.id=r.replacement_id)) OR (r.collection='names' AND NOT EXISTS(SELECT 1 FROM atlas_names c WHERE c.id=r.replacement_id)) OR (r.collection='relationships' AND NOT EXISTS(SELECT 1 FROM atlas_relationships c WHERE c.id=r.replacement_id)) OR (r.collection='media_links' AND NOT EXISTS(SELECT 1 FROM atlas_media_links c WHERE c.id=r.replacement_id))));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_retirements_contract BEFORE INSERT ON atlas_evidence_retirements BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_evidence_retirements') WHERE EXISTS(SELECT 1 FROM atlas_evidence_retirements x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.collection IS NEW.collection AND x.target_id IS NEW.target_id AND x.source_id IS NEW.source_id AND x.reason IS NEW.reason AND x.replacement_id IS NEW.replacement_id AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Claim already retired') WHERE EXISTS(SELECT 1 FROM atlas_evidence_retirements x WHERE x.collection=NEW.collection AND x.target_id=NEW.target_id AND x.id!=NEW.id);
 SELECT RAISE(ABORT,'Empty retirement identity or reason') WHERE length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.target_id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.reason,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR (NEW.replacement_id IS NOT NULL AND length(trim(NEW.replacement_id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0);
 SELECT RAISE(ABORT,'Retired claim must exist') WHERE (NEW.collection='records' AND NOT EXISTS(SELECT 1 FROM atlas_attribute_records c WHERE c.id=NEW.target_id)) OR (NEW.collection='names' AND NOT EXISTS(SELECT 1 FROM atlas_names c WHERE c.id=NEW.target_id)) OR (NEW.collection='relationships' AND NOT EXISTS(SELECT 1 FROM atlas_relationships c WHERE c.id=NEW.target_id)) OR (NEW.collection='media_links' AND NOT EXISTS(SELECT 1 FROM atlas_media_links c WHERE c.id=NEW.target_id));
 SELECT RAISE(ABORT,'Example sources cannot retire factual claims') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example') AND ((NEW.collection='records' AND EXISTS(SELECT 1 FROM atlas_attribute_records c WHERE c.id=NEW.target_id AND c.is_example=0)) OR (NEW.collection='names' AND EXISTS(SELECT 1 FROM atlas_names c WHERE c.id=NEW.target_id AND c.is_example=0)) OR (NEW.collection='relationships' AND EXISTS(SELECT 1 FROM atlas_relationships c WHERE c.id=NEW.target_id AND c.is_example=0)) OR (NEW.collection='media_links' AND EXISTS(SELECT 1 FROM atlas_media_links c WHERE c.id=NEW.target_id AND c.is_example=0)));
 WITH RECURSIVE chain(id) AS (SELECT NEW.replacement_id WHERE NEW.replacement_id IS NOT NULL UNION SELECT r.replacement_id FROM atlas_evidence_retirements r JOIN chain c ON r.target_id=c.id WHERE r.collection=NEW.collection AND r.replacement_id IS NOT NULL)
 SELECT RAISE(ABORT,'Supersession cycle') WHERE EXISTS(SELECT 1 FROM chain WHERE id=NEW.target_id);
END;
--> statement-breakpoint
