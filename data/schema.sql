PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS units (
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  level TEXT NOT NULL CHECK(level IN ('province','area','region','subcontinent','continent')),
  parent_id TEXT REFERENCES units(id), metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata))
);
DROP TRIGGER IF EXISTS unit_parent_insert;
CREATE TRIGGER unit_parent_insert BEFORE INSERT ON units BEGIN
  SELECT RAISE(ABORT, 'Invalid hierarchy parent: levels cannot be skipped') WHERE
    (NEW.level = 'continent' AND NEW.parent_id IS NOT NULL) OR
    (NEW.level != 'continent' AND NOT EXISTS (SELECT 1 FROM units WHERE id = NEW.parent_id AND level =
      CASE NEW.level WHEN 'province' THEN 'area' WHEN 'area' THEN 'region' WHEN 'region' THEN 'subcontinent' WHEN 'subcontinent' THEN 'continent' END));
END;
DROP TRIGGER IF EXISTS unit_parent_update;
CREATE TRIGGER unit_parent_update BEFORE UPDATE ON units BEGIN
  SELECT RAISE(ABORT, 'Hierarchy identity and level are immutable') WHERE NEW.id != OLD.id OR NEW.level != OLD.level;
  SELECT RAISE(ABORT, 'Invalid hierarchy parent: levels cannot be skipped') WHERE
    (NEW.level = 'continent' AND NEW.parent_id IS NOT NULL) OR
    (NEW.level != 'continent' AND NOT EXISTS (SELECT 1 FROM units WHERE id = NEW.parent_id AND level =
      CASE NEW.level WHEN 'province' THEN 'area' WHEN 'area' THEN 'region' WHEN 'region' THEN 'subcontinent' WHEN 'subcontinent' THEN 'continent' END));
END;
CREATE TABLE IF NOT EXISTS locations (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, parent_id TEXT NOT NULL REFERENCES units(id),
  geometry TEXT NOT NULL CHECK(json_valid(geometry)), reference_owner TEXT,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata))
);
DROP TRIGGER IF EXISTS location_parent_insert;
CREATE TRIGGER location_parent_insert BEFORE INSERT ON locations BEGIN
  SELECT RAISE(ABORT, 'Location requires a province parent') WHERE NOT EXISTS (SELECT 1 FROM units WHERE id = NEW.parent_id AND level = 'province');
END;
DROP TRIGGER IF EXISTS location_parent_update;
CREATE TRIGGER location_parent_update BEFORE UPDATE OF parent_id ON locations BEGIN
  SELECT RAISE(ABORT, 'Location requires a province parent') WHERE NOT EXISTS (SELECT 1 FROM units WHERE id = NEW.parent_id AND level = 'province');
END;
CREATE TABLE IF NOT EXISTS polities (
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  valid_from INTEGER NOT NULL, valid_to INTEGER NOT NULL CHECK(valid_to > valid_from),
  geometry TEXT NOT NULL CHECK(json_valid(geometry)), metadata TEXT NOT NULL CHECK(json_valid(metadata))
);
CREATE INDEX IF NOT EXISTS polities_dates ON polities(valid_from, valid_to);
CREATE TABLE IF NOT EXISTS states (
  id INTEGER PRIMARY KEY, location_id TEXT NOT NULL REFERENCES locations(id),
  valid_from INTEGER NOT NULL CHECK(valid_from BETWEEN -3000 AND 2026 AND valid_from != 0),
  valid_to INTEGER NOT NULL CHECK(valid_to BETWEEN -2999 AND 2027 AND valid_to != 0 AND valid_to > valid_from),
  owner TEXT, population INTEGER CHECK(population IS NULL OR (population >= 0 AND typeof(population) = 'integer')),
  culture TEXT, religion TEXT, topography TEXT, vegetation TEXT, climate TEXT,
  rank TEXT CHECK(rank IN ('unsettled','rural settlement','town','city','metropolis')),
  is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)), source TEXT NOT NULL CHECK(length(trim(source)) > 0)
);
CREATE INDEX IF NOT EXISTS states_interval ON states(location_id, is_example, valid_from, valid_to);
CREATE TRIGGER IF NOT EXISTS states_overlap BEFORE INSERT ON states BEGIN
  SELECT RAISE(ABORT, 'Overlapping state intervals') WHERE EXISTS (SELECT 1 FROM states
    WHERE location_id = NEW.location_id AND is_example = NEW.is_example AND valid_from < NEW.valid_to AND valid_to > NEW.valid_from);
END;
CREATE TABLE IF NOT EXISTS boundaries (
  id INTEGER PRIMARY KEY, location_id TEXT NOT NULL REFERENCES locations(id),
  valid_from INTEGER NOT NULL CHECK(valid_from BETWEEN -3000 AND 2026 AND valid_from != 0),
  valid_to INTEGER NOT NULL CHECK(valid_to BETWEEN -2999 AND 2027 AND valid_to != 0 AND valid_to > valid_from),
  geometry TEXT NOT NULL CHECK(json_valid(geometry)), source TEXT NOT NULL CHECK(length(trim(source)) > 0),
  is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1))
);
CREATE INDEX IF NOT EXISTS boundaries_interval ON boundaries(location_id, is_example, valid_from, valid_to);
CREATE TRIGGER IF NOT EXISTS boundaries_overlap BEFORE INSERT ON boundaries BEGIN
  SELECT RAISE(ABORT, 'Overlapping boundary intervals') WHERE EXISTS (SELECT 1 FROM boundaries
    WHERE location_id = NEW.location_id AND is_example = NEW.is_example AND valid_from < NEW.valid_to AND valid_to > NEW.valid_from);
END;
-- Identity is independent of its names, political owner, and dated membership.
CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('location','province','area','region','subcontinent','continent','settlement')),
  name TEXT NOT NULL, parent_id TEXT REFERENCES entities(id) DEFERRABLE INITIALLY DEFERRED,
  valid_from INTEGER, valid_to INTEGER, source TEXT,
  is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)),
  CHECK(valid_from IS NULL OR (valid_from BETWEEN -3000 AND 2026 AND valid_from != 0)),
  CHECK(valid_to IS NULL OR (valid_to BETWEEN -2999 AND 2027 AND valid_to != 0)),
  CHECK(valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from),
  CHECK((valid_from IS NULL AND valid_to IS NULL) OR length(trim(source)) > 0)
);
CREATE TABLE IF NOT EXISTS entity_history (
  id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id),
  field TEXT NOT NULL CHECK(field IN ('name','parent','existence','attributes')),
  valid_from INTEGER NOT NULL CHECK(valid_from BETWEEN -3000 AND 2026 AND valid_from != 0),
  valid_to INTEGER NOT NULL CHECK(valid_to BETWEEN -2999 AND 2027 AND valid_to != 0 AND valid_to > valid_from),
  language TEXT NOT NULL DEFAULT 'und', name_role TEXT NOT NULL DEFAULT 'preferred' CHECK(name_role IN ('preferred','alias')),
  value TEXT NOT NULL CHECK(json_valid(value)), source TEXT NOT NULL CHECK(length(trim(source)) > 0),
  is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1))
);
CREATE INDEX IF NOT EXISTS entity_history_dates ON entity_history(entity_id,field,valid_from,valid_to);
CREATE TRIGGER IF NOT EXISTS entity_history_overlap BEFORE INSERT ON entity_history WHEN NEW.name_role != 'alias' BEGIN
  SELECT RAISE(ABORT, 'Overlapping entity history') WHERE EXISTS (SELECT 1 FROM entity_history WHERE entity_id=NEW.entity_id AND field=NEW.field AND is_example=NEW.is_example AND language=NEW.language AND name_role=NEW.name_role AND valid_from<NEW.valid_to AND valid_to>NEW.valid_from);
END;
CREATE TABLE IF NOT EXISTS entity_links (
  id TEXT PRIMARY KEY, predecessor_id TEXT NOT NULL REFERENCES entities(id), successor_id TEXT NOT NULL REFERENCES entities(id),
  kind TEXT NOT NULL CHECK(kind IN ('successor','split','merge')),
  year INTEGER NOT NULL CHECK(year BETWEEN -3000 AND 2026 AND year != 0),
  source TEXT NOT NULL CHECK(length(trim(source)) > 0), is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)),
  CHECK(predecessor_id != successor_id)
);
-- Typed, field-specific evidence; legacy snapshots remain supported.
CREATE TABLE IF NOT EXISTS attribute_entities (
 id TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('owner','culture','religion')),
 name TEXT NOT NULL CHECK(length(trim(name))>0), source TEXT NOT NULL CHECK(length(trim(source))>0)
);
CREATE TABLE IF NOT EXISTS attribute_records (
 id TEXT PRIMARY KEY NOT NULL, location_id TEXT NOT NULL REFERENCES locations(id),
 attribute TEXT NOT NULL CHECK(attribute IN ('owner','culture','religion','population','rank','topography','vegetation','climate','habitation')),
 value TEXT NOT NULL CHECK(json_valid(value)) CHECK(json_type(value) IN ('null','text','integer')), category_id TEXT REFERENCES attribute_entities(id),
 valid_from INTEGER NOT NULL CHECK(typeof(valid_from)='integer' AND valid_from BETWEEN -3000 AND 2026 AND valid_from!=0),
 valid_to INTEGER NOT NULL CHECK(typeof(valid_to)='integer' AND valid_to BETWEEN -2999 AND 2027 AND valid_to!=0 AND valid_to>valid_from),
 method TEXT NOT NULL CHECK(method IN ('direct','majority-area','derived','reference','estimate')),
 status TEXT NOT NULL CHECK(status IN ('sourced','derived','reference','estimate','unknown','disputed','no-majority','example')),
 source TEXT NOT NULL CHECK(length(trim(source))>0), is_example INTEGER NOT NULL DEFAULT 0 CHECK(is_example IN (0,1)),
 metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata)),
 CHECK(json_type(value)!='text' OR length(trim(json_extract(value,'$')))>0),
 CHECK(attribute='population' OR json_type(value) IN ('null','text')),
 CHECK(attribute NOT IN ('owner','culture','religion') OR json_type(value)='null' OR category_id IS NOT NULL),
 CHECK(category_id IS NULL OR (attribute IN ('owner','culture','religion') AND json_type(value)='text')),
 CHECK(attribute!='population' OR json_type(value)='null' OR (json_type(value)='integer' AND CAST(value AS INTEGER) BETWEEN 0 AND 9007199254740991)),
 CHECK(attribute!='rank' OR json_type(value)='null' OR json_extract(value,'$') IN ('unsettled','rural settlement','town','city','metropolis')),
 CHECK(attribute!='habitation' OR json_type(value)='null' OR json_extract(value,'$') IN ('inhabited','uninhabited','unknown'))
);
CREATE INDEX IF NOT EXISTS attribute_record_dates ON attribute_records(location_id,attribute,valid_from,valid_to);
CREATE TRIGGER IF NOT EXISTS attribute_record_overlap BEFORE INSERT ON attribute_records BEGIN
 SELECT RAISE(ABORT,'Overlapping attribute evidence') WHERE EXISTS(SELECT 1 FROM attribute_records WHERE location_id=NEW.location_id AND attribute=NEW.attribute AND method=NEW.method AND is_example=NEW.is_example AND valid_from<NEW.valid_to AND valid_to>NEW.valid_from);
 SELECT RAISE(ABORT,'Category kind mismatch') WHERE NEW.category_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM attribute_entities WHERE id=NEW.category_id AND kind=NEW.attribute);
END;
CREATE TRIGGER IF NOT EXISTS attribute_record_append_only BEFORE UPDATE ON attribute_records BEGIN SELECT RAISE(ABORT,'Attribute evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS attribute_record_no_delete BEFORE DELETE ON attribute_records BEGIN SELECT RAISE(ABORT,'Attribute evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS attribute_entity_identity BEFORE UPDATE ON attribute_entities BEGIN SELECT RAISE(ABORT,'Category identity is immutable; import dated labels as evidence'); END;
CREATE TRIGGER IF NOT EXISTS attribute_entity_no_delete BEFORE DELETE ON attribute_entities BEGIN SELECT RAISE(ABORT,'Category identity is immutable'); END;
-- Recreated triggers apply the current contract to databases whose tables predate
-- new CHECK constraints, without rewriting or discarding their imported evidence.
DROP TRIGGER IF EXISTS attribute_record_contract;
CREATE TRIGGER attribute_record_contract BEFORE INSERT ON attribute_records BEGIN
 SELECT RAISE(ABORT,'Invalid attribute identity or source') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.source,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
 SELECT RAISE(ABORT,'Invalid half-open date interval') WHERE typeof(NEW.valid_from)!='integer' OR typeof(NEW.valid_to)!='integer' OR NEW.valid_from NOT BETWEEN -3000 AND 2026 OR NEW.valid_to NOT BETWEEN -2999 AND 2027 OR NEW.valid_from=0 OR NEW.valid_to=0 OR NEW.valid_to<=NEW.valid_from;
 SELECT RAISE(ABORT,'Attribute must have one scalar value') WHERE json_type(NEW.value) NOT IN ('null','text','integer') OR (NEW.attribute!='population' AND json_type(NEW.value) NOT IN ('null','text')) OR (json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$')))=0);
 SELECT RAISE(ABORT,'Attribute value must not be empty') WHERE json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$'),char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
 SELECT RAISE(ABORT,'Invalid population') WHERE NEW.attribute='population' AND json_type(NEW.value)!='null' AND (json_type(NEW.value)!='integer' OR json_extract(NEW.value,'$') NOT BETWEEN 0 AND 9007199254740991);
 SELECT RAISE(ABORT,'Category ID requires a known categorical value') WHERE NEW.category_id IS NOT NULL AND (NEW.attribute NOT IN ('owner','culture','religion') OR json_type(NEW.value)!='text');
 SELECT RAISE(ABORT,'Attribute provenance metadata must be an object') WHERE json_type(NEW.metadata)!='object';
 SELECT RAISE(ABORT,'Attribute record exceeds entity lifetime') WHERE EXISTS(SELECT 1 FROM entities WHERE id=NEW.location_id AND ((valid_from IS NOT NULL AND NEW.valid_from<valid_from) OR (valid_to IS NOT NULL AND NEW.valid_to>valid_to)));
END;
DROP TRIGGER IF EXISTS attribute_entity_contract;
CREATE TRIGGER attribute_entity_contract BEFORE INSERT ON attribute_entities BEGIN
 SELECT RAISE(ABORT,'Invalid category identity, name or source') WHERE NEW.id IS NULL OR length(trim(NEW.id,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.name,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0 OR length(trim(NEW.source,char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))=0;
END;
CREATE TRIGGER IF NOT EXISTS attribute_entity_lifetime BEFORE UPDATE OF valid_from,valid_to ON entities BEGIN
 SELECT RAISE(ABORT,'Entity lifetime would invalidate attribute evidence') WHERE EXISTS(SELECT 1 FROM attribute_records WHERE location_id=NEW.id AND ((NEW.valid_from IS NOT NULL AND valid_from<NEW.valid_from) OR (NEW.valid_to IS NOT NULL AND valid_to>NEW.valid_to)));
END;

DROP TRIGGER IF EXISTS attribute_habitation_consistency;
CREATE TRIGGER attribute_habitation_consistency BEFORE INSERT ON attribute_records WHEN NEW.method='direct' BEGIN
 SELECT RAISE(ABORT,'Uninhabited / unsettled conflicts with settlement attributes') WHERE EXISTS(SELECT 1 FROM attribute_records r WHERE r.location_id=NEW.location_id AND r.method='direct' AND r.is_example=NEW.is_example AND r.valid_from<NEW.valid_to AND r.valid_to>NEW.valid_from AND ((((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='uninhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$')='unsettled') OR (NEW.attribute='population' AND NEW.method='direct' AND NEW.status='sourced' AND json_extract(NEW.value,'$')=0 AND coalesce(json_extract(NEW.metadata,'$.estimate'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(NEW.metadata,'$.legacy_attributes'),0)=0 AND (json_type(NEW.metadata,'$.rounding') IS NULL OR json_type(NEW.metadata,'$.rounding')='null') AND (json_type(NEW.metadata,'$.model') IS NULL OR json_type(NEW.metadata,'$.model')='null') AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(NEW.metadata,'$.precision'),'')) NOT LIKE '%approx%')) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='inhabited') OR (r.attribute='rank' AND json_extract(r.value,'$') IN ('rural settlement','town','city','metropolis')) OR (r.attribute='population' AND json_extract(r.value,'$')>0))) OR (((NEW.attribute='habitation' AND json_extract(NEW.value,'$')='inhabited') OR (NEW.attribute='rank' AND json_extract(NEW.value,'$') IN ('rural settlement','town','city','metropolis')) OR (NEW.attribute='population' AND json_extract(NEW.value,'$')>0)) AND ((r.attribute='habitation' AND json_extract(r.value,'$')='uninhabited') OR (r.attribute='rank' AND json_extract(r.value,'$')='unsettled') OR (r.attribute='population' AND r.method='direct' AND r.status='sourced' AND json_extract(r.value,'$')=0 AND coalesce(json_extract(r.metadata,'$.estimate'),0)=0 AND coalesce(json_extract(r.metadata,'$.estimated'),0)=0 AND coalesce(json_extract(r.metadata,'$.is_estimate'),0)=0 AND coalesce(json_extract(r.metadata,'$.modeled'),0)=0 AND coalesce(json_extract(r.metadata,'$.modelled'),0)=0 AND coalesce(json_extract(r.metadata,'$.rounded'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_snapshot'),0)=0 AND coalesce(json_extract(r.metadata,'$.legacy_attributes'),0)=0 AND (json_type(r.metadata,'$.rounding') IS NULL OR json_type(r.metadata,'$.rounding')='null') AND (json_type(r.metadata,'$.model') IS NULL OR json_type(r.metadata,'$.model')='null') AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%round%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%model%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%estimate%' AND lower(coalesce(json_extract(r.metadata,'$.precision'),'')) NOT LIKE '%approx%')))));
END;


DROP TRIGGER IF EXISTS entity_history_settlement_consistency;
CREATE TRIGGER entity_history_settlement_consistency BEFORE INSERT ON entity_history WHEN NEW.field='attributes' BEGIN
 SELECT RAISE(ABORT,'Uninhabited / unsettled conflicts with settlement attributes') WHERE (json_extract(NEW.value,'$.rank')='unsettled' AND (json_extract(NEW.value,'$.population')>0 OR json_extract(NEW.value,'$.habitation')='inhabited')) OR (json_extract(NEW.value,'$.habitation')='uninhabited' AND (json_extract(NEW.value,'$.population')>0 OR json_extract(NEW.value,'$.rank') IN ('rural settlement','town','city','metropolis')));
END;

DROP TRIGGER IF EXISTS states_settlement_consistency;
CREATE TRIGGER states_settlement_consistency BEFORE INSERT ON states BEGIN
 SELECT RAISE(ABORT,'Unsettled conflicts with positive population') WHERE NEW.rank='unsettled' AND NEW.population>0;
END;
