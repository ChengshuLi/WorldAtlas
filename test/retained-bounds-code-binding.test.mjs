import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {retainedBoundsCodeCompatibility,requireBoundsExecutionIdentity,requireRetainedProducerIdentity} from '../scripts/retained-bounds-code-binding.mjs';
const names=['retained_helper','current_helper','retained_grid','current_grid'];
const bodies=Object.fromEntries(names.map(n=>[n,gunzipSync(fs.readFileSync(new URL('./fixtures/retained-bounds-code/'+n+'.gz',import.meta.url))).toString()]));
test('actual historical/current complete bodies admit only the reviewed JSON bounds edge',()=>{
 const r=retainedBoundsCodeCompatibility(bodies);
 assert.equal(r.native_qualification_authorized,false);
 assert.match(r.basis,/reviewed/);
 for(const n of names)assert.throws(()=>retainedBoundsCodeCompatibility({...bodies,[n]:bodies[n]+'\n// changed'}),/Unreviewed/);
 assert.throws(()=>retainedBoundsCodeCompatibility({...bodies,current_grid:undefined}),/Complete/);
 assert.match(retainedBoundsCodeCompatibility({...bodies,current_helper:bodies.retained_helper,current_grid:bodies.retained_grid}).basis,/literal/);
});
test('current execution and historical producer are distinct explicit immutable bindings',()=>{
 const old='1'.repeat(40),now='2'.repeat(40);
 const config={method_commit:old,execution_commit:now,accepted_commit:now,inputs:{method_package:{commit:old}}};
 for(const k of ['current_coordinate_helper','current_native_grid','native_selection','native_manifest','execution_package'])config.inputs[k]={commit:now};
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
const old=extracted('retained'),current=extracted('current');
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
test('retained periodic numerical scanner and lattice dependencies are literal',()=>{
 const prefix=s=>s.slice(0,s.indexOf('// Validate a reviewed canonical view'));
 assert.equal(prefix(bodies.retained_grid),prefix(bodies.current_grid));
 assert.equal(createHash('sha256').update(prefix(bodies.current_grid)).digest('hex'),'9b2e369c470c35d82015aae5c74299ca4ca6cccd1db5494956b0a9ae87c814dd');
});

test('historical completion/config/driver custody cannot be relabeled to current execution',()=>{
 const sha=v=>createHash('sha256').update(v).digest('hex');
 const driver=Buffer.from('retained producer'),old='1'.repeat(40),now='2'.repeat(40);
 const config={method_commit:old,execution_commit:now,inputs:{previous_config:{sha256:sha('old config')}}};
 const completion={driver_sha256:sha(driver),config_sha256:sha('old config')},previous={method_commit:old};
 requireRetainedProducerIdentity(config,completion,previous,driver);
 assert.throws(()=>requireRetainedProducerIdentity(config,completion,{method_commit:now},driver),/producer identity/);
 assert.throws(()=>requireRetainedProducerIdentity(config,completion,previous,Buffer.from('changed')),/producer identity/);
 assert.throws(()=>requireRetainedProducerIdentity(config,{...completion,config_sha256:sha('new config')},previous,driver),/producer identity/);
});
test('actual retained/current seam preprocessing preserves complete small lattice oracle and refusals',()=>{
 const load=prefix=>{
   const s=bodies[prefix+'_grid'],start=s.indexOf('export function verifyNativeSeamView'),end=s.indexOf('\nexport ',start+10);
   const context=vm.createContext({});
   vm.runInContext(s.slice(0,end).replaceAll('export ','')+'\nglobalThis.check=verifyNativeSeamView;',context);
   return (a,b,o)=>{try{return {ok:JSON.stringify(context.check(a,b,o))};}catch(e){return {error:e.message};}};
 };
 const before=load('retained'),after=load('current');
 const raw=polygon([[179,-20],[180.00000000000003,-20],[180.00000000000003,20],[179,-20]]);
 const view=polygon([[179,-20],[180,-20],[180,20],[179,-20]]);
 const options={size:8,latitudes:[80,60,40,20,0,-20,-40,-60]};
 assert.deepEqual(after(raw,view,options),before(raw,view,options));
 assert.ok(after(raw,view,options).ok);
 for(const [a,b,o] of [[view,view,options],[raw,view,{...options,size:0}],[raw,view,{...options,latitudes:[0]}],[raw,polygon([[179,-20],[181,-20],[181,20],[179,-20]]),options]]){
   assert.deepEqual(after(a,b,o),before(a,b,o));assert.ok(after(a,b,o).error);
 }
});
