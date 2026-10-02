import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {levels} from './src/model.js';
import {importTemporal, syncEntities} from './temporal.mjs';

// These are cartographic revision identities, not dated historical successors.
const recordTables=['states','boundaries','entity_history','entity_links'];
const columns=(db,table)=>db.prepare(`PRAGMA table_info(${table})`).all().map(row=>row.name);
const values=(row,fields)=>fields.map(field=>row[field]);
const identical=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

export function restoreReferenceArchive(db,path=new URL('./data/geographic-migration-archive.json.gz',import.meta.url)){
  const archive=JSON.parse(gunzipSync(fs.readFileSync(path)).toString('utf8'));
  if(archive.version!==1||archive.kind!=='undated-cartographic-reference-archive'||archive.historical_effective_year!==null)throw Error('Unsupported cartographic reference archive');
  if(!Array.isArray(archive.units)||!Array.isArray(archive.locations)||!archive.original_records)throw Error('Incomplete reference archive');
  const counts={units:0,locations:0,entities:0,states:0,boundaries:0,entity_history:0,entity_links:0};
  const fields=new Map(recordTables.map(table=>[table,columns(db,table)]));
  // Reject ID collisions before touching reference geometry or identity records.
  for(const table of recordTables)for(const row of archive.original_records[table]?.rows||[]){
    if(!Array.isArray(row)||row.length!==fields.get(table).length)throw Error(`Invalid archived ${table} row`);
    const existing=db.prepare(`SELECT * FROM ${table} WHERE id=?`).get(row[0]);
    if(existing&&!identical(values(existing,fields.get(table)),row))throw Error(`Archive record collision: ${table}/${row[0]}`);
  }
  db.exec('SAVEPOINT restore_reference_archive');
  try{
    const getUnit=db.prepare('SELECT * FROM units WHERE id=?');
    const putUnit=db.prepare('INSERT INTO units(id,name,level,parent_id,metadata) VALUES (?,?,?,?,?)');
    for(const unit of [...archive.units].sort((a,b)=>levels.indexOf(b.level)-levels.indexOf(a.level))){
      const existing=getUnit.get(unit.id);
      if(existing){if(existing.level!==unit.level)throw Error(`Archive unit identity collision: ${unit.id}`);continue;}
      putUnit.run(unit.id,unit.name,unit.level,unit.parent_id??null,JSON.stringify(unit.metadata||{}));counts.units++;
    }
    const getLocation=db.prepare('SELECT id FROM locations WHERE id=?');
    const putLocation=db.prepare('INSERT INTO locations(id,name,parent_id,geometry,reference_owner,metadata,active) VALUES (?,?,?,?,?,?,0)');
    for(const location of archive.locations){
      if(getLocation.get(location.id))continue;
      if(!['Polygon','MultiPolygon'].includes(location.geometry?.type))throw Error(`Invalid archived territory geometry: ${location.id}`);
      // Missing political/reference evidence stays null; never infer an owner from a name.
      putLocation.run(location.id,location.name,location.parent_id,JSON.stringify(location.geometry),location.reference_owner??null,JSON.stringify(location.metadata||{}));counts.locations++;
    }
    syncEntities(db);
    const originalEntities=archive.original_entities||[];
    const entityFields=columns(db,'entities');
    for(const entity of originalEntities){
      const existing=db.prepare('SELECT * FROM entities WHERE id=?').get(entity.id);
      if(existing&&!identical(values(existing,entityFields),values(entity,entityFields)))throw Error(`Archive entity collision: ${entity.id}`);
    }
    const missingEntities=originalEntities.filter(entity=>!db.prepare('SELECT 1 FROM entities WHERE id=?').get(entity.id));
    const missingHistory=(archive.original_records.entity_history?.rows||[]).filter(row=>!db.prepare('SELECT 1 FROM entity_history WHERE id=?').get(row[0]));
    const missingLinks=(archive.original_records.entity_links?.rows||[]).filter(row=>!db.prepare('SELECT 1 FROM entity_links WHERE id=?').get(row[0]));
    if(missingEntities.length||missingHistory.length||missingLinks.length){
      const object=(table,row)=>Object.fromEntries(fields.get(table).map((field,i)=>[field,field==='value'?JSON.parse(row[i]):row[i]]));
      importTemporal(db,{entities:missingEntities,entity_history:missingHistory.map(row=>object('entity_history',row)),entity_links:missingLinks.map(row=>object('entity_links',row))});
      counts.entities=missingEntities.length;counts.entity_history=missingHistory.length;counts.entity_links=missingLinks.length;
    }
    for(const table of ['states','boundaries']){
      const names=fields.get(table);
      const insert=db.prepare(`INSERT INTO ${table} (${names.join(',')}) VALUES (${names.map(()=>'?').join(',')})`);
      const get=db.prepare(`SELECT 1 FROM ${table} WHERE id=?`);
      for(const row of archive.original_records[table]?.rows||[]){if(get.get(row[0]))continue;insert.run(...row);counts[table]++;}
    }
    // Check complete serialized rows again, including preserved source JSON text.
    for(const table of recordTables)for(const row of archive.original_records[table]?.rows||[]){
      const restored=db.prepare(`SELECT * FROM ${table} WHERE id=?`).get(row[0]);
      if(!restored||!identical(values(restored,fields.get(table)),row))throw Error(`Archive restoration changed original record: ${table}/${row[0]}`);
    }
    db.exec('RELEASE restore_reference_archive');
    return counts;
  }catch(error){db.exec('ROLLBACK TO restore_reference_archive; RELEASE restore_reference_archive');throw error;}
}
