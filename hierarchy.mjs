import fs from 'node:fs';
import { levels } from './src/model.js';

import { validateHierarchy } from './src/hierarchy.js';
export { validateHierarchy } from './src/hierarchy.js';

// Migrate membership only: retain all imported states, temporal boundaries and locations.
export function migrateHierarchy(db, read) {
  if(!db.prepare("SELECT 1 FROM locations WHERE coalesce(json_extract(metadata,'$.hierarchy_version'),0) < 3 LIMIT 1").get())return;
  const units=read('hierarchy.json');
  const features=read('world-index.json').parts.flatMap(part=>read(part).features);
  const existing=new Map(db.prepare('SELECT id,metadata FROM locations').all().map(l=>[l.id,JSON.parse(l.metadata)]));
  const pending=features.filter(f=>existing.has(f.id) && (existing.get(f.id).hierarchy_version || 0)<3);
  if(!pending.length)return;
  const file=db.prepare('PRAGMA database_list').all().find(d=>d.name==='main')?.file;
  if(file && fs.existsSync(file))db.prepare('VACUUM INTO ?').run(`${file}.hierarchy-v3-backup-${Date.now()}`);
  db.exec('BEGIN');
  try {
    const upsert=db.prepare('INSERT INTO units(id,name,level,parent_id,metadata) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,parent_id=excluded.parent_id,metadata=excluded.metadata');
    for(const u of [...units].sort((a,b)=>levels.indexOf(b.level)-levels.indexOf(a.level)))upsert.run(u.id,u.name,u.level,u.parent_id,JSON.stringify(u.metadata));
    const update=db.prepare('UPDATE locations SET parent_id=?,metadata=? WHERE id=?');
    for(const f of pending)update.run(f.properties.parent_id,JSON.stringify({...existing.get(f.id),...f.properties.metadata}),f.id);
    db.exec('WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations UNION SELECT u.parent_id FROM units u JOIN used x ON u.id=x.id WHERE u.parent_id IS NOT NULL) DELETE FROM units WHERE id NOT IN (SELECT id FROM used)');
    validateHierarchy(db.prepare('SELECT * FROM units').all(),db.prepare('SELECT * FROM locations').all());
    db.exec('COMMIT');
  } catch(error) { db.exec('ROLLBACK');throw error; }
}
