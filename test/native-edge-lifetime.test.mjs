import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import * as actual from '../src/native-grid.js';

const modulePath=process.env.NATIVE_EDGE_TEST_MODULE
  ?path.resolve(process.env.NATIVE_EDGE_TEST_MODULE):fileURLToPath(new URL('../src/native-grid.js',import.meta.url));
const rectangle=(west,south,east,north)=>Float64Array.from([
  west,south,east,south,east,north,west,north,west,south]);
const latitudes=Float64Array.from({length:128},(_,y)=>63.5-y);
const banded=()=>[{index:1,polygons:[[rectangle(-170,-64,170,64),
  ...Array.from({length:30},(_,i)=>rectangle(-40,58-i*4,40,60-i*4))]]}];
const options={size:128,rowStart:0,rowEnd:128,latitudes};

// Observe only counts, never retain an edge/cache reference. The exact scanner
// remains the numerical authority; no production hook or altered input is used.
async function observed(t){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'native-edge-lifetime-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const load=async(filename,name)=>{
    let source=fs.readFileSync(filename,'utf8');
    const hooks=[
      ['function prepareEdge(edge){','function prepareEdge(edge){\n__prepared(edge);'],
      ['function scanNativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes},longitudeLimit){',
       'function scanNativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes},longitudeLimit){\n__stats.scans++;'],
      ['        const latitude=binary(latitudes[y]),columns=[];',
       '        __observe(edges,active,y,next);\n        const latitude=binary(latitudes[y]),columns=[];']
    ];
    for(const [before,after]of hooks){assert.equal(source.split(before).length,2,'observe each real boundary once');source=source.replace(before,after);}
    source=`const __stats={scans:0,prepared:0,reactivated:0,peakCached:0,peakActive:0,expiredCached:0,futureCached:0,expiredRecords:0,peakAfterLastActivation:0,observations:0};
const __seen=new WeakSet();
function __prepared(edge){__stats.prepared++;if(__seen.has(edge))__stats.reactivated++;__seen.add(edge);}
function __observe(edges,active,y,next){let cached=0;const retained=new Set([...edges.filter(Boolean),...active]);
 for(const edge of retained){if(edge.end<=y)__stats.expiredRecords++;if(edge.exact){cached++;
 if(edge.end<=y)__stats.expiredCached++;if(edge.first>y)__stats.futureCached++;}}
 if(next===edges.length)__stats.peakAfterLastActivation=Math.max(__stats.peakAfterLastActivation,retained.size);
 __stats.peakCached=Math.max(__stats.peakCached,cached);__stats.peakActive=Math.max(__stats.peakActive,active.length);__stats.observations++;}
`+source+'\nexport {__stats};\n';
    const target=path.join(directory,name+'.mjs');fs.writeFileSync(target,source);return import(pathToFileURL(target));
  };
  const candidate=await load(modulePath,'candidate');
  const reference=process.env.OLD_NATIVE_GRID_MODULE?await load(path.resolve(process.env.OLD_NATIVE_GRID_MODULE),'preimage'):actual;
  return {candidate,reference};
}
const compare=(candidate,reference,index,opts)=>{
  const original=structuredClone(index),result=candidate.nativePolygonIntervals(index,opts);
  assert.deepEqual(result,reference.nativePolygonIntervals(index,opts),'complete rows, ties and flags equal the numerical preimage');
  assert.deepEqual(index,original,'input coordinates and owner/polygon roster stay unchanged');return result;
};

test('consumed pending slots release expired edges while future and active records remain usable',async t=>{
  const {candidate,reference}=await observed(t),result=compare(candidate,reference,banded(),options);
  assert.equal(result.rows.size,128);assert.equal(candidate.__stats.prepared,62);
  assert.equal(candidate.__stats.peakActive,4);assert.equal(candidate.__stats.peakCached,4);
  assert.equal(candidate.__stats.expiredCached,0);assert.equal(candidate.__stats.futureCached,0);
  assert.equal(candidate.__stats.expiredRecords,0);assert.equal(candidate.__stats.peakAfterLastActivation,4);
  assert.equal(candidate.__stats.reactivated,0);
  if(reference.__stats){assert.equal(reference.__stats.peakCached,62);assert(reference.__stats.expiredCached>0);
    assert.equal(reference.__stats.peakAfterLastActivation,62);assert(reference.__stats.expiredRecords>0);}
  t.diagnostic(JSON.stringify({scope:'bounded live cache census, no elapsed/RSS claim',vertices:155,scheduled_edges:62,
    before:reference.__stats??null,after:candidate.__stats}));
});

test('expired edges retain lower-vertex, horizontal and exact intersection boundary ties',async t=>{
  const {candidate,reference}=await observed(t);
  const opts={size:36,rowStart:0,rowEnd:36,latitudes:Float64Array.from({length:36},(_,y)=>18-y)};
  const index=[{index:1,polygons:[[rectangle(-175,0,-5,10)]]},{index:2,polygons:[[rectangle(-5,0,175,10)]]}];
  const result=compare(candidate,reference,index,opts);
  for(const kind of ['horizontal-native-boundary-centres','excluded-native-lower-vertex-centre','native-intersection-on-cell-centre'])
    assert(result.ties.some(tie=>tie.kind===kind),kind);
  assert(result.ties.some(tie=>tie.y===18&&tie.kind==='excluded-native-lower-vertex-centre'));
  assert.equal(result.rows.has(18),false,'excluded lower latitude does not regain ownership');
  assert.equal(candidate.__stats.expiredCached,0);assert.equal(candidate.__stats.reactivated,0);
});

test('repeated, overlapping and out-of-order row blocks reconstruct their own edge caches',async t=>{
  const {candidate,reference}=await observed(t),index=banded();
  for(const [rowStart,rowEnd]of [[64,128],[0,64],[31,97],[0,128],[31,97]])
    compare(candidate,reference,index,{...options,rowStart,rowEnd});
  assert.equal(candidate.__stats.scans,5);assert(candidate.__stats.prepared>62);
  assert.equal(candidate.__stats.expiredCached,0);assert.equal(candidate.__stats.futureCached,0);
  assert.equal(candidate.__stats.reactivated,0,'each scheduled edge is activated only once within its own scan');
});

test('canonical seam comparison and later reuse preserve complete multi-block results',async t=>{
  const {candidate,reference}=await observed(t);
  const box=east=>({type:'Polygon',coordinates:[[[170,-70],[east,-70],[east,70],[170,70],[170,-70]]]});
  const original=box(180.00000000000003),view=box(180),before=structuredClone({original,view});
  const opts={size:8192,latitudes:actual.nativeRowLatitudes(8192)};
  const expected=reference.verifyNativeSeamView(original,view,opts);
  for(let i=0;i<2;i++)assert.deepEqual(candidate.verifyNativeSeamView(original,view,opts),expected);
  assert(expected.checked_rows>4096);assert(candidate.__stats.scans>=8);
  assert.equal(candidate.__stats.expiredCached,0);assert.equal(candidate.__stats.reactivated,0);
  assert.deepEqual({original,view},before);
});
