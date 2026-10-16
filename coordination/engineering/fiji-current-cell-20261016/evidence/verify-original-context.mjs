import fs from 'node:fs';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';import {createHash} from 'node:crypto';
import {verifyNativeSeamView} from '../../../../src/native-grid.js';
import {valueSha} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const baseline='ab0d2088bc66e0d9847b273eb8519a92c0f109b1',prefix='coordination/engineering/fiji-current-cell-20261016/';
const sha=body=>createHash('sha256').update(body).digest('hex');
const raw=name=>execFileSync('git',['show',baseline+':'+name],{maxBuffer:16*1024**2});
const catalogue=JSON.parse(raw('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'));
const sourceProducts=new Map(),families=[];
for(const key of ['gb:FJI:ADM1','gb:FJI:ADM2']){
 const record=catalogue.products.find(p=>p.key===key),parts=[];
 for(const part of record.parts){const body=raw(part.path);assert.equal(body.length,part.bytes);assert.equal(sha(body),part.sha256);
  const decoded=gunzipSync(body);assert.equal(decoded.length,part.uncompressed_bytes);assert.equal(sha(decoded),part.uncompressed_sha256);parts.push(decoded);}
 const body=Buffer.concat(parts);assert.equal(body.length,record.original_bytes);assert.equal(sha(body),record.original_sha256);
 const product=JSON.parse(body);assert.equal(product.features.length,record.feature_count);
 for(const feature of product.features){assert.equal(feature.properties.shapeGroup,'FJI');assert.equal(feature.properties.shapeType,key.split(':')[2]);}
 sourceProducts.set(key,product);
 families.push({key,features:record.feature_count,original_bytes:body.length,original_sha256:sha(body),source_url:record.recorded_consumed_url,
  represented_year_claim:record.source_represented_year_claim,recorded_license:record.recorded_license});
}
const stage=JSON.parse(fs.readFileSync(prefix+'original-stage-inputs.json')),family=sourceProducts.get('gb:FJI:ADM2');
assert.equal(stage.length,15);assert.equal(new Set(stage.map(s=>s.target)).size,15);
for(const input of stage){const original=family.features.find(f=>'gb:FJI:ADM2:'+f.properties.shapeID===input.target);
 assert.deepEqual(input.consumed,original);assert.equal(input.selected.id,input.target);assert.equal(input.selected.properties.reference_owner,'Fiji');
 assert.equal(input.selected.properties.metadata.source_id,'gb:FJI:ADM2');}
const evidence=JSON.parse(fs.readFileSync(prefix+'source-002/source-evidence.json')),p=evidence.native_latitudes;
const latraw=gunzipSync(execFileSync('git',['show',p.commit+':'+p.path],{maxBuffer:8*1024**2}));assert.equal(sha(latraw),p.decoded_sha256);
const latitudes=Float64Array.from({length:latraw.length/8},(_,i)=>latraw.readDoubleLE(i*8));
const qname='coordination/engineering/global-current-cell-work-queue-20261014/normalized-source-seams.json',qraw=raw(qname);
assert.equal(sha(qraw),'0e74bb81ae45ae9913ee5d43afd303fa33a4b7da8b06e4e6f1cd4419ecd264b4');
const seams=JSON.parse(qraw),comparisons=[];
for(const record of seams){const family=record.source_id.split(':').slice(0,3).join(':');
 const feature=sourceProducts.get(family).features.find(f=>family+':'+f.properties.shapeID===record.source_id);
 assert.deepEqual(feature.geometry,record.original_geometry);
 comparisons.push({source_id:record.source_id,name:record.name,method:record.normalization,original_geometry_sha256:valueSha(feature.geometry),
  ...verifyNativeSeamView(feature.geometry,record.geometry,{size:latitudes.length,latitudes})});
}
const report={version:1,baseline,complete_families:families,exact_direct_source_target_joins:stage.length,
 frozen_normalization:{path:qname,sha256:sha(qraw),comparisons},
 limits:['ADM1 is complete reviewed source context only; no ADM1 assignment.',
 'The 2020 and 2006 fields are retained source vintage claims, not newly verified present-day legal applicability.',
 'The simplified consumed products remain distinct from full-resolution URLs in selected display metadata.']};
assert.deepEqual(JSON.parse(fs.readFileSync(prefix+'complete-source-context.json')),report,'Retained whole report differs');
console.log(JSON.stringify({families:families.map(f=>({key:f.key,features:f.features})),direct_joins:stage.length,comparisons:comparisons.map(c=>({name:c.name,cells:c.native_cells}))}));
