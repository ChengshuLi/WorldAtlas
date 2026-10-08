import test from 'node:test';
import assert from 'node:assert/strict';
import {applyAdditiveNativePatch,loadAdditiveNativePatch,footprintValueSha256 as hash} from '../src/effective-footprint.js';
import {packOwnership,pickOwnership,samplePackedOwnership} from '../src/pixel-ownership.js';
import {nativeSourceDigest} from '../src/native-source-digest.js';
import {createHash} from 'node:crypto';
const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
function fixture(){
 const rows=Array.from({length:262166},()=>new Uint32Array());rows[3]=Uint32Array.from([1,3,1,8,10,2]);
 const baseReference={id:'geography:base',footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)};
 const effectiveReference={...baseReference,id:'geography:effective',footprints_sha256:'c'.repeat(64)};
 const base={...packOwnership({size:262166,rows}),method:'native-linear-evenodd-first-owner-v1',geographic_release:baseReference.id,...baseReference};
 const f={id:'owner1',pixelIndex:1,geometry:rectangle(0,0,1,1)};
 f.additiveFootprint={version:1,kind:'retained-base-plus-additions',baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:hash(f.geometry),ledger_sha256:'d'.repeat(64),rule_sha256:'e'.repeat(64),additions:[{component_id:'gap',geometry:rectangle(1,0,2,1),geometry_sha256:hash(rectangle(1,0,2,1)),source_receipt_sha256:'f'.repeat(64)}]};
 const features=[f,{id:'owner2',pixelIndex:2,geometry:rectangle(2,0,3,1)}];
 const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,ledger_sha256:'d'.repeat(64),rule_sha256:'e'.repeat(64),rows:[{y:3,runs:[[3,5,1]]}]};
 return{base,patch,options:{baseReference,effectiveReference,features}};
}
test('actual renderer and picker consume identical sparse overlay; all old cells and full source primitives preserved',()=>{
 const {base,patch,options}=fixture(),oldRows=base.rows.slice(),oldRuns=base.runs.slice(),out=applyAdditiveNativePatch(base,patch,options);
 assert.equal(out.additive_added_cells,2);
 for(let x=0;x<20;x++){const old=pickOwnership(base,x,3);if(old)assert.equal(pickOwnership(out,x,3),old);}
 assert.deepEqual([...samplePackedOwnership(out,{x:0,y:3,width:12,height:1})],[0,1,1,1,1,0,0,0,2,2,0,0]);
 assert.deepEqual(base.rows,oldRows);assert.deepEqual(base.runs,oldRuns);assert.equal(applyAdditiveNativePatch(out,patch,options),out);
 out.runs[0]^=1;assert.throws(()=>applyAdditiveNativePatch(out,patch,options),/drifted/);
});
test('assigned cells, conflicts, foreign owner, stale baseline and rule rebind reject without changing base',()=>{
 for(const alter of [p=>p.rows[0].runs=[[2,4,1]],p=>p.rows[0].runs=[[8,9,1]],p=>p.rows[0].runs=[[3,6,1],[5,7,2]],p=>p.rows[0].runs=[[3,5,3]],p=>p.base_reference.footprints_sha256='0'.repeat(64),p=>p.rule_sha256='0'.repeat(64),p=>p.rows.push(p.rows[0])]){
  const {base,patch,options}=fixture(),before=base.runs.slice();alter(patch);assert.throws(()=>applyAdditiveNativePatch(base,patch,options));assert.deepEqual(base.runs,before);
 }
 const {base,patch,options}=fixture();base.additive_patch_sha256=hash(patch);assert.throws(()=>applyAdditiveNativePatch(base,patch,options),/Foreign/);
});
test('real bounded asset load authenticates whole patch and complete effective digest; no silent legacy fallback',async()=>{
 const {base,patch,options}=fixture(),digest=(await nativeSourceDigest(options.features)).sha256;
 options.effectiveReference.footprints_sha256=digest;patch.effective_reference={...options.effectiveReference};
 const raw=Buffer.from(JSON.stringify(patch));
 const data={reference_release:options.effectiveReference,additiveRelease:{version:1,kind:'retained-native-base-plus-delta-v1',base_reference:options.baseReference,effective_reference:options.effectiveReference,patch:{path:'additive-repairs/batch1.json',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}}};
 const fetcher=async()=>new Response(raw);
 const out=await loadAdditiveNativePatch(data,options.features,base,{fetcher,effectiveDigest:digest});assert.equal(pickOwnership(out,3,3),1);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher,effectiveDigest:'0'.repeat(64)}),/digest/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async()=>new Response(Buffer.concat([raw,Buffer.from('x')])),effectiveDigest:digest}),/exceeds/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async()=>new Response(Buffer.from('x'.repeat(raw.length))),effectiveDigest:digest}),/checksum/);
 await assert.rejects(loadAdditiveNativePatch({reference_release:options.baseReference},options.features,base),/explicit/);
});
