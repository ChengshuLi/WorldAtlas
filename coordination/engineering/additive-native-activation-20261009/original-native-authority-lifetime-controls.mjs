import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {fileURLToPath,pathToFileURL} from 'node:url';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
import * as proposed from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const repo=fileURLToPath(new URL('../../../',import.meta.url));
const registry=JSON.parse(fs.readFileSync(new URL('../additive-native-gap-batch-20261008/composition-v2/original-registry.json',import.meta.url)));
const source=fs.readFileSync(new URL('../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url),'utf8');
const oldFunction=fs.readFileSync(new URL('./original-native-authority-function.fixture.txt',import.meta.url),'utf8');
const cache=path.join(repo,'.cache');if(!fs.existsSync(cache))fs.mkdirSync(cache);assert(fs.lstatSync(cache).isDirectory()&&!fs.lstatSync(cache).isSymbolicLink());
const temp=fs.mkdtempSync(path.join(cache,'native-authority-control-'));
const a=source.indexOf('export function qualifyOriginalNativeAuthority('),z=source.indexOf('\n// Comparison is conservation',a);assert(a>=0&&z>a);
let fixture=source.slice(0,a)+oldFunction+source.slice(z);
fixture=fixture.replace("'../../../scripts/check-effective-geographic-regression.mjs'",JSON.stringify(pathToFileURL(path.join(repo,'scripts/check-effective-geographic-regression.mjs')).href)).replace("'../../../src/ownership-codec.js'",JSON.stringify(pathToFileURL(path.join(repo,'src/ownership-codec.js')).href));
fs.writeFileSync(path.join(temp,'original.mjs'),fixture,{flag:'wx'});
try{
const original=await import(pathToFileURL(path.join(temp,'original.mjs')).href);
const options={runtimeBytes:146540752,executionBytes:282529,metadataBytes:8388608,outputBytes:4194304,gitExecutable:'/Library/Developer/CommandLineTools/usr/bin/git'};
const reader=metadata=>new ImmutableReader(repo,'c3cd586bbbc73ff44932a2c170e339c820cdfafd',{...options,metadataBytes:metadata});
const strip=v=>{if(Array.isArray(v))return v.map(strip);if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).filter(([k])=>k!=='complete_phase_bytes').map(([k,x])=>[k,strip(x)]));return v;};
const receipts=[];
for(const entry of registry.entries){
 const oldReader=reader(8388608),oldReads=[];const oldRead=oldReader.read.bind(oldReader);oldReader.read=(name,opts)=>{oldReads.push(name);return oldRead(name,opts);};const old=original.readRetainedRegistryAuthority(oldReader,entry);
 const r=reader(81334899-2*(entry.rule_preimage.bytes+entry.source_authority.bytes));let max=0,reads=[];const phase=r.phase.bind(r);r.phase=()=>{phase();max=Math.max(max,r.used);};const read=r.read.bind(r);r.read=(name,opts)=>{const value=read(name,opts);reads.push(name);max=Math.max(max,r.used);return value;};
 const next=proposed.readRetainedRegistryAuthority(r,entry);assert.deepEqual(strip(next),strip(old));
 assert(next.native_proof.complete_phase_bytes<=268435456);assert(r.metadataBytes>81334899);assert(r.charged.size===0);assert(max<=268435456);
 const binding=oldReader.json(entry.source_authority.path,{version:entry.source_authority.commit,expected:entry.source_authority.sha256});
 const all=[binding.native_proof.publication,binding.native_proof.inventory,binding.native_proof.operating,...binding.native_proof.assets];
 for(const pin of all)assert.equal(reads.filter(x=>x===pin.path).length,oldReads.filter(x=>x===pin.path).length);
 receipts.push({rule:entry.rule_sha256,scopes:next.native_proof.scope_ids.length,complete_native_body_reads:all.length,max_phase_bytes:next.native_proof.complete_phase_bytes,final_retained_metadata_bytes:r.metadataBytes,semantic_equal_excluding_phase_metric:true});
}
const entry=registry.entries[1];
function genuine(){const r=reader(8388608);const binding=r.json(entry.source_authority.path,{version:entry.source_authority.commit,expected:entry.source_authority.sha256});const custody=proposed.readOriginalRuleAuthority(r,binding.original_pins);proposed.qualifyOriginalSourceAuthority(custody);return{r,custody,pins:structuredClone(binding.native_proof)};}
const refusals=[];
for(const kind of ['encoded-sha','decoded-sha','mode','omitted-asset','reordered-assets','carry-cap','foreign-custody']){const {r,custody,pins}=genuine();let calls=0;const read=r.read.bind(r);r.read=(...args)=>{calls++;return read(...args);};
 if(kind==='encoded-sha')pins.assets[0].sha256='0'.repeat(64);
 if(kind==='decoded-sha'){const p=pins.assets.find(x=>x.uncompressed_sha256||x.decoded_sha256);if(p.uncompressed_sha256)p.uncompressed_sha256='0'.repeat(64);else p.decoded_sha256='0'.repeat(64);}
 if(kind==='mode')pins.inventory.mode='100755';
 if(kind==='omitted-asset')pins.assets.pop();
 if(kind==='reordered-assets')pins.assets.reverse();
 if(kind==='carry-cap')r.metadataBytes=268435455;
 assert.throws(()=>proposed.qualifyOriginalNativeAuthority(kind==='foreign-custody'?structuredClone(custody):custody,pins));
 if(kind==='carry-cap'||kind==='foreign-custody')assert.equal(calls,0);
 refusals.push({kind,refused:true,native_body_reads_before_refusal:calls});
}
console.log(JSON.stringify({limits:'Retained original custody reader controls only; no source/scientific operator, selected full gate or activation claim. Original authority function fixture is the literal pre-fix function, inserted into the current module; only two fixture imports are redirected to the actual helper/codec.',positives:receipts,refusals},null,2));

}finally{fs.rmSync(temp,{recursive:true});}
