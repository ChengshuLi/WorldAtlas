-- WorldAtlas PostgreSQL foundation. Apply once to an empty schema.
-- Equivalent persistent content contract to frozen SQLite migrations 0000..0007.
-- JSON evidence stays TEXT: original whitespace/key order/value bytes are retained.
-- Do not rerun this file on a populated database; future changes are new migrations.
BEGIN;
CREATE DOMAIN atlas_year_start AS numeric CHECK (VALUE=trunc(VALUE) AND VALUE BETWEEN -3000 AND 2026 AND VALUE<>0);
CREATE DOMAIN atlas_year_end AS numeric CHECK (VALUE=trunc(VALUE) AND VALUE BETWEEN -2999 AND 2027 AND VALUE<>0);
CREATE SEQUENCE atlas_ingestions_rowid_seq AS bigint;
CREATE FUNCTION atlas_next_ingestion_rowid() RETURNS bigint LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(807245315,1);
 RETURN nextval('atlas_ingestions_rowid_seq');
END $$;
CREATE FUNCTION atlas_nonblank(value text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT value IS NOT NULL AND length(btrim(value,U&'\0009\000A\000B\000C\000D\0020\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000\FEFF'))>0
$$;
CREATE FUNCTION json_valid(value text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN PERFORM value::json; RETURN value IS NOT NULL; EXCEPTION WHEN invalid_text_representation THEN RETURN false; END $$;
CREATE FUNCTION atlas_json_at(value text,path text DEFAULT '$') RETURNS json LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE keys text[];
BEGIN
 IF path='$' THEN RETURN value::json; END IF;
 IF left(path,2)<>'$.' THEN RAISE EXCEPTION 'Unsupported atlas JSON path'; END IF;
 keys:=string_to_array(substr(path,3),'.'); RETURN value::json #> keys;
END $$;
CREATE FUNCTION json_type(value text,path text DEFAULT '$') RETURNS text LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE item json; kind text; token text;
BEGIN
 item:=atlas_json_at(value,path); IF item IS NULL THEN RETURN NULL; END IF;
 kind:=json_typeof(item); token:=btrim(item::text,E' \t\n\r');
 IF kind='string' THEN RETURN 'text'; END IF;
 IF kind='number' THEN RETURN CASE WHEN token ~ '^-?(0|[1-9][0-9]*)$' THEN 'integer' ELSE 'real' END; END IF;
 IF kind='boolean' THEN RETURN token; END IF;
 RETURN kind;
END $$;
CREATE FUNCTION json_extract(value text,path text DEFAULT '$') RETURNS text LANGUAGE sql IMMUTABLE AS $$
 SELECT atlas_json_at(value,path) #>> '{}'
$$;
CREATE FUNCTION json_each(input_json text,path text DEFAULT '$') RETURNS TABLE(key text,value text,type text) LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE item json;
BEGIN
 item:=atlas_json_at(input_json,path);
 IF json_typeof(item)='object' THEN RETURN QUERY SELECT p.key,p.value #>> '{}',json_type(p.value::text) FROM pg_catalog.json_each(item) p;
 ELSIF json_typeof(item)='array' THEN RETURN QUERY SELECT (p.ordinality-1)::text,p.value #>> '{}',json_type(p.value::text) FROM json_array_elements(item) WITH ORDINALITY p(value,ordinality);
 END IF;
END $$;
CREATE FUNCTION instr(value text,needle text) RETURNS integer LANGUAGE sql IMMUTABLE AS $$ SELECT strpos(value,needle) $$;

CREATE TABLE atlas_sources (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"url" text COLLATE "C",
	"license" text COLLATE "C" NOT NULL,
	"vintage" text COLLATE "C" NOT NULL,
	"supported_from" atlas_year_start NOT NULL,
	"supported_to" atlas_year_end NOT NULL,
	"status" text COLLATE "C" NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	CONSTRAINT "source_text" CHECK(length(trim("atlas_sources"."id"))>0 AND length(trim("atlas_sources"."name"))>0 AND length(trim("atlas_sources"."license"))>0 AND length(trim("atlas_sources"."vintage"))>0),
	CONSTRAINT "source_dates" CHECK("atlas_sources"."supported_from" BETWEEN -3000 AND 2026 AND "atlas_sources"."supported_from"!=0 AND "atlas_sources"."supported_to" BETWEEN -2999 AND 2027 AND "atlas_sources"."supported_to"!=0 AND "atlas_sources"."supported_to">"atlas_sources"."supported_from"),
	CONSTRAINT "source_status" CHECK("atlas_sources"."status" IN ('historical','reference','estimate','example')),
	CONSTRAINT "source_metadata" CHECK(json_valid("atlas_sources"."metadata") AND json_type("atlas_sources"."metadata")='object')
);

CREATE TABLE atlas_entity_types (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"geographic_level" integer,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	CONSTRAINT "entity_type_text" CHECK(length(trim("atlas_entity_types"."id"))>0 AND length(trim("atlas_entity_types"."name"))>0),
	CONSTRAINT "entity_type_level" CHECK(("atlas_entity_types"."id" IN ('location','province','area','region','subcontinent','continent') AND "atlas_entity_types"."geographic_level" IS NOT NULL AND "atlas_entity_types"."geographic_level"=CASE "atlas_entity_types"."id" WHEN 'location' THEN 0 WHEN 'province' THEN 1 WHEN 'area' THEN 2 WHEN 'region' THEN 3 WHEN 'subcontinent' THEN 4 WHEN 'continent' THEN 5 END) OR ("atlas_entity_types"."id" NOT IN ('location','province','area','region','subcontinent','continent') AND "atlas_entity_types"."geographic_level" IS NULL)),
	CONSTRAINT "entity_type_metadata" CHECK(json_valid("atlas_entity_types"."metadata") AND json_type("atlas_entity_types"."metadata")='object')
);

CREATE TABLE atlas_entities (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"kind" text COLLATE "C" NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"parent_id" text COLLATE "C",
	"valid_from" atlas_year_start,
	"valid_to" atlas_year_end,
	"source_id" text COLLATE "C",
	"reference_owner" text COLLATE "C",
	"is_example" integer DEFAULT 0 NOT NULL,
	"active" integer DEFAULT 1 NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("kind") REFERENCES "atlas_entity_types"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("parent_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "entity_text" CHECK(length(trim("atlas_entities"."id"))>0 AND length(trim("atlas_entities"."name"))>0),
	CONSTRAINT "entity_dates" CHECK(("atlas_entities"."valid_from" IS NULL OR "atlas_entities"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_entities"."valid_from"!=0) AND ("atlas_entities"."valid_to" IS NULL OR "atlas_entities"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_entities"."valid_to"!=0) AND ("atlas_entities"."valid_from" IS NULL OR "atlas_entities"."valid_to" IS NULL OR "atlas_entities"."valid_to">"atlas_entities"."valid_from") AND (("atlas_entities"."valid_from" IS NULL AND "atlas_entities"."valid_to" IS NULL) OR "atlas_entities"."source_id" IS NOT NULL)),
	CONSTRAINT "entity_example" CHECK("atlas_entities"."is_example" IN (0,1)),
	CONSTRAINT "entity_active" CHECK("atlas_entities"."active" IN (0,1)),
	CONSTRAINT "entity_metadata" CHECK(json_valid("atlas_entities"."metadata") AND json_type("atlas_entities"."metadata")='object')
);

CREATE TABLE atlas_categories (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"kind" text COLLATE "C" NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "category_text" CHECK(length(trim("atlas_categories"."id"))>0 AND length(trim("atlas_categories"."name"))>0),
	CONSTRAINT "category_kind" CHECK("atlas_categories"."kind" IN ('owner','culture','religion')),
	CONSTRAINT "category_metadata" CHECK(json_valid("atlas_categories"."metadata") AND json_type("atlas_categories"."metadata")='object')
);

CREATE TABLE atlas_attribute_records (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"location_id" text COLLATE "C" NOT NULL,
	"attribute" text COLLATE "C" NOT NULL,
	"value" text COLLATE "C" NOT NULL,
	"category_id" text COLLATE "C",
	"valid_from" atlas_year_start NOT NULL,
	"valid_to" atlas_year_end NOT NULL,
	"method" text COLLATE "C" NOT NULL,
	"status" text COLLATE "C" NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"is_example" integer DEFAULT 0 NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("location_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("category_id") REFERENCES "atlas_categories"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "attribute_names" CHECK("atlas_attribute_records"."attribute" IN ('owner','population','culture','religion','rank','topography','vegetation','climate','habitation')),
	CONSTRAINT "attribute_dates" CHECK("atlas_attribute_records"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_attribute_records"."valid_from"!=0 AND "atlas_attribute_records"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_attribute_records"."valid_to"!=0 AND "atlas_attribute_records"."valid_to">"atlas_attribute_records"."valid_from"),
	CONSTRAINT "attribute_value" CHECK(CASE WHEN json_type(value)='null' THEN true WHEN attribute='population' THEN json_type(value)='integer' AND (json_extract(value))::numeric BETWEEN 0 AND 9007199254740991 WHEN json_type(value)='text' THEN atlas_nonblank(json_extract(value)) ELSE false END),
	CONSTRAINT "attribute_category" CHECK(("atlas_attribute_records"."attribute" NOT IN ('owner','culture','religion') OR json_type("atlas_attribute_records"."value")='null' OR "atlas_attribute_records"."category_id" IS NOT NULL) AND ("atlas_attribute_records"."category_id" IS NULL OR ("atlas_attribute_records"."attribute" IN ('owner','culture','religion') AND json_type("atlas_attribute_records"."value")='text'))),
	CONSTRAINT "attribute_rank" CHECK("atlas_attribute_records"."attribute"!='rank' OR json_type("atlas_attribute_records"."value")='null' OR json_extract("atlas_attribute_records"."value",'$') IN ('unsettled','rural settlement','town','city','metropolis')),
	CONSTRAINT "attribute_habitation" CHECK("atlas_attribute_records"."attribute"!='habitation' OR json_type("atlas_attribute_records"."value")='null' OR json_extract("atlas_attribute_records"."value",'$') IN ('inhabited','uninhabited','unknown')),
	CONSTRAINT "attribute_method" CHECK("atlas_attribute_records"."method" IN ('direct','majority-area','derived','reference','estimate')),
	CONSTRAINT "attribute_status" CHECK("atlas_attribute_records"."status" IN ('sourced','derived','reference','estimate','unknown','disputed','no-majority','example')),
	CONSTRAINT "attribute_example" CHECK("atlas_attribute_records"."is_example" IN (0,1)),
	CONSTRAINT "attribute_metadata" CHECK(json_valid("atlas_attribute_records"."metadata") AND json_type("atlas_attribute_records"."metadata")='object')
);

CREATE TABLE atlas_ingestions (
 "rowid" bigint NOT NULL DEFAULT atlas_next_ingestion_rowid() UNIQUE,
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"fingerprint" text COLLATE "C" NOT NULL,
	"counts" text COLLATE "C" NOT NULL,
	"created_at" bigint NOT NULL,
	CONSTRAINT "ingestion_counts" CHECK(json_valid("atlas_ingestions"."counts") AND json_type("atlas_ingestions"."counts")='object'),
	CONSTRAINT "ingestion_fingerprint" CHECK(length("atlas_ingestions"."fingerprint")=64)
);

CREATE TABLE atlas_media (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"object_key" text COLLATE "C" NOT NULL,
	"sha256" text NOT NULL,
	"bytes" bigint NOT NULL,
	"mime" text COLLATE "C" NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"license" text COLLATE "C" NOT NULL,
	"attribution" text COLLATE "C" NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"status" text COLLATE "C" DEFAULT 'ready' NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "media_digest" CHECK(length("atlas_media"."sha256")=64 AND "atlas_media"."sha256" ~ '^[0-9a-f]{64}$' AND "atlas_media"."object_key"='media/'||"atlas_media"."sha256"),
	CONSTRAINT "media_bytes" CHECK("atlas_media"."bytes">=0 AND "atlas_media"."bytes"<=9007199254740991),
	CONSTRAINT "media_text" CHECK(length(trim("atlas_media"."object_key"))>0 AND length(trim("atlas_media"."mime"))>0 AND length(trim("atlas_media"."name"))>0 AND length(trim("atlas_media"."license"))>0 AND length(trim("atlas_media"."attribution"))>0),
	CONSTRAINT "media_status" CHECK("atlas_media"."status" IN ('pending','ready','published')),
	CONSTRAINT "media_metadata" CHECK(json_valid("atlas_media"."metadata") AND json_type("atlas_media"."metadata")='object')
);

CREATE TABLE atlas_media_links (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"media_id" text COLLATE "C" NOT NULL,
	"entity_id" text COLLATE "C" NOT NULL,
	"role" text COLLATE "C" NOT NULL,
	"caption" text COLLATE "C",
	"source_id" text COLLATE "C" NOT NULL,
	"is_example" integer DEFAULT 0 NOT NULL,
	"valid_from" atlas_year_start,
	"valid_to" atlas_year_end,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("media_id") REFERENCES "atlas_media"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "media_link_example" CHECK("atlas_media_links"."is_example" IN (0,1)),
	CONSTRAINT "media_link_role" CHECK(length(trim("atlas_media_links"."role"))>0),
	CONSTRAINT "media_link_dates" CHECK(("atlas_media_links"."valid_from" IS NULL AND "atlas_media_links"."valid_to" IS NULL) OR ("atlas_media_links"."valid_from" IS NOT NULL AND "atlas_media_links"."valid_to" IS NOT NULL AND "atlas_media_links"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_media_links"."valid_from"!=0 AND "atlas_media_links"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_media_links"."valid_to"!=0 AND "atlas_media_links"."valid_to">"atlas_media_links"."valid_from")),
	CONSTRAINT "media_link_metadata" CHECK(json_valid("atlas_media_links"."metadata") AND json_type("atlas_media_links"."metadata")='object')
);

CREATE TABLE atlas_names (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"entity_id" text COLLATE "C" NOT NULL,
	"name" text COLLATE "C" NOT NULL,
	"language" text COLLATE "C" DEFAULT 'und' NOT NULL,
	"role" text COLLATE "C" DEFAULT 'preferred' NOT NULL,
	"valid_from" atlas_year_start NOT NULL,
	"valid_to" atlas_year_end NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"is_example" integer DEFAULT 0 NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "name_text" CHECK(length(trim("atlas_names"."name"))>0 AND length(trim("atlas_names"."language"))>0),
	CONSTRAINT "name_role" CHECK("atlas_names"."role" IN ('preferred','alias')),
	CONSTRAINT "name_dates" CHECK("atlas_names"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_names"."valid_from"!=0 AND "atlas_names"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_names"."valid_to"!=0 AND "atlas_names"."valid_to">"atlas_names"."valid_from"),
	CONSTRAINT "name_example" CHECK("atlas_names"."is_example" IN (0,1)),
	CONSTRAINT "name_metadata" CHECK(json_valid("atlas_names"."metadata") AND json_type("atlas_names"."metadata")='object')
);

CREATE TABLE atlas_relationships (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"source_entity_id" text COLLATE "C" NOT NULL,
	"target_entity_id" text COLLATE "C" NOT NULL,
	"relationship_type" text COLLATE "C" NOT NULL,
	"valid_from" atlas_year_start,
	"valid_to" atlas_year_end,
	"source_id" text COLLATE "C" NOT NULL,
	"is_example" integer DEFAULT 0 NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("source_entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("target_entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "relationship_text" CHECK(length(trim("atlas_relationships"."relationship_type"))>0),
	CONSTRAINT "relationship_dates" CHECK(("atlas_relationships"."valid_from" IS NULL AND "atlas_relationships"."valid_to" IS NULL) OR ("atlas_relationships"."valid_from" IS NOT NULL AND "atlas_relationships"."valid_to" IS NOT NULL AND "atlas_relationships"."valid_from" BETWEEN -3000 AND 2026 AND "atlas_relationships"."valid_from"!=0 AND "atlas_relationships"."valid_to" BETWEEN -2999 AND 2027 AND "atlas_relationships"."valid_to"!=0 AND "atlas_relationships"."valid_to">"atlas_relationships"."valid_from")),
	CONSTRAINT "relationship_example" CHECK("atlas_relationships"."is_example" IN (0,1)),
	CONSTRAINT "relationship_metadata" CHECK(json_valid("atlas_relationships"."metadata") AND json_type("atlas_relationships"."metadata")='object')
);

CREATE TABLE atlas_evidence_retirements (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"collection" text COLLATE "C" NOT NULL,
	"target_id" text COLLATE "C" NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"reason" text COLLATE "C" NOT NULL,
	"replacement_id" text COLLATE "C",
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "retirement_collection" CHECK("atlas_evidence_retirements"."collection" IN ('records','names','relationships','media_links')),
	CONSTRAINT "retirement_text" CHECK(length(trim("atlas_evidence_retirements"."id"))>0 AND length(trim("atlas_evidence_retirements"."target_id"))>0 AND length(trim("atlas_evidence_retirements"."reason"))>0),
	CONSTRAINT "retirement_replacement" CHECK("atlas_evidence_retirements"."replacement_id" IS NULL OR (length(trim("atlas_evidence_retirements"."replacement_id"))>0 AND "atlas_evidence_retirements"."replacement_id"!="atlas_evidence_retirements"."target_id")),
	CONSTRAINT "retirement_metadata" CHECK(json_valid("atlas_evidence_retirements"."metadata") AND json_type("atlas_evidence_retirements"."metadata")='object')
);

CREATE TABLE atlas_geographic_releases (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"version" integer NOT NULL,
	"reference_date" text COLLATE "C" NOT NULL,
	"status" text COLLATE "C" DEFAULT 'staged' NOT NULL,
	"hierarchy_sha256" text NOT NULL,
	"footprints_sha256" text NOT NULL,
	"membership_sha256" text NOT NULL,
	"location_ids_sha256" text NOT NULL,
	"changes_sha256" text NOT NULL,
	"expected_counts" text COLLATE "C" NOT NULL,
	"metadata" text COLLATE "C" DEFAULT '{}' NOT NULL,
	"published_at" bigint,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_release_text" CHECK(length(trim("atlas_geographic_releases"."id"))>0 AND length(trim("atlas_geographic_releases"."reference_date"))>0),
	CONSTRAINT "geographic_release_version" CHECK("atlas_geographic_releases"."version">0),
	CONSTRAINT "geographic_release_status" CHECK(("atlas_geographic_releases"."status"='staged' AND "atlas_geographic_releases"."published_at" IS NULL) OR ("atlas_geographic_releases"."status"='published' AND "atlas_geographic_releases"."published_at">0)),
	CONSTRAINT "geographic_release_hashes" CHECK(length("atlas_geographic_releases"."hierarchy_sha256")=64 AND "atlas_geographic_releases"."hierarchy_sha256" ~ '^[0-9a-f]{64}$' AND length("atlas_geographic_releases"."footprints_sha256")=64 AND "atlas_geographic_releases"."footprints_sha256" ~ '^[0-9a-f]{64}$' AND length("atlas_geographic_releases"."membership_sha256")=64 AND "atlas_geographic_releases"."membership_sha256" ~ '^[0-9a-f]{64}$' AND length("atlas_geographic_releases"."location_ids_sha256")=64 AND "atlas_geographic_releases"."location_ids_sha256" ~ '^[0-9a-f]{64}$' AND length("atlas_geographic_releases"."changes_sha256")=64 AND "atlas_geographic_releases"."changes_sha256" ~ '^[0-9a-f]{64}$'),
	CONSTRAINT "geographic_release_counts" CHECK(json_valid("atlas_geographic_releases"."expected_counts") AND json_type("atlas_geographic_releases"."expected_counts")='object'),
	CONSTRAINT "geographic_release_metadata" CHECK(json_valid("atlas_geographic_releases"."metadata") AND json_type("atlas_geographic_releases"."metadata")='object')
);

CREATE TABLE atlas_geographic_memberships (
	"release_id" text COLLATE "C" NOT NULL,
	"entity_id" text COLLATE "C" NOT NULL,
	"parent_id" text COLLATE "C",
	"reference_name" text COLLATE "C",
	"active" integer DEFAULT 1 NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"evidence" text COLLATE "C" DEFAULT '{}' NOT NULL,
	PRIMARY KEY("release_id", "entity_id"),
	FOREIGN KEY ("release_id") REFERENCES "atlas_geographic_releases"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("parent_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_membership_active" CHECK("atlas_geographic_memberships"."active" IN (0,1)),
	CONSTRAINT "geographic_membership_name" CHECK("atlas_geographic_memberships"."reference_name" IS NULL OR length(trim("atlas_geographic_memberships"."reference_name"))>0),
	CONSTRAINT "geographic_membership_evidence" CHECK(json_valid("atlas_geographic_memberships"."evidence") AND json_type("atlas_geographic_memberships"."evidence")='object')
);

CREATE TABLE atlas_geographic_changes (
	"id" text COLLATE "C" PRIMARY KEY NOT NULL,
	"release_id" text COLLATE "C" NOT NULL,
	"old_entity_id" text COLLATE "C",
	"new_entity_id" text COLLATE "C",
	"change_type" text COLLATE "C" NOT NULL,
	"source_id" text COLLATE "C" NOT NULL,
	"evidence" text COLLATE "C" NOT NULL,
	FOREIGN KEY ("release_id") REFERENCES "atlas_geographic_releases"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("old_entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("new_entity_id") REFERENCES "atlas_entities"("id") ON UPDATE no action ON DELETE no action,
	FOREIGN KEY ("source_id") REFERENCES "atlas_sources"("id") ON UPDATE no action ON DELETE no action,
	CONSTRAINT "geographic_change_text" CHECK(length(trim("atlas_geographic_changes"."id"))>0),
	CONSTRAINT "geographic_change_kind" CHECK("atlas_geographic_changes"."change_type" IN ('retain','rename','reparent','merge','split','replace','retire','create')),
	CONSTRAINT "geographic_change_endpoints" CHECK(("atlas_geographic_changes"."change_type"='create' AND "atlas_geographic_changes"."old_entity_id" IS NULL AND "atlas_geographic_changes"."new_entity_id" IS NOT NULL) OR ("atlas_geographic_changes"."change_type"='retire' AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."new_entity_id" IS NULL) OR ("atlas_geographic_changes"."change_type" IN ('retain','rename','reparent') AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."old_entity_id"="atlas_geographic_changes"."new_entity_id") OR ("atlas_geographic_changes"."change_type" IN ('merge','split','replace') AND "atlas_geographic_changes"."old_entity_id" IS NOT NULL AND "atlas_geographic_changes"."new_entity_id" IS NOT NULL AND "atlas_geographic_changes"."old_entity_id"!="atlas_geographic_changes"."new_entity_id")),
	CONSTRAINT "geographic_change_evidence" CHECK(json_valid("atlas_geographic_changes"."evidence") AND json_type("atlas_geographic_changes"."evidence")='object')
);

CREATE INDEX "attributes_location_dates" ON "atlas_attribute_records" ("location_id","attribute","valid_from","valid_to");

CREATE INDEX "attributes_date_id" ON "atlas_attribute_records" ("valid_from","valid_to","id");

CREATE INDEX "entities_kind_id" ON "atlas_entities" ("kind","active","id");

CREATE INDEX "entities_parent" ON "atlas_entities" ("parent_id");

CREATE UNIQUE INDEX "atlas_media_object_key_unique" ON "atlas_media" ("object_key");

CREATE INDEX "media_links_entity" ON "atlas_media_links" ("entity_id");

CREATE INDEX "names_entity_dates" ON "atlas_names" ("entity_id","valid_from","valid_to");

CREATE INDEX "relationships_source_dates" ON "atlas_relationships" ("source_entity_id","valid_from","valid_to");

CREATE INDEX "relationships_target_dates" ON "atlas_relationships" ("target_entity_id","valid_from","valid_to");

CREATE UNIQUE INDEX "retirements_target" ON "atlas_evidence_retirements" ("collection","target_id");

CREATE INDEX "geographic_changes_page" ON "atlas_geographic_changes" ("release_id","id");

CREATE INDEX "geographic_changes_old" ON "atlas_geographic_changes" ("old_entity_id","release_id");

CREATE INDEX "geographic_membership_parent" ON "atlas_geographic_memberships" ("release_id","active","parent_id","entity_id");

CREATE INDEX "geographic_membership_page" ON "atlas_geographic_memberships" ("release_id","active","entity_id");

CREATE UNIQUE INDEX "geographic_releases_version" ON "atlas_geographic_releases" ("version");

CREATE INDEX "geographic_releases_published" ON "atlas_geographic_releases" ("status","version");
-- No runtime bypass setting: restoring legacy evidence is an owner-only verified
-- maintenance transaction that temporarily disables USER triggers with writes paused.
CREATE FUNCTION atlas_immutable_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior jsonb; incoming jsonb; identity text; keys text[];
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Evidence and identities are append-only: '||TG_TABLE_NAME; END IF;
 incoming:=to_jsonb(NEW);
 IF TG_TABLE_NAME='atlas_geographic_memberships' THEN
  identity:=NEW.release_id||'/'||NEW.entity_id;
  EXECUTE format('SELECT to_jsonb(r) FROM %I r WHERE release_id=$1 AND entity_id=$2',TG_TABLE_NAME) INTO prior USING NEW.release_id,NEW.entity_id;
 ELSE
  identity:=NEW.id;
 END IF;
 IF NOT atlas_nonblank(identity) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Invalid stable ID'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(TG_TABLE_NAME||':'||identity,0));
 IF TG_TABLE_NAME='atlas_geographic_memberships' THEN
  EXECUTE format('SELECT to_jsonb(r) FROM %I r WHERE release_id=$1 AND entity_id=$2',TG_TABLE_NAME) INTO prior USING NEW.release_id,NEW.entity_id;
 ELSE
  EXECUTE format('SELECT to_jsonb(r) FROM %I r WHERE id=$1',TG_TABLE_NAME) INTO prior USING NEW.id;
 END IF;
 IF TG_TABLE_NAME='atlas_ingestions' THEN incoming:=incoming-'rowid'-'created_at'; prior:=prior-'rowid'-'created_at'; END IF;
 IF TG_TABLE_NAME='atlas_geographic_releases' THEN incoming:=incoming-'status'-'published_at'; prior:=prior-'status'-'published_at'; END IF;
 IF prior IS NOT NULL THEN
  IF prior IS DISTINCT FROM incoming THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Stable ID collision: '||TG_TABLE_NAME; END IF;
  RETURN NULL; -- Identical retry never rewrites original bytes or timestamps.
 END IF;
 FOR identity IN SELECT unnest(CASE TG_TABLE_NAME
  WHEN 'atlas_sources' THEN ARRAY['name','license','vintage']
  WHEN 'atlas_entity_types' THEN ARRAY['name'] WHEN 'atlas_entities' THEN ARRAY['name']
  WHEN 'atlas_categories' THEN ARRAY['name'] WHEN 'atlas_names' THEN ARRAY['name','language','role']
  WHEN 'atlas_relationships' THEN ARRAY['relationship_type']
  WHEN 'atlas_media' THEN ARRAY['name','license','attribution','mime']
  WHEN 'atlas_media_links' THEN ARRAY['role']
  WHEN 'atlas_evidence_retirements' THEN ARRAY['target_id','reason'] ELSE ARRAY[]::text[] END)
 LOOP IF NOT atlas_nonblank(incoming->>identity) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Empty source or identity text'; END IF; END LOOP;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas_claim_exists(collection text,identity text) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE exists_claim boolean; table_name text;
BEGIN
 table_name:=CASE collection WHEN 'records' THEN 'atlas_attribute_records' WHEN 'names' THEN 'atlas_names' WHEN 'relationships' THEN 'atlas_relationships' WHEN 'media_links' THEN 'atlas_media_links' END;
 IF table_name IS NULL THEN RETURN false; END IF;
 EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I WHERE id=$1)',table_name) INTO exists_claim USING identity; RETURN exists_claim;
END $$;
CREATE FUNCTION atlas_is_retired(collection text,identity text) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM atlas_evidence_retirements t WHERE t.collection=$1 AND t.target_id=$2)
$$;
CREATE FUNCTION atlas_metadata_zero(metadata text,key text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT coalesce(json_type(metadata,'$.'||key) IN ('null','false') OR json_type(metadata,'$.'||key) IN ('integer','real') AND json_extract(metadata,'$.'||key)::numeric=0,json_type(metadata,'$.'||key) IS NULL)
$$;
CREATE FUNCTION atlas_literal_zero(attribute text,value text,method text,status text,source_id text,metadata text) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN attribute='population' AND method='direct' AND status='sourced' AND json_type(value)='integer' THEN
  json_extract(value)::numeric=0 AND EXISTS(SELECT 1 FROM atlas_sources s WHERE s.id=source_id AND s.status NOT IN ('estimate','example'))
  AND NOT EXISTS(SELECT 1 FROM unnest(ARRAY['estimate','estimated','is_estimate','modeled','modelled','rounded','legacy_snapshot','legacy_attributes']) flag WHERE NOT atlas_metadata_zero(metadata,flag))
  AND coalesce(json_type(metadata,'$.rounding'),'null')='null' AND coalesce(json_type(metadata,'$.model'),'null')='null'
  AND lower(coalesce(json_extract(metadata,'$.precision'),'')) !~ '(round|model|estimate|approx)' ELSE false END
$$;
CREATE FUNCTION atlas_settlement_polarity(attribute text,value text,method text,status text,source_id text,metadata text) RETURNS integer LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN attribute='habitation' AND json_extract(value)='uninhabited' OR attribute='rank' AND json_extract(value)='unsettled' OR atlas_literal_zero(attribute,value,method,status,source_id,metadata) THEN -1
 WHEN attribute='habitation' AND json_extract(value)='inhabited' OR attribute='rank' AND json_extract(value) IN ('rural settlement','town','city','metropolis') THEN 1
 WHEN attribute='population' AND json_type(value)='integer' THEN CASE WHEN json_extract(value)::numeric>0 THEN 1 ELSE 0 END ELSE 0 END
$$;

CREATE FUNCTION atlas_content_contract() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE data jsonb:=to_jsonb(NEW); evidence_source atlas_sources%ROWTYPE; subject atlas_entities%ROWTYPE; item jsonb; expected_parent text; ids text[]; new_polarity integer;
BEGIN
 IF data->>'source_id' IS NOT NULL THEN
  SELECT * INTO evidence_source FROM atlas_sources WHERE id=data->>'source_id';
  IF TG_TABLE_NAME IN ('atlas_entities','atlas_attribute_records','atlas_names','atlas_relationships','atlas_media_links') AND coalesce((data->>'is_example')::integer,0)=0 AND evidence_source.status='example' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example source must stay opt-in'; END IF;
  IF data->>'valid_from' IS NOT NULL AND ((data->>'valid_from')::numeric<evidence_source.supported_from OR (data->>'valid_to')::numeric>evidence_source.supported_to) OR TG_TABLE_NAME='atlas_entities' AND data->>'valid_to' IS NOT NULL AND (data->>'valid_to')::numeric>evidence_source.supported_to THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Record exceeds supported source interval'; END IF;
 END IF;
 IF TG_TABLE_NAME='atlas_entities' THEN
  expected_parent:=CASE NEW.kind WHEN 'location' THEN 'province' WHEN 'province' THEN 'area' WHEN 'area' THEN 'region' WHEN 'region' THEN 'subcontinent' WHEN 'subcontinent' THEN 'continent' WHEN 'settlement' THEN 'location' END;
  IF NEW.kind='continent' AND NEW.parent_id IS NOT NULL OR expected_parent IS NOT NULL AND (NEW.kind<>'settlement' OR NEW.parent_id IS NOT NULL) AND NOT EXISTS(SELECT 1 FROM atlas_entities p WHERE p.id=NEW.parent_id AND p.kind=expected_parent) OR expected_parent IS NULL AND NEW.kind<>'continent' AND NEW.parent_id IS NOT NULL THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Invalid adjacent geographic parent'; END IF;
 ELSIF TG_TABLE_NAME='atlas_categories' THEN
  IF NOT EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=NEW.id AND e.kind=CASE NEW.kind WHEN 'owner' THEN 'polity' ELSE NEW.kind END) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Category must share a matching graph identity'; END IF;
 ELSIF TG_TABLE_NAME='atlas_attribute_records' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended('location-evidence:'||NEW.location_id,0));
  SELECT * INTO subject FROM atlas_entities WHERE id=NEW.location_id;
  IF subject.kind IS DISTINCT FROM 'location' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Attribute requires a location territory'; END IF;
  IF NEW.category_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM atlas_categories c WHERE c.id=NEW.category_id AND c.kind=NEW.attribute) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Category kind mismatch'; END IF;
  IF NEW.is_example=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id IN (NEW.location_id,NEW.category_id) AND e.is_example=1) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example identities must stay opt-in'; END IF;
  IF evidence_source.status='reference' AND NEW.method<>'reference' OR evidence_source.status='estimate' AND NEW.method<>'estimate' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Source class must match evidence method'; END IF;
  IF NEW.valid_from<subject.valid_from OR NEW.valid_to>subject.valid_to THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Attribute exceeds location lifetime'; END IF;
  IF NEW.status IN ('unknown','disputed','no-majority') AND (json_type(NEW.value)<>'null' OR NEW.category_id IS NOT NULL) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Unresolved attribute status requires null value and category_id'; END IF;
  IF json_type(NEW.value)='text' AND NOT atlas_nonblank(json_extract(NEW.value)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Attribute scalar must not be blank'; END IF;
  IF NOT atlas_is_retired('records',NEW.id) THEN
   IF EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id<>NEW.id AND r.location_id=NEW.location_id AND r.attribute=NEW.attribute AND r.method=NEW.method AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT atlas_is_retired('records',r.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Overlapping attribute evidence'; END IF;
   IF NEW.method='direct' THEN
    new_polarity:=atlas_settlement_polarity(NEW.attribute,NEW.value,NEW.method,NEW.status,NEW.source_id,NEW.metadata);
    IF new_polarity<>0 AND EXISTS(SELECT 1 FROM atlas_attribute_records r WHERE r.id<>NEW.id AND r.location_id=NEW.location_id AND r.method='direct' AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND NOT atlas_is_retired('records',r.id) AND atlas_settlement_polarity(r.attribute,r.value,r.method,r.status,r.source_id,r.metadata)=-new_polarity) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Uninhabited / unsettled conflicts with settlement attributes'; END IF;
   END IF;
  END IF;
 ELSIF TG_TABLE_NAME='atlas_names' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended('entity-name:'||NEW.entity_id,0));
  SELECT * INTO subject FROM atlas_entities WHERE id=NEW.entity_id;
  IF NEW.is_example=0 AND subject.is_example=1 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example identities must stay opt-in'; END IF;
  IF NEW.valid_from<subject.valid_from OR NEW.valid_to>subject.valid_to THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Name exceeds entity lifetime'; END IF;
  IF NEW.role='preferred' AND NOT atlas_is_retired('names',NEW.id) AND EXISTS(SELECT 1 FROM atlas_names n WHERE n.id<>NEW.id AND n.entity_id=NEW.entity_id AND n.language=NEW.language AND n.role='preferred' AND n.is_example=NEW.is_example AND n.valid_from<NEW.valid_to AND n.valid_to>NEW.valid_from AND NOT atlas_is_retired('names',n.id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Overlapping preferred names'; END IF;
 ELSIF TG_TABLE_NAME IN ('atlas_relationships','atlas_media_links') THEN
  IF TG_TABLE_NAME='atlas_relationships' THEN ids:=ARRAY[data->>'source_entity_id',data->>'target_entity_id']; ELSE ids:=ARRAY[data->>'entity_id']; END IF;
  IF coalesce((data->>'is_example')::integer,0)=0 AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=ANY(ids) AND e.is_example=1) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example identities must stay opt-in'; END IF;
  IF data->>'valid_from' IS NOT NULL AND EXISTS(SELECT 1 FROM atlas_entities e WHERE e.id=ANY(ids) AND ((data->>'valid_from')::numeric<e.valid_from OR (data->>'valid_to')::numeric>e.valid_to)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Relationship or media link exceeds known entity lifetime'; END IF;
  IF TG_TABLE_NAME='atlas_media_links' AND (data->>'is_example')::integer=0 AND EXISTS(SELECT 1 FROM atlas_media m JOIN atlas_sources s ON s.id=m.source_id WHERE m.id=data->>'media_id' AND s.status='example') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example media must stay opt-in'; END IF;
 ELSIF TG_TABLE_NAME='atlas_evidence_retirements' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended('retirement:'||NEW.collection||':'||NEW.target_id,0));
  IF NOT atlas_claim_exists(NEW.collection,NEW.target_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Retired claim must exist'; END IF;
  IF EXISTS(SELECT 1 FROM atlas_evidence_retirements r WHERE r.collection=NEW.collection AND r.target_id=NEW.target_id AND r.id<>NEW.id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Claim already retired'; END IF;
  IF NOT atlas_nonblank(NEW.replacement_id) AND NEW.replacement_id IS NOT NULL THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Empty replacement identity'; END IF;
  IF evidence_source.status='example' THEN
   EXECUTE format('SELECT to_jsonb(r) FROM %I r WHERE id=$1',CASE NEW.collection WHEN 'records' THEN 'atlas_attribute_records' WHEN 'names' THEN 'atlas_names' WHEN 'relationships' THEN 'atlas_relationships' ELSE 'atlas_media_links' END) INTO item USING NEW.target_id;
   IF (item->>'is_example')::integer=0 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Example sources cannot retire factual claims'; END IF;
  END IF;
  IF EXISTS(WITH RECURSIVE chain(id) AS (SELECT NEW.replacement_id WHERE NEW.replacement_id IS NOT NULL UNION SELECT r.replacement_id FROM atlas_evidence_retirements r JOIN chain c ON c.id=r.target_id WHERE r.collection=NEW.collection AND r.replacement_id IS NOT NULL) SELECT 1 FROM chain WHERE id=NEW.target_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Supersession cycle'; END IF;
 ELSIF TG_TABLE_NAME='atlas_ingestions' THEN
  IF EXISTS(SELECT 1 FROM atlas_evidence_retirements r JOIN json_each(NEW.counts,'$._retirement_ids') b ON b.value=r.id WHERE r.replacement_id IS NOT NULL AND NOT atlas_claim_exists(r.collection,r.replacement_id)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Replacement claim is missing'; END IF;
 END IF;
 RETURN NEW;
END $$;

-- A replacement can be inserted after its retirement in the same transaction,
-- but a committed dangling replacement is impossible even for direct SQL callers.
CREATE FUNCTION atlas_replacement_complete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.replacement_id IS NOT NULL AND NOT atlas_claim_exists(NEW.collection,NEW.replacement_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Replacement claim is missing'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER atlas_retirement_replacement_complete AFTER INSERT ON atlas_evidence_retirements DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION atlas_replacement_complete();
CREATE FUNCTION atlas_geography_contract() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE subject atlas_entities%ROWTYPE; level integer; parent_level integer; manifest json; data jsonb;
BEGIN
 IF TG_TABLE_NAME='atlas_geographic_releases' THEN
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'staged' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic release must begin staged'; END IF;
   IF (SELECT status FROM atlas_sources WHERE id=NEW.source_id) IS DISTINCT FROM 'reference' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic release requires a reference source'; END IF;
   manifest:=NEW.expected_counts::json;
   IF (SELECT count(*) FROM pg_catalog.json_each(manifest))<>6 OR EXISTS(SELECT 1 FROM json_each(NEW.expected_counts) c WHERE c.key NOT IN ('location','province','area','region','subcontinent','continent') OR c.type<>'integer' OR c.value::numeric<0 OR c.value::numeric>9007199254740991) OR json_extract(NEW.expected_counts,'$.continent') IS DISTINCT FROM '6' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Release manifest requires six tiers and six continents'; END IF;
  ELSE
   PERFORM pg_advisory_xact_lock(hashtextextended('geography-release:'||NEW.id,0));
   PERFORM pg_advisory_xact_lock(hashtextextended('geography-published-version',0));
   IF OLD.status='published' OR NEW.status<>'published' OR (to_jsonb(NEW)-'status'-'published_at') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'published_at') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic release definitions are immutable'; END IF;
   IF EXISTS(SELECT 1 FROM atlas_geographic_releases WHERE status='published' AND version>=NEW.version) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Published release versions must advance'; END IF;
   IF EXISTS(SELECT 1 FROM json_each(NEW.expected_counts) c WHERE c.value::numeric<>(SELECT count(*) FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=NEW.id AND m.active=1 AND e.kind=c.key)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic release manifest count mismatch'; END IF;
   IF EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id LEFT JOIN atlas_geographic_memberships p ON p.release_id=m.release_id AND p.entity_id=m.parent_id AND p.active=1 WHERE m.release_id=NEW.id AND m.active=1 AND e.kind<>'continent' AND p.entity_id IS NULL) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Incomplete active reference parent chain'; END IF;
   IF EXISTS(SELECT 1 FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=NEW.id AND m.active=1 AND e.kind<>'location' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships c WHERE c.release_id=m.release_id AND c.parent_id=m.entity_id AND c.active=1)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Active geographic group has no member territory'; END IF;
   IF EXISTS(SELECT 1 FROM atlas_geographic_changes c LEFT JOIN atlas_geographic_memberships n ON n.release_id=c.release_id AND n.entity_id=c.new_entity_id AND n.active=1 LEFT JOIN atlas_geographic_memberships o ON o.release_id=c.release_id AND o.entity_id=c.old_entity_id AND o.active=1 WHERE c.release_id=NEW.id AND ((c.new_entity_id IS NOT NULL AND n.entity_id IS NULL) OR (c.change_type IN ('merge','split','replace','retire') AND o.entity_id IS NOT NULL))) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic crosswalk must agree with active reference membership'; END IF;
  END IF;
 ELSE
  PERFORM pg_advisory_xact_lock(hashtextextended('geography-release:'||NEW.release_id,0));
  IF (SELECT status FROM atlas_geographic_releases WHERE id=NEW.release_id) IS DISTINCT FROM 'staged' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Published geographic memberships and crosswalks are immutable'; END IF;
  IF (SELECT status FROM atlas_sources WHERE id=NEW.source_id) IS DISTINCT FROM 'reference' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Reference geography requires a reference source'; END IF;
  IF TG_TABLE_NAME='atlas_geographic_memberships' THEN
   SELECT e.* INTO subject FROM atlas_entities e WHERE e.id=NEW.entity_id;
   SELECT geographic_level INTO level FROM atlas_entity_types WHERE id=subject.kind;
   IF subject.is_example<>0 OR level IS NULL THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Membership requires a non-example geographic identity'; END IF;
   SELECT t.geographic_level INTO parent_level FROM atlas_entities p JOIN atlas_entity_types t ON t.id=p.kind WHERE p.id=NEW.parent_id AND p.is_example=0;
   IF level=5 AND NEW.parent_id IS NOT NULL OR level<5 AND (NEW.parent_id IS NULL OR parent_level IS DISTINCT FROM level+1) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Reference membership must use an adjacent-tier parent'; END IF;
  ELSE
   IF NOT EXISTS(SELECT 1 FROM pg_catalog.json_each(NEW.evidence::json)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic change requires explicit source evidence'; END IF;
   IF EXISTS(SELECT 1 FROM atlas_entities e LEFT JOIN atlas_entity_types t ON t.id=e.kind WHERE e.id IN (NEW.old_entity_id,NEW.new_entity_id) AND (e.is_example<>0 OR t.geographic_level IS NULL)) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Crosswalk requires non-example geographic identities'; END IF;
   IF NEW.old_entity_id IS NOT NULL AND NEW.new_entity_id IS NOT NULL AND (SELECT kind FROM atlas_entities WHERE id=NEW.old_entity_id) IS DISTINCT FROM (SELECT kind FROM atlas_entities WHERE id=NEW.new_entity_id) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Geographic crosswalk endpoints must stay in tier'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION atlas_environment_contract() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.attribute='topography' AND json_type(NEW.value)='text' AND json_extract(NEW.value) NOT IN ('topography:flat','Flatland','flat','flatland','topography:peak','Peak','peak','topography:ridge','Ridge','ridge','topography:shoulder','Shoulder','shoulder','topography:spur','Spur','spur','topography:slope','Slope','slope','topography:hollow','Hollow','hollow','topography:footslope','Footslope','footslope','topography:valley','Valley','valley','topography:pit','Pit','pit','topography:hills','Hills','hills','topography:mountains','Mountains','mountains') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Invalid fixed topography classification'; END IF;
 IF NEW.attribute='vegetation' AND json_type(NEW.value)='text' AND json_extract(NEW.value) NOT IN ('vegetation:tropical-moist-broadleaf-forest','Tropical & Subtropical Moist Broadleaf Forests','vegetation:tropical-dry-broadleaf-forest','Tropical & Subtropical Dry Broadleaf Forests','vegetation:tropical-conifer-forest','Tropical & Subtropical Coniferous Forests','vegetation:temperate-broadleaf-mixed-forest','Temperate Broadleaf & Mixed Forests','vegetation:temperate-conifer-forest','Temperate Conifer Forests','vegetation:boreal-forest','Boreal Forests/Taiga','vegetation:tropical-grassland-savanna-shrubland','Tropical & Subtropical Grasslands, Savannas & Shrublands','vegetation:temperate-grassland-savanna-shrubland','Temperate Grasslands, Savannas & Shrublands','vegetation:flooded-grassland-savanna','Flooded Grasslands & Savannas','vegetation:montane-grassland-shrubland','Montane Grasslands & Shrublands','vegetation:tundra','Tundra','tundra','vegetation:mediterranean-forest-woodland-scrub','Mediterranean Forests, Woodlands & Scrub','vegetation:desert-xeric-shrubland','Deserts & Xeric Shrublands','vegetation:mangroves','Mangroves','mangroves','vegetation:farmlands','Farmlands','farmlands','vegetation:woodlands','Woodlands','woodlands') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Invalid fixed vegetation classification'; END IF;
 IF NEW.attribute='climate' AND json_type(NEW.value)='text' AND json_extract(NEW.value) NOT IN ('climate:Af','Af tropical rainforest','Af','climate:Am','Am tropical monsoon','Am','climate:Aw','Aw tropical savanna','Aw','climate:BWh','BWh hot desert','BWh','climate:BWk','BWk cold desert','BWk','climate:BSh','BSh hot steppe','BSh','climate:BSk','BSk cold steppe','BSk','climate:Csa','Csa hot-summer Mediterranean','Csa','climate:Csb','Csb warm-summer Mediterranean','Csb','climate:Csc','Csc cold-summer Mediterranean','Csc','climate:Cwa','Cwa dry-winter humid subtropical','Cwa','climate:Cwb','Cwb subtropical highland','Cwb','climate:Cwc','Cwc cold subtropical highland','Cwc','climate:Cfa','Cfa humid subtropical','Cfa','climate:Cfb','Cfb oceanic','Cfb','climate:Cfc','Cfc subpolar oceanic','Cfc','climate:Dsa','Dsa hot dry-summer continental','Dsa','climate:Dsb','Dsb warm dry-summer continental','Dsb','climate:Dsc','Dsc cold dry-summer continental','Dsc','climate:Dsd','Dsd very cold dry-summer continental','Dsd','climate:Dwa','Dwa hot dry-winter continental','Dwa','climate:Dwb','Dwb warm dry-winter continental','Dwb','climate:Dwc','Dwc dry-winter subarctic','Dwc','climate:Dwd','Dwd very cold dry-winter subarctic','Dwd','climate:Dfa','Dfa hot humid continental','Dfa','climate:Dfb','Dfb warm humid continental','Dfb','climate:Dfc','Dfc subarctic','Dfc','climate:Dfd','Dfd very cold subarctic','Dfd','climate:ET','ET tundra','ET','climate:EF','EF ice cap','EF','climate:oceanic','Oceanic','oceanic','climate:mediterranean','Mediterranean','mediterranean') THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='Invalid fixed climate classification'; END IF;
 RETURN NEW;
END $$;
-- Alphabetic trigger order makes byte-identical retries return before new-evidence
-- guards. The frozen legacy values stay unchanged; only genuinely new claims are checked.
DO $$
DECLARE table_name text;
BEGIN
 FOREACH table_name IN ARRAY ARRAY['atlas_sources','atlas_entity_types','atlas_entities','atlas_categories','atlas_attribute_records','atlas_ingestions','atlas_media','atlas_media_links','atlas_names','atlas_relationships','atlas_evidence_retirements','atlas_geographic_releases','atlas_geographic_memberships','atlas_geographic_changes'] LOOP
  EXECUTE format('CREATE TRIGGER atlas_00_identity BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION atlas_immutable_guard()',table_name);
  EXECUTE format('CREATE TRIGGER atlas_no_truncate BEFORE TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION atlas_immutable_guard()',table_name);
  IF table_name<>'atlas_geographic_releases' THEN EXECUTE format('CREATE TRIGGER atlas_immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION atlas_immutable_guard()',table_name); END IF;
 END LOOP;
 FOREACH table_name IN ARRAY ARRAY['atlas_sources','atlas_entity_types','atlas_entities','atlas_categories','atlas_attribute_records','atlas_ingestions','atlas_media','atlas_media_links','atlas_names','atlas_relationships','atlas_evidence_retirements'] LOOP
  EXECUTE format('CREATE TRIGGER atlas_10_content BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION atlas_content_contract()',table_name);
 END LOOP;
 FOREACH table_name IN ARRAY ARRAY['atlas_geographic_releases','atlas_geographic_memberships','atlas_geographic_changes'] LOOP
  EXECUTE format('CREATE TRIGGER atlas_10_geography BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION atlas_geography_contract()',table_name);
 END LOOP;
END $$;
CREATE TRIGGER atlas_20_environment BEFORE INSERT ON atlas_attribute_records FOR EACH ROW EXECUTE FUNCTION atlas_environment_contract();
CREATE TRIGGER atlas_geographic_publish BEFORE UPDATE ON atlas_geographic_releases FOR EACH ROW EXECUTE FUNCTION atlas_geography_contract();
CREATE TRIGGER atlas_geographic_retain BEFORE DELETE ON atlas_geographic_releases FOR EACH ROW EXECUTE FUNCTION atlas_immutable_guard();
COMMIT;
