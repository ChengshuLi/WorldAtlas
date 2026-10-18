import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import * as native from '../src/native-grid.js';
import {admitNativeMetadataStore} from '../scripts/native-patch-store.mjs';

// Local differential runs can execute the exact immutable preimage. Normal
// repository checks exercise literal and authenticated stored operands directly.
const reference=process.env.OLD_NATIVE_GRID_MODULE
  ? await import(pathToFileURL(path.resolve(process.env.OLD_NATIVE_GRID_MODULE))) : native;
const rectangle=(left=-89,right=89,bottom=-40,top=40)=>({type:'Polygon',coordinates:[
  [[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]
]});
const mask=geometry=>({id:'owner',pixelIndex:7,source_id:'member',geometry});
const input=geometry=>({targets:[{id:'owner',pixelIndex:7}],
  sourceFeatures:[{id:'member',pixelIndex:7,target_id:'owner',geometry:rectangle()}],
  coverageFeatures:[mask(geometry)],size:8,latitudes:native.nativeRowLatitudes(8),rowStart:0,rowEnd:8,
  ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
  diagnosticRows:[{y:3,runs:[[0,8,7]]},{y:4,runs:[[0,8,7]]}]});
const outcome=fn=>{try{return {value:fn()};}catch(error){return {name:error.name,message:error.message};}};
const ring=()=>rectangle().coordinates[0];
const polygon=coordinates=>({type:'Polygon',coordinates});
const multi=coordinates=>({type:'MultiPolygon',coordinates});

const malformed=[
  ['missing geometry',()=>undefined],['null geometry',()=>null],['foreign type',()=>({type:'LineString',coordinates:ring()})],
  ['foreign field',()=>({...rectangle(),foreign:true})],['missing coordinates',()=>({type:'Polygon'})],
  ['empty multipolygon',()=>multi([])],['missing polygons',()=>multi(null)],['sparse polygons',()=>multi(new Array(1))],
  ['empty polygon',()=>polygon([])],['missing rings',()=>polygon(null)],['sparse rings',()=>polygon(new Array(1))],
  ['short ring',()=>polygon([ring().slice(0,3)])],['missing ring',()=>polygon([null])],
  ['sparse point',()=>polygon([[[0,0],[1,0],, [0,0]]])],
  ['missing point',()=>polygon([[[0,0],[1,0],null,[0,0]]])],
  ['short point',()=>polygon([[[0,0],[1,0],[1],[0,0]]])],
  ['extra ordinate',()=>polygon([[[0,0],[1,0],[1,1,0],[0,0]]])],
  ['sparse ordinate',()=>polygon([[[0,0],[1,0],[,1],[0,0]]])],
  ['string ordinate',()=>polygon([[[0,0],[1,0],['1',1],[0,0]]])],
  ...[NaN,Infinity,-Infinity,181,-181].map(value=>['longitude '+value,()=>polygon([[[0,0],[1,0],[value,1],[0,0]]])]),
  ...[NaN,Infinity,-Infinity,91,-91].map(value=>['latitude '+value,()=>polygon([[[0,0],[1,0],[1,value],[0,0]]])]),
  ['unclosed ring',()=>polygon([[[0,0],[1,0],[1,1],[0,1]]])]
];
for(const [name,make] of malformed)test('strict mask conversion preserves '+name+' refusal for each original',()=>{
  const geometry=make(),expected=outcome(()=>native.polygonParts(geometry));
  assert.ok(expected.message,'the independent strict footprint boundary must reject');
  const value=input(geometry);
  // A valid sibling for the same original must not hide an empty/malformed body.
  value.coverageFeatures.unshift(mask(rectangle()));
  assert.deepEqual(outcome(()=>native.deriveSourceTargetNativeDelta(value)),expected);
  assert.deepEqual(outcome(()=>reference.deriveSourceTargetNativeDelta(value)),expected);
  value.coverageFeatureGroups=[[mask(geometry)]];value.coverageFeatures=[mask(rectangle())];
  assert.deepEqual(outcome(()=>native.deriveSourceTargetNativeDelta(value)),expected);
});

test('strict sparse and foreign-field controls are not satisfied by loose runtime conversion',()=>{
  for(const geometry of [polygon([[[0,0],[1,0],, [0,0]]]),{...rectangle(),foreign:true}]){
    assert.doesNotThrow(()=>native.nativePolygonIntervals(native.nativeRuntimeIndex([
      {id:'member',pixelIndex:1,geometry}
    ]),{size:8,latitudes:native.nativeRowLatitudes(8),rowStart:0,rowEnd:8}));
    assert.throws(()=>native.deriveSourceTargetNativeDelta(input(geometry)),/footprint coordinate|foreign fields/);
  }
});

const denseRing=count=>{
  const points=Array.from({length:count-1},(_,i)=>{
    const angle=2*Math.PI*i/(count-1);return [80*Math.cos(angle),35*Math.sin(angle)];
  });return [...points,points[0]];
};
const shape=(kind,count)=>kind==='vertices'?polygon([denseRing(count)])
  :kind==='rings'?polygon([ring(),...Array.from({length:count-1},()=>rectangle(-5,5,20,30).coordinates[0])])
  :multi(Array.from({length:count},()=>rectangle().coordinates));
async function storedGeometry(geometry,consume){
  const raw=Buffer.from(JSON.stringify(geometry)),directory=fs.mkdtempSync(path.join(os.tmpdir(),'strict-mask-'));
  let store;
  try{
    store=await admitNativeMetadataStore({directory,chunks:[raw],expected:{bytes:raw.length,
      sha256:createHash('sha256').update(raw).digest('hex')}});
    await consume(store.metadata,store);
  }finally{store?.close();assert.deepEqual(fs.readdirSync(directory),[]);fs.rmdirSync(directory);}
}
for(const kind of ['vertices','rings','polygons'])for(const count of [31,32,33])
test('strict mask conversion preserves complete eager/stored '+kind+' at '+count,async()=>{
  const geometry=shape(kind,count),value=input(geometry),before=structuredClone(value);
  value.coverageFeatureGroups=[[mask(geometry)],[mask(rectangle(-89,-1))]];
  const expected=reference.deriveSourceTargetNativeDelta(value);
  assert.ok(expected.assigned_cells>0,'the parity control must contain actual assigned cells');
  assert.deepEqual(native.deriveSourceTargetNativeDelta(value),expected);
  await storedGeometry(geometry,stored=>{
    const array=kind==='vertices'?stored.coordinates[0]:stored.coordinates;
    assert.equal(Array.isArray(array),count<=32,'exercise the genuine coordinate storage threshold');
    assert.deepEqual(native.deriveSourceTargetNativeDelta({...value,coverageFeatures:[mask(stored)],
      coverageFeatureGroups:[[mask(stored)],value.coverageFeatureGroups[1]]}),expected);
  });
  const {coverageFeatureGroups,...unchanged}=value;assert.deepEqual(unchanged,before);
});

test('strict mask grouping keeps original ordinals, holes, duplicate masks, boundary ties and exclusions',()=>{
  const left=rectangle(-89,22.5),right=rectangle(0,89),hole=rectangle(-46,46);
  const geometry=multi([[...left.coordinates,...hole.coordinates],right.coordinates]);
  const value=input(geometry);
  value.sourceFeatures=[{id:'member',pixelIndex:7,target_id:'owner',geometry:left},
    {id:'sibling',pixelIndex:7,target_id:'owner',geometry:right}];
  value.coverageFeatures=[mask(geometry),mask(rectangle(-89,-1)),{...mask(right),source_id:'sibling'}];
  value.coverageFeatureGroups=[[mask(rectangle())],[{...mask(right),source_id:'sibling'}]];
  value.territorialExclusions=[{id:'owner',pixelIndex:7,geometry:rectangle(-40,-5)}];
  value.ownerRows[3].complete_owner_intervals=[[2,3,99],[4,5,7]];
  const before=structuredClone(value),actual=native.deriveSourceTargetNativeDelta(value);
  assert.deepEqual(actual,reference.deriveSourceTargetNativeDelta(value));
  assert.ok(actual.boundary_cells>0);assert.ok(actual.already_owned_cells>0);
  assert.ok(actual.territorial_exclusion_cells>0);assert.ok(actual.assigned_cells>0);
  assert.notDeepEqual(actual.coverage_groups[0],actual.coverage_groups[1]);
  assert.deepEqual(value,before);
});

test('strict mask conversion reads each original coordinate once without a cross-call cache',()=>{
  const points=ring();let visits=0,closes=0;
  const stored=native.nativeSequence(points.length,function*(){try{for(const point of points){visits++;yield point;}}finally{closes++;}});
  const geometry=polygon([stored]),value=input(geometry);
  const first=native.deriveSourceTargetNativeDelta(value);
  assert.equal(visits,points.length);assert.equal(closes,1);
  value.coverageFeatures.push(mask(geometry));value.coverageFeatureGroups=[[mask(geometry)]];
  visits=0;closes=0;native.deriveSourceTargetNativeDelta(value);
  assert.equal(visits,3*points.length,'every original operand converts once, including each class');assert.equal(closes,3);
  points[1][0]=points[2][0]=-1;visits=0;closes=0;
  const changed=native.deriveSourceTargetNativeDelta(value);
  assert.ok(changed.assigned_cells<first.assigned_cells);assert.equal(visits,3*points.length);assert.equal(closes,3);
  points[2][0]=181;
  assert.throws(()=>native.deriveSourceTargetNativeDelta(value),/Invalid native footprint coordinate/);
});

test('strict mask conversion retains signed zero and literal closed endpoints',()=>{
  const geometry=polygon([[[-0,-0],[89,-0],[89,40],[-0,40],[0,0]]]);
  assert.deepEqual(native.deriveSourceTargetNativeDelta(input(geometry)),reference.deriveSourceTargetNativeDelta(input(geometry)));
  assert.ok(Object.is(geometry.coordinates[0][0][0],-0));
});

for(const kind of ['omitted','excess','late failure'])test('strict mask conversion refuses '+kind+' sequence and closes the iterator',()=>{
  let closes=0;const sentinel=Error('literal coordinate producer failure');
  const points=ring(),stored=native.nativeSequence(points.length,function*(){try{
    yield* kind==='omitted'?points.slice(0,-1):points;
    if(kind==='excess')yield points[0];if(kind==='late failure')throw sentinel;
  }finally{closes++;}});
  assert.throws(()=>native.deriveSourceTargetNativeDelta(input(polygon([stored]))),
    kind==='late failure'?error=>error===sentinel:/Native sequence (omitted|exceeds)/);
  assert.equal(closes,1);
});

test('strict mask conversion cannot reuse a closed stored geometry',async()=>{
  await storedGeometry(shape('vertices',33),(geometry,store)=>{
    assert.ok(native.deriveSourceTargetNativeDelta(input(geometry)).assigned_cells>0);
    store.close();assert.throws(()=>native.deriveSourceTargetNativeDelta(input(geometry)),/closed|released/i);
  });
});
