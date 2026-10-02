import fs from 'node:fs';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {validYear} from '../src/model.js';
import {checkPrepared} from './check-prepared.mjs';

const read=p=>JSON.parse(fs.readFileSync('data/'+p));
const zipped=p=>JSON.parse(gunzipSync(fs.readFileSync('data/'+p)));
const features=read('world-index.json').parts.flatMap(p=>read(p).features);
const ids=new Set(features.map(f=>f.id));
checkPrepared(features);
const owner=read('ownership-history/index.json');
assert.equal(owner.version,2,'Publication requires the compact ownership format');
const sourceRecords=new Map(read('cliopatria/index.json').records.map(r=>[r.id,r]));
assert.ok(owner.source&&owner.source_url&&owner.license);
for(const id of owner.owner_ids)assert.equal(owner.entities[id]?.id,id);
for(const id of owner.source_ids)assert.ok(sourceRecords.has(id),`Unknown historical source record: ${id}`);

// Check evidence once, retaining numerical/date summaries rather than millions
// of expanded ownership objects from the runtime decoder's evidence cache.
const count=owner.evidence_records;
const shares=new Float64Array(count),sourceFrom=new Int32Array(count),sourceTo=new Int32Array(count),topOwner=new Uint32Array(count);
let evidenceCount=0;
for(const part of owner.evidence_parts){
 for(const [name,share,covered,candidates,sources,dated] of zipped('ownership-history/'+part.path)){
  const i=evidenceCount++;
  assert.ok(i<count&&share>=0&&share<=1&&covered>=0&&covered<=1);
  assert.ok(name===null||Number.isInteger(name)&&typeof owner.labels[name]==='string');
  assert.ok(dated===0||dated===1);
  assert.ok(Array.isArray(candidates)&&Array.isArray(sources)&&sources.length);
  const candidateIds=new Set();let previous=Infinity;
  for(const [polity,value] of candidates){
   assert.ok(Number.isInteger(polity)&&owner.owner_ids[polity]&&value>=0&&value<=1);
   assert.ok(!candidateIds.has(polity)&&value<=previous);
   candidateIds.add(polity);previous=value;
  }
  if(candidates.length){assert.equal(candidates[0][1],share);topOwner[i]=candidates[0][0]+1;}
  else assert.equal(share,0);
  let from=-3000,to=2027;
  for(const index of sources){
   assert.ok(Number.isInteger(index)&&index>=0&&index<owner.source_ids.length);
   const r=sourceRecords.get(owner.source_ids[index]);
   from=Math.max(from,r.valid_from);to=Math.min(to,r.valid_to);
  }
  shares[i]=share;sourceFrom[i]=from;sourceTo[i]=to;
 }
}
assert.equal(evidenceCount,count);
const seen=new Set(),statuses={};let intervals=0;
for(const part of owner.parts)for(const [id,rows] of zipped('ownership-history/'+part.path)){
 assert.ok(ids.has(id)&&!seen.has(id),id);seen.add(id);let end=-3000;
 for(const [a,b,polity,statusIndex,evidence] of rows){
  assert.ok(validYear(a)&&(validYear(b)||b===2027)&&a<b&&a>=end,id);end=b;
  assert.ok(Number.isInteger(evidence)&&evidence>=0&&evidence<count);
  const status=owner.statuses_order[statusIndex];
  assert.ok(['derived','disputed','no-majority','unknown'].includes(status));
  assert.equal(status==='derived',polity!==null);
  if(polity!==null){assert.ok(Number.isInteger(polity)&&owner.owner_ids[polity]);assert.ok(shares[evidence]>.5);assert.equal(topOwner[evidence],polity+1);}
  assert.ok(a>=sourceFrom[evidence]&&b<=sourceTo[evidence],`Evidence interval does not support ${id}/${a}`);
  statuses[status]=(statuses[status]||0)+1;intervals++;
 }
}
assert.equal(seen.size,features.length);assert.equal(intervals,owner.intervals);
for(const [status,n] of Object.entries(owner.statuses))assert.equal(statuses[status]||0,n);
for(const refinement of owner.refinements||[]){
 if(refinement.kind==='adaptive-majority-area'){
  const hash=p=>createHash('sha256').update(fs.readFileSync('data/ownership-history/algorithms/'+p)).digest('hex');
  assert.equal(hash('refine-ownership-threshold.py'),refinement.script_sha256);
  assert.equal(hash('majority-refinement.py'),refinement.area_algorithm_sha256);
 }
}

const reference=read('reference-attributes/index.json'),referenceIntervals=new Map();let records=0;
for(const part of reference.parts)for(const [id,rows] of zipped('reference-attributes/'+part)){
 assert.ok(ids.has(id),`Unknown reference location: ${id}`);
 let intervalsByField=referenceIntervals.get(id);
 if(!intervalsByField){intervalsByField=new Map();referenceIntervals.set(id,intervalsByField);}
 for(const [type,value,share,covered] of rows){
  const t=reference.types[type];assert.ok(t&&(reference.values[value]===null||typeof reference.values[value]==='string'));
  assert.ok(validYear(t.valid_from)&&(validYear(t.valid_to)||t.valid_to===2027)&&t.valid_from<t.valid_to);
  assert.ok(t.source&&t.method==='reference'&&['reference','unknown'].includes(t.status));
  assert.ok(share>=0&&share<=1);if(covered!=null)assert.ok(covered>=.5&&covered<=1.00001);
  const list=intervalsByField.get(t.attribute)||[];
  for(const [a,b] of list)assert.ok(a>=t.valid_to||b<=t.valid_from,id+'/'+t.attribute);
  list.push([t.valid_from,t.valid_to]);intervalsByField.set(t.attribute,list);records++;
 }
}
assert.equal(records,reference.records);
console.log(JSON.stringify({locations:seen.size,ownership_intervals:intervals,evidence_records:evidenceCount,reference_records:records,checks:'Streamed exhaustive IDs, intervals, categories, majority shares, source support, uniqueness and prepared hashes passed'}));
