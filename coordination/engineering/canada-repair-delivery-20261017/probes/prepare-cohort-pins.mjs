import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
const [root,commit,destination]=process.argv.slice(2);
if(!root||!/^[a-f0-9]{40}$/.test(commit)||!destination)throw Error('Require checkout, exact accepted commit and fresh output path');
const {pinReader}=await import(pathToFileURL(root+'/scripts/prepare-delivery-handoff.mjs'));
const reader=pinReader(root),index=reader.pin(commit,'data/macro-foundation/world-review-projection.json'),body=reader.json(index);
const world=reader.pin(commit,'data/world-index.json');
if(body.version!==1||body.kind!=='current-membership-projection'||body.current_pins.location_index_sha256!==world.sha256)throw Error('Stale canonical inventory');
const rows=[];
const parts=body.location_parts.map(name=>{
 const pin=reader.pin(commit,'data/'+name),decoded=gunzipSync(reader.read(pin));
 rows.push(...JSON.parse(decoded));
 return {...pin,decoded_bytes:decoded.length,decoded_sha256:createHash('sha256').update(decoded).digest('hex')};
});
if(rows.length!==body.locations||new Set(rows.map(row=>row.id)).size!==rows.length)throw Error('Incomplete or duplicate complete cohort IDs');
fs.writeFileSync(destination,JSON.stringify({index,parts},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({accepted_commit:commit,world_index_sha256:world.sha256,complete_ids:rows.length,parts:parts.length,encoded_part_bytes:parts.reduce((n,p)=>n+p.bytes,0),Canada_ids:rows.filter(row=>row.owner==='Canada').length,output:destination}));
