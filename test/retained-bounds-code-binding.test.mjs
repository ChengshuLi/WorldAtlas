import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {requireHistoricalBoundsMethod,requireBoundsExecutionIdentity,requireRetainedProducerIdentity} from '../scripts/retained-bounds-code-binding.mjs';
import {retainedCoordinateBounds,RETAINED_BOUNDS_CONTRACT} from '../scripts/retained-coordinate-bounds.mjs';
const names=['retained_helper','retained_grid'];
const bodies=Object.fromEntries(names.map(n=>[n,gunzipSync(fs.readFileSync(new URL('./fixtures/retained-bounds-code/'+n+'.gz',import.meta.url))).toString()]));
test('authentic historical producer remains exact independently of current broad modules',()=>{
 requireHistoricalBoundsMethod(bodies.retained_helper,bodies.retained_grid);
 assert.throws(()=>requireHistoricalBoundsMethod(bodies.retained_helper+'changed',bodies.retained_grid),/historical/);
 assert.throws(()=>requireHistoricalBoundsMethod(bodies.retained_helper,bodies.retained_grid+'changed'),/historical/);
});
test('current execution and historical producer are distinct explicit immutable bindings',()=>{
 const old='1'.repeat(40),now='2'.repeat(40);
 const config={method_commit:old,execution_commit:now,accepted_commit:now,inputs:{method_package:{commit:old}}};
 for(const k of ['current_bounds_module','native_selection','native_manifest','execution_package'])config.inputs[k]={commit:now};
 requireBoundsExecutionIdentity(config);
 for(const k of Object.keys(config.inputs)){
   const c=structuredClone(config);c.inputs[k].commit='3'.repeat(40);
   assert.throws(()=>requireBoundsExecutionIdentity(c),/bound|provenance/);
 }
 assert.throws(()=>requireBoundsExecutionIdentity({...config,execution_commit:undefined}),/Explicit/);
 assert.throws(()=>requireBoundsExecutionIdentity({...config,execution_commit:old}),/Explicit/);
});
function extracted(prefix) {
 const helper=bodies[prefix+'_helper'],grid=bodies[prefix+'_grid'];
 const scanner=grid.slice(0,grid.indexOf('// Validate a reviewed canonical view'));
 const hash=helper.slice(helper.indexOf('export function valueSha(value)'),helper.indexOf('const freeze='));
 const bounds=helper.slice(helper.indexOf('export function coordinateBounds(g){'),helper.indexOf('export function possibleNeighbors'));
 const context=vm.createContext({createHash});
 vm.runInContext(scanner.replaceAll('export ','')+'\nconst demand=(v,m)=>{if(!v)throw Error(m);};\n'+hash.replaceAll('export ','')+bounds.replaceAll('export ','')+'\nglobalThis.check=coordinateBounds;',context);
 return g=>{try{return {ok:JSON.stringify(context.check(g))};}catch(e){return {error:e.message};}};
}
const old=extracted('retained'),current=g=>{try{return {ok:JSON.stringify(retainedCoordinateBounds(g))};}catch(e){return {error:e.message};}};
const polygon=ring=>({type:'Polygon',coordinates:[ring]});
test('dense JSON arrays preserve actual bounds, multipart, seam, endpoint and hash semantics',()=>{
 const fixtures=[
 polygon([[0,0],[1,0],[1,1],[0,0]]),
 polygon([[-179,1],[179,1],[179,2],[-179,1]]),
 polygon([[-180,-90],[180,-90],[180,90],[-180,-90]]),
 polygon([[0,0],[Number.MIN_VALUE,0],[0,Number.MIN_VALUE],[0,0]]),
 polygon([[-0,-0],[1,0],[1,1],[0,0]]),
 {type:'MultiPolygon',coordinates:[[[[1,1],[2,1],[2,2],[1,1]]],[[[3,3],[4,3],[4,4],[3,3]]]]}
 ];
 for(const x of fixtures){const g=JSON.parse(JSON.stringify(x));assert.deepEqual(current(g),old(g));assert.ok(current(g).ok);}
 assert.equal(current(fixtures[1]).ok,'[[-180,1,180,2]]');
 for(let i=0;i<100;i++){
  const x=-170+i*3,y=-80+i;
  const g=polygon([[x,y],[x+0.25,y],[x+0.25,y+0.125],[x,y]]);
  assert.deepEqual(current(g),old(g));
 }
});
test('actual old/current bounds preserve malformed dense input refusals',()=>{
 const bad=[null,{}, {type:'LineString',coordinates:[]},{type:'Polygon',coordinates:[]},
 {type:'Polygon',coordinates:[[]]},polygon([[0,0],[1,0],[0,0]]),
 polygon([[0,0],[1,0],[1,1],[0,1]]),polygon([[181,0],[1,0],[1,1],[181,0]]),
 polygon([[0,91],[1,0],[1,1],[0,91]]),polygon([[null,0],[1,0],[1,1],[null,0]]),
 polygon([[0,0,2],[1,0],[1,1],[0,0,2]]),{...polygon([[0,0],[1,0],[1,1],[0,0]]),extra:true},
 polygon([[NaN,0],[1,0],[1,1],[NaN,0]]),polygon([[Infinity,0],[1,0],[1,1],[Infinity,0]])];
 for(const g of bad){assert.deepEqual(current(g),old(g));assert.ok(current(g).error);}
});
test('historical completion/config/driver custody cannot be relabeled to current execution',()=>{
 const sha=v=>createHash('sha256').update(v).digest('hex');
 const driver=Buffer.from('retained producer'),old='1'.repeat(40),now='2'.repeat(40);
 const closure=[{commit:old,path:'a.mjs',mode:'100644',git_blob_oid:'a'.repeat(40),bytes:1,sha256:sha('a')}];
 const config={method_commit:old,execution_commit:now,retained_code_closure:closure,inputs:{previous_config:{sha256:sha('old config')}}};
 const completion={driver_sha256:sha(driver),config_sha256:sha('old config')},previous={method_commit:old,code_closure:closure};
 requireRetainedProducerIdentity(config,completion,previous,driver);
 assert.throws(()=>requireRetainedProducerIdentity(config,completion,{method_commit:now},driver),/producer identity/);
 assert.throws(()=>requireRetainedProducerIdentity(config,completion,previous,Buffer.from('changed')),/producer identity/);
 assert.throws(()=>requireRetainedProducerIdentity(config,{...completion,config_sha256:sha('new config')},previous,driver),/producer identity/);
});
test('current pure bounds closure has no broad helper/grid/scanner dependencies',()=>{
 const code=fs.readFileSync(new URL('../scripts/retained-coordinate-bounds.mjs',import.meta.url),'utf8');
 assert.equal(RETAINED_BOUNDS_CONTRACT,'dense-json-whole-primitive-bounds-v1');
 assert.doesNotMatch(code,/\bimport\s|\brequire\s*\(/);
 const g=polygon([[0,0],[1,0],[1,1],[0,0]]),before=JSON.stringify(g);
 retainedCoordinateBounds(g);assert.equal(JSON.stringify(g),before);
});
test('out-of-domain sparse and embellished arrays refuse rather than broaden JSON contract',()=>{
 const g=polygon([[0,0],[1,0],[1,1],[0,0]]);
 const sparse=structuredClone(g);delete sparse.coordinates[0][1];assert.throws(()=>retainedCoordinateBounds(sparse),/Incomplete ring/);
 const extra=structuredClone(g);extra.coordinates[0].other=1;assert.throws(()=>retainedCoordinateBounds(extra),/Incomplete ring/);
});
test('historical closure must match authentic previous config, ignoring only materialization paths',()=>{
 const sha=v=>createHash('sha256').update(v).digest('hex'),driver='old',old='1'.repeat(40);
 const pin={commit:old,path:'a.mjs',mode:'100644',git_blob_oid:'a'.repeat(40),bytes:1,sha256:sha('a')};
 const config={method_commit:old,inputs:{previous_config:{sha256:sha('config')}},retained_code_closure:[{...pin,task_file:'new/a.mjs'}]};
 const completion={driver_sha256:sha(driver),config_sha256:sha('config')},previous={method_commit:old,code_closure:[{...pin,task_file:'old/a.mjs'}]};
 requireRetainedProducerIdentity(config,completion,previous,driver);
 for(const key of ['commit','path','mode','git_blob_oid','bytes','sha256']){
  const bad=structuredClone(config);bad.retained_code_closure[0][key]='changed';
  assert.throws(()=>requireRetainedProducerIdentity(bad,completion,previous,driver),/Retained closure/);
 }
});
