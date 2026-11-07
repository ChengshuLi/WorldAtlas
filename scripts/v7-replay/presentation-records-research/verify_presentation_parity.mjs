import fs from 'node:fs';
const fds=process.argv.slice(2).map(Number);
if(fds.length!==6 || fds.some(x=>!Number.isInteger(x)||x<3))throw Error('invalid sealed inputs');
const raw=i=>fs.readFileSync('/proc/self/fd/'+fds[i]);
const read=i=>JSON.parse(raw(i).toString('utf8'));
const meta=read(0), water=read(1), references=read(2), records=read(3);
const old=await import('data:text/javascript;base64,'+raw(4).toString('base64'));
const next=await import('data:text/javascript;base64,'+raw(5).toString('base64'));
const original=old.buildReferenceIndex(meta,water,water.source);
const migrated=next.buildReferenceIndex(meta,water,water.source,records);
if (JSON.stringify(original)!==JSON.stringify(references) || JSON.stringify(migrated)!==JSON.stringify(original) ||
    !next.validateReferenceIndex(references,migrated)) throw Error('historical reference parity mismatch');
const land=migrated.lists.find(x=>x.number===1);
const count=land.continents.reduce((n,c)=>n+c.reasons.reduce((k,r)=>k+r.items.length,0),0);
process.stdout.write(JSON.stringify({original,migrated,report:{full_index_equal:true,land_leaves:count,record_groups:records.groups.length,record_leaves:records.leaves.length}}));

