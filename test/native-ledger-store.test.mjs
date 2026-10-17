import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {admitNativeLedgerStore} from '../scripts/native-patch-store.mjs';
import {valueBytes} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const hash=body=>createHash('sha256').update(body).digest('hex');
const temporary=t=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ledger-store-test-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return dir;};
const chunks=function*(body,width=29){for(let i=0;i<body.length;i+=width)yield body.subarray(i,i+width);};
const open=(directory,text,options={})=>{const body=Buffer.from(text);return admitNativeLedgerStore({directory,size:100,ownerCount:10,chunks:chunks(body),expected:{bytes:body.length,sha256:hash(body)},...options});};
const materialize=(store,component)=>({...store.componentMetadata(component),...(component.hasNativeRows?{native_rows:[...store.componentRows(component)].map(row=>({y:row.y,runs:[...store.intervals(row)]}))}:{})});

test('ledger stores complete ordered components, metadata, native rows and both raw/normalized canonical identities',async t=>{
 const directory=temporary(t),value={version:3,scope_ids:['A','B','C'],rows:[
  {component_id:'A',geometry:{type:'Polygon',coordinates:[[[0,0],[1,1]]]},native_rows:[{y:1,runs:[[0,2,1]]}],pixelIndex:1},
  {component_id:'B',base_geometry:{type:'Polygon',coordinates:[]},disposition:'held',extra:{unknown:'kept'}},
  {component_id:'C',native_rows:[{y:0,runs:[]},{y:2,runs:[[3,9,2]]}],pixelIndex:2}
 ]};
 const store=await open(directory,JSON.stringify(value,null,2));
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.equal(store.componentCount,3);assert.equal(store.nativeRowCount,3);assert.equal(store.runCount,2);
 const all=[...store.componentEntries()];assert.deepEqual(all.map(c=>materialize(store,c)),value.rows);
 for(const component of all){
  assert.equal(component.canonical_sha256,hash(valueBytes(value.rows[component.ordinal])));
  assert.equal([...store.componentCanonicalChunks(component)].join(''),valueBytes(value.rows[component.ordinal]).toString());
  const overrides={rule_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64)};
  assert.equal([...store.componentCanonicalChunks(component,{overrides})].join(''),valueBytes({...value.rows[component.ordinal],...overrides}).toString());
  assert.equal([...store.componentCanonicalChunks(component,{newline:false})].join('')+'\n',valueBytes(value.rows[component.ordinal]).toString());
  assert(Object.isFrozen(store.componentMetadata(component)));
 }
 assert.throws(()=>store.componentMetadata({...all[0]}),/Foreign/);
 assert.throws(()=>[...store.componentCanonicalChunks(all[0],{overrides:{native_rows:[]}})],/cannot replace/);
 const first=store.componentEntries(),second=store.componentEntries();assert.deepEqual(first.next().value,second.next().value);
 store.close();assert.throws(()=>first.next(),/closed/);assert.throws(()=>store.componentMetadata(all[0]),/closed/);assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger duplicate root/component/native row fields preserve final JSON semantics without materializing dense rows',async t=>{
 const directory=temporary(t);
 for(const text of [
  '{"rows":false,"rows":[{"component_id":"A"}]}',
  '{"rows":[2,{"native_rows":false}],"rows":[]}',
  '{"rows":[{"native_rows":false,"native_rows":[{"y":-2,"y":0,"runs":null,"runs":[[0,1,1]]}],"component_id":"old","component_id":"new"}]}',
  '{"rows":[{"native_rows":[{"y":0,"runs":[[0,2,1]]}],"native_rows":[]}],"rows":[{"native_rows":[],"x":{"__proto__":1}}]}',
  '{"rows":[{"bad":1e400}],"rows":[{"native_rows":[],"bad":1}]}',
  '{"rows":[{"pixelIndex":1,"native_rows":[{"y":2,"runs":[[8,9,1]]}],"disposition":"held","native_rows":[{"y":0,"runs":[[1,3,2]]}],"pixelIndex":2,"disposition":"assigned"}]}',
  '{"rows":[],"__proto__":{"x":2},"rows":[{"__proto__":{"y":3},"2":false,"10":true}]}'
 ]){
  const store=await open(directory,text),value=JSON.parse(text);
  assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.deepEqual([...store.componentEntries()].map(c=>materialize(store,c)),value.rows);store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger metadata larger than writer windows is retained exactly one component at a time',async t=>{
 const directory=temporary(t),value={rows:[{component_id:'large',text:'x😀'.repeat(30000),native_rows:[{y:0,runs:[[0,1,1]]}]}]};
 const store=await open(directory,JSON.stringify(value));const [component]=store.componentEntries();
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.deepEqual(materialize(store,component),value.rows[0]);store.close();
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger malformed syntax, final domain errors and late identity failures return no admitted component',async t=>{
 const directory=temporary(t);
 for(const text of ['{"rows":[{"native_rows":[],}],"rows":[]}','{"rows":[{"x":01}],"rows":[]}',
  '{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}]} true','{"rows":[null]}',
  '{"rows":[{"native_rows":false}]}','{"rows":[{"native_rows":[{"y":0,"runs":[[0,101,1]]}]}]}',
  '{"rows":[{"x":1e400}]}']){
  await assert.rejects(open(directory,text));assert.deepEqual(fs.readdirSync(directory),[]);
 }
 const text='{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}]}';
 await assert.rejects(open(directory,text,{expected:{bytes:Buffer.byteLength(text),sha256:'0'.repeat(64)}}),/identity/);
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger runtime read/write failures cannot be excused by a later duplicate rows field',async t=>{
 const directory=temporary(t),text='{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}],"rows":[]}';
 for(const method of ['readSync','writeSync']){
  t.mock.method(fs,method,()=>{throw Error('real disk failure '+method);});
  await assert.rejects(open(directory,text),/real disk failure/);t.mock.restoreAll();
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('ledger component and dense-row ingestion retains bounded working graphs under a 64MiB child heap',async t=>{
 const directory=temporary(t),module=new URL('../scripts/native-patch-store.mjs',import.meta.url).href;
 const script=`import {admitNativeLedgerStore} from ${JSON.stringify(module)};import {createHash} from 'node:crypto';
  function* chunks(){yield Buffer.from('{"rows":[');for(let c=0;c<4;c++){yield Buffer.from((c?',':'')+'{"component_id":"'+c+'","native_rows":[{"runs":[');
   for(let i=0;i<100000;i++)yield Buffer.from((i?',':'')+JSON.stringify([i*2,i*2+1,c+1]));yield Buffer.from('],"y":0}]}');}yield Buffer.from(']}\\n');}
  let bytes=0;const hash=createHash('sha256');for(const chunk of chunks()){bytes+=chunk.length;hash.update(chunk);}const sha256=hash.digest('hex');
  const store=await admitNativeLedgerStore({directory:${JSON.stringify(directory)},size:200000,ownerCount:4,chunks:chunks(),expected:{bytes,sha256}});
  let count=0;for(const component of store.componentEntries())for(const row of store.componentRows(component))for(const run of store.intervals(row))count++;
  console.log(JSON.stringify({count,componentCount:store.componentCount,sha256,canonical:store.canonical_sha256,maxRSS:process.resourceUsage().maxRSS}));store.close();`;
 const result=spawnSync(process.execPath,['--max-old-space-size=64','--input-type=module','-e',script],{encoding:'utf8',timeout:120000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 assert.equal(result.status,0,result.stderr);const observed=JSON.parse(result.stdout);
 assert.equal(observed.count,400000);assert.equal(observed.componentCount,4);assert.equal(observed.canonical,observed.sha256);assert.deepEqual(fs.readdirSync(directory),[]);
});

test('component ordinal lookup equals complete iteration and rejects foreign or closed handles',async t=>{
 const value={rows:[{component_id:'a',native_rows:[{y:1,runs:[[0,2,1]]}]},{component_id:'b',geometry:{type:'Polygon',coordinates:[]}}]};
 const store=await open(temporary(t),JSON.stringify(value));
 const sequential=[...store.componentEntries()];
 for(let i=0;i<sequential.length;i++){
  const lookup=store.componentAt(i);assert.deepEqual(lookup,sequential[i]);
  assert.deepEqual(materialize(store,lookup),value.rows[i]);
  assert.throws(()=>store.componentMetadata({...lookup}),/Foreign native component/);
 }
 assert.equal(store.componentAt(-1),undefined);assert.equal(store.componentAt(2),undefined);
 assert.throws(()=>store.componentAt(0.5),/ordinal/);store.close();
 assert.throws(()=>store.componentAt(0),/closed/);
});

test('constructor ledger_rows uses the same component store and complete canonical identity',async t=>{
 const value={component_ids:['A'],ledger_rows:[{component_id:'A',base_geometry:{type:'Polygon',coordinates:[]},native_rows:[{y:2,runs:[[1,3,2]]}]}]};
 const directory=temporary(t),store=await open(directory,JSON.stringify(value),{rowField:'ledger_rows'});
 try{
  assert.equal(store.componentCount,1);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
  assert.deepEqual(materialize(store,store.componentAt(0)),value.ledger_rows[0]);
 }finally{store.close();}
 const replaced=await open(directory,'{"ledger_rows":false,"ledger_rows":'+JSON.stringify(value.ledger_rows)+'}',{rowField:'ledger_rows'});
 try{assert.equal(replaced.canonical_sha256,hash(valueBytes({ledger_rows:value.ledger_rows})));}finally{replaced.close();}
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('large coordinate rings use repeatable semantic cursors with exact canonical numbers and duplicate keys',async t=>{
 const directory=temporary(t),ring=Array.from({length:129},(_,i)=>[i/10,-i/100]);ring.push(ring[0]);
 const geometry={type:'Polygon',coordinates:[ring]},value={rows:[{component_id:'geometry',geometry}]};
 const source=JSON.stringify(value).replace('"geometry":','"geometry":{"discarded":true},"geometry":').replace('[0,0]','[-0e0, 0.000]');
 const store=await open(directory,source),component=store.componentAt(0),actual=store.componentMetadata(component);
 const storedRing=actual.geometry.coordinates[0];assert.equal(Array.isArray(storedRing),false);
 assert.equal(storedRing.length,ring.length);assert.deepEqual([...storedRing],JSON.parse(source).rows[0].geometry.coordinates[0]);
 assert.deepEqual([...storedRing],[...storedRing]);assert.deepEqual(storedRing.at(64),ring[64]);
 assert.equal(store.canonical_sha256,hash(valueBytes(JSON.parse(source))));
 assert.equal([...store.componentCanonicalChunks(component)].join(''),valueBytes(value.rows[0]).toString());
 store.close();assert.throws(()=>storedRing.at(0),/closed/);assert.deepEqual(fs.readdirSync(directory),[]);
});

test('nested coordinate cursor indices preserve multiple rings, polygons and last-key-wins errors',async t=>{
 const directory=temporary(t),ring=n=>Array.from({length:70},(_,i)=>[i+n,i-n]);
 const value={rows:[{geometry:{type:'MultiPolygon',coordinates:[[ring(0),ring(2)],[ring(4)]]}},{geometry:{type:'Polygon',coordinates:[ring(6)]}}]};
 const store=await open(directory,JSON.stringify(value));
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));
 for(const component of store.componentEntries())assert.equal([...store.componentCanonicalChunks(component)].join(''),valueBytes(value.rows[component.ordinal]).toString());
 store.close();
 const bad='{"coordinates":['+Array(40).fill('[1e400,0]').join(',')+']}';
 for(const source of ['{"rows":[{"geometry":'+bad+'}],"rows":[]}','{"rows":[{"geometry":'+bad+',"geometry":{}}]}']){
  const admitted=await open(directory,source);assert.equal(admitted.canonical_sha256,hash(valueBytes(JSON.parse(source))));admitted.close();
 }
 await assert.rejects(open(directory,'{"rows":[{"geometry":'+bad+'}]}'),/Nonfinite/);
 assert.deepEqual(fs.readdirSync(directory),[]);
});

import {nativeRuntimeIndex,polygonParts,nativeSequence} from '../src/native-grid.js';
import {coordinateBounds,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
test('stored geometry shares exact bounds, runtime polygons and malformed-coordinate refusals with literals',async t=>{
 const directory=temporary(t),ring=Array.from({length:40},(_,i)=>[i/100,i/100]);ring.push(ring[0]);
 const geometries=[{type:'Polygon',coordinates:[ring]},...[
  points=>points.slice(0,-1),points=>points.map((p,i)=>i===17?[181,0]:p),
  points=>points.map((p,i)=>i===17?[0,0,0]:p),points=>points.map((p,i)=>i===17?null:p)
 ].map(change=>({type:'Polygon',coordinates:[change(ring)]}))];
 for(const geometry of geometries){
  const store=await open(directory,JSON.stringify({rows:[{geometry}]})),stored=store.componentMetadata(store.componentAt(0)).geometry;
  for(const fn of [coordinateBounds,polygonParts,g=>nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry:g}])]){
   let expected;try{expected=fn(geometry);}catch(error){assert.throws(()=>fn(stored),{message:error.message});continue;}
   const actual=fn(stored);assert.equal(valueSha(actual),valueSha(expected));
  }
  store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('private coordinate-reference lookalikes stay ordinary input and spill I/O remains fatal',async t=>{
 const directory=temporary(t),lookalike={depth:0,start:0,count:129,error:'pretend',coordinates:Array(40).fill([3,{depth:99,start:0,count:1}])};
 const value={rows:[{geometry:lookalike,reference:[null,[['geometry'],{depth:0,start:0,count:99}]]}]};
 const store=await open(directory,JSON.stringify(value));assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
 const geometry={coordinates:[Array.from({length:40},(_,i)=>[i,i])]};
 const text='{"rows":[{"geometry":'+JSON.stringify(geometry)+'}],"rows":[]}';
 for(const method of ['readSync','writeSync']){
  t.mock.method(fs,method,()=>{throw Error('coordinate spill I/O sentinel');});
  await assert.rejects(open(directory,text),/coordinate spill I\/O sentinel/);t.mock.restoreAll();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

import {validateWitnessGeometry,witnessCellEffects,nativePolygonIntervals,nativeRowLatitudes,verifyNativeSeamView} from '../src/native-grid.js';
test('stored coordinates preserve all witness primitive kinds and exact cell predicates',async t=>{
 const directory=temporary(t),points=Array.from({length:40},(_,i)=>[i/10-2,i/20-1]),ring=[...points,points[0]];
 const shapes=[{type:'Point',coordinates:[0,0]},{type:'MultiPoint',coordinates:points},{type:'LineString',coordinates:points},
  {type:'MultiLineString',coordinates:[points,points.slice().reverse()]},{type:'Polygon',coordinates:[ring]},
  {type:'MultiPolygon',coordinates:[[ring]]}];
 shapes.push({type:'GeometryCollection',geometries:shapes.slice()});
 const options={size:16,latitudes:nativeRowLatitudes(16),requestedRows:[{y:8,runs:[[0,16,1]]}],nativePolygonIntervals};
 for(const geometry of shapes){
  const store=await open(directory,JSON.stringify({rows:[{geometry}]})),stored=store.componentMetadata(store.componentAt(0)).geometry;
  assert.deepEqual(validateWitnessGeometry(stored),validateWitnessGeometry(geometry));
  assert.deepEqual(witnessCellEffects(stored,options),witnessCellEffects(geometry,options));store.close();
 }
 for(const geometry of [{type:'MultiPoint',coordinates:[...points,null]},{type:'LineString',coordinates:[...points,[181,0]]},
  {type:'Polygon',coordinates:[points]},{type:'MultiPolygon',coordinates:[[points]]}]){
  const store=await open(directory,JSON.stringify({rows:[{geometry}]})),stored=store.componentMetadata(store.componentAt(0)).geometry;
  let expected;try{validateWitnessGeometry(geometry);}catch(error){expected=error.message;}assert(expected);
  assert.throws(()=>validateWitnessGeometry(stored),{message:expected});store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('stored seam coordinates preserve exact canonical-frame verification',async t=>{
 const directory=temporary(t),epsilon=180.00000000000003;
 const ring=Array.from({length:40},(_,i)=>[i%2?epsilon:179.99,i/100]);ring.push(ring[0]);
 const original={type:'Polygon',coordinates:[ring]},view={type:'Polygon',coordinates:[ring.map(([x,y])=>[Math.min(180,x),y])]};
 const store=await open(directory,JSON.stringify({rows:[{geometry:original},{geometry:view}]}));
 const options={size:16,latitudes:nativeRowLatitudes(16)},a=store.componentMetadata(store.componentAt(0)).geometry,b=store.componentMetadata(store.componentAt(1)).geometry;
 assert.deepEqual(verifyNativeSeamView(a,b,options),verifyNativeSeamView(original,view,options));store.close();
});

test('spilled polygon and ring rosters preserve eager runtime materialization and complete scans',async t=>{
 const directory=temporary(t),ring=[[-20,-20],[20,-20],[20,20],[-20,20],[-20,-20]];
 const shapes=[{type:'Polygon',coordinates:Array.from({length:41},()=>ring)},
  {type:'MultiPolygon',coordinates:Array.from({length:41},()=>[ring])}];
 for(const geometry of shapes){
  const store=await open(directory,JSON.stringify({rows:[{geometry}]})),stored=store.componentMetadata(store.componentAt(0)).geometry;
  const a=nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry:stored}]),b=nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry}]);
  assert.deepEqual(a,b);assert(Array.isArray(a[0].polygons));assert(Array.isArray(a[0].polygons[0]));
  const options={size:16,rowStart:0,rowEnd:16,latitudes:nativeRowLatitudes(16)};
  assert.deepEqual(nativePolygonIntervals(a,options),nativePolygonIntervals(b,options));
  assert.deepEqual(validateWitnessGeometry(stored),validateWitnessGeometry(geometry));store.close();
 }
});

test('coordinate cursor adaptation preserves existing literal runtime array behavior',()=>{
 const ring=[[0,0],,[1,1],[0,0]],geometry={type:'Polygon',coordinates:[ring]};
 const index=nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry}]);
 assert.deepEqual(index[0].polygons[0][0],new Float64Array([0,0,0,0,1,1,0,0]));
 const polygons=new Array(1),multi=nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry:{type:'MultiPolygon',coordinates:polygons}}]);
 assert.equal(multi[0].polygons.length,1);assert.equal(Object.hasOwn(multi[0].polygons,0),false);
});


test('geometry closure is checked against consumed coordinates rather than an inconsistent fast lookup',()=>{
 const points=Array.from({length:40},(_,i)=>[i/100,i/100]);
 const ring=nativeSequence(points.length,()=>points.values(),{entryAt:()=>points[0]});
 const geometry={type:'Polygon',coordinates:[ring]};
 assert.throws(()=>coordinateBounds(geometry),/Unclosed original ring/);
 assert.throws(()=>polygonParts(geometry),/Unclosed footprint ring/);
 assert.throws(()=>nativeRuntimeIndex([{id:'A',pixelIndex:1,geometry}]),/Original native closed ring required/);
});

test('raw metadata admission preserves JSON values and ignored nonfinite fields without canonical claims',async t=>{
 const {admitNativeMetadataStore}=await import('../scripts/native-patch-store.mjs');
 const {isNativeSequence}=await import('../src/native-grid.js');
 const directory=temporary(t);
 const expand=value=>isNativeSequence(value)?Array.from(value,expand):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([k,v])=>[k,expand(v)])):value;
 for(const text of ['null','1e400','-1e400','-0','true','"x"','[1,null,-0]',
  '{"ignored":1e400,"ignored":7,"__proto__":{"ok":true}}',
  JSON.stringify({complete_cold_custody:Array.from({length:40},(_,i)=>({facts:{entries:[i]},inventory:[{path:'x'}],effective_additions:Array.from({length:40},()=>({coordinates:Array.from({length:40},()=>[-0,1])}))}))}).replace('"path":"x"','"path":"x","ignored":1e400'),
  '{"coordinates":['+Array(40).fill('{"nonfinite":1,"depth":0,"start":0,"count":3,"x":-1e400}').join(',')+']}']){
  const body=Buffer.from(text),store=await admitNativeMetadataStore({directory,chunks:chunks(body,7),expected:{bytes:body.length,sha256:hash(body)},metadataArrays:['complete_cold_custody','effective_additions','inventory']});
  assert.equal(store.canonical_sha256,null);assert.deepEqual(expand(store.metadata),JSON.parse(text));
  if(store.metadata?.complete_cold_custody)assert(Array.isArray(store.metadata.complete_cold_custody.at(0).facts.entries));
  store.close();assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('raw metadata authenticates complete malformed bodies before syntax refusal and closes producers',async t=>{
 const {admitNativeMetadataStore}=await import('../scripts/native-patch-store.mjs');const directory=temporary(t);
 for(const text of ['{"a":[1,]}','{"a":1 "b":2}','[1,2','{1:2}','null true','{"coordinates":['+Array(40).fill('1e400').join(',')+'],"x":}']){
  assert.throws(()=>JSON.parse(text),SyntaxError);const body=Buffer.from(text);let closed=0,seen=0;
  const source=function*(){try{for(const chunk of chunks(body,3)){seen+=chunk.length;yield chunk;}}finally{closed++;}};
  await assert.rejects(admitNativeMetadataStore({directory,chunks:source(),expected:{bytes:body.length,sha256:hash(body)}}),SyntaxError);
  assert.equal(seen,body.length);assert.equal(closed,1);assert.deepEqual(fs.readdirSync(directory),[]);
  await assert.rejects(admitNativeMetadataStore({directory,chunks:chunks(body,3),expected:{bytes:body.length,sha256:'0'.repeat(64)}}),/identity differs/);
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('raw ignored nesting has no extra recursive freeze or spill-serialization depth limit',async t=>{
 const {admitNativeMetadataStore}=await import('../scripts/native-patch-store.mjs');const directory=temporary(t),depth=5000;
 for(const spill of [false,true])for(const object of [false,true]){
  const item='{"ignored":'+(object?'{"constructor":':'[').repeat(depth)+'-1e400'+(object?'}':']').repeat(depth)+'}';
  const body=Buffer.from(spill?'{"inventory":['+Array(33).fill(item).join(',')+']}':item);JSON.parse(body);
  const store=await admitNativeMetadataStore({directory,chunks:chunks(body,4096),metadataArrays:['inventory'],expected:{bytes:body.length,sha256:hash(body)}});
  let value=(spill?store.metadata.inventory.at(32):store.metadata).ignored;
  for(let i=0;i<depth;i++){assert(Object.isFrozen(value));value=object?value.constructor:value[0];}assert.equal(value,-Infinity);
  store.close();assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('raw metadata preserves own special keys and freezes without consuming spilled values',async t=>{
 const {admitNativeMetadataStore}=await import('../scripts/native-patch-store.mjs');const directory=temporary(t);
 const item='{"__proto__":{"old":1},"__proto__":{"coordinates":['+Array(40).fill('[-0,1e400]').join(',')+']},"constructor":{"prototype":-0},"prototype":{"constructor":-1e400}}';
 const body=Buffer.from('{"inventory":['+Array(33).fill(item).join(',')+']}'),literal=JSON.parse(item);
 const read=fs.readSync;let reads=0;fs.readSync=(...args)=>{reads++;return read(...args);};let store;
 try{store=await admitNativeMetadataStore({directory,chunks:chunks(body),metadataArrays:['inventory'],expected:{bytes:body.length,sha256:hash(body)}});assert.equal(reads,0,'freezing must not decode any spilled value');}finally{fs.readSync=read;}
 const value=store.metadata.inventory.at(32);
 assert.equal(Object.getPrototypeOf(value),Object.prototype);assert(Object.hasOwn(value,'__proto__'));
 assert.deepEqual(Object.keys(value),Object.keys(literal));assert.equal(Object.getPrototypeOf(value.constructor),Object.prototype);
 assert(Object.is(value.constructor.prototype,-0));assert.equal(value.prototype.constructor,-Infinity);
 assert.deepEqual([...value.__proto__.coordinates],literal.__proto__.coordinates);
 assert.equal(Object.prototype.old,undefined);store.close();assert.deepEqual(fs.readdirSync(directory),[]);
});
