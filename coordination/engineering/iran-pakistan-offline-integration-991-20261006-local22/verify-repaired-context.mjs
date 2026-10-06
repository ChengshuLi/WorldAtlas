// Complete independent readback of context parts, stable identities and shapes.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const [oneName,twoName,outName]=process.argv.slice(2),names=[oneName,twoName,outName];
const owned=name=>{const p=path.resolve(root,name??'');if(!p.startsWith(path.join(root,prefix)+path.sep))throw Error('Owned path required');return p;};
const [one,two,out]=names.map(owned);if(one===two||fs.existsSync(out))throw Error('Distinct vintages and fresh receipt required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),digest=raw=>createHash('sha256').update(raw).digest('hex');
const executed=committedPreparationFiles(root,head,['package.json',prefix+'/verify-repaired-context.mjs','scripts/native-ownership/native-preparation-guards.mjs']);
const files=dir=>fs.readdirSync(dir).sort().map(name=>{const raw=fs.readFileSync(path.join(dir,name));return {path:name,bytes:raw.length,sha256:digest(raw)};});
const products=files(one);if(!isDeepStrictEqual(products,files(two)))throw Error('Complete context runs differ');
const report=JSON.parse(fs.readFileSync(path.join(one,'inputs.json'))),baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const read=name=>execFileSync('git',['-C',root,'show',baseline+':'+name],{maxBuffer:32*1024*1024});
const oldDir='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1';
const old=JSON.parse(read(oldDir+'/inputs.json')),before=[],after=[];
for(const part of old.parts){
  const raw=read(oldDir+'/'+part.path),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
  if(raw.length!==part.bytes||digest(raw)!==part.sha256||digest(decoded)!==part.uncompressed_sha256)throw Error('Original context bytes differ');
  before.push(...JSON.parse(decoded));
}
for(const part of report.parts){
  const raw=fs.readFileSync(path.join(one,part.path)),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
  if(raw.length!==part.bytes||digest(raw)!==part.sha256||decoded.length!==part.uncompressed_bytes||digest(decoded)!==part.uncompressed_sha256||part.first_owner!==after.length+1)throw Error('New context bytes/sequence differ');
  const rows=JSON.parse(decoded);if(rows.length!==part.owners)throw Error('New context part owner count differs');after.push(...rows);
}
const geometry=JSON.parse(read('coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json'));
function compare(rows){
  if(rows.length!==49625||rows.length!==before.length)throw Error('Incomplete context roster');
  for(let i=0;i<rows.length;i++){
    const source=before[i],expected=geometry[source.id]?{...source,geometry:geometry[source.id]}:source;
    if(!isDeepStrictEqual(rows[i],expected))throw Error('Non-target geometry or stable identity/parent mutated');
  }
  const owner=digest(Buffer.from(JSON.stringify(rows.map(f=>[f.pixelIndex,f.id]))));
  const ordered=[...rows].sort((a,b)=>a.id.localeCompare(b.id));
  const footprint=digest(Buffer.from(JSON.stringify(ordered.map(f=>[f.id,f.geometry]))));
  if(owner!==old.owner_sha256||owner!==report.owner_sha256||footprint!==report.footprints_sha256)throw Error('Complete context footprint/owner hashes differ');
}
compare(after);const controls=[];
for(const [name,mutate] of [['wrong target parent',r=>{r.find(f=>geometry[f.id]).properties.parent_id='wrong';}],
  ['lost non-target vertex',r=>{const f=r.find(f=>!geometry[f.id]);f.geometry.coordinates=[];}],
  ['changed owner index',r=>{r[0].pixelIndex=999999;}]]){
  const rows=structuredClone(after);mutate(rows);let rejected=false;try{compare(rows);}catch{rejected=true;}
  if(!rejected)throw Error('Control accepted: '+name);controls.push({name,outcome:'rejected'});
}
fs.writeFileSync(out,JSON.stringify({version:1,evaluation_commit:head,executed_sources:executed,preparation_commit:report.execution_commit,
  products,two_run_products:products.length,run_one_sha256:digest(Buffer.from(JSON.stringify(products))),run_two_sha256:digest(Buffer.from(JSON.stringify(files(two)))),
  locations:after.length,changed_locations:2,unchanged_locations:49623,footprints_sha256:report.footprints_sha256,owner_sha256:report.owner_sha256,
  successor_release:report.successor_release,controls,installed:false,published:false,installation_ready:false,
  limits:['Lossless application context readback; does not install or grant source/geographic approval.']})+'\n',{flag:'wx'});
console.log(JSON.stringify({locations:after.length,changed:2,controls:controls.length,two_run_products:products.length}));
