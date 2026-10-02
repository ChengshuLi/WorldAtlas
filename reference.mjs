import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {levels} from './src/model.js';
import {archiveLocationReference} from './geographic-archive.mjs';
const bundledSources=new Set(['Natural Earth','geoBoundaries gbOpen','geoBoundaries gbHumanitarian','Atlas source aggregation','AAFC physical geography adaptation','OpenStreetMap district crosswalk','Named physical region adaptation']);
// Replacing the cartographic reference never moves history between footprints.
export function migrateReference(db,read){
  const features=read('world-index.json').parts.flatMap(p=>read(p).features);
  const ids=new Set(features.map(f=>f.id));
  const revision=createHash('sha256').update(JSON.stringify(features)).update(JSON.stringify(read('hierarchy.json'))).digest('hex');
  const current=new Map(db.prepare('SELECT id,metadata,active FROM locations').all().map(l=>[l.id,{...l,metadata:JSON.parse(l.metadata)}]));
  const retired=new Set(read('semantic-report.json').retired.map(r=>r.id));
  const obsolete=[...current.values()].filter(l=>l.active&&!ids.has(l.id)&&(retired.has(l.id)||bundledSources.has(l.metadata.source_name)));
  if(!obsolete.length&&features.every(f=>current.get(f.id)?.metadata.reference_revision===revision))return;
  const file=db.prepare('PRAGMA database_list').all().find(d=>d.name==='main')?.file;
  if(file&&fs.existsSync(file))db.prepare('VACUUM INTO ?').run(`${file}.reference-backup-${Date.now()}`);
  db.exec('BEGIN');
  try{
    // Capture old coordinates and the old complete chain before changing units.
    // Imported evidence remains byte-for-byte on its original stable identity.
    const allRows=new Map(db.prepare('SELECT * FROM locations').all().map(l=>[l.id,l]));
    for(const f of features){const previous=allRows.get(f.id),p=f.properties;if(previous&&(previous.geometry!==JSON.stringify(f.geometry)||previous.name!==p.name||previous.parent_id!==p.parent_id||previous.reference_owner!==(p.reference_owner??null)))archiveLocationReference(db,previous);}
    for(const l of obsolete)archiveLocationReference(db,allRows.get(l.id));
    const putUnit=db.prepare('INSERT INTO units VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,parent_id=excluded.parent_id,metadata=excluded.metadata');
    for(const u of read('hierarchy.json').sort((a,b)=>levels.indexOf(b.level)-levels.indexOf(a.level)))putUnit.run(u.id,u.name,u.level,u.parent_id,JSON.stringify(u.metadata));
    const put=db.prepare('INSERT INTO locations(id,name,parent_id,geometry,reference_owner,metadata) VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,parent_id=excluded.parent_id,geometry=excluded.geometry,reference_owner=excluded.reference_owner,metadata=excluded.metadata,active=1');
    for(const f of features){const p=f.properties;put.run(f.id,p.name,p.parent_id,JSON.stringify(f.geometry),p.reference_owner,JSON.stringify({...current.get(f.id)?.metadata,...p.metadata,reference_version:3,reference_revision:revision}));}
    for(const l of obsolete)db.prepare('UPDATE locations SET active=0,metadata=? WHERE id=?').run(JSON.stringify({...l.metadata,retired_reason:'Superseded by the semantic reference coverage; original geometry and all historical records retained'}),l.id);
    db.exec('COMMIT');
  }catch(e){db.exec('ROLLBACK');throw e;}
}
