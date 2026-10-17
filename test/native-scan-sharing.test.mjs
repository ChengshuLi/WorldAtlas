import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const modulePath = process.env.NATIVE_SCAN_TEST_MODULE
  ? path.resolve(process.env.NATIVE_SCAN_TEST_MODULE)
  : fileURLToPath(new URL('../src/native-grid.js', import.meta.url));
const rectangle = (left, right) => ({type:'Polygon', coordinates:[
  [[left,-40],[right,-40],[right,40],[left,40],[left,-40]]
]});
const feature = (id, pixelIndex, geometry, target_id) =>
  ({id,pixelIndex,geometry,...(target_id ? {target_id} : {})});
const mask = (source_id, geometry) => ({id:'owner:A',pixelIndex:7,source_id,geometry});

// Observe the existing scanner at its actual call boundary. This test-only
// instrumentation changes no geometry or decision and adds no production hook.
async function observedNative(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'native-scan-sharing-'));
  t.after(() => fs.rmSync(directory,{recursive:true,force:true}));
  // Observe the numerical scanner itself, whether it is the retained exported
  // preimage or the current private body behind the strict public wrapper.
  const signatures = [
    'export function nativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes}){',
    'function scanNativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes},longitudeLimit){'
  ];
  const record = '\n__testScans.push({rowStart,rowEnd,index:index.map(item=>({index:item.index,polygons:item.polygons.map(p=>p.map(r=>Array.from(r)))}))});';
  const load = async (original,name) => {
    const source = fs.readFileSync(original,'utf8');
    const matches = signatures.flatMap(signature =>
      Array.from({length:source.split(signature).length-1},()=>signature));
    assert.equal(matches.length,1,'instrument the actual scanner exactly once');
    const [signature] = matches;
    const instrumented = 'const __testScans=[];\n' + source.replace(signature,signature+record)
      + '\nexport {__testScans};\n';
    const filename = path.join(directory,name+'.mjs');
    fs.writeFileSync(filename,instrumented);
    return import(pathToFileURL(filename));
  };
  const native=await load(modulePath,'candidate');
  // Local differential validation can supply the actual immutable preimage.
  // Normal repository tests need no historical Git object or copied old module.
  const reference=process.env.OLD_NATIVE_GRID_MODULE
    ? await load(path.resolve(process.env.OLD_NATIVE_GRID_MODULE),'preimage') : native;
  return {...native,reference};
}

function input(native) {
  const original = feature('source:A',7,rectangle(-89,89),'owner:A');
  const left = mask(original.id,rectangle(-89,-1));
  const right = mask(original.id,rectangle(1,89));
  return {
    targets:[{id:'owner:A',pixelIndex:7}],sourceFeatures:[original],
    coverageFeatures:[mask(original.id,{type:'MultiPolygon',coordinates:[
      left.geometry.coordinates,right.geometry.coordinates
    ]})],
    size:8,latitudes:native.nativeRowLatitudes(8),rowStart:0,rowEnd:8,
    ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
    diagnosticRows:[{y:3,runs:[[0,8,7]]},{y:4,runs:[[0,8,7]]}],
    groups:[[left],[right]]
  };
}

function compare(native, value, groups=value.groups) {
  const {groups:unused,...base}=value;
  const before=structuredClone({base,groups});
  native.__testScans.length=0;
  const actual=native.deriveSourceTargetNativeDelta({...base,coverageFeatureGroups:groups});
  const sharedScans=structuredClone(native.__testScans);
  assert.ok(Object.hasOwn(actual,'coverage_groups'));
  const reference=native.reference;
  reference.__testScans.length=0;
  const expectedBase=reference.deriveSourceTargetNativeDelta(base);
  const expectedGroups=groups.map(coverageFeatures=>reference.deriveSourceTargetNativeDelta({
    ...base,coverageFeatures,diagnosticRows:undefined
  }));
  const separateScans=structuredClone(reference.__testScans);
  const {coverage_groups,...actualBase}=actual;
  assert.deepEqual(actualBase,expectedBase,'base result and diagnostics retain the legacy shape and values');
  assert.deepEqual(coverage_groups,expectedGroups,'each group equals an independent legacy call');
  assert.deepEqual(native.deriveSourceTargetNativeDelta(base),expectedBase,
    'candidate plain path also equals the reference plain path');
  for(const group of coverage_groups) {
    assert.equal(Object.hasOwn(group,'diagnostic_rows'),false);
    assert.equal(Object.hasOwn(group,'coverage_groups'),false);
  }
  assert.deepEqual({base,groups},before,'original arrays, geometries, IDs and rows are untouched');
  return {actual,sharedScans,separateScans};
}

const scanSignature = index => JSON.stringify(index.map(item=>({index:item.index,
  polygons:item.polygons.map(p=>p.map(r=>Array.from(r)))})));
const recordedSignature = scan => JSON.stringify(scan.index);

for(const withExclusion of [false,true])test('sources and '+(withExclusion?'exclusions':'empty exclusions')+' scan once across the base and two physical classes',async t=>{
  const native=await observedNative(t),v=input(native);
  if(withExclusion)v.territorialExclusions=[feature('owner:A',7,rectangle(-40,-5))];
  const {actual,sharedScans,separateScans}=compare(native,v);
  assert.equal(sharedScans.length,withExclusion?5:4);
  assert.equal(separateScans.length,withExclusion?9:6);
  const source=scanSignature(native.nativeRuntimeIndex(v.sourceFeatures.map((f,i)=>({...f,pixelIndex:i+1}))));
  assert.equal(sharedScans.filter(s=>recordedSignature(s)===source).length,1);
  assert.equal(separateScans.filter(s=>recordedSignature(s)===source).length,3);
  if(withExclusion) {
    const shapes=index=>JSON.stringify(index.map(item=>item.polygons));
    const exclusion=shapes(native.nativeRuntimeIndex(v.territorialExclusions).map(item=>({
      polygons:item.polygons.map(p=>p.map(r=>Array.from(r)))})));
    assert.equal(sharedScans.filter(s=>shapes(s.index)===exclusion).length,1);
    assert.equal(separateScans.filter(s=>shapes(s.index)===exclusion).length,3);
  }
  assert.equal(actual.assigned_cells,withExclusion?6:8);
  assert.deepEqual(actual.coverage_groups.map(g=>g.assigned_cells),withExclusion?[2,4]:[4,4]);
});

test('absent optional groups preserve exact legacy output and an explicit empty list performs no extra scan',async t=>{
  const native=await observedNative(t),v=input(native),{groups,...base}=v;
  const plain=native.deriveSourceTargetNativeDelta(base);
  assert.equal(Object.hasOwn(plain,'coverage_groups'),false);
  assert.deepEqual(native.deriveSourceTargetNativeDelta({...base,coverageFeatureGroups:undefined}),plain);
  const {actual,sharedScans,separateScans}=compare(native,v,[]);
  assert.deepEqual(actual.coverage_groups,[]);
  assert.equal(sharedScans.length,2);assert.equal(separateScans.length,2);
});

test('group order is literal and returned group rows do not alias each other or the input',async t=>{
  const native=await observedNative(t),v=input(native);
  const a=compare(native,v).actual;
  const b=compare(native,v,[...v.groups].reverse()).actual;
  assert.deepEqual(b.coverage_groups,[...a.coverage_groups].reverse());
  assert.notDeepEqual(a.coverage_groups[0].rows,a.coverage_groups[1].rows);
  const right=structuredClone(a.coverage_groups[1]);
  a.coverage_groups[0].rows[0].runs[0][0]=0;
  assert.deepEqual(a.coverage_groups[1],right);
  assert.deepEqual(compare(native,v).actual,b.coverage_groups.length===2
    ? {...b,coverage_groups:[...b.coverage_groups].reverse()} : b);
});

test('class-specific coverage ties stay within that class while the base and other class remain clean',async t=>{
  const native=await observedNative(t),v=input(native);
  v.groups[0]=[mask('source:A',rectangle(-89,22.5))];
  const {actual}=compare(native,v);
  assert.equal(actual.boundary_cells,0);assert.equal(actual.assigned_cells,8);
  assert.equal(actual.coverage_groups[0].boundary_cells,2);
  assert.equal(actual.coverage_groups[0].assigned_cells,4);
  assert.equal(actual.coverage_groups[1].boundary_cells,0);
  assert.equal(actual.coverage_groups[1].assigned_cells,4);
});

test('an original member tie stays withheld in every same-owner group and sibling support cannot be borrowed',async t=>{
  const native=await observedNative(t),v=input(native);
  const a=feature('source:A',7,rectangle(-89,22.5),'owner:A');
  const b=feature('source:B',7,rectangle(0,89),'owner:A');
  v.sourceFeatures=[a,b];v.coverageFeatures=[mask(a.id,a.geometry),mask(b.id,b.geometry)];
  v.groups=[[mask(a.id,rectangle(-89,89))],[mask(b.id,b.geometry)]];
  const {actual}=compare(native,v);
  assert.equal(actual.assigned_cells,6);assert.equal(actual.boundary_cells,2);
  assert.deepEqual(actual.coverage_groups.map(g=>g.boundary_cells),[2,2]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.assigned_cells),[4,2]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.unsupported_coverage_cells),[2,4]);
});

test('a competing original owner remains ambiguous in every physical class',async t=>{
  const native=await observedNative(t),v=input(native);
  v.sourceFeatures.push(feature('source:competitor',9,rectangle(-1,89),'owner:competitor'));
  const {actual}=compare(native,v);
  assert.equal(actual.ambiguous_owner_cells,4);assert.equal(actual.assigned_cells,4);
  assert.deepEqual(actual.coverage_groups.map(g=>g.ambiguous_owner_cells),[4,4]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.assigned_cells),[4,0]);
});

test('holes and a separately measured same-owner island retain exact member coverage',async t=>{
  const native=await observedNative(t),v=input(native);
  const hole={type:'Polygon',coordinates:[...rectangle(-89,89).coordinates,...rectangle(-46,46).coordinates]};
  const island=rectangle(-30,0);
  v.sourceFeatures=[feature('source:A',7,hole,'owner:A'),feature('source:B',7,island,'owner:A')];
  v.coverageFeatures=[mask('source:A',rectangle(-89,89)),mask('source:B',island)];
  v.groups=[[v.coverageFeatures[0]],[v.coverageFeatures[1]]];
  const {actual}=compare(native,v);
  assert.equal(actual.assigned_cells,6);
  assert.deepEqual(actual.coverage_groups.map(g=>g.assigned_cells),[4,2]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.unsupported_coverage_cells),[2,4]);
  assert.ok(actual.diagnostic_rows.every(r=>r.runs.some(run=>run[0]<=4&&4<run[1]&&run[3]==='no-target-source-domain')));
});

test('foreign and same intended occupied owners plus a real exclusion retain their precedence in both classes',async t=>{
  const native=await observedNative(t),v=input(native);
  v.ownerRows[3].complete_owner_intervals=[[2,3,99],[4,5,7]];
  v.territorialExclusions=[feature('owner:A',7,rectangle(-40,-5))];
  const {actual}=compare(native,v);
  assert.equal(actual.already_owned_cells,2);assert.equal(actual.territorial_exclusion_cells,2);
  assert.equal(actual.assigned_cells,4);assert.equal(actual.reassigned_cells,0);
  assert.deepEqual(actual.coverage_groups.map(g=>g.assigned_cells),[1,3]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.already_owned_cells),[2,2]);
  assert.deepEqual(actual.coverage_groups.map(g=>g.territorial_exclusion_cells),[2,2]);
});

for(const [name,change,pattern] of [
  ['non-array groups',v=>null,/coverage groups/],
  ['empty feature group',v=>[[]],/Missing reviewed coverage/],
  ['foreign original coverage',v=>[[{...v.groups[0][0],source_id:'source:missing'}]],/exact original source/],
  ['foreign target',v=>[[{...v.groups[0][0],id:'foreign-target'}]],/Foreign coverage/]
])test('invalid additional '+name+' fails instead of dropping or accepting a group',async t=>{
  const native=await observedNative(t),v=input(native),{groups,...base}=v;
  assert.throws(()=>native.deriveSourceTargetNativeDelta({...base,coverageFeatureGroups:change(v)}),pattern);
});

function twoOwners(native) {
  const a=feature('source:A',7,rectangle(-100,-1),'owner:A');
  const b=feature('source:B',9,rectangle(1,100),'owner:B');
  return {targets:[{id:'owner:A',pixelIndex:7},{id:'owner:B',pixelIndex:9}],
    sourceFeatures:[a,b],coverageFeatures:[mask(a.id,a.geometry),
      {id:'owner:B',pixelIndex:9,source_id:b.id,geometry:b.geometry}],
    size:8,latitudes:native.nativeRowLatitudes(8),rowStart:0,rowEnd:8,
    ownerRows:Array.from({length:8},(_,y)=>({y,complete_owner_intervals:[]})),
    diagnosticRows:[{y:3,runs:[[2,4,7],[4,6,9]]},{y:4,runs:[[2,4,7],[4,6,9]]}]};
}

function compareNegatives(native,v) {
  const before=structuredClone(v);
  native.__testScans.length=0;
  const actual=native.deriveSourceTargetNativeDelta(v);
  const scans=structuredClone(native.__testScans);
  // Separate literal copies exercise the unshared route. Local differential
  // runs additionally execute the exact immutable preimage when supplied.
  const separate={...v,territorialExclusions:v.territorialExclusions.map(f=>({
    ...f,geometry:structuredClone(f.geometry)}))};
  const expected=native.reference.deriveSourceTargetNativeDelta(separate);
  assert.deepEqual(actual,expected,'all rows, reasons, counts and operand contacts equal unshared whole negatives');
  assert.deepEqual(v,before,'whole inputs and every owner/ordinal binding stay unchanged');
  return {actual,scans};
}

test('one shared whole negative is scanned once while every repeated and distinct owner veto remains',async t=>{
  const native=await observedNative(t),v=twoOwners(native),geometry=rectangle(-60,60);
  v.territorialExclusions=[feature('owner:A',7,geometry),feature('owner:B',9,geometry),feature('owner:A',7,geometry)];
  const {actual,scans}=compareNegatives(native,v);
  assert.equal(scans.length,3);
  assert.equal(scans[2].index.length,1);
  assert.equal(scans[2].index[0].polygons.length,1,'no repeated polygon copies hidden under one scan owner');
  assert.equal(actual.territorial_exclusion_cells,4);
  assert.equal(actual.assigned_cells,4);
  assert.ok(actual.diagnostic_rows.every(row=>row.runs.some(run=>run[2]===7&&run[3]==='territorial_exclusion_cells')
    &&row.runs.some(run=>run[2]===9&&run[3]==='territorial_exclusion_cells')));
});

for(const boundary of [false,true])test('shared negatives retain every applicability ordinal and '+(boundary?'boundary veto':'contrary interior decision'),async t=>{
  const native=await observedNative(t),v=twoOwners(native),geometry=rectangle(-60,boundary?22.5:60);
  const h='a'.repeat(64),operand='b'.repeat(64);
  v.territorialExclusions=[feature('owner:A',7,geometry),feature('owner:B',9,geometry),feature('owner:A',7,geometry)]
    .map(f=>({...f,geometry_sha256:h,operand_sha256:operand}));
  v.territorialApplicability=[{source_id:'source:A',pixelIndex:7,y:3,x:3,exclusion_index:0,
    exclusion_geometry_sha256:h,operand_sha256:operand,decision_sha256:'c'.repeat(64)},
  {source_id:'source:B',pixelIndex:9,y:3,x:4,exclusion_index:1,
    exclusion_geometry_sha256:h,operand_sha256:operand,decision_sha256:'d'.repeat(64)}];
  const {actual,scans}=compareNegatives(native,v);
  assert.equal(scans[2].index.length,1);
  assert.deepEqual([...new Set(actual.territorial_contacts.map(hit=>hit.exclusion_index))].sort(),[0,1,2]);
  assert.ok(actual.territorial_contacts.some(hit=>hit.exclusion_index===0&&hit.resolution==='contextual'));
  assert.ok(actual.territorial_contacts.some(hit=>hit.exclusion_index===2&&hit.resolution==='contextual'));
  if(boundary)assert.ok(actual.territorial_contacts.some(hit=>hit.exclusion_index===1&&hit.resolution==='retained-boundary-veto'));
  else assert.ok(actual.territorial_contacts.some(hit=>hit.exclusion_index===1&&hit.resolution==='contextual'));
  assert.ok(actual.diagnostic_rows.find(row=>row.y===4).runs.some(run=>run[3]==='territorial_exclusion_cells'),
    'a contact interpretation never clears the same operand at another centre');
});

test('shared polygon holes, separate overlapping masks and class groups preserve complete negative geometry',async t=>{
  const native=await observedNative(t),v=twoOwners(native);
  const geometry={type:'MultiPolygon',coordinates:[[
    rectangle(-80,80).coordinates[0],rectangle(-30,30).coordinates[0]],rectangle(-15,15).coordinates]};
  v.territorialExclusions=[feature('owner:A',7,geometry),feature('owner:B',9,geometry),
    feature('owner:A',7,rectangle(-55,-40))];
  v.coverageFeatureGroups=[v.coverageFeatures];
  const {actual,scans}=compareNegatives(native,v);
  assert.equal(scans[2].index.length,2);
  assert.equal(scans[2].index[0].polygons.length,2);
  assert.deepEqual(actual.coverage_groups[0].rows,actual.rows);
  assert.ok(actual.assigned_cells>0);
});

test('negative reuse never trusts a declared hash or survives changed geometry, result, latitude or block',async t=>{
  const native=await observedNative(t),v=twoOwners(native),geometry=rectangle(-60,60);
  v.territorialExclusions=[feature('owner:A',7,geometry),feature('owner:B',9,geometry),
    {...feature('owner:A',7,rectangle(-99,-70)),geometry_sha256:'e'.repeat(64)}];
  v.territorialExclusions[0].geometry_sha256='e'.repeat(64);
  const first=compareNegatives(native,v);
  assert.equal(first.scans[2].index.length,2,'same claimed hash cannot merge different actual geometries');
  const original=structuredClone(first.actual);
  first.actual.rows.length=0;
  geometry.coordinates[0][1][0]=geometry.coordinates[0][2][0]=10;
  const changed=compareNegatives(native,v);
  assert.notDeepEqual(changed.actual,original);
  assert.ok(changed.actual.assigned_cells>original.assigned_cells);
  for(const [rowStart,rowEnd]of [[0,4],[4,8]])compareNegatives(native,{...v,rowStart,rowEnd,
    ownerRows:v.ownerRows.slice(rowStart,rowEnd),diagnosticRows:v.diagnosticRows.filter(row=>row.y>=rowStart&&row.y<rowEnd)});
  const otherTable={...v,latitudes:Float64Array.from(v.latitudes,value=>value/2)};
  compareNegatives(native,otherTable);
  geometry.coordinates[0][1][0]=181;
  assert.throws(()=>native.deriveSourceTargetNativeDelta(v),/lon\/lat|native/,'changed malformed geometry must be read again');
});
