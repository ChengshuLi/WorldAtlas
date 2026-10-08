import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
const sha=b=>createHash('sha256').update(b).digest('hex');
const FILE=32*1024*1024, PHASE=256*1024*1024;
function relative(p){if(typeof p!=='string'||path.isAbsolute(p)||p.split('/').some(x=>!x||x==='.'||x==='..'))throw Error('Unsafe original path');return p;}
function ordinary(p){const s=fs.lstatSync(p);if(!s.isFile()||fs.realpathSync(p)!==path.resolve(p))throw Error('Nonordinary input');return s;}
function checked(p,pin){if(pin.bytes>FILE||pin.uncompressed_bytes>FILE||ordinary(p).size!==pin.bytes)throw Error('Whole file cap/length');const b=fs.readFileSync(p);if(sha(b)!==pin.sha256)throw Error('Whole encoded hash');return b;}
function decoded(raw,pin){if(pin.uncompressed_bytes===undefined)return raw;const b=gunzipSync(raw,{maxOutputLength:pin.uncompressed_bytes});if(b.length!==pin.uncompressed_bytes||sha(b)!==pin.uncompressed_sha256)throw Error('Whole decoded hash');return b;}
export function verifyCustody(indexPath,indexSha,{compareOriginal=false,onMember=()=>{}}={}){
 const stat=ordinary(indexPath);if(stat.size>FILE)throw Error('Index cap');const raw=fs.readFileSync(indexPath);if(sha(raw)!==indexSha)throw Error('Independent index hash');const index=JSON.parse(raw);
 if(index.kind!=='qualified-original-inventory-output-byte-custody-v1'||index.original_jobs!==160||index.original_members!==480)throw Error('Incomplete custody scope');
 const runtime=ordinary(process.execPath);if(runtime.size!==index.runtime.bytes||process.version!==index.runtime.version)throw Error('Installed runtime identity');
 const runtimeHash=createHash('sha256'),buffer=Buffer.alloc(65536),fd=fs.openSync(process.execPath,'r');try{for(let n;(n=fs.readSync(fd,buffer,0,buffer.length,null));)runtimeHash.update(buffer.subarray(0,n));}finally{fs.closeSync(fd);}if(runtimeHash.digest('hex')!==index.runtime.sha256)throw Error('Installed runtime whole hash');
 const journal=JSON.parse(decoded(checked(index.journal.path,index.journal),index.journal));const jobs=journal.phases.flatMap(p=>p.journal.completed);
 if(jobs.length!==160||new Set(jobs.map(j=>j.destination)).size!==160)throw Error('Original job scope');
 const expected=new Map();for(const job of jobs){if(!job.qualified||job.exit.code!==0||job.exit.signal||job.refusal||job.owned_processes_remaining.length)throw Error('Unqualified predecessor');for(const n of ['publication.json','facts.json','inventory.jsonl.gz'])expected.set(relative(job.destination+'/'+n),job);}
 const declared=index.archives.flatMap(a=>a.members);if(declared.length!==480||new Set(declared.map(m=>m.path)).size!==480||declared.some(m=>!expected.has(m.path)||m.execution_commit!==expected.get(m.path).execution_commit))throw Error('Foreign/duplicate/missing members');
 const seen=new Set();let bytes=0;
 for(const archive of index.archives){
  relative(archive.path);const admission=archive.admission;
  const encoded=archive.members.reduce((n,m)=>n+m.bytes,0),wholeDecoded=archive.members.reduce((n,m)=>n+(m.uncompressed_bytes??0),0);
  const minimum=encoded+wholeDecoded+archive.bytes+archive.uncompressed_bytes+runtime.size+raw.length+index.journal.bytes+index.journal.uncompressed_bytes+ordinary(import.meta.filename).size+131072;
  if(!admission||minimum>PHASE||admission.complete_phase_bytes>PHASE||archive.members.length>512||encoded!==admission.original_encoded_bytes||wholeDecoded!==admission.original_decoded_bytes||archive.uncompressed_bytes!==admission.archive_decoded_reserve||archive.bytes>admission.archive_encoded_reserve)throw Error('Prospective complete phase');
  const body=decoded(checked(archive.path,archive),archive);const rows=body.toString('utf8').split('\n');if(rows.pop()!==''||rows.length!==archive.members.length)throw Error('Complete archive rows');
  for(let i=0;i<rows.length;i++){
   const row=JSON.parse(rows[i]),{body_base64,...pin}=row,want=archive.members[i];
   if(JSON.stringify(pin)!==JSON.stringify(want)||seen.has(pin.path)||!/^[0-7]{3}$/.test(pin.mode))throw Error('Member provenance/order');
   const b=Buffer.from(body_base64,'base64');if(b.toString('base64')!==body_base64||b.length!==pin.bytes||sha(b)!==pin.sha256)throw Error('Whole inverse bytes');
   const expanded=decoded(b,pin),job=expected.get(pin.path);
   if(pin.path.endsWith('/publication.json')){const pub=JSON.parse(b);if(pub.complete!==true||JSON.stringify(pub.inventory)!==JSON.stringify(job.inventory))throw Error('Original publication binding');}
   if(pin.path.endsWith('/facts.json')&&JSON.parse(b).execution_commit!==job.execution_commit)throw Error('Original facts vintage');
   if(pin.path.endsWith('/inventory.jsonl.gz')&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].some(k=>pin[k]!==job.inventory[k]))throw Error('Original journal inventory binding');
   if(compareOriginal){const original=checked(pin.path,pin);if(!original.equals(b)||(ordinary(pin.path).mode&0o777).toString(8)!==pin.mode)throw Error('Original comparison failed');}
   onMember(pin,b);seen.add(pin.path);bytes+=b.length;
  }
 }
 if(seen.size!==480)throw Error('Incomplete final inverse');return {jobs:160,members:seen.size,encoded_member_bytes:bytes,complete:true,scope:'Original inventory output byte restoration only; no scientific or physical approval.'};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){const [index,hash,option]=process.argv.slice(2);if(!index||!hash||!['--compare-original',undefined].includes(option))throw Error('Usage: node restore-qualified-inventory-outputs.mjs INDEX SHA [--compare-original]');console.log(JSON.stringify(verifyCustody(index,hash,{compareOriginal:option==='--compare-original'})));}
