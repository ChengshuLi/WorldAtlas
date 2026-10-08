import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const sha=b=>createHash('sha256').update(b).digest('hex');
const cap=32*1024*1024,phaseCap=256*1024*1024;
const packet='coordination/engineering/additive-native-gap-repair-20261008';
const journalPath=packet+'/complete-inventory-operating-journals.json.gz';
const output=packet+'/qualified-inventory-output-custody';
const ordinary=name=>{const absolute=path.resolve(name);if(fs.realpathSync(absolute)!==absolute||!fs.lstatSync(absolute).isFile())throw Error('Nonordinary source');return fs.statSync(absolute);};
try{fs.lstatSync(output);throw Error('Destination exists');}catch(e){if(e.code!=='ENOENT')throw e;}
if(fs.realpathSync(path.dirname(output))!==path.resolve(path.dirname(output)))throw Error('Symlink parent');
const runtime=ordinary(process.execPath),journalRaw=fs.readFileSync(journalPath),journalDecoded=gunzipSync(journalRaw,{maxOutputLength:cap});
const journal=JSON.parse(journalDecoded),jobs=journal.phases.flatMap(p=>p.journal.completed);
if(jobs.length!==160||new Set(jobs.map(r=>r.destination)).size!==160)throw Error('Incomplete original160jobs');
const members=[],keys=new Set();
for(const job of jobs){
 if(!job.qualified||job.exit.code!==0||job.exit.signal||job.refusal||job.owned_processes_remaining.length)throw Error('Unqualified job');
 const pubPath=job.destination+'/publication.json';const pubRaw=fs.readFileSync(pubPath),pub=JSON.parse(pubRaw);
 if(pub.complete!==true||JSON.stringify(pub.inventory)!==JSON.stringify(job.inventory))throw Error('Wrong whole original publication');
 for(const name of ['publication.json','facts.json','inventory.jsonl.gz']){
  const source=job.destination+'/'+name,stat=ordinary(source),pin=name==='publication.json'?{bytes:pubRaw.length,sha256:sha(pubRaw)}:pub[name==='facts.json'?'facts':'inventory'];
  if(stat.size!==pin.bytes||stat.size>cap||pin.uncompressed_bytes>cap||keys.has(source))throw Error('Invalid complete original member');keys.add(source);
  members.push({path:source,bytes:pin.bytes,sha256:pin.sha256,mode:(stat.mode&0o777).toString(8),execution_commit:job.execution_commit,...(pin.uncompressed_bytes===undefined?{}:{uncompressed_bytes:pin.uncompressed_bytes,uncompressed_sha256:pin.uncompressed_sha256})});
 }
}
const metadataCharge=journalRaw.length+journalDecoded.length+fs.statSync(import.meta.filename).size+131072;
const plan=[],fresh=()=>({members:[],original_encoded_bytes:0,original_decoded_bytes:0,archive_decoded_reserve:0});let group=fresh();
const reserve=entry=>Buffer.byteLength(JSON.stringify({...entry,body_base64:''})+'\n')+4*Math.ceil(entry.bytes/3);
const charge=g=>{const encodedReserve=Math.ceil(g.archive_decoded_reserve*1.01)+65536;return {...g,archive_encoded_reserve:encodedReserve,installed_runtime_bytes:runtime.size,metadata_charge:metadataCharge,complete_phase_bytes:g.original_encoded_bytes+g.original_decoded_bytes+g.archive_decoded_reserve+encodedReserve+runtime.size+metadataCharge};};
for(const member of members){
 const next={members:[...group.members,member],original_encoded_bytes:group.original_encoded_bytes+member.bytes,original_decoded_bytes:group.original_decoded_bytes+(member.uncompressed_bytes??0),archive_decoded_reserve:group.archive_decoded_reserve+reserve(member)};
 const cost=charge(next);
 if(cost.complete_phase_bytes>phaseCap||cost.archive_decoded_reserve>cap||cost.archive_encoded_reserve>cap){if(!group.members.length)throw Error('Single whole member cannot fit');plan.push(charge(group));group=fresh();}
 group.members.push(member);group.original_encoded_bytes+=member.bytes;group.original_decoded_bytes+=member.uncompressed_bytes??0;group.archive_decoded_reserve+=reserve(member);
 const current=charge(group);if(current.complete_phase_bytes>phaseCap||current.archive_decoded_reserve>cap||current.archive_encoded_reserve>cap)throw Error('Whole member admission failed');
}
if(group.members.length)plan.push(charge(group));
// Complete stage admissions are fixed before any inventory member read or output.
fs.mkdirSync(output);
const index={version:1,kind:'qualified-original-inventory-output-byte-custody-v1',original_jobs:160,original_members:480,journal:{path:journalPath,bytes:journalRaw.length,sha256:sha(journalRaw),uncompressed_bytes:journalDecoded.length,uncompressed_sha256:sha(journalDecoded)},runtime:{bytes:runtime.size,sha256:sha(fs.readFileSync(process.execPath)),mode:(runtime.mode&0o777).toString(8),version:process.version},producer_sha256:sha(fs.readFileSync(import.meta.filename)),archives:[],limits:['Exact original output bytes and actual execution commits retained; no source/geometry reinterpretation, scientific rerun, authority approval or release activation. Original installed runtime restoration remains external and exact-hash-bound.']};
for(let ordinal=0;ordinal<plan.length;ordinal++){
 const stage=plan[ordinal],lines=[];
 for(const member of stage.members){
  const raw=fs.readFileSync(member.path);if(raw.length!==member.bytes||sha(raw)!==member.sha256||(ordinary(member.path).mode&0o777).toString(8)!==member.mode)throw Error('Original source member drift');
  if(member.uncompressed_bytes!==undefined){const decoded=gunzipSync(raw,{maxOutputLength:member.uncompressed_bytes});if(decoded.length!==member.uncompressed_bytes||sha(decoded)!==member.uncompressed_sha256)throw Error('Whole original decoded member drift');}
  if(member.path.endsWith('/facts.json')){const facts=JSON.parse(raw);if(facts.execution_commit!==member.execution_commit)throw Error('Foreign original execution facts');}
  lines.push(JSON.stringify({...member,body_base64:raw.toString('base64')})+'\n');
 }
 const decoded=Buffer.from(lines.join(''));if(decoded.length!==stage.archive_decoded_reserve)throw Error('Archive reserve/inverse length mismatch');
 const encoded=gzipSync(decoded,{level:9});if(encoded.length>stage.archive_encoded_reserve||encoded.length>cap)throw Error('Archive output bound exceeded');
 const name='original-outputs-'+String(ordinal).padStart(3,'0')+'.jsonl.gz';fs.writeFileSync(output+'/'+name,encoded,{flag:'wx'});
 index.archives.push({path:output+'/'+name,bytes:encoded.length,sha256:sha(encoded),uncompressed_bytes:decoded.length,uncompressed_sha256:sha(decoded),members:stage.members,admission:{...stage,members:stage.members.length}});
}
if(sha(fs.readFileSync(journalPath))!==index.journal.sha256||sha(fs.readFileSync(process.execPath))!==index.runtime.sha256)throw Error('Archive context drift');
fs.writeFileSync(output+'/index.json',JSON.stringify(index,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({archives:index.archives.length,members:members.length,encoded:index.archives.reduce((n,a)=>n+a.bytes,0),peak_admitted_phase:Math.max(...index.archives.map(a=>a.admission.complete_phase_bytes))}));
