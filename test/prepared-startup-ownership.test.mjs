import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {packagePreparedStartupOwnership} from '../scripts/package-startup-ownership.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const nativePath='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/manifest.json';

async function fixture(t){
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-prepared-startup-'));
  t.after(()=>fs.rm(directory,{recursive:true,force:true}));
  const source=path.join(directory,'source'),destination=path.join(directory,'out');
  await fs.mkdir(source);const native=JSON.parse(await fs.readFile(nativePath));
  const manifestSha='a'.repeat(64),row=native.parts.find(part=>part.kind==='rows');
  const payloads=new Map([[row.path,Buffer.from('row')],['ownership-vintages/'+manifestSha+'/native-v1/ownership/startup-runs-0.bin.gz',Buffer.from('runs')],['native-v1/native-row-latitudes.f64le.gz',Buffer.from('latitudes')],['native-v1/ownership/startup-runs-0.bin.gz',Buffer.from('previous public URL')]]);
  const manifest={...native,parts:[{...row,sha256:hash(payloads.get(row.path))}],native_latitudes:{...native.native_latitudes,sha256:hash(payloads.get('native-v1/native-row-latitudes.f64le.gz'))}};
  const parts=[manifest.parts[0],{kind:'runs',path:[...payloads.keys()][1],offset:0,words:manifest.runWords,encoding:'byte-shuffle',sha256:hash(Buffer.from('runs')),decoded_sha256:'b'.repeat(64)}];
  const pixelMap=Object.fromEntries(['version','coordinateBits','size','runWords','method','footprints_sha256','hierarchy_sha256','geographic_release'].map(key=>[key,manifest[key]]));
  pixelMap.parts=parts;pixelMap.native_latitudes={...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'};
  const files=[];for(const [relative,raw]of payloads){await fs.mkdir(path.dirname(path.join(source,relative)),{recursive:true});await fs.writeFile(path.join(source,relative),raw);files.push({path:relative,bytes:raw.length,sha256:hash(raw)});}
  const index={version:1,native_manifest_sha256:manifestSha,release_id:manifest.geographic_release,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,pixelMap,files};
  const write=()=>fs.writeFile(path.join(source,'index.json'),JSON.stringify(index));await write();
  return{source,destination,manifest,manifestSha,payloads,index,write};
}

test('prepared startup copies every exact current and retained public asset',async t=>{
 const f=await fixture(t),result=await packagePreparedStartupOwnership(f);
 assert.deepEqual(result.pixelMap,f.index.pixelMap);
 for(const [name,bytes]of f.payloads)assert.deepEqual(await fs.readFile(path.join(f.destination,name)),bytes);
 await assert.rejects(packagePreparedStartupOwnership(f),/EEXIST/);
});

test('prepared startup rejects stale selection, missing rosters and changed bytes before publication',async t=>{
 const f=await fixture(t);
 await assert.rejects(packagePreparedStartupOwnership({...f,manifestSha:'c'.repeat(64)}),/selected native reference/);
 f.index.files.pop();await f.write();await assert.rejects(packagePreparedStartupOwnership(f),/roster omits/);
 f.index.files.push({path:'native-v1/ownership/startup-runs-0.bin.gz',bytes:19,sha256:hash(Buffer.from('previous public URL'))});await f.write();
 await fs.writeFile(path.join(f.source,f.index.files[0].path),'truncated gzip');
 await assert.rejects(packagePreparedStartupOwnership(f),/bytes changed/);
 await assert.rejects(fs.stat(f.destination),{code:'ENOENT'});
});

test('prepared startup refuses unsafe paths and source or destination links without overwriting sentinels',async t=>{
 const f=await fixture(t),outside=path.join(path.dirname(f.source),'sentinel');await fs.writeFile(outside,'retained');
 const current=f.index.files[0];f.index.files[0]={...current,path:'../sentinel'};await f.write();
 await assert.rejects(packagePreparedStartupOwnership(f),/roster omits|Unsafe/);
 f.index.files[0]=current;await f.write();await fs.unlink(path.join(f.source,current.path));await fs.symlink(outside,path.join(f.source,current.path));
 await assert.rejects(packagePreparedStartupOwnership(f),/nonordinary/);
 assert.equal(await fs.readFile(outside,'utf8'),'retained');
});
