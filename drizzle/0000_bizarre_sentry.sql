CREATE TABLE `atlas_attribute_records` (
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
	CONSTRAINT "attribute_names" CHECK("atlas_attribute_records"."attribute" IN ('owner','population','culture','religion','rank','topography','vegetation','climate','habitation')),
	CONSTRAINT "attribute_dates" CHECK(typeof("atlas_attribute_records"."valid_from")='integer' AND "atlas_attribute_records"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_attribute_records"."valid_from"!=0 AND typeof("atlas_attribute_records"."valid_to")='integer' AND "atlas_attribute_records"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_attribute_records"."valid_to"!=0 AND "atlas_attribute_records"."valid_to">"atlas_attribute_records"."valid_from"),
	CONSTRAINT "attribute_value" CHECK(json_valid("atlas_attribute_records"."value") AND (json_type("atlas_attribute_records"."value")='null' OR ("atlas_attribute_records"."attribute"='population' AND json_type("atlas_attribute_records"."value")='integer' AND json_extract("atlas_attribute_records"."value",'$') BETWEEN 0 AND 9007199254740991) OR ("atlas_attribute_records"."attribute"!='population' AND json_type("atlas_attribute_records"."value")='text' AND length(trim(json_extract("atlas_attribute_records"."value",'$')))>0))),
	CONSTRAINT "attribute_category" CHECK(("atlas_attribute_records"."attribute" NOT IN ('owner','culture','religion') OR json_type("atlas_attribute_records"."value")='null' OR "atlas_attribute_records"."category_id" IS NOT NULL) AND ("atlas_attribute_records"."category_id" IS NULL OR ("atlas_attribute_records"."attribute" IN ('owner','culture','religion') AND json_type("atlas_attribute_records"."value")='text'))),
	CONSTRAINT "attribute_rank" CHECK("atlas_attribute_records"."attribute"!='rank' OR json_type("atlas_attribute_records"."value")='null' OR json_extract("atlas_attribute_records"."value",'$') IN ('rural settlement','town','city','metropolis')),
	CONSTRAINT "attribute_habitation" CHECK("atlas_attribute_records"."attribute"!='habitation' OR json_type("atlas_attribute_records"."value")='null' OR json_extract("atlas_attribute_records"."value",'$') IN ('inhabited','uninhabited','unknown')),
	CONSTRAINT "attribute_method" CHECK("atlas_attribute_records"."method" IN ('direct','majority-area','derived','reference','estimate')),
	CONSTRAINT "attribute_status" CHECK("atlas_attribute_records"."status" IN ('sourced','derived','reference','estimate','unknown','disputed','no-majority','example')),
	CONSTRAINT "attribute_example" CHECK("atlas_attribute_records"."is_example" IN (0,1)),
	CONSTRAINT "attribute_metadata" CHECK(json_valid("atlas_attribute_records"."metadata") AND json_type("atlas_attribute_records"."metadata")='object')
);
--> statement-breakpoint
CREATE INDEX `attributes_location_dates` ON `atlas_attribute_records` (`location_id`,`attribute`,`valid_from`,`valid_to`);--> statement-breakpoint
CREATE INDEX `attributes_date_id` ON `atlas_attribute_records` (`valid_from`,`valid_to`,`id`);--> statement-breakpoint
CREATE TABLE `atlas_categories` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`name` text NOT NULL,
	`source_id` text NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "category_text" CHECK(length(trim("atlas_categories"."id"))>0 AND length(trim("atlas_categories"."name"))>0),
	CONSTRAINT "category_kind" CHECK("atlas_categories"."kind" IN ('owner','culture','religion')),
	CONSTRAINT "category_metadata" CHECK(json_valid("atlas_categories"."metadata") AND json_type("atlas_categories"."metadata")='object')
);
--> statement-breakpoint
CREATE TABLE `atlas_entities` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`name` text NOT NULL,
	`parent_id` text,
	`valid_from` integer,
	`valid_to` integer,
	`source_id` text,
	`reference_owner` text,
	`is_example` integer DEFAULT 0 NOT NULL,
	`active` integer DEFAULT 1 NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`kind`) REFERENCES `atlas_entity_types`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`parent_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "entity_text" CHECK(length(trim("atlas_entities"."id"))>0 AND length(trim("atlas_entities"."name"))>0),
	CONSTRAINT "entity_dates" CHECK(("atlas_entities"."valid_from" IS NULL OR typeof("atlas_entities"."valid_from")='integer' AND "atlas_entities"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_entities"."valid_from"!=0) AND ("atlas_entities"."valid_to" IS NULL OR typeof("atlas_entities"."valid_to")='integer' AND "atlas_entities"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_entities"."valid_to"!=0) AND ("atlas_entities"."valid_from" IS NULL OR "atlas_entities"."valid_to" IS NULL OR "atlas_entities"."valid_to">"atlas_entities"."valid_from") AND (("atlas_entities"."valid_from" IS NULL AND "atlas_entities"."valid_to" IS NULL) OR "atlas_entities"."source_id" IS NOT NULL)),
	CONSTRAINT "entity_example" CHECK("atlas_entities"."is_example" IN (0,1)),
	CONSTRAINT "entity_active" CHECK("atlas_entities"."active" IN (0,1)),
	CONSTRAINT "entity_metadata" CHECK(json_valid("atlas_entities"."metadata") AND json_type("atlas_entities"."metadata")='object')
);
--> statement-breakpoint
CREATE INDEX `entities_kind_id` ON `atlas_entities` (`kind`,`active`,`id`);--> statement-breakpoint
CREATE INDEX `entities_parent` ON `atlas_entities` (`parent_id`);--> statement-breakpoint
CREATE TABLE `atlas_entity_types` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`geographic_level` integer,
	`metadata` text DEFAULT '{}' NOT NULL,
	CONSTRAINT "entity_type_text" CHECK(length(trim("atlas_entity_types"."id"))>0 AND length(trim("atlas_entity_types"."name"))>0),
	CONSTRAINT "entity_type_level" CHECK(("atlas_entity_types"."id" IN ('location','province','area','region','subcontinent','continent') AND "atlas_entity_types"."geographic_level" IS NOT NULL AND "atlas_entity_types"."geographic_level"=CASE "atlas_entity_types"."id" WHEN 'location' THEN 0 WHEN 'province' THEN 1 WHEN 'area' THEN 2 WHEN 'region' THEN 3 WHEN 'subcontinent' THEN 4 WHEN 'continent' THEN 5 END) OR ("atlas_entity_types"."id" NOT IN ('location','province','area','region','subcontinent','continent') AND "atlas_entity_types"."geographic_level" IS NULL)),
	CONSTRAINT "entity_type_metadata" CHECK(json_valid("atlas_entity_types"."metadata") AND json_type("atlas_entity_types"."metadata")='object')
);
--> statement-breakpoint
CREATE TABLE `atlas_ingestions` (
	`id` text PRIMARY KEY NOT NULL,
	`fingerprint` text NOT NULL,
	`counts` text NOT NULL,
	`created_at` integer NOT NULL,
	CONSTRAINT "ingestion_counts" CHECK(json_valid("atlas_ingestions"."counts") AND json_type("atlas_ingestions"."counts")='object'),
	CONSTRAINT "ingestion_fingerprint" CHECK(length("atlas_ingestions"."fingerprint")=64)
);
--> statement-breakpoint
CREATE TABLE `atlas_media` (
	`id` text PRIMARY KEY NOT NULL,
	`object_key` text NOT NULL,
	`sha256` text NOT NULL,
	`bytes` integer NOT NULL,
	`mime` text NOT NULL,
	`name` text NOT NULL,
	`license` text NOT NULL,
	`attribution` text NOT NULL,
	`source_id` text NOT NULL,
	`status` text DEFAULT 'ready' NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "media_digest" CHECK(length("atlas_media"."sha256")=64 AND "atlas_media"."sha256" NOT GLOB '*[^0-9a-f]*' AND "atlas_media"."object_key"='media/'||"atlas_media"."sha256"),
	CONSTRAINT "media_bytes" CHECK(typeof("atlas_media"."bytes")='integer' AND "atlas_media"."bytes">=0 AND "atlas_media"."bytes"<=9007199254740991),
	CONSTRAINT "media_text" CHECK(length(trim("atlas_media"."object_key"))>0 AND length(trim("atlas_media"."mime"))>0 AND length(trim("atlas_media"."name"))>0 AND length(trim("atlas_media"."license"))>0 AND length(trim("atlas_media"."attribution"))>0),
	CONSTRAINT "media_status" CHECK("atlas_media"."status" IN ('pending','ready','published')),
	CONSTRAINT "media_metadata" CHECK(json_valid("atlas_media"."metadata") AND json_type("atlas_media"."metadata")='object')
);
--> statement-breakpoint
CREATE UNIQUE INDEX `atlas_media_object_key_unique` ON `atlas_media` (`object_key`);--> statement-breakpoint
CREATE TABLE `atlas_media_links` (
	`id` text PRIMARY KEY NOT NULL,
	`media_id` text NOT NULL,
	`entity_id` text NOT NULL,
	`role` text NOT NULL,
	`caption` text,
	`source_id` text NOT NULL,
	`is_example` integer DEFAULT 0 NOT NULL,
	`valid_from` integer,
	`valid_to` integer,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`media_id`) REFERENCES `atlas_media`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "media_link_example" CHECK("atlas_media_links"."is_example" IN (0,1)),
	CONSTRAINT "media_link_role" CHECK(length(trim("atlas_media_links"."role"))>0),
	CONSTRAINT "media_link_dates" CHECK(("atlas_media_links"."valid_from" IS NULL AND "atlas_media_links"."valid_to" IS NULL) OR ("atlas_media_links"."valid_from" IS NOT NULL AND "atlas_media_links"."valid_to" IS NOT NULL AND typeof("atlas_media_links"."valid_from")='integer' AND "atlas_media_links"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_media_links"."valid_from"!=0 AND typeof("atlas_media_links"."valid_to")='integer' AND "atlas_media_links"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_media_links"."valid_to"!=0 AND "atlas_media_links"."valid_to">"atlas_media_links"."valid_from")),
	CONSTRAINT "media_link_metadata" CHECK(json_valid("atlas_media_links"."metadata") AND json_type("atlas_media_links"."metadata")='object')
);
--> statement-breakpoint
CREATE INDEX `media_links_entity` ON `atlas_media_links` (`entity_id`);--> statement-breakpoint
CREATE TABLE `atlas_names` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_id` text NOT NULL,
	`name` text NOT NULL,
	`language` text DEFAULT 'und' NOT NULL,
	`role` text DEFAULT 'preferred' NOT NULL,
	`valid_from` integer NOT NULL,
	`valid_to` integer NOT NULL,
	`source_id` text NOT NULL,
	`is_example` integer DEFAULT 0 NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "name_text" CHECK(length(trim("atlas_names"."name"))>0 AND length(trim("atlas_names"."language"))>0),
	CONSTRAINT "name_role" CHECK("atlas_names"."role" IN ('preferred','alias')),
	CONSTRAINT "name_dates" CHECK(typeof("atlas_names"."valid_from")='integer' AND "atlas_names"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_names"."valid_from"!=0 AND typeof("atlas_names"."valid_to")='integer' AND "atlas_names"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_names"."valid_to"!=0 AND "atlas_names"."valid_to">"atlas_names"."valid_from"),
	CONSTRAINT "name_example" CHECK("atlas_names"."is_example" IN (0,1)),
	CONSTRAINT "name_metadata" CHECK(json_valid("atlas_names"."metadata") AND json_type("atlas_names"."metadata")='object')
);
--> statement-breakpoint
CREATE INDEX `names_entity_dates` ON `atlas_names` (`entity_id`,`valid_from`,`valid_to`);--> statement-breakpoint
CREATE TABLE `atlas_relationships` (
	`id` text PRIMARY KEY NOT NULL,
	`source_entity_id` text NOT NULL,
	`target_entity_id` text NOT NULL,
	`relationship_type` text NOT NULL,
	`valid_from` integer,
	`valid_to` integer,
	`source_id` text NOT NULL,
	`is_example` integer DEFAULT 0 NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	FOREIGN KEY (`source_entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`target_entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "relationship_text" CHECK(length(trim("atlas_relationships"."relationship_type"))>0),
	CONSTRAINT "relationship_dates" CHECK(("atlas_relationships"."valid_from" IS NULL AND "atlas_relationships"."valid_to" IS NULL) OR ("atlas_relationships"."valid_from" IS NOT NULL AND "atlas_relationships"."valid_to" IS NOT NULL AND typeof("atlas_relationships"."valid_from")='integer' AND "atlas_relationships"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_relationships"."valid_from"!=0 AND typeof("atlas_relationships"."valid_to")='integer' AND "atlas_relationships"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_relationships"."valid_to"!=0 AND "atlas_relationships"."valid_to">"atlas_relationships"."valid_from")),
	CONSTRAINT "relationship_example" CHECK("atlas_relationships"."is_example" IN (0,1)),
	CONSTRAINT "relationship_metadata" CHECK(json_valid("atlas_relationships"."metadata") AND json_type("atlas_relationships"."metadata")='object')
);
--> statement-breakpoint
CREATE INDEX `relationships_source_dates` ON `atlas_relationships` (`source_entity_id`,`valid_from`,`valid_to`);--> statement-breakpoint
CREATE INDEX `relationships_target_dates` ON `atlas_relationships` (`target_entity_id`,`valid_from`,`valid_to`);--> statement-breakpoint
CREATE TABLE `atlas_sources` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`url` text,
	`license` text NOT NULL,
	`vintage` text NOT NULL,
	`supported_from` integer NOT NULL,
	`supported_to` integer NOT NULL,
	`status` text NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	CONSTRAINT "source_text" CHECK(length(trim("atlas_sources"."id"))>0 AND length(trim("atlas_sources"."name"))>0 AND length(trim("atlas_sources"."license"))>0 AND length(trim("atlas_sources"."vintage"))>0),
	CONSTRAINT "source_dates" CHECK(typeof("atlas_sources"."supported_from")='integer' AND "atlas_sources"."supported_from" BETWEEN -3000 AND 2026 AND "atlas_sources"."supported_from"!=0 AND typeof("atlas_sources"."supported_to")='integer' AND "atlas_sources"."supported_to" BETWEEN -2999 AND 2027 AND "atlas_sources"."supported_to"!=0 AND "atlas_sources"."supported_to">"atlas_sources"."supported_from"),
	CONSTRAINT "source_status" CHECK("atlas_sources"."status" IN ('historical','reference','estimate','example')),
	CONSTRAINT "source_metadata" CHECK(json_valid("atlas_sources"."metadata") AND json_type("atlas_sources"."metadata")='object')
);

--> statement-breakpoint
-- Append this file to the generated Drizzle base migration.
-- Triggers retain source identity and enforce cross-table evidence contracts.
CREATE TRIGGER atlas_sources_collision BEFORE INSERT ON atlas_sources BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_sources') WHERE EXISTS(SELECT 1 FROM atlas_sources x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.name IS NEW.name AND x.url IS NEW.url AND x.license IS NEW.license AND x.vintage IS NEW.vintage AND x.supported_from IS NEW.supported_from AND x.supported_to IS NEW.supported_to AND x.status IS NEW.status AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_sources_required_text BEFORE INSERT ON atlas_sources BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.license,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.vintage,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_sources_immutable BEFORE UPDATE ON atlas_sources BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_sources_retain BEFORE DELETE ON atlas_sources BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_entity_types_collision BEFORE INSERT ON atlas_entity_types BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_entity_types') WHERE EXISTS(SELECT 1 FROM atlas_entity_types x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.name IS NEW.name AND x.geographic_level IS NEW.geographic_level AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entity_types_required_text BEFORE INSERT ON atlas_entity_types BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entity_types_immutable BEFORE UPDATE ON atlas_entity_types BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_entity_types_retain BEFORE DELETE ON atlas_entity_types BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_collision BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_entities') WHERE EXISTS(SELECT 1 FROM atlas_entities x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.kind IS NEW.kind AND x.name IS NEW.name AND x.parent_id IS NEW.parent_id AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.reference_owner IS NEW.reference_owner AND x.is_example IS NEW.is_example AND x.active IS NEW.active AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_required_text BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_retain BEFORE DELETE ON atlas_entities BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_categories_collision BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_categories') WHERE EXISTS(SELECT 1 FROM atlas_categories x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.kind IS NEW.kind AND x.name IS NEW.name AND x.source_id IS NEW.source_id AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_categories_required_text BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_categories_immutable BEFORE UPDATE ON atlas_categories BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_categories_retain BEFORE DELETE ON atlas_categories BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_collision BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_attribute_records') WHERE EXISTS(SELECT 1 FROM atlas_attribute_records x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.location_id IS NEW.location_id AND x.attribute IS NEW.attribute AND x.value IS NEW.value AND x.category_id IS NEW.category_id AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.method IS NEW.method AND x.status IS NEW.status AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_immutable BEFORE UPDATE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_retain BEFORE DELETE ON atlas_attribute_records BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_collision BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_names') WHERE EXISTS(SELECT 1 FROM atlas_names x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.entity_id IS NEW.entity_id AND x.name IS NEW.name AND x.language IS NEW.language AND x.role IS NEW.role AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_required_text BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.language,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.role,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_immutable BEFORE UPDATE ON atlas_names BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_retain BEFORE DELETE ON atlas_names BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_collision BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_relationships') WHERE EXISTS(SELECT 1 FROM atlas_relationships x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.source_entity_id IS NEW.source_entity_id AND x.target_entity_id IS NEW.target_entity_id AND x.relationship_type IS NEW.relationship_type AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_required_text BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.relationship_type,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_immutable BEFORE UPDATE ON atlas_relationships BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_retain BEFORE DELETE ON atlas_relationships BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_collision BEFORE INSERT ON atlas_media BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_media') WHERE EXISTS(SELECT 1 FROM atlas_media x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.object_key IS NEW.object_key AND x.sha256 IS NEW.sha256 AND x.bytes IS NEW.bytes AND x.mime IS NEW.mime AND x.name IS NEW.name AND x.license IS NEW.license AND x.attribution IS NEW.attribution AND x.source_id IS NEW.source_id AND x.status IS NEW.status AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_required_text BEFORE INSERT ON atlas_media BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.license,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.attribution,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.mime,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_retain BEFORE DELETE ON atlas_media BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_collision BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_media_links') WHERE EXISTS(SELECT 1 FROM atlas_media_links x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.media_id IS NEW.media_id AND x.entity_id IS NEW.entity_id AND x.role IS NEW.role AND x.caption IS NEW.caption AND x.source_id IS NEW.source_id AND x.is_example IS NEW.is_example AND x.valid_from IS NEW.valid_from AND x.valid_to IS NEW.valid_to AND x.metadata IS NEW.metadata));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_required_text BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Empty source or identity text') WHERE length(trim(NEW.role,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_immutable BEFORE UPDATE ON atlas_media_links BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_retain BEFORE DELETE ON atlas_media_links BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_ingestions_collision BEFORE INSERT ON atlas_ingestions BEGIN
 SELECT RAISE(ABORT,'Stable ID collision: atlas_ingestions') WHERE EXISTS(SELECT 1 FROM atlas_ingestions x WHERE x.id=NEW.id AND NOT(x.id IS NEW.id AND x.fingerprint IS NEW.fingerprint AND x.counts IS NEW.counts));
 SELECT RAISE(ABORT,'Invalid stable ID') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_ingestions_immutable BEFORE UPDATE ON atlas_ingestions BEGIN SELECT RAISE(ABORT,'Evidence and identities are append-only'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_ingestions_retain BEFORE DELETE ON atlas_ingestions BEGIN SELECT RAISE(ABORT,'Archived evidence must be retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_parent BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Invalid adjacent geographic parent') WHERE
 (NEW.kind='continent' AND NEW.parent_id IS NOT NULL) OR
 (NEW.kind IN ('location','province','area','region','subcontinent') AND NOT EXISTS(SELECT 1 FROM atlas_entities p WHERE p.id=NEW.parent_id AND p.kind=CASE NEW.kind WHEN 'location' THEN 'province' WHEN 'province' THEN 'area' WHEN 'area' THEN 'region' WHEN 'region' THEN 'subcontinent' WHEN 'subcontinent' THEN 'continent' END)) OR
 (NEW.kind='settlement' AND NEW.parent_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_entities p WHERE p.id=NEW.parent_id AND p.kind='location')) OR
 (NEW.kind NOT IN ('location','province','area','region','subcontinent','continent','settlement') AND NEW.parent_id IS NOT NULL);
 SELECT RAISE(ABORT,'Entity lifetime exceeds source coverage') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND ((NEW.valid_from IS NOT NULL AND NEW.valid_from<s.supported_from) OR (NEW.valid_to IS NOT NULL AND NEW.valid_to>s.supported_to)));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_immutable BEFORE UPDATE ON atlas_entities BEGIN SELECT RAISE(ABORT,'Entity changes require an explicit sourced migration; identity is retained'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_contract BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute requires a location territory') WHERE NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND e.kind='location');
 SELECT RAISE(ABORT,'Category kind mismatch') WHERE NEW.category_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_categories c WHERE c.id=NEW.category_id AND c.kind=NEW.attribute);
 SELECT RAISE(ABORT,'Overlapping attribute evidence') WHERE EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND r.location_id=NEW.location_id AND r.attribute=NEW.attribute AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Attribute exceeds location lifetime') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.location_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
 SELECT RAISE(ABORT,'Uninhabited conflicts with settlement attributes') WHERE NEW.method='direct' AND EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id!=NEW.id AND r.location_id=NEW.location_id AND r.method='direct' AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND ((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='uninhabited' AND ((r.attribute='population' AND json_extract(r.value,'$')>0) OR (r.attribute='rank' AND json_type(r.value)!='null'))) OR (r.attribute='habitation' AND json_extract(r.value,'$')='uninhabited' AND ((NEW.attribute='population' AND json_extract(NEW.value,'$')>0) OR (NEW.attribute='rank' AND json_type(NEW.value)!='null')))));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_contract BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Overlapping preferred names') WHERE NEW.role='preferred' AND EXISTS(SELECT 1 FROM atlas_names n WHERE n.id!=NEW.id AND n.entity_id=NEW.entity_id AND n.language=NEW.language AND n.role='preferred' AND n.is_example=NEW.is_example AND n.valid_from<NEW.valid_to AND n.valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Name exceeds entity lifetime') WHERE EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_immutable BEFORE UPDATE ON atlas_media BEGIN SELECT RAISE(ABORT,'Registered media is immutable; new content needs a new digest and identity'); END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_source_interval BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_source_interval BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_source_interval BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_source_interval BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Record exceeds supported source interval') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND (NEW.valid_from<s.supported_from OR NEW.valid_to>s.supported_to));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_records_example_source BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_example_source BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_example_source BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Example source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_nonempty BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Attribute scalar must not be blank') WHERE json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$'),char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_entity_lifetime BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Relationship exceeds known entity lifetime') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.source_entity_id,NEW.target_entity_id) AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_entity_lifetime BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Media link exceeds known entity lifetime') WHERE NEW.valid_from IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND ((e.valid_from IS NOT NULL AND NEW.valid_from<e.valid_from) OR (e.valid_to IS NOT NULL AND NEW.valid_to>e.valid_to)));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_categories_entity_kind BEFORE INSERT ON atlas_categories BEGIN
 SELECT RAISE(ABORT,'Category must share a matching graph identity') WHERE NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.id AND e.kind=CASE NEW.kind WHEN 'owner' THEN 'polity' ELSE NEW.kind END);
END;
--> statement-breakpoint
CREATE TRIGGER atlas_entities_example_source BEFORE INSERT ON atlas_entities BEGIN
 SELECT RAISE(ABORT,'Example entity source must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example');
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_example_identity BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.is_example=1 AND (e.id=NEW.location_id OR e.id=NEW.category_id));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_names_example_identity BEFORE INSERT ON atlas_names BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND e.is_example=1);
END;
--> statement-breakpoint
CREATE TRIGGER atlas_relationships_example_identity BEFORE INSERT ON atlas_relationships BEGIN
 SELECT RAISE(ABORT,'Example identities must stay opt-in') WHERE NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.source_entity_id,NEW.target_entity_id) AND e.is_example=1);
END;
--> statement-breakpoint
CREATE TRIGGER atlas_media_links_example BEFORE INSERT ON atlas_media_links BEGIN
 SELECT RAISE(ABORT,'Example media must stay opt-in') WHERE NEW.is_example=0 AND (EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND s.status='example') OR EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND e.is_example=1) OR EXISTS(SELECT 1 FROM atlas_media m JOIN atlas_sources s ON s.id=m.source_id WHERE m.id=NEW.media_id AND s.status='example'));
END;
--> statement-breakpoint
CREATE TRIGGER atlas_attribute_source_class BEFORE INSERT ON atlas_attribute_records BEGIN
 SELECT RAISE(ABORT,'Source class must match evidence method') WHERE EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=NEW.source_id AND ((s.status='reference' AND NEW.method!='reference') OR (s.status='estimate' AND NEW.method!='estimate')));
END;
--> statement-breakpoint
