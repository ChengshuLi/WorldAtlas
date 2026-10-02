CREATE TABLE `atlas_geographic_changes` (
	`id` text PRIMARY KEY NOT NULL,
	`release_id` text NOT NULL,
	`old_entity_id` text,
	`new_entity_id` text,
	`change_type` text NOT NULL,
	`source_id` text NOT NULL,
	`evidence` text NOT NULL,
	FOREIGN KEY (`release_id`) REFERENCES `atlas_geographic_releases`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`old_entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`new_entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_change_text" CHECK(length(trim("atlas_geographic_changes"."id"))>0),
	CONSTRAINT "geographic_change_kind" CHECK("atlas_geographic_changes"."change_type" IN ('retain','rename','reparent','merge','split','replace','retire','create')),
	CONSTRAINT "geographic_change_endpoints" CHECK(("atlas_geographic_changes"."change_type"='create' AND "atlas_geographic_changes"."old_entity_id" IS NULL AND "atlas_geographic_changes"."new_entity_id" IS NOT NULL) OR ("atlas_geographic_changes"."change_type"='retire' AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."new_entity_id" IS NULL) OR ("atlas_geographic_changes"."change_type" IN ('retain','rename','reparent') AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."old_entity_id"="atlas_geographic_changes"."new_entity_id") OR ("atlas_geographic_changes"."change_type" IN ('merge','split','replace') AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."new_entity_id" IS NOT NULL AND "atlas_geographic_changes"."old_entity_id"!="atlas_geographic_changes"."new_entity_id")),
	CONSTRAINT "geographic_change_evidence" CHECK(json_valid("atlas_geographic_changes"."evidence") AND json_type("atlas_geographic_changes"."evidence")='object')
);
--> statement-breakpoint
CREATE INDEX `geographic_changes_page` ON `atlas_geographic_changes` (`release_id`,`id`);--> statement-breakpoint
CREATE INDEX `geographic_changes_old` ON `atlas_geographic_changes` (`old_entity_id`,`release_id`);--> statement-breakpoint
CREATE TABLE `atlas_geographic_memberships` (
	`release_id` text NOT NULL,
	`entity_id` text NOT NULL,
	`parent_id` text,
	`reference_name` text,
	`active` integer DEFAULT 1 NOT NULL,
	`source_id` text NOT NULL,
	`evidence` text DEFAULT '{}' NOT NULL,
	PRIMARY KEY(`release_id`, `entity_id`),
	FOREIGN KEY (`release_id`) REFERENCES `atlas_geographic_releases`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`entity_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`parent_id`) REFERENCES `atlas_entities`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_membership_active" CHECK("atlas_geographic_memberships"."active" IN (0,1)),
	CONSTRAINT "geographic_membership_name" CHECK("atlas_geographic_memberships"."reference_name" IS NULL OR length(trim("atlas_geographic_memberships"."reference_name"))>0),
	CONSTRAINT "geographic_membership_evidence" CHECK(json_valid("atlas_geographic_memberships"."evidence") AND json_type("atlas_geographic_memberships"."evidence")='object')
);
--> statement-breakpoint
CREATE INDEX `geographic_membership_parent` ON `atlas_geographic_memberships` (`release_id`,`active`,`parent_id`,`entity_id`);--> statement-breakpoint
CREATE INDEX `geographic_membership_page` ON `atlas_geographic_memberships` (`release_id`,`active`,`entity_id`);--> statement-breakpoint
CREATE TABLE `atlas_geographic_releases` (
	`id` text PRIMARY KEY NOT NULL,
	`source_id` text NOT NULL,
	`version` integer NOT NULL,
	`reference_date` text NOT NULL,
	`status` text DEFAULT 'staged' NOT NULL,
	`hierarchy_sha256` text NOT NULL,
	`footprints_sha256` text NOT NULL,
	`membership_sha256` text NOT NULL,
	`location_ids_sha256` text NOT NULL,
	`changes_sha256` text NOT NULL,
	`expected_counts` text NOT NULL,
	`metadata` text DEFAULT '{}' NOT NULL,
	`published_at` integer,
	FOREIGN KEY (`source_id`) REFERENCES `atlas_sources`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_release_text" CHECK(length(trim("atlas_geographic_releases"."id"))>0 AND length(trim("atlas_geographic_releases"."reference_date"))>0),
	CONSTRAINT "geographic_release_version" CHECK(typeof("atlas_geographic_releases"."version")='integer' AND "atlas_geographic_releases"."version">0),
	CONSTRAINT "geographic_release_status" CHECK(("atlas_geographic_releases"."status"='staged' AND "atlas_geographic_releases"."published_at" IS NULL) OR ("atlas_geographic_releases"."status"='published' AND typeof("atlas_geographic_releases"."published_at")='integer' AND "atlas_geographic_releases"."published_at">0)),
	CONSTRAINT "geographic_release_hashes" CHECK(length("atlas_geographic_releases"."hierarchy_sha256")=64 AND "atlas_geographic_releases"."hierarchy_sha256" NOT GLOB '*[^0-9a-f]*' AND length("atlas_geographic_releases"."footprints_sha256")=64 AND "atlas_geographic_releases"."footprints_sha256" NOT GLOB '*[^0-9a-f]*' AND length("atlas_geographic_releases"."membership_sha256")=64 AND "atlas_geographic_releases"."membership_sha256" NOT GLOB '*[^0-9a-f]*' AND length("atlas_geographic_releases"."location_ids_sha256")=64 AND "atlas_geographic_releases"."location_ids_sha256" NOT GLOB '*[^0-9a-f]*' AND length("atlas_geographic_releases"."changes_sha256")=64 AND "atlas_geographic_releases"."changes_sha256" NOT GLOB '*[^0-9a-f]*'),
	CONSTRAINT "geographic_release_counts" CHECK(json_valid("atlas_geographic_releases"."expected_counts") AND json_type("atlas_geographic_releases"."expected_counts")='object'),
	CONSTRAINT "geographic_release_metadata" CHECK(json_valid("atlas_geographic_releases"."metadata") AND json_type("atlas_geographic_releases"."metadata")='object')
);
--> statement-breakpoint
CREATE UNIQUE INDEX `geographic_releases_version` ON `atlas_geographic_releases` (`version`);--> statement-breakpoint
CREATE INDEX `geographic_releases_published` ON `atlas_geographic_releases` (`status`,`version`);--> statement-breakpoint
CREATE TRIGGER geographic_release_insert BEFORE INSERT ON atlas_geographic_releases BEGIN
 SELECT CASE WHEN NEW.status!='staged' THEN RAISE(ABORT,'Geographic release must begin staged') END;
 SELECT CASE WHEN (SELECT status FROM atlas_sources WHERE id=NEW.source_id)!='reference' THEN RAISE(ABORT,'Geographic release requires a reference source') END;
 SELECT CASE WHEN (SELECT count(*) FROM json_each(NEW.expected_counts))!=6 OR EXISTS(SELECT 1 FROM json_each(NEW.expected_counts) WHERE key NOT IN ('location','province','area','region','subcontinent','continent') OR type!='integer' OR value<0 OR value>9007199254740991) OR json_extract(NEW.expected_counts,'$.continent') IS NOT 6 THEN RAISE(ABORT,'Release manifest requires six tiers and six continents') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_releases r WHERE r.id=NEW.id AND (r.source_id IS NOT NEW.source_id OR r.version IS NOT NEW.version OR r.reference_date IS NOT NEW.reference_date OR r.hierarchy_sha256 IS NOT NEW.hierarchy_sha256 OR r.footprints_sha256 IS NOT NEW.footprints_sha256 OR r.membership_sha256 IS NOT NEW.membership_sha256 OR r.location_ids_sha256 IS NOT NEW.location_ids_sha256 OR r.changes_sha256 IS NOT NEW.changes_sha256 OR r.expected_counts IS NOT NEW.expected_counts OR r.metadata IS NOT NEW.metadata)) THEN RAISE(ABORT,'Stable geographic release ID collision') END;
END;
--> statement-breakpoint
CREATE TRIGGER geographic_membership_insert BEFORE INSERT ON atlas_geographic_memberships BEGIN
 SELECT CASE WHEN (SELECT status FROM atlas_geographic_releases WHERE id=NEW.release_id)!='staged' THEN RAISE(ABORT,'Published geographic memberships are immutable') END;
 SELECT CASE WHEN (SELECT status FROM atlas_sources WHERE id=NEW.source_id)!='reference' THEN RAISE(ABORT,'Geographic membership requires a reference source') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.entity_id AND (e.is_example!=0 OR e.kind NOT IN ('location','province','area','region','subcontinent','continent'))) THEN RAISE(ABORT,'Membership requires a non-example geographic identity') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_entities e JOIN atlas_entity_types t ON t.id=e.kind WHERE e.id=NEW.entity_id AND ((t.geographic_level=5 AND NEW.parent_id IS NOT NULL) OR (t.geographic_level<5 AND (NEW.parent_id IS NULL OR NOT EXISTS(SELECT 1 FROM atlas_entities p JOIN atlas_entity_types pt ON pt.id=p.kind WHERE p.id=NEW.parent_id AND p.is_example=0 AND pt.geographic_level=t.geographic_level+1))))) THEN RAISE(ABORT,'Reference membership must use an adjacent-tier parent') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_memberships m WHERE m.release_id=NEW.release_id AND m.entity_id=NEW.entity_id AND (m.parent_id IS NOT NEW.parent_id OR m.reference_name IS NOT NEW.reference_name OR m.active IS NOT NEW.active OR m.source_id IS NOT NEW.source_id OR m.evidence IS NOT NEW.evidence)) THEN RAISE(ABORT,'Stable geographic membership collision') END;
END;
--> statement-breakpoint
CREATE TRIGGER geographic_change_insert BEFORE INSERT ON atlas_geographic_changes BEGIN
 SELECT CASE WHEN (SELECT status FROM atlas_geographic_releases WHERE id=NEW.release_id)!='staged' THEN RAISE(ABORT,'Published geographic crosswalks are immutable') END;
 SELECT CASE WHEN (SELECT status FROM atlas_sources WHERE id=NEW.source_id)!='reference' THEN RAISE(ABORT,'Geographic change requires a reference source') END;
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM json_each(NEW.evidence)) THEN RAISE(ABORT,'Geographic change requires explicit source evidence') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.old_entity_id,NEW.new_entity_id) AND (e.is_example!=0 OR e.kind NOT IN ('location','province','area','region','subcontinent','continent'))) THEN RAISE(ABORT,'Crosswalk requires non-example geographic identities') END;
 SELECT CASE WHEN NEW.old_entity_id IS NOT NULL AND NEW.new_entity_id IS NOT NULL AND (SELECT kind FROM atlas_entities WHERE id=NEW.old_entity_id) IS NOT (SELECT kind FROM atlas_entities WHERE id=NEW.new_entity_id) THEN RAISE(ABORT,'Geographic crosswalk endpoints must stay in tier') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_changes c WHERE c.id=NEW.id AND (c.release_id IS NOT NEW.release_id OR c.old_entity_id IS NOT NEW.old_entity_id OR c.new_entity_id IS NOT NEW.new_entity_id OR c.change_type IS NOT NEW.change_type OR c.source_id IS NOT NEW.source_id OR c.evidence IS NOT NEW.evidence)) THEN RAISE(ABORT,'Stable geographic change ID collision') END;
END;
--> statement-breakpoint
CREATE TRIGGER geographic_release_update BEFORE UPDATE ON atlas_geographic_releases BEGIN
 SELECT CASE WHEN OLD.status='published' OR NEW.status!='published' OR NEW.id IS NOT OLD.id OR NEW.source_id IS NOT OLD.source_id OR NEW.version IS NOT OLD.version OR NEW.reference_date IS NOT OLD.reference_date OR NEW.hierarchy_sha256 IS NOT OLD.hierarchy_sha256 OR NEW.footprints_sha256 IS NOT OLD.footprints_sha256 OR NEW.membership_sha256 IS NOT OLD.membership_sha256 OR NEW.location_ids_sha256 IS NOT OLD.location_ids_sha256 OR NEW.changes_sha256 IS NOT OLD.changes_sha256 OR NEW.expected_counts IS NOT OLD.expected_counts OR NEW.metadata IS NOT OLD.metadata THEN RAISE(ABORT,'Geographic release definitions are immutable') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_releases WHERE status='published' AND version>=NEW.version) THEN RAISE(ABORT,'Published release versions must advance') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM json_each(NEW.expected_counts) c WHERE c.value!=(SELECT count(*) FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=NEW.id AND m.active=1 AND e.kind=c.key)) THEN RAISE(ABORT,'Geographic release manifest count mismatch') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id LEFT JOIN atlas_geographic_memberships p ON p.release_id=m.release_id AND p.entity_id=m.parent_id AND p.active=1 WHERE m.release_id=NEW.id AND m.active=1 AND e.kind!='continent' AND p.entity_id IS NULL) THEN RAISE(ABORT,'Incomplete active reference parent chain') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=NEW.id AND m.active=1 AND e.kind!='location' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships c WHERE c.release_id=m.release_id AND c.parent_id=m.entity_id AND c.active=1)) THEN RAISE(ABORT,'Active geographic group has no member territory') END;
 SELECT CASE WHEN EXISTS(SELECT 1 FROM atlas_geographic_changes c LEFT JOIN atlas_geographic_memberships n ON n.release_id=c.release_id AND n.entity_id=c.new_entity_id AND n.active=1 LEFT JOIN atlas_geographic_memberships o ON o.release_id=c.release_id AND o.entity_id=c.old_entity_id AND o.active=1 WHERE c.release_id=NEW.id AND ((c.new_entity_id IS NOT NULL AND n.entity_id IS NULL) OR (c.change_type IN ('merge','split','replace','retire') AND o.entity_id IS NOT NULL))) THEN RAISE(ABORT,'Geographic crosswalk must agree with active reference membership') END;
END;
--> statement-breakpoint
CREATE TRIGGER geographic_release_delete BEFORE DELETE ON atlas_geographic_releases BEGIN SELECT RAISE(ABORT,'Geographic releases are retained'); END;
--> statement-breakpoint
CREATE TRIGGER geographic_membership_update BEFORE UPDATE ON atlas_geographic_memberships BEGIN SELECT RAISE(ABORT,'Geographic memberships are immutable'); END;
--> statement-breakpoint
CREATE TRIGGER geographic_membership_delete BEFORE DELETE ON atlas_geographic_memberships BEGIN SELECT RAISE(ABORT,'Geographic memberships are retained'); END;
--> statement-breakpoint
CREATE TRIGGER geographic_change_update BEFORE UPDATE ON atlas_geographic_changes BEGIN SELECT RAISE(ABORT,'Geographic crosswalks are immutable'); END;
--> statement-breakpoint
CREATE TRIGGER geographic_change_delete BEFORE DELETE ON atlas_geographic_changes BEGIN SELECT RAISE(ABORT,'Geographic crosswalks are retained'); END;
