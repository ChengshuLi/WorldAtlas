import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync,gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {candidateBudget,committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {BUILD_CONTEXT_VALIDATOR_SOURCES,validateBuildContextStage} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {readGeographicReleaseManifest} from '../../../scripts/read-geographic-release-manifest.mjs';
import {readPreparedEvidenceBundle} from '../../../scripts/read-prepared-evidence-bundle.mjs';
import {preparedEvidenceJSON,validatePreparedEvidenceIndex} from '../../../src/prepared-evidence.js';
requirePlainExecution();
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22',output=prefix+'/prepared-evidence-revalidation-v1.json';
if(fs.existsSync(output))throw Error('Preserve previous verification');
const sha=b=>createHash('sha256').update(b).digest('hex'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,[...new Set([...BUILD_CONTEXT_VALIDATOR_SOURCES,prefix+'/revalidate-retained-evidence.mjs','scripts/read-prepared-evidence-bundle.mjs','src/prepared-evidence.js','src/model.js','src/environment-classifications.js'])]);
const budget=candidateBudget(code),inputs=[],products=[];
const read=p=>{const raw=fs.readFileSync(p);const pin={path:p,bytes:raw.length,sha256:sha(raw)};budget.add(pin);inputs.push(pin);return raw;};
const write=(p,raw)=>{budget.add({bytes:raw.length});fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,raw);assert.deepEqual(fs.readFileSync(p),raw);products.push({path:p,bytes:raw.length,sha256:sha(raw)});};
const release=readGeographicReleaseManifest('data/geographic-releases').releases.at(-1);
const lineage=await validateBuildContextStage({expectedReference:release});
const stage=JSON.parse(read('data/native-context-migration/manifest.json'));
function context(pin){const raw=read(pin.path);assert.equal(sha(raw),pin.sha256);const index=JSON.parse(raw),features=[];
 for(const part of index.parts){const bytes=read(path.posix.dirname(pin.path)+'/'+part.path);assert.equal(sha(bytes),part.sha256);const decoded=gunzipSync(bytes,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,part.uncompressed_bytes);assert.equal(sha(decoded),part.uncompressed_sha256);features.push(...JSON.parse(decoded));}return features;}
const before=context(stage.before_context),after=context(stage.after_context),hierarchy=JSON.parse(read('data/hierarchy.json'));
function footprints(features){const units=new Map(hierarchy.map(u=>[u.id,u])),locations=new Map(features.map(f=>[f.id,f])),members=new Map();
 for(const f of features){let id=f.properties.parent_id;const seen=new Set();while(id){assert(!seen.has(id)&&units.has(id));seen.add(id);if(!members.has(id))members.set(id,[]);members.get(id).push(f.id);id=units.get(id).parent_id;}}
 return id=>{const ids=locations.has(id)?[id]:members.get(id);assert(ids?.length,'Missing evidence territory');return {kind:locations.has(id)?'location':units.get(id).level,members:ids.length,sha256:sha(preparedEvidenceJSON(ids.sort().map(id=>[id,locations.get(id).geometry])))};};}
const oldFootprint=footprints(before),newFootprint=footprints(after);
const priorIndexBytes=read('data/prepared-evidence/index.json'),index=await readPreparedEvidenceBundle();
assert.equal(index.footprints_sha256,lineage.predecessorRelease.footprints_sha256);
const oldImports=read('data/prepared-evidence/imports/index.json'),imports=JSON.parse(oldImports);
const reports=[];
for(const product of index.products){assert(['dated-reference-names','demographic-evidence'].includes(product.id));
 const dir='data/'+product.id,receiptPath=dir+'/revalidation.json',oldRaw=read(receiptPath),prior=JSON.parse(oldRaw);
 assert.equal(sha(oldRaw),product.revalidation.sha256);assert.equal(prior.revalidated_geography.footprints_sha256,index.footprints_sha256);
 const manifest=JSON.parse(read(dir+'/index.json')),entities=new Set();let rows=0;
 for(const file of prior.source_product_files)assert.equal(sha(read(dir+'/'+file.path)),file.sha256);
 for(const part of manifest.record_parts??manifest.parts){const p=typeof part==='string'?part:part.path,raw=fs.readFileSync(dir+'/'+p);for(const row of JSON.parse(p.endsWith('.gz')?gunzipSync(raw):raw)){entities.add(product.id==='dated-reference-names'?row.entity_id:row.location_id);rows++;}}
 assert.equal(rows,manifest.records);assert.equal(rows,prior.records);assert.equal(entities.size,prior.entities.length);
 const oldEntities=new Map(prior.entities.map(e=>[e.entity_id,e]));assert.equal(oldEntities.size,entities.size);
 const checked=[...entities].sort().map(id=>{const a=oldFootprint(id),b=newFootprint(id),previous=oldEntities.get(id);assert.deepEqual(a,b,'Affected evidence territory: '+id);assert(previous);assert.equal(previous.result,'identical-footprint');assert.equal(previous.kind,a.kind);assert.equal(previous.member_locations,a.members);assert.equal(previous.revalidated_footprint_sha256,a.sha256);return {...previous,revalidated_footprint_sha256:b.sha256};});
 const archive='data/reference-migrations/retained-seam-v7/'+product.id+'-revalidation.json.archive.gz';write(archive,gzipSync(oldRaw,{level:9}));
 const updated={...prior,revalidation_algorithm_sha256:code.find(p=>p.path===prefix+'/revalidate-retained-evidence.mjs').sha256,
  revalidated_geography:{...prior.revalidated_geography,footprints_sha256:release.footprints_sha256},entities:checked,
  migration_receipts:[...prior.migration_receipts,{path:stage.geometry_manifest.path,sha256:stage.geometry_manifest.sha256}],
  prior_revalidation:{sha256:sha(oldRaw),archive_path:archive,archive_sha256:products.at(-1).sha256,compression:'gzip',revalidated_geography:prior.revalidated_geography},historical_membership_assigned:false};
 write(receiptPath,Buffer.from(JSON.stringify(updated,null,2)+'\n'));
 const receiptHash=products.at(-1).sha256;product.revalidation.sha256=receiptHash;
 for(const pin of product.inputs)if(pin.path==='revalidation.json')pin.sha256=receiptHash;
 reports.push({product:product.id,records:rows,entities:checked.length,result:'all referenced location geometries and descendant identities unchanged'});
}
assert.equal(reports.length,2);assert.equal(reports.reduce((n,r)=>n+r.records,0),index.records+index.names);
write('data/prepared-evidence/prior-release-6-index.json.archive.gz',gzipSync(priorIndexBytes,{level:9}));
write('data/prepared-evidence/prior-release-6-imports.json.archive.gz',gzipSync(oldImports,{level:9}));
imports.footprints_sha256=release.footprints_sha256;write('data/prepared-evidence/imports/index.json',Buffer.from(JSON.stringify(imports,null,2)));
index.footprints_sha256=release.footprints_sha256;index.imports.sha256=products.at(-1).sha256;
validatePreparedEvidenceIndex(index,release);write('data/prepared-evidence/index.json',Buffer.from(JSON.stringify(index,null,2)));
await readPreparedEvidenceBundle();
fs.writeFileSync(output,JSON.stringify({version:1,execution_commit:head,code,inputs,products,reports,mandatory_context_lineage:lineage.receipt,budget:budget.snapshot(),payload_bytes_unchanged:true,historical_membership_assigned:false,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({records:index.records,names:index.names,reports,budget:budget.snapshot()}));
