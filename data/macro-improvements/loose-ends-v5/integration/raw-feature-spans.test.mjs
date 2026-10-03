import assert from 'node:assert/strict';
import test from 'node:test';
import {replaceFeatureSpans} from './raw-feature-spans.mjs';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';

test('unchanged numeric spellings survive replacement beside nested keys and escaped strings',()=>{
 const untouched=String.raw`{"type":"Feature","id":"unchanged","properties":{"id":"unchanged","name":"escaped \\\" features [ ] { }","metadata":{"features":["noise"]}},"geometry":{"type":"Polygon","coordinates":[[[30.0,0.0],[31.00,0.0],[31.0,1.0],[30.0,0.0]]]}}`;
 const changed='{"type":"Feature","id":"changed","properties":{"id":"changed"},"geometry":{"type":"Polygon","coordinates":[[[40.0,0],[41.0,0],[41.0,1],[40.0,0]]]}}';
 const raw=`{ "metadata":{"features": ["not top level"]}, "features" : [ ${untouched},\n ${changed} ], "type":"FeatureCollection" }`;
 const next=JSON.parse(changed);next.geometry.coordinates[0][0][0]=42;
 const result=replaceFeatureSpans(raw,new Map([['changed',next]]));
 assert.ok(result.raw.includes(untouched));assert.deepEqual(result.changed_ids,['changed']);
 const intended=JSON.parse(raw);intended.features[1]=next;
 assert.equal(footprintHash(JSON.parse(result.raw).features),footprintHash(intended.features));
 assert.equal(replaceFeatureSpans(raw,new Map()).raw,raw);
});

test('duplicate identities and changed replacement identities are rejected',()=>{
 const feature={type:'Feature',id:'one',properties:{id:'one'},geometry:{type:'Polygon',coordinates:[]}};
 assert.throws(()=>replaceFeatureSpans(JSON.stringify({features:[feature,feature]}),new Map()),/duplicate feature identity/);
 assert.throws(()=>replaceFeatureSpans(JSON.stringify({features:[feature]}),new Map([['one',{...feature,id:'two'}]])),/Replacement identity changed/);
});
