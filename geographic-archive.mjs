import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {levels} from './src/model.js';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;

export function archiveLocationReference(db,row,{chain=null,source='Retained local reference before a cartographic correction'}={}){
 if(!row?.id)throw Error('Reference archive needs a stable location identity');
 if(chain===null){chain=[];let parent=row.parent_id;const seen=new Set();while(parent){if(seen.has(parent))throw Error('Reference archive parent cycle');seen.add(parent);const unit=db.prepare('SELECT * FROM units WHERE id=?').get(parent);if(!unit)throw Error('Reference archive missing parent');chain.push({...unit});parent=unit.parent_id;}}
 const claims={};for(const [table,key] of [['states','location_id'],['boundaries','location_id'],['attribute_records','location_id'],['entity_history','entity_id']])claims[table]=db.prepare(`SELECT * FROM ${table} WHERE ${key}=? ORDER BY id`).all(row.id);
 const snapshot=JSON.stringify(canonical({location:{...row},parent_chain:chain,claims,history_transfer:false,historical_effective_year:null})),id=sha(snapshot);
 db.prepare('INSERT OR IGNORE INTO reference_location_archives(id,location_id,snapshot,source) VALUES (?,?,?,?)').run(id,row.id,snapshot,source);
 return id;
}

/** Restore predecessor identities/source geometry in fresh and existing seeds. */
export function restoreGeographicRepairArchive(db,folder=new URL('./data/geographic-repair-evidence/',import.meta.url)){
 const directory=folder instanceof URL?folder.pathname:folder,indexFile=directory+'/index.json';
 if(!fs.existsSync(indexFile))return {locations:0,snapshots:0};
 const index=read(indexFile),entry=index.files['archive.json.gz'],path=directory+'/'+entry.archive_path;
 if(sha(fs.readFileSync(path))!==entry.sha256)throw Error('Geographic repair archive hash mismatch');
 const archive=read(path);
 if(archive.history_transfer!==false||!Array.isArray(archive.locations))throw Error('Unsupported geographic repair archive');
 const unitsEntry=index.files['before/hierarchy.json'],unitsPath=directory+'/'+unitsEntry.archive_path;
 if(sha(fs.readFileSync(unitsPath))!==unitsEntry.sha256)throw Error('Geographic repair ancestor archive hash mismatch');
 const units=read(unitsPath);let locations=0,snapshots=0;
 db.exec('SAVEPOINT restore_geographic_repair');
 try{
  for(const unit of [...units].sort((a,b)=>levels.indexOf(b.level)-levels.indexOf(a.level)))if(!db.prepare('SELECT 1 FROM units WHERE id=?').get(unit.id))db.prepare('INSERT INTO units(id,name,level,parent_id,metadata) VALUES (?,?,?,?,?)').run(unit.id,unit.name,unit.level,unit.parent_id??null,JSON.stringify(unit.metadata??{}));
  for(const entry of archive.locations){
   const f=entry.feature,p=f.properties;
   if(f.id!==entry.id||p.id!==entry.id)throw Error('Conflicting archived location identity');
   const row={id:entry.id,name:p.name,parent_id:p.parent_id,geometry:JSON.stringify(f.geometry),reference_owner:p.reference_owner??null,metadata:JSON.stringify(p.metadata??{}),active:0};
   if(!db.prepare('SELECT 1 FROM locations WHERE id=?').get(row.id)){db.prepare('INSERT INTO locations(id,name,parent_id,geometry,reference_owner,metadata,active) VALUES (?,?,?,?,?,?,0)').run(row.id,row.name,row.parent_id,row.geometry,row.reference_owner,row.metadata);locations++;}
   archiveLocationReference(db,row,{chain:entry.parent_chain,source:`Retained geographic repair source archive SHA-256 ${entry.geometry_sha256}; archive ${index.files['archive.json.gz'].sha256}`});snapshots++;
  }
  db.exec('RELEASE restore_geographic_repair');return {locations,snapshots};
 }catch(error){db.exec('ROLLBACK TO restore_geographic_repair; RELEASE restore_geographic_repair');throw error;}
}
