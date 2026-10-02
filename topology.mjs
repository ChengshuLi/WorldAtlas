import fs from 'node:fs';

// Retire duplicated display records without deleting their history or source geometry.
export function migrateTopology(db,read) {
  const report=read('topology-report.json');
  const existing=new Map(db.prepare('SELECT id,metadata,active FROM locations').all().map(l=>[l.id,{...l,metadata:JSON.parse(l.metadata)}]));
  const stale=[...existing.values()].some(l=>l.active && l.metadata.topology_version!==report.version);
  const retire=report.retired.filter(r=>existing.get(r.id)?.active);
  if(!stale && !retire.length)return;
  const current=read('world-index.json').parts.flatMap(p=>read(p).features).filter(f=>existing.has(f.id) && existing.get(f.id).metadata.topology_version!==report.version);
  if(!current.length && !retire.length)return;
  const file=db.prepare('PRAGMA database_list').all().find(d=>d.name==='main')?.file;
  if(file && fs.existsSync(file))db.prepare('VACUUM INTO ?').run(`${file}.topology-backup-${Date.now()}`);
  db.exec('BEGIN');
  try {
    const update=db.prepare('UPDATE locations SET geometry=?,metadata=? WHERE id=?');
    for(const f of current)update.run(JSON.stringify(f.geometry),JSON.stringify({...existing.get(f.id).metadata,...f.properties.metadata}),f.id);
    const archive=db.prepare('UPDATE locations SET active=0,metadata=? WHERE id=?');
    for(const r of retire)archive.run(JSON.stringify({...existing.get(r.id).metadata,retired_reason:r.reason}),r.id);
    db.exec('COMMIT');
  } catch(error) {db.exec('ROLLBACK');throw error;}
}
