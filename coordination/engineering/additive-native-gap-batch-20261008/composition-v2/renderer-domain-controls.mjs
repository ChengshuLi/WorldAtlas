import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';import {createHash} from 'node:crypto';
import {effectiveFootprintBounds} from '../../../../src/effective-footprint.js';
const file='src/pixel-canvas-layer.js',source=fs.readFileSync(file,'utf8'),start=source.indexOf('  constructor(features,options)'),end=source.indexOf('\n  sendIndex(',start);
assert(start>=0&&end>start);const code='class ActualConstructor extends L.Layer {\n'+source.slice(start,end)+'\n} ActualConstructor';
// Literal production constructor; leaf/staging/worker surfaces are bounded
// stubs. Drawing and picking algorithms are not replaced or claimed by this test.
const c={L:{Layer:class{}},NATIVE_GRID_METHOD:'native-linear-evenodd-first-owner-v1',effectiveFootprintBounds,createGridIndex:features=>features.map(feature=>({feature,polygons:[],bounds:[]})),projectCell:(x,y)=>[x,y],Worker:class{postMessage(){}},URL:class{},Object,Set};
const Constructor=vm.runInNewContext(code.replaceAll('import.meta.url',JSON.stringify('file:///fixture/')),c);
const Q='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/',features=JSON.parse(fs.readFileSync('coordination/engineering/additive-native-gap-batch-20261008/batch-proposal-v1-run1/features.json'));
const v1=features.filter(f=>Object.hasOwn(f,'additiveFootprint')).slice(0,1),row=JSON.parse(fs.readFileSync(Q+'composed-original-ledger.json')).rows.find(r=>r.disposition==='assigned');
const v2=[{id:row.target_id,pixelIndex:row.pixelIndex,properties:{parent_id:'fixture'},geometry:row.base_geometry,additiveFootprint:{version:2,kind:'retained-base-plus-additions',baseline_release_sha256:'1'.repeat(64),base_geometry_sha256:row.base_geometry_sha256,ledger_sha256:'2'.repeat(64),authority_registry_sha256:'3'.repeat(64),components:[row]}}];
const grid=v=>({method:'native-linear-evenodd-first-owner-v1',effective_footprint_domain:'worldatlas-effective-native-footprints:v'+v,effective_footprint_sha256:'a'.repeat(64)});
new Constructor(v1,{ownership:grid(1)});new Constructor(v2,{ownership:grid(2)});
let negatives=0;const reject=(f,o)=>{assert.throws(()=>new Constructor(f,o));negatives++;};
reject(v2,{ownership:grid(1)});reject(v1,{ownership:grid(2)});reject(v2,{ownership:{...grid(2),method:'projected'}});reject(v2,{ownership:{...grid(2),effective_footprint_sha256:'foreign'}});reject([...v1,...v2],{ownership:grid(2)});reject(v2,{});
fs.writeFileSync(Q+'renderer-domain-controls.json',JSON.stringify({version:1,kind:'literal-renderer-constructor-domain-controls',source_sha256:createHash('sha256').update(source).digest('hex'),positives:2,negative_controls:negatives,limits:['Literal production constructor with bounded browser/worker stubs; domain dispatch only, not full rendering or bank qualification.']},null,2)+'\n');console.log(JSON.stringify({positives:2,negatives}));
