import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {readGeographicReleaseManifest,decodeGeographicReleaseBatch} from '../scripts/read-geographic-release-manifest.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
function fixture(run){const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-manifest-'));try{
 const base={version:1,original_catalog_sha256:'original',releases:[{id:'r1',version:1}],batches:[{path:'sources.json',sha256:sha('original'),route:'/api/records/import'}],new_entities:0,total_memberships:2,changes:0,sources_batches:['sources.json']};
 const original=Buffer.from(JSON.stringify(base,null,2)+'\n');fs.writeFileSync(path.join(directory,'index.json'),original);
 const next={...base,releases:[...base.releases,{id:'r2',version:2}],batches:[...base.batches,{path:'sources-2.json',sha256:sha('new'),route:'/api/records/import'}],sources_batches:['sources.json','sources-2.json'],new_entities:1,total_memberships:4,changes:1};
 function write(candidate=next,override={}){const bytes=gzipSync(Buffer.from(JSON.stringify(candidate)),{mtime:0});fs.writeFileSync(path.join(directory,'releases-v2.json.gz'),bytes);fs.writeFileSync(path.join(directory,'current-manifest.json'),JSON.stringify({path:'releases-v2.json.gz',sha256:sha(bytes),predecessor_index_sha256:sha(original),...override}));}
 run({directory,base,next,write,original});
 }finally{fs.rmSync(directory,{recursive:true,force:true});}}
test('legacy index remains unchanged; verified extension resolves new release',()=>fixture(({directory,base,next,write,original})=>{assert.deepEqual(readGeographicReleaseManifest(directory),base);write();assert.deepEqual(readGeographicReleaseManifest(directory),next);assert.deepEqual(fs.readFileSync(path.join(directory,'index.json')),original);}));
test('pointer rejects traversal, wrong digest and changed predecessor bytes',()=>fixture(({directory,write})=>{write(undefined,{path:'../releases-v2.json.gz'});assert.throws(()=>readGeographicReleaseManifest(directory),/pointer/);write(undefined,{sha256:'0'.repeat(64)});assert.throws(()=>readGeographicReleaseManifest(directory),/hash mismatch/);write();fs.appendFileSync(path.join(directory,'index.json'),' ');assert.throws(()=>readGeographicReleaseManifest(directory),/predecessor index changed/);}));
test('extension rejects altered predecessor release or batch metadata',()=>fixture(({directory,next,write})=>{let bad=structuredClone(next);bad.releases[0].id='mutated';write(bad);assert.throws(()=>readGeographicReleaseManifest(directory),/predecessor releases changed/);bad=structuredClone(next);bad.batches[0].sha256=sha('mutated');write(bad);assert.throws(()=>readGeographicReleaseManifest(directory),/predecessor batches changed/);}));
test('extension rejects duplicate identities, decreasing versions and repeated batch paths',()=>fixture(({directory,next,write})=>{for(const key of ['identity','version','batch']){const bad=structuredClone(next);if(key==='identity')bad.releases[1].id='r1';if(key==='version')bad.releases[1].version=1;if(key==='batch')bad.batches[1].path='sources.json';write(bad);assert.throws(()=>readGeographicReleaseManifest(directory),/unique ordered|Invalid geographic manifest batch/);}}));
test('manifest pointers cannot load symbolic links',()=>fixture(({directory,write})=>{write();fs.renameSync(path.join(directory,'releases-v2.json.gz'),path.join(directory,'payload.gz'));fs.symlinkSync('payload.gz',path.join(directory,'releases-v2.json.gz'));assert.throws(()=>readGeographicReleaseManifest(directory),/Invalid geographic manifest file/);}));

test('compressed transport retains exact JSON bytes and rejects transport or payload tampering',()=>{
 const original=Buffer.from('{"memberships": []}\n'),compressed=gzipSync(original,{mtime:0}),part={path:'4-memberships-0.json.gz',encoding:'gzip',sha256:sha(compressed),payload_sha256:sha(original)};
 assert.deepEqual(decodeGeographicReleaseBatch(compressed,part),original);assert.deepEqual(decodeGeographicReleaseBatch(original,{path:'original.json',sha256:sha(original)}),original);
 assert.throws(()=>decodeGeographicReleaseBatch(Buffer.concat([compressed,Buffer.from('tamper')]),part),/hash mismatch/);assert.throws(()=>decodeGeographicReleaseBatch(compressed,{...part,payload_sha256:sha('different')}),/payload hash mismatch/);
});
