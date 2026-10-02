import test from 'node:test';
import assert from 'node:assert/strict';
import {previewImport,submitImport} from '../src/import-records.js';
const source={id:'source',name:'Documented source',license:'CC0',vintage:'2026',supported_from:1000,supported_to:1100,status:'historical'};
const record={id:'record',location_id:'location',attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:'source'};
test('import preview rejects invalid dates, scalar values and unsupported source intervals before upload',()=>{
 for(const change of [{valid_from:0},{valid_to:1000},{value:-1},{value:1.5},{value:{}},{valid_to:1200}])assert.throws(()=>previewImport(JSON.stringify({sources:[source],records:[{...record,...change}]})));
 const result=previewImport(JSON.stringify({sources:[source],records:[record],names:[{id:'name',entity_id:'location',name:'Old name',valid_from:1000,valid_to:1100,source_id:'source'}]}));assert.equal(result.rows.length,3);assert.equal(result.rows[1].value,42);assert.equal(result.counts.names,1);
 assert.throws(()=>previewImport(JSON.stringify({records:[{...record,attribute:'owner',value:'Country'}]})),/category ID/);
 assert.throws(()=>previewImport(JSON.stringify({records:[record],attribute_records:[record]})),/Duplicate/);
});
test('import preview enforces whole-batch row and UTF-8 byte bounds',()=>{
 assert.throws(()=>previewImport(JSON.stringify({records:Array.from({length:251},(_,i)=>({...record,id:String(i)}))})),/250/);
 assert.throws(()=>previewImport(JSON.stringify({records:[record],padding:'界'.repeat(400000)})),/1 MiB/);
 assert.throws(()=>previewImport('[]'),/object/);assert.throws(()=>previewImport('{}'),/1–250/);assert.throws(()=>previewImport('{'),/valid JSON/);
});
test('import submission preserves evidence and reports database rejection without treating it as saved',async()=>{
 const payload={sources:[source],records:[record]};let sent;
 const result=await submitImport(payload,async(url,options)=>{sent={url,options};return Response.json({duplicate:false,counts:{records:1},revision:7});});
 assert.equal(result.revision,7);assert.equal(sent.url,'/api/records/import');assert.equal(sent.options.method,'POST');assert.deepEqual(JSON.parse(sent.options.body),payload);
 await assert.rejects(submitImport(payload,async()=>Response.json({error:'Source interval conflict'},{status:409})),/Source interval conflict/);
});


test('source-backed corrections preview withdrawal and replacement while retaining source evidence',()=>{
 const correction={id:'correction',collection:'records',target_id:'record',source_id:'source',reason:'Revised source corrects the earlier claim'};
 const preview=previewImport(JSON.stringify({sources:[source],retirements:[correction]}));
 assert.equal(preview.rows[1].subject,'record');assert.equal(preview.rows[1].value,'withdraw');assert.equal(preview.rows[1].source,'source');assert.deepEqual(preview.payload.retirements[0],correction);
 const replacement=previewImport(JSON.stringify({retirements:[{...correction,replacement_id:'replacement'}]}));assert.equal(replacement.rows[0].value,'supersede with replacement');
 for(const change of [{source_id:''},{target_id:''},{reason:''},{collection:'entities'}])assert.throws(()=>previewImport(JSON.stringify({retirements:[{...correction,...change}]})));
});
