import {importAttributes} from './attribute-records.mjs';
import {derivedRecordsAt,preparedBoundariesMatch,invalidatePreparedFootprints} from './derived.mjs';
import {preparedEvidenceAt} from './prepared-evidence.mjs';
import {mergePreparedEvidence} from './src/prepared-evidence.js';
import {syncEntities,importTemporal,temporalCatalog} from './temporal.mjs';
import {migrateReference} from './reference.mjs';
import {restoreReferenceArchive} from './reference-archive.mjs';
import {restoreGeographicRepairArchive} from './geographic-archive.mjs';
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import { attributes, levels, ranks, validYear } from './src/model.js';
import { migrateHierarchy, validateHierarchy } from './hierarchy.mjs';
import { migrateTopology } from './topology.mjs';
export function openDatabase(path = 'data/atlas.sqlite') {
  const db = new DatabaseSync(path);
  widenRankChecks(db);
  db.exec(fs.readFileSync(new URL('./data/schema.sql', import.meta.url), 'utf8'));
  for (const table of ['units','locations']) if (!db.prepare(`PRAGMA table_info(${table})`).all().some(c=>c.name==='metadata')) db.exec(`ALTER TABLE ${table} ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'`);
  if(!db.prepare('PRAGMA table_info(locations)').all().some(c=>c.name==='active'))db.exec('ALTER TABLE locations ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))');
  return db;
}
// Widen the two legacy enums without changing any evidence IDs or values.
// Drop/recreate dependent triggers around the rebuild to avoid SQLite's ALTER
// validation observing an temporarily absent table. Current schema restores
// the updated contracts immediately afterward.
function widenRankChecks(db){
 const tables=['states','attribute_records'].map(name=>({name,sql:db.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name=?").get(name)?.sql})).filter(t=>t.sql&&!t.sql.includes("'unsettled'")&&t.sql.includes("'rural settlement'"));
 if(!tables.length)return;
 const triggers=db.prepare("SELECT name,sql FROM sqlite_master WHERE type='trigger' AND sql IS NOT NULL").all(),foreignKeys=db.prepare('PRAGMA foreign_keys').get().foreign_keys;
 const indexes=tables.flatMap(t=>db.prepare("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL").all(t.name));
 db.exec('PRAGMA foreign_keys=OFF; BEGIN IMMEDIATE');
 try{
  for(const trigger of triggers)db.exec(`DROP TRIGGER "${trigger.name.replaceAll('"','""')}"`);
  for(const table of tables){const temporary=`__rank_${table.name}`,definition=table.sql.replace(/^CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|\w+)/i,`CREATE TABLE "${temporary}"`).replaceAll("('rural settlement','town','city','metropolis')","('unsettled','rural settlement','town','city','metropolis')");db.exec(definition);const columns=db.prepare(`PRAGMA table_info("${table.name}")`).all().map(c=>`"${c.name.replaceAll('"','""')}"`).join(',');db.exec(`INSERT INTO "${temporary}"(${columns}) SELECT ${columns} FROM "${table.name}"; DROP TABLE "${table.name}"; ALTER TABLE "${temporary}" RENAME TO "${table.name}"`);}
  for(const index of indexes)db.exec(index.sql);for(const trigger of triggers)db.exec(trigger.sql);db.exec('COMMIT');
 }catch(error){db.exec('ROLLBACK');throw error;}finally{db.exec(`PRAGMA foreign_keys=${foreignKeys?'ON':'OFF'}`);}
}
function requiredText(value, field) {
  if (typeof value !== 'string' || !value.trim() || value.length > 2000) throw new Error(`Invalid ${field}`);
}
export function validateGeometry(geometry) {
  if (!geometry || !['Polygon', 'MultiPolygon'].includes(geometry.type)) throw new Error('Location geometry must be a Polygon or MultiPolygon');
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  if (!Array.isArray(polygons) || !polygons.length) throw new Error('Empty geometry');
  for (const polygon of polygons) {
    if (!Array.isArray(polygon) || !polygon.length) throw new Error('Empty polygon');
    for (const ring of polygon) {
      if (!Array.isArray(ring) || ring.length < 4) throw new Error('Polygon ring needs at least four coordinates');
      for (const point of ring) if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite) || Math.abs(point[0]) > 180 || Math.abs(point[1]) > 90) throw new Error('Invalid longitude/latitude');
      if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) throw new Error('Polygon ring must be closed');
    }
  }
}
export function importRecords(db, payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('Import must be an object');
  for (const key of Object.keys(payload)) if (!['units','locations','states','boundaries','entities','entity_history','entity_links','attribute_entities','attribute_records'].includes(key)) throw new Error(`Unknown collection: ${key}`);
  for (const value of Object.values(payload)) if (!Array.isArray(value)) throw new Error('Collections must be arrays');
  db.exec('BEGIN');
  try {
    const units = [...(payload.units || [])].sort((a,b) => levels.indexOf(b.level) - levels.indexOf(a.level));
    for (const u of units) {
      requiredText(u.id, 'id'); requiredText(u.name, 'name');
      db.prepare('INSERT INTO units (id,name,level,parent_id,metadata) VALUES (?,?,?,?,?)').run(u.id, u.name, u.level, u.parent_id ?? null, JSON.stringify(u.metadata || {}));
    }
    for (const l of payload.locations || []) {
      requiredText(l.id, 'id'); requiredText(l.name, 'name'); validateGeometry(l.geometry);
      db.prepare('INSERT INTO locations (id,name,parent_id,geometry,reference_owner,metadata) VALUES (?,?,?,?,?,?)').run(l.id, l.name, l.parent_id, JSON.stringify(l.geometry), l.reference_owner ?? null, JSON.stringify(l.metadata || {}));
    }
    for (const table of ['states', 'boundaries']) for (const r of payload[table] || []) {
      requiredText(r.source, 'source');
      if (!validYear(r.valid_from) || !(validYear(r.valid_to) || r.valid_to === 2027) || r.valid_to <= r.valid_from) throw new Error('Invalid half-open date interval');
      if (r.is_example != null && ![0,1].includes(r.is_example)) throw new Error('is_example must be 0 or 1');
      if (table === 'boundaries') validateGeometry(r.geometry);
      else for (const field of attributes) if (r[field] != null) {
        if (field === 'population') { if (!Number.isSafeInteger(r[field]) || r[field] < 0) throw new Error('Population must be a nonnegative integer'); }
        else { requiredText(r[field], field); if (field === 'rank' && !ranks.includes(r[field])) throw new Error('Invalid location rank'); }
      }
      if(table==='states'&&r.rank==='unsettled'&&r.population>0)throw new Error('Unsettled conflicts with positive population');
      const fields = ['location_id', 'valid_from', 'valid_to', ...(table === 'states' ? attributes : ['geometry']), 'is_example', 'source'];
      const values = fields.map(k => k === 'geometry' ? JSON.stringify(r[k]) : k === 'is_example' ? r[k] ?? 0 : r[k] ?? null);
      db.prepare(`INSERT INTO ${table} (${fields.join(',')}) VALUES (${fields.map(() => '?').join(',')})`).run(...values);
    }
    importTemporal(db,payload);
    importAttributes(db,payload);
    db.exec('COMMIT');
  } catch (error) { db.exec('ROLLBACK'); throw error; }
}
export function seedDatabase(db) {
  const read = file => JSON.parse(fs.readFileSync(new URL(`./data/${file}`, import.meta.url), 'utf8'));
  if (!db.prepare('SELECT count(*) AS n FROM locations').get().n) {
    const features=read('world-index.json').parts.flatMap(part=>read(part).features);
    validateHierarchy(read('hierarchy.json'),features.map(f=>f.properties));
    importRecords(db, { units: read('hierarchy.json'), locations: features.map(f => ({ ...f.properties, geometry: f.geometry })) });
    const archive=new URL('./data/geographic-migration-archive.json.gz',import.meta.url);
    if(fs.existsSync(archive))restoreReferenceArchive(db,archive);
  }
  migrateReference(db,read);
  migrateHierarchy(db,read);
  migrateTopology(db,read);
  restoreGeographicRepairArchive(db);
  syncEntities(db);
  const putCategory=db.prepare('INSERT OR IGNORE INTO attribute_entities VALUES (?,?,?,?)');
  for(const r of db.prepare("SELECT DISTINCT json_extract(metadata,'$.reference_owner_id') id,coalesce(json_extract(metadata,'$.reference_polity'),reference_owner) name FROM locations WHERE active=1 AND json_extract(metadata,'$.reference_owner_id') IS NOT NULL").all())putCategory.run(r.id,'owner',r.name,'Natural Earth / source-geography modern reference');
  if(fs.existsSync(new URL('./data/ownership-history/index.json',import.meta.url)))for(const e of Object.values(read('ownership-history/index.json').entities))putCategory.run(e.id,e.kind,e.name,e.source);
  // New illustrative fixtures have an explicit new footprint; imported history stays archived.
  const examples=read('examples.json').states.filter(r=>!db.prepare('SELECT 1 FROM states WHERE location_id=? AND is_example=1 AND valid_from=?').get(r.location_id,r.valid_from));
  if(examples.length)importRecords(db,{states:examples});
  if(fs.existsSync(new URL('./data/temporal-examples.json',import.meta.url)) && !db.prepare("SELECT 1 FROM entity_history WHERE id='example:v2:london-name'").get())importRecords(db,read('temporal-examples.json'));
  if(fs.existsSync(new URL('./data/settlement-estimates.json',import.meta.url)) && !db.prepare("SELECT 1 FROM entities WHERE id LIKE 'settlement:ne:%' LIMIT 1").get())importRecords(db,read('settlement-estimates.json'));
  if (!db.prepare('SELECT count(*) AS n FROM polities').get().n && fs.existsSync(new URL('./data/cliopatria/index.json', import.meta.url))) {
    const index=read('cliopatria/index.json');
    db.exec('BEGIN');
    try {
      const insert=db.prepare('INSERT INTO polities VALUES (?,?,?,?,?,?)');
      for (const chunk of new Set(index.records.map(r=>r.chunk))) for (const f of read(`cliopatria/${chunk}`).features) {
        const p=f.properties; insert.run(f.id,p.name,p.valid_from,p.valid_to,JSON.stringify(f.geometry),JSON.stringify(p));
      }
      db.exec('COMMIT');
    } catch(error) { db.exec('ROLLBACK'); throw error; }
  }
}
export function geography(db) {
  const units=db.prepare('WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations WHERE active=1 UNION SELECT u.parent_id FROM units u JOIN used x ON u.id=x.id WHERE u.parent_id IS NOT NULL) SELECT * FROM units WHERE id IN (SELECT id FROM used)').all();
  return { type: 'FeatureCollection', temporal:temporalCatalog(db), units: units.map(u=>({...u,metadata:JSON.parse(u.metadata)})), features: db.prepare('SELECT * FROM locations WHERE active=1').all().map(({geometry, metadata, ...properties}) => ({type: 'Feature', id: properties.id, properties:{...properties,metadata:JSON.parse(metadata)}, geometry: JSON.parse(geometry)})) };
}
export function snapshot(db, year, examples = false,sourceEvidence=false) {
  if (!validYear(year)) throw new Error('Year must be between 3000 BC and 2026 AD, excluding zero');
  const select = table => db.prepare(`SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY is_example ASC) AS preference FROM ${table} WHERE valid_from <= ? AND valid_to > ? AND is_example <= ? AND location_id IN (SELECT id FROM locations WHERE active=1)) WHERE preference = 1`).all(year, year, Number(examples)).map(({preference, ...r}) => r);
  const polities=sourceEvidence?db.prepare('SELECT * FROM polities WHERE valid_from <= ? AND valid_to > ?').all(year,year).map(r=>({type:'Feature',id:r.id,properties:JSON.parse(r.metadata),geometry:JSON.parse(r.geometry)})):[];
  const attributes=db.prepare('SELECT * FROM attribute_records WHERE valid_from<=? AND valid_to>? AND is_example<=? AND location_id IN (SELECT id FROM locations WHERE active=1)').all(year,year,Number(examples)).map(r=>({...r,value:JSON.parse(r.value),metadata:JSON.parse(r.metadata)}));
  const boundaryRows=db.prepare('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0').all().map(r=>[r.location_id,r.valid_from,r.valid_to,r.geometry]);
  const evidence=preparedEvidenceAt(year,{examples});
  const merged=mergePreparedEvidence(attributes,[],evidence);
  const prepared=invalidatePreparedFootprints([...derivedRecordsAt(year),...merged.records],boundaryRows,preparedBoundariesMatch(boundaryRows));
  return { year, temporal_history:merged.names, attributes:prepared, states: select('states'), boundaries: select('boundaries').map(r => ({...r, geometry: JSON.parse(r.geometry)})), polities };
}
