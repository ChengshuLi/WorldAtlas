// #1569 prevention helper. Input pins/binding must be derived by the trusted
// selected-bank resolver. These functions do not select/activate a release.
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader, SelectedGeometrySources, NativeAssetImage} from '../../../scripts/check-effective-geographic-regression.mjs';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
const FILE=33554432, PHASE=268435456, SLOT=512;
const certificates=new WeakMap(), originalAuthorities=new WeakMap(), selectedAdditions=new WeakMap();
// Original accepted source/native programs. Case rosters are not policy IDs.
// Changing a complete program requires ordinary trusted-code/rule review.
const SUPPORTED_PROGRAMS=[{"preimage_version":2,"source_profile":null,"source_executed_code":[{"path":"package.json","bytes":1417,"sha256":"2af9169f046047a5cbc14592bdd776740d1b6e2871ec8216fa4a0b5e52b739a3"},{"path":"scripts/additive-gap-repair.mjs","bytes":47289,"sha256":"120c39451219ae58c4ea7252a7286c100d19e052b700a62cf134779c9a366ca2"},{"path":"src/effective-footprint.js","bytes":16601,"sha256":"af5a5926603b5eb1bb41e65553b2899b6ae46e36c79d7d4d932445e8bb08d62d"},{"path":"scripts/native-ownership/native-preparation-guards.mjs","bytes":6371,"sha256":"6c4ea2f29f6bfed9176fa8c38dfde522d859442797e4a3cce76f250c69c75fb0"},{"path":"src/native-runtime.js","bytes":3497,"sha256":"988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600"},{"path":"scripts/native-ownership/compile-native-ownership.mjs","bytes":4472,"sha256":"2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378"},{"path":"src/native-grid.js","bytes":6408,"sha256":"b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663"},{"path":"scripts/audit-grid-intervals.mjs","bytes":6777,"sha256":"084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9"},{"path":"scripts/native-ownership/require-verified-selection.mjs","bytes":4377,"sha256":"20a8e3f472db4c06386ce2b7bd01330ea8acfd6d1ff414f6d2d32e8b1995d50c"},{"path":"scripts/native-ownership/read-pinned-build-file.mjs","bytes":1540,"sha256":"7633087e97d7fbceeaf87c0e5f0225c2c456a7141f534b7fb53f4312222166cb"},{"path":"scripts/native-ownership/verified-candidates.json","bytes":1362,"sha256":"d04a08074fad869f0dd618a6ba46cbad6e07d023f8acaedeec0ece4a9a9621b7"},{"path":"scripts/evidence-quality.mjs","bytes":28506,"sha256":"8950701f659808b0f1aa527d1d79dbdaa06921abd601bef80a6b030963eb0d97"},{"path":"src/ownership-method.js","bytes":3126,"sha256":"3a19f5fb267e32f9a4ab302d7de9dea84f1b6e2cdfa93701229917c86ff4e3df"},{"path":"package-lock.json","bytes":246591,"sha256":"471d035f92567ea447f221661db5fa8febfc7afc32af8ac975506ce9e0303255"}],"native_executed_code":[{"bytes":1417,"path":"package.json","sha256":"2af9169f046047a5cbc14592bdd776740d1b6e2871ec8216fa4a0b5e52b739a3"},{"bytes":59957,"path":"scripts/additive-gap-repair.mjs","sha256":"870b4d7b0d52ed2a2fe2cd2a36a6b3a144d2166f03726e9c450a02cd6595bd73"},{"bytes":30650,"path":"src/effective-footprint.js","sha256":"aca206b6c253e3bc7291bd27ce932747c279a09832b285ddb875e806703b05ea"},{"bytes":6371,"path":"scripts/native-ownership/native-preparation-guards.mjs","sha256":"6c4ea2f29f6bfed9176fa8c38dfde522d859442797e4a3cce76f250c69c75fb0"},{"bytes":3497,"path":"src/native-runtime.js","sha256":"988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600"},{"bytes":4472,"path":"scripts/native-ownership/compile-native-ownership.mjs","sha256":"2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378"},{"bytes":6408,"path":"src/native-grid.js","sha256":"b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663"},{"bytes":2948,"path":"src/ownership-codec.js","sha256":"64630f340a2815d5c86706cc4456718054990083d1026e0b420dd8f9f02f593d"},{"bytes":6777,"path":"scripts/audit-grid-intervals.mjs","sha256":"084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9"},{"bytes":4377,"path":"scripts/native-ownership/require-verified-selection.mjs","sha256":"20a8e3f472db4c06386ce2b7bd01330ea8acfd6d1ff414f6d2d32e8b1995d50c"},{"bytes":1540,"path":"scripts/native-ownership/read-pinned-build-file.mjs","sha256":"7633087e97d7fbceeaf87c0e5f0225c2c456a7141f534b7fb53f4312222166cb"},{"bytes":1362,"path":"scripts/native-ownership/verified-candidates.json","sha256":"d04a08074fad869f0dd618a6ba46cbad6e07d023f8acaedeec0ece4a9a9621b7"},{"bytes":28506,"path":"scripts/evidence-quality.mjs","sha256":"8950701f659808b0f1aa527d1d79dbdaa06921abd601bef80a6b030963eb0d97"},{"bytes":3126,"path":"src/ownership-method.js","sha256":"3a19f5fb267e32f9a4ab302d7de9dea84f1b6e2cdfa93701229917c86ff4e3df"},{"bytes":246591,"path":"package-lock.json","sha256":"471d035f92567ea447f221661db5fa8febfc7afc32af8ac975506ce9e0303255"}],"accepted_head":"52bed5c24c27e4a9256ae6aea26c640b9082a2a2","independent_review_comment":6071720745},{"preimage_version":3,"source_profile":"retained-USA-ADM2-counties-2018","source_executed_code":[{"path":"package.json","bytes":1417,"sha256":"2af9169f046047a5cbc14592bdd776740d1b6e2871ec8216fa4a0b5e52b739a3"},{"path":"scripts/additive-gap-repair.mjs","bytes":93926,"sha256":"64a05191c5ab32a0c930591f170552feab95a5836f0b185b692d5701a1b8f521"},{"path":"src/effective-footprint.js","bytes":30650,"sha256":"aca206b6c253e3bc7291bd27ce932747c279a09832b285ddb875e806703b05ea"},{"path":"scripts/native-ownership/native-preparation-guards.mjs","bytes":6371,"sha256":"6c4ea2f29f6bfed9176fa8c38dfde522d859442797e4a3cce76f250c69c75fb0"},{"path":"src/native-runtime.js","bytes":3497,"sha256":"988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600"},{"path":"scripts/native-ownership/compile-native-ownership.mjs","bytes":4472,"sha256":"2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378"},{"path":"src/native-grid.js","bytes":6408,"sha256":"b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663"},{"path":"src/ownership-codec.js","bytes":2948,"sha256":"64630f340a2815d5c86706cc4456718054990083d1026e0b420dd8f9f02f593d"},{"path":"scripts/audit-grid-intervals.mjs","bytes":6777,"sha256":"084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9"},{"path":"scripts/native-ownership/require-verified-selection.mjs","bytes":4377,"sha256":"20a8e3f472db4c06386ce2b7bd01330ea8acfd6d1ff414f6d2d32e8b1995d50c"},{"path":"scripts/native-ownership/read-pinned-build-file.mjs","bytes":1540,"sha256":"7633087e97d7fbceeaf87c0e5f0225c2c456a7141f534b7fb53f4312222166cb"},{"path":"scripts/native-ownership/verified-candidates.json","bytes":1362,"sha256":"d04a08074fad869f0dd618a6ba46cbad6e07d023f8acaedeec0ece4a9a9621b7"},{"path":"scripts/evidence-quality.mjs","bytes":28506,"sha256":"8950701f659808b0f1aa527d1d79dbdaa06921abd601bef80a6b030963eb0d97"},{"path":"src/ownership-method.js","bytes":3126,"sha256":"3a19f5fb267e32f9a4ab302d7de9dea84f1b6e2cdfa93701229917c86ff4e3df"},{"path":"package-lock.json","bytes":246591,"sha256":"471d035f92567ea447f221661db5fa8febfc7afc32af8ac975506ce9e0303255"}],"native_executed_code":[{"bytes":1417,"path":"package.json","sha256":"2af9169f046047a5cbc14592bdd776740d1b6e2871ec8216fa4a0b5e52b739a3"},{"bytes":95874,"path":"scripts/additive-gap-repair.mjs","sha256":"5bda202160724a6128cc891d9770b799c205c9fe99b9d2d4c8794b46b00e610c"},{"bytes":30650,"path":"src/effective-footprint.js","sha256":"aca206b6c253e3bc7291bd27ce932747c279a09832b285ddb875e806703b05ea"},{"bytes":6371,"path":"scripts/native-ownership/native-preparation-guards.mjs","sha256":"6c4ea2f29f6bfed9176fa8c38dfde522d859442797e4a3cce76f250c69c75fb0"},{"bytes":3497,"path":"src/native-runtime.js","sha256":"988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600"},{"bytes":4472,"path":"scripts/native-ownership/compile-native-ownership.mjs","sha256":"2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378"},{"bytes":6408,"path":"src/native-grid.js","sha256":"b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663"},{"bytes":2948,"path":"src/ownership-codec.js","sha256":"64630f340a2815d5c86706cc4456718054990083d1026e0b420dd8f9f02f593d"},{"bytes":6777,"path":"scripts/audit-grid-intervals.mjs","sha256":"084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9"},{"bytes":4377,"path":"scripts/native-ownership/require-verified-selection.mjs","sha256":"20a8e3f472db4c06386ce2b7bd01330ea8acfd6d1ff414f6d2d32e8b1995d50c"},{"bytes":1540,"path":"scripts/native-ownership/read-pinned-build-file.mjs","sha256":"7633087e97d7fbceeaf87c0e5f0225c2c456a7141f534b7fb53f4312222166cb"},{"bytes":1362,"path":"scripts/native-ownership/verified-candidates.json","sha256":"d04a08074fad869f0dd618a6ba46cbad6e07d023f8acaedeec0ece4a9a9621b7"},{"bytes":28506,"path":"scripts/evidence-quality.mjs","sha256":"8950701f659808b0f1aa527d1d79dbdaa06921abd601bef80a6b030963eb0d97"},{"bytes":3126,"path":"src/ownership-method.js","sha256":"3a19f5fb267e32f9a4ab302d7de9dea84f1b6e2cdfa93701229917c86ff4e3df"},{"bytes":246591,"path":"package-lock.json","sha256":"471d035f92567ea447f221661db5fa8febfc7afc32af8ac975506ce9e0303255"}],"accepted_head":"b82ee098641b0dda3fc27d281b438ec4958ffbce","independent_review_comment":6073179645}];
const demand=(v,m)=>{if(!v)throw Error(m);};
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const sha=b=>createHash('sha256').update(b).digest('hex');
const canonical=v=>{
 if(Array.isArray(v))return v.map(canonical);
 if(v&&typeof v==='object'){const out=Object.create(null);for(const k of Object.keys(v).sort())out[k]=canonical(v[k]);return out;}
 demand((v===null||['number','string','boolean'].includes(typeof v))&&(typeof v!=='number'||Number.isFinite(v)),'Nonfinite/missing/non-JSON canonical value');return v;
};
export const valueBytes=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
export const valueSha=v=>sha(valueBytes(v));
const same=(a,b)=>valueBytes(a).equals(valueBytes(b));
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
function pinCheck(p){
 demand(p&&/^[a-f0-9]{40}$/.test(p.commit)&&['100644','100755'].includes(p.mode)&&/^[a-f0-9]{40}$/.test(p.git_blob_oid),'Missing immutable body identity');
 demand(typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..'),'Unsafe immutable path');
 demand(Number.isSafeInteger(p.bytes)&&p.bytes>=0&&p.bytes<=FILE&&hash(p.sha256),'Ordinary encoded body cap/hash');
 if(p.decoded_bytes!==undefined)demand(Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>=0&&p.decoded_bytes<=FILE&&hash(p.decoded_sha256),'Ordinary decoded body cap/hash');
}
// Bounds derive ONLY from complete actual pointsets. Camera bounds are ignored.
// A seam-spanning polygon widens to the entire longitude domain conservatively.
export function coordinateBounds(g){
 demand(g&&['Polygon','MultiPolygon'].includes(g.type)&&same(Object.keys(g).sort(),['coordinates','type']),'Unsupported whole primitive');
 const polys=g.type==='Polygon'?[g.coordinates]:g.coordinates;demand(Array.isArray(polys)&&polys.length>0,'Missing polygons');const boxes=[];
 for(const poly of polys){demand(Array.isArray(poly)&&poly.length>0,'Missing rings');let lo=Infinity,hi=-Infinity,south=Infinity,north=-Infinity,seam=false;
  for(const ring of poly){demand(Array.isArray(ring)&&ring.length>=4,'Incomplete ring');let prior;
   for(const p of ring){demand(Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=180&&Math.abs(p[1])<=90,'Invalid/nonfinite coordinate');lo=Math.min(lo,p[0]);hi=Math.max(hi,p[0]);south=Math.min(south,p[1]);north=Math.max(north,p[1]);if(prior&&Math.abs(prior[0]-p[0])>180)seam=true;prior=p;}
   demand(same(ring[0],ring.at(-1)),'Unclosed original ring');
  }
  if(seam||hi-lo>180){lo=-180;hi=180;}boxes.push([lo,south,hi,north]);
 }
 return boxes;
}
export function possibleNeighbors(certificate,changedGeometry,{targetId}={}){
 demand(certificates.has(certificate)&&certificate.kind==='selected-coordinate-neighbor-certificate-v2','Incomplete/unqualified neighbor certificate');
 demand(typeof targetId==='string'&&certificate.entries.some(r=>r.id===targetId),'Require exact SELF target identity; no arbitrary exclusions');
 const boxes=coordinateBounds(changedGeometry),skip=new Set([targetId]);const hit=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
 return certificate.entries.filter(r=>!skip.has(r.id)&&r.boxes.some(a=>boxes.some(b=>hit(a,b))));
}
// Lossless fixed-column projection: all original identity/source/hash/bounds
// values remain complete. Shared getters avoid materializing duplicate rows.
const COORDINATE_FIELDS=Object.freeze(['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes']);
class CoordinateRow extends Array {}
for(const [i,name]of COORDINATE_FIELDS.entries())Object.defineProperty(CoordinateRow.prototype,name,{get(){return this[i];},enumerable:false,configurable:false});
Object.freeze(CoordinateRow.prototype);
const coordinateRow=value=>Object.setPrototypeOf(COORDINATE_FIELDS.map(k=>value[k]),CoordinateRow.prototype);
function bindCoordinateRows(certificate){
 demand(certificate?.version===2&&same(certificate.entry_fields,COORDINATE_FIELDS)&&Array.isArray(certificate.entries),'Unsupported lossless coordinate row schema');
 for(const row of certificate.entries){demand(Array.isArray(row)&&row.length===COORDINATE_FIELDS.length&&Object.keys(row).join(',')===COORDINATE_FIELDS.map((_,i)=>String(i)).join(','),'Foreign/incomplete coordinate tuple');Object.setPrototypeOf(row,CoordinateRow.prototype);}
}
// Selected source adapter: whole source bodies are acquired through the trusted
// data-only selected-bank resolver, never the historical raw target path.
export function selectedCoordinateShard(resolver,sourcePaths,{priorShards=[],outputReserve=4*1024*1024,onFeature}={}) {
 demand(resolver instanceof SelectedGeometrySources&&Array.isArray(sourcePaths)&&sourcePaths.length>0&&new Set(sourcePaths).size===sourcePaths.length,'Require actual selected source resolver and unique whole containing scope');
 demand(sourcePaths.every(p=>resolver.paths.includes(p)),'Foreign selected source shard');
 const snapshot=resolver.snapshot,reader=resolver.reader;
 demand(Number.isSafeInteger(outputReserve)&&outputReserve>0&&outputReserve<=FILE,'Bounded coordinate output reserve required');reader.outputBytes=outputReserve;
 const binding={version:1,kind:'selected-complete-coordinate-binding-v1',selection:snapshot.selection,release:resolver.release,
   sources:resolver.sources,owners_sha256:valueSha(snapshot.owners),coordinate_domain:'complete-original-pointset-bounds:v1'};
 for(const shard of priorShards)demand(certificates.has(shard)&&same(shard.binding,binding),'Unqualified or foreign retained coordinate shard');
 // Complete immutable metadata is the only state retained across genuine
 // acquisition phases. Original source collections are discarded after each
 // iteration; bounds are not substitute geometry inputs to polygon consumers.
 const ownerIdentity=snapshot.owners.map(r=>[r.index,r.id,r.province_index,r.province_id]);
 const retained=valueBytes({binding,ownerIdentity,image:resolver.image?{index:resolver.image.index,map:resolver.image.map}:null,bank:resolver.bank??null,priorShards}).length;
 demand(retained<=FILE,'Retained coordinate certificate metadata exceeds ordinary bound');
 reader.metadataBytes=8*1024*1024+2*(snapshot.metadataBytes+retained)+snapshot.acquisition_buffer_bytes;reader.phase();
 const roster=new Map(snapshot.owners.map(r=>[r.id,r])),entries=[],seen=new Set(),inputFacts=[],phases=[];
 for(const name of sourcePaths){
  reader.metadataBytes=8*1024*1024+2*(snapshot.metadataBytes+retained+valueBytes({entries,inputFacts}).length)+snapshot.acquisition_buffer_bytes;reader.phase();const actual=resolver.read(name);inputFacts.push({path:name,source:actual.source,whole_body_sha256:actual.whole_sha256,bytes:actual.body.length});
  for(let ordinal=0;ordinal<actual.collection.features.length;ordinal++){
   const f=actual.collection.features[ordinal],id=f.id??f.properties?.id,owner=roster.get(id);
   demand(f.type==='Feature'&&owner&&!seen.has(id)&&f.properties?.parent_id===owner.province_id,'Foreign/duplicate/misparented whole selected row');seen.add(id);
   const additions=(snapshot.additive?.normalized_rows??[]).filter(r=>r.target_id===id);
   for(const addition of additions)demand(addition.base_geometry_sha256===valueSha(f.geometry),'Effective addition target pointsets are stale against complete selected source');
   const effective={base_geometry_sha256:valueSha(f.geometry),additions};
   const allBounds=[...coordinateBounds(f.geometry),...additions.flatMap(r=>coordinateBounds(r.geometry))];
   // One conservative rectangle contains every original member/addition bound.
   // A seam member already spans all longitude; merging can only widen exclusion.
   const boxes=[allBounds.reduce((a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])])];
   entries.push(coordinateRow({id,index:owner.index,parent_id:owner.province_id,parent_index:owner.province_index,source:name,ordinal,whole_feature_sha256:valueSha(f),geometry_sha256:valueSha(f.geometry),effective_geometry_sha256:valueSha(effective),boxes}));
   if(onFeature!==undefined){demand(typeof onFeature==='function','Require trusted source digest callback');onFeature(f);}
  }
  phases.push({source:name,complete_phase_bytes:reader.used,descriptors:reader.charged.size});
 }
 const result={version:2,kind:'selected-complete-coordinate-shard-v2',entry_fields:COORDINATE_FIELDS,binding,paths:sourcePaths,inputs:inputFacts,entries,phases};
 demand(valueBytes(result).length<=reader.outputBytes,'Selected coordinate shard exceeds prospective output');freeze(result);certificates.set(result,{binding,resolver});return result;
}
export function joinSelectedCoordinateCertificate(resolver,shards,{outputReserve=32*1024*1024}={}) {
 demand(resolver instanceof SelectedGeometrySources&&Array.isArray(shards)&&shards.length>0,'Missing actual selected coordinate shards');
 const expected=new Set(resolver.paths),seenPaths=new Set(),seenIds=new Set(),entries=[],inputs=[];
 let binding;for(const shard of shards){
  const proof=certificates.get(shard);demand(proof&&proof.resolver===resolver&&shard.kind==='selected-complete-coordinate-shard-v2','Unqualified/foreign selected coordinate stage');
  if(!binding)binding=shard.binding;demand(same(binding,shard.binding),'Mixed selected coordinate vintage');
  for(const p of shard.paths){demand(expected.has(p)&&!seenPaths.has(p),'Foreign/duplicate source containing closure');seenPaths.add(p);}
  for(const input of shard.inputs){demand(input.path===resolver.paths[inputs.length]&&same(input.source,{...resolver.sources[inputs.length],...(input.source.whole_encoded_alias?{whole_encoded_alias:input.source.whole_encoded_alias}:{})}), 'Complete selected source input order or whole binding differs');inputs.push(input);}for(const row of shard.entries){demand(!seenIds.has(row.id),'Duplicate complete location join');seenIds.add(row.id);entries.push(row);}
 }
 demand(seenPaths.size===expected.size&&seenIds.size===resolver.snapshot.owners.length&&resolver.snapshot.owners.every(o=>seenIds.has(o.id)),'Incomplete canonical source/owner roster; exclusion forbidden');
 const retained=2*(resolver.snapshot.metadataBytes+valueBytes({shards,ownerIdentity:resolver.snapshot.owners.map(r=>[r.index,r.id,r.province_index,r.province_id]),binding}).length)+resolver.snapshot.acquisition_buffer_bytes;
 const reader=resolver.reader;demand(Number.isSafeInteger(outputReserve)&&outputReserve>0&&outputReserve<=FILE,'Bounded complete certificate output reserve required');reader.outputBytes=outputReserve;reader.metadataBytes=8*1024*1024+retained;reader.phase();
 demand(shards.length+inputs.length<=SLOT,'Complete coordinate join descriptor cap');entries.sort((a,b)=>a.index-b.index);
 const result={version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:COORDINATE_FIELDS,binding,entries,inputs,complete_phase_bytes:reader.used,limitations:['Certificate projects complete owner identity/index/parent tuples and merged coordinate bounds. Full original camera metadata remains authenticated source custody and charged carried state; it is not duplicated as certificate geometry.','Conservative exclusion only. Actual whole geometry and original polygon predicates are mandatory for every possible neighbor.']};
 demand(valueBytes(result).length<=reader.outputBytes,'Complete selected certificate exceeds prospective output');freeze(result);certificates.set(result,{binding,resolver});return result;
}
// Qualification of a persisted cold product uses the independently retained
// live trusted child acknowledgement, plus the actual selected resolver. The
// acknowledgement is issued by the parent invocation, never read from candidate
// files or inferred from the product's own facts.
export function acceptColdCoordinateCertificate(resolver,certificate,{facts,expectedPublication,publication,encoded_sha256,decoded_sha256}) {
 demand(resolver instanceof SelectedGeometrySources&&same(publication,expectedPublication)&&publication.complete===true&&publication.kind==='trusted-selected-coordinate-stage-v1','Missing actual issued cold-stage acknowledgement');
 demand(encoded_sha256===publication.certificate.sha256&&decoded_sha256===publication.certificate.decoded_sha256,'Cold complete certificate bytes differ');
 demand(facts.kind===publication.kind&&facts.selected_commit===resolver.reader.version&&facts.candidate_code_executed===false&&certificate.kind==='selected-coordinate-neighbor-certificate-v2','Foreign cold certificate execution/input');
 demand(same(certificate.binding.selection,resolver.snapshot.selection)&&same(certificate.binding.release,resolver.release)&&same(certificate.binding.sources,resolver.sources)&&certificate.binding.owners_sha256===valueSha(resolver.snapshot.owners)&&same(facts.binding,certificate.binding),'Cold certificate selected source/owner binding differs');
 bindCoordinateRows(certificate);
 const paths=new Set(resolver.paths),owners=new Map(resolver.snapshot.owners.map(r=>[r.id,r])),seen=new Set(),sources=new Set();
 demand(Array.isArray(certificate.inputs)&&certificate.inputs.length===paths.size&&Array.isArray(certificate.entries)&&certificate.entries.length===owners.size,'Incomplete cold source/owner certificate');
 for(let i=0;i<certificate.inputs.length;i++){const input=certificate.inputs[i],expected=resolver.sources[i];
  demand(input.path===resolver.paths[i]&&!sources.has(input.path)&&sources.add(input.path)&&same(input.source,{...expected,...(input.source?.whole_encoded_alias?{whole_encoded_alias:input.source.whole_encoded_alias}:{})})&&hash(input.whole_body_sha256)&&Number.isSafeInteger(input.bytes)&&input.bytes>0&&input.bytes<=FILE,'Foreign/duplicate/reordered/drifted complete cold source');
  const rawHash=expected.decoded_sha256??expected.sha256,rawBytes=expected.decoded_bytes??expected.bytes;demand(input.whole_body_sha256===rawHash&&input.bytes===rawBytes,'Whole cold selected source body differs from independent source bank');
 }
 for(let i=0;i<certificate.entries.length;i++){const row=certificate.entries[i],owner=owners.get(row.id);demand(row.id===resolver.snapshot.owners[i].id&&owner&&!seen.has(row.id)&&seen.add(row.id)&&row.index===owner.index&&row.parent_id===owner.province_id&&row.parent_index===owner.province_index&&paths.has(row.source)&&Number.isSafeInteger(row.ordinal)&&row.ordinal>=0&&hash(row.whole_feature_sha256)&&hash(row.geometry_sha256)&&hash(row.effective_geometry_sha256)&&Array.isArray(row.boxes)&&row.boxes.length>0,'Foreign/duplicate/drifted cold owner record');
  const additions=(resolver.snapshot.additive?.normalized_rows??[]).filter(r=>r.target_id===row.id);
  demand(row.effective_geometry_sha256===valueSha({base_geometry_sha256:row.geometry_sha256,additions})&&additions.every(r=>r.base_geometry_sha256===row.geometry_sha256),'Cold effective primitive set differs from independently authenticated selection');
  for(const box of row.boxes)demand(Array.isArray(box)&&box.length===4&&box.every(Number.isFinite)&&box[0]>=-180&&box[2]<=180&&box[1]>=-90&&box[3]<=90&&box[0]<=box[2]&&box[1]<=box[3],'Invalid complete coordinate exclusion bound');
 }
 demand(facts.complete_owners===owners.size&&facts.complete_sources===paths.size,'Cold scope denominator differs');
 freeze(certificate);certificates.set(certificate,{binding:certificate.binding,resolver});return certificate;
}

export function selectedCertificateAffectedPlan(before,after) {
 demand(certificates.has(before)&&certificates.has(after),'Require both complete cold source certificates');
 const old=new Map(before.entries.map(r=>[r.id,r])),next=new Map(after.entries.map(r=>[r.id,r]));
 demand(old.size===next.size&&[...old].every(([id,row])=>next.has(id)&&row.index===next.get(id).index&&row.parent_id===next.get(id).parent_id&&row.parent_index===next.get(id).parent_index),'Selected continuous identity/owner/parent roster changed');
 const changed=[...old.keys()].filter(id=>old.get(id).effective_geometry_sha256!==next.get(id).effective_geometry_sha256).sort(),needed=new Set(changed),pairs=new Set();
 const intersects=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
 for(const id of changed){const bounds=[...old.get(id).boxes,...next.get(id).boxes];
  for(const certificate of [before,after])for(const row of certificate.entries)if(row.id!==id&&row.boxes.some(a=>bounds.some(b=>intersects(a,b)))){needed.add(row.id);pairs.add([id,row.id].sort().join('\0'));}
 }
 demand(valueBytes([...needed,...pairs]).length<=FILE,'Complete continuous affected closure exceeds output cap');
 return freeze({version:1,kind:'complete-selected-continuous-plan-v1',changed_ids:changed,required_ids:[...needed].sort(),pairs:[...pairs].sort().map(p=>p.split('\0')),source_paths:{baseline:[...new Set([...needed].map(id=>old.get(id).source))].sort(),candidate:[...new Set([...needed].map(id=>next.get(id).source))].sort()},
  source_bindings:{baseline:before.binding,candidate:after.binding},limits:['Coordinate exclusion only. All required full original polygons and unchanged strict coverage/overlap predicates remain mandatory.']});
}

// No caller-supplied exclusion set. Other changed owners remain possible
// neighbors and are compared pairwise; same-owner additions keep all primitives.
export function selectedAffectedPlan(certificate,changes) {
 demand(certificates.has(certificate)&&certificate.kind==='selected-coordinate-neighbor-certificate-v2'&&Array.isArray(changes)&&changes.length>0,'Missing qualified complete selected certificate');
 const targets=new Map(),pairs=new Set(),needed=new Set();
 for(const change of changes){demand(change&&typeof change.id==='string'&&!targets.has(change.id),'Duplicate/foreign changed target');
  const own=certificate.entries.find(r=>r.id===change.id);demand(own&&Array.isArray(change.primitives)&&change.primitives.length>0,'Changed target outside original complete roster');
  targets.set(change.id,change);needed.add(change.id);
  const hit=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
  for(const neighbor of certificate.entries)if(neighbor.id!==change.id&&neighbor.boxes.some(a=>own.boxes.some(b=>hit(a,b)))){needed.add(neighbor.id);pairs.add([change.id,neighbor.id].sort().join('\0'));}
  for(const geometry of change.primitives)for(const neighbor of possibleNeighbors(certificate,geometry,{targetId:change.id})){
   needed.add(neighbor.id);pairs.add([change.id,neighbor.id].sort().join('\0'));
  }
 }
 const boxes=[...targets.values()].flatMap(change=>change.primitives.flatMap(g=>coordinateBounds(g).map(box=>({id:change.id,box})))).sort((a,b)=>a.box[0]-b.box[0]);
 const active=[];for(const current of boxes){for(let i=active.length-1;i>=0;i--)if(active[i].box[2]<current.box[0])active.splice(i,1);
  for(const other of active)if(other.id!==current.id&&other.box[1]<=current.box[3]&&current.box[1]<=other.box[3])pairs.add([other.id,current.id].sort().join('\0'));active.push(current);
 }
 demand(valueBytes([...pairs]).length<=FILE,'Complete affected pair roster exceeds bounded output; refuse incomplete comparison');
 return {version:1,kind:'complete-selected-affected-plan-v1',binding:certificate.binding,changed_ids:[...targets.keys()].sort(),required_ids:[...needed].sort(),pairs:[...pairs].sort().map(p=>p.split('\0')),
  source_paths:[...new Set(certificate.entries.filter(r=>needed.has(r.id)).map(r=>r.source))].sort(),limitations:['Original strict polygon predicates still required; this plan is not geographic approval.']};
}

// Authenticate original executed rule bodies before deriving their preimage.
// This is historical authority custody, not source approval or bank activation.
export function readOriginalRuleAuthority(reader, pins) {
 demand(reader instanceof ImmutableReader&&pins&&Object.keys(pins).sort().join(',')==='ledger,native_facts,native_manifest,native_request,source_facts,source_request','Require exact original rule body roster');
 const normal=p=>({...p,git_blob_oid:p.git_blob_oid??p.blob});
 const identity=p=>{const q=normal(p);return {commit:q.commit,path:q.path,mode:q.mode,git_blob_oid:q.git_blob_oid,bytes:q.bytes,sha256:q.sha256};};
 const admitted=new Map();
 // All six whole bodies and retained parsed metadata are prospectively charged
 // before reading the first body. No callback or arbitrary loader is accepted.
 const retained=Object.values(pins).reduce((n,p)=>n+2*p.bytes,0);
 demand(Number.isSafeInteger(retained)&&retained<=FILE,'Original rule metadata exceeds whole bound');
 reader.metadataBytes+=retained;reader.phase();
 for(const [key,p]of Object.entries(pins)){
  pinCheck(normal(p));let version=p.commit;
  try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);
  demand(actual.mode===p.mode&&actual.git_blob_oid===normal(p).git_blob_oid&&actual.bytes===p.bytes,'Original authority body mode/OID differs');
  reader.admit(actual);admitted.set(key,{pin:p,version});
 }
 const bodies={};for(const [key,{pin,version}]of admitted)bodies[key]=JSON.parse(reader.read(pin.path,{version,expected:pin.sha256}));
 const {ledger,native_facts:native, native_manifest:manifest,native_request:request,source_facts:source,source_request:issued}=bodies;
 demand(same(identity(native.request),identity(pins.native_request))&&same(identity(source.request),identity(pins.source_request)),'Original facts rebound issued request');
 demand(same(native.executed_code,request.executed_code)&&same(source.executed_code,issued.executed_code),'Original executed code differs from issued closure');
 demand(source.operation==='retained-land-source-premises-v1'&&issued.operation===source.operation&&same(issued.source_rule,source.source_rule),'Original whole source rule differs');
 demand(request.operation===native.operation&&['unactivated-additive-native-release-v1','unactivated-additive-native-batch-v1'].includes(native.operation),'Unsupported original proposal operation');
 const spec=request.additive;demand(spec&&same(spec,native.source_predecessor),'Original proposal source predecessor changed');
 for(const [key,name]of [['source_request','source_request_path'],['source_facts','facts_path']]){
  const pin=spec.inputs?.find(p=>p.path===spec[name]);
  demand(pin&&same(identity(pin),identity(pins[key])),'Original proposal omits/rebinds complete predecessor: '+key);
 }
 const manifestOriginal=request.baseline?.pins?.find(p=>p.path===spec.manifest_path);
 demand(manifestOriginal&&same({mode:manifestOriginal.mode,git_blob_oid:normal(manifestOriginal).git_blob_oid,bytes:manifestOriginal.bytes,sha256:manifestOriginal.sha256},{mode:pins.native_manifest.mode,git_blob_oid:normal(pins.native_manifest).git_blob_oid,bytes:pins.native_manifest.bytes,sha256:pins.native_manifest.sha256}),'Original baseline/native whole manifest alias differs');
 demand(same(issued.baseline,source.baseline)&&same(request.baseline,native.baseline)&&same(issued.parent,source.parent)&&same(request.parent,native.parent),'Original baseline or parent changed');
 const batch=native.operation==='unactivated-additive-native-batch-v1';
 const preimage=batch?{version:3,source_profile:issued.source_rule.profile,source_rule:issued.source_rule,representation:'literal-base-or-complete-additions',native_method:manifest.method,executed_code:request.executed_code}:
  {version:2,source_rule_body_sha256:issued.source_rule.review_body_sha256,representation:'literal-base-or-complete-additions',native_method:manifest.method,executed_code:request.executed_code};
 demand(valueSha(preimage)===ledger.rule_sha256,'Original complete executed rule preimage differs');
 demand(ledger.version===1&&ledger.kind==='native-additive-repair-ledger-v1'&&Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.rows.length===ledger.scope_ids.length&&new Set(ledger.scope_ids).size===ledger.rows.length&&ledger.rows.every((r,i)=>r.component_id===ledger.scope_ids[i]),'Original complete ledger scope changed');
 demand(Array.isArray(issued.source_rule.expected_ids)&&same([...issued.source_rule.expected_ids].sort(),[...ledger.scope_ids].sort())&&source.components===ledger.scope_ids.length,'Original complete source denominator differs');
 const selected=ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition));
 for(const row of selected){demand(row.source_receipt_sha256===pins.source_facts.sha256&&valueSha(row.geometry)===row.geometry_sha256,'Original whole primitive/source receipt changed');coordinateBounds(row.geometry);}
 demand(batch?same(spec.scope_ids,ledger.scope_ids):selected.length===1&&selected[0].component_id===spec.component_id,'Original proposal selection differs');
 const result=freeze({version:1,kind:'authenticated-original-rule-custody-v1',pins,manifest_original_pin:manifestOriginal,rule_sha256:ledger.rule_sha256,rule_preimage:preimage,source_rule:issued.source_rule,ledger,
  source_scope_ids:ledger.scope_ids,complete_phase_bytes:reader.used,limitations:['Historical whole executed rule custody only. Full predecessor publication/operating/source closure and current-bank rebind are independently required before selection. No physical authority or activation approval.']});
 originalAuthorities.set(result,{reader,bodies});return result;
}

// Reuse the actually qualified source predecessor; never infer permission from
// a hash-shaped receipt or caller-written approval boolean. No source method is
// rerun here. Original whole case/source pins remain in the retained closure.
export function qualifyOriginalSourceAuthority(custody) {
 const proof=originalAuthorities.get(custody);demand(proof,'Require actual authenticated original rule custody');
 const {reader,bodies}=proof,{native_request:request,source_request:issued,source_facts:facts}=bodies,spec=request.additive;
 const keys=['publication_path','inventory_path','operating_path'];
 const pins=keys.map(key=>{const p=spec.inputs.find(p=>p.path===spec[key]);demand(p,'Omitted qualified source proof '+key);pinCheck({...p,git_blob_oid:p.git_blob_oid??p.blob});return p;});
 const retained=pins.reduce((n,p)=>n+2*(p.bytes+(p.uncompressed_bytes??0)),0);
 demand(Number.isSafeInteger(retained)&&retained<=FILE,'Qualified proof retained metadata cap');reader.metadataBytes+=retained;
 // Retain and charge the prior six whole bodies: no phase reset while live.
 demand(reader.used+retained<=PHASE,'Complete original source proof phase exceeds cap');reader.used+=retained;
 const admitted=pins.map(p=>{let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);demand(actual.mode===p.mode&&actual.git_blob_oid===(p.git_blob_oid??p.blob)&&actual.bytes===p.bytes,'Qualified original proof mode/OID differs');reader.admit(actual,p.uncompressed_bytes??0);return {p,version};});
 const raw=admitted.map(({p,version})=>{const encoded=reader.read(p.path,{version,expected:p.sha256,decoded:p.uncompressed_bytes??0});if(p.uncompressed_bytes===undefined)return encoded;
  demand(hash(p.uncompressed_sha256),'Missing complete decoded proof hash');const decoded=gunzipSync(encoded,{maxOutputLength:p.uncompressed_bytes});demand(decoded.length===p.uncompressed_bytes&&sha(decoded)===p.uncompressed_sha256,'Whole decoded original proof differs');return decoded;});
 const [publication,inventory,operating]=[JSON.parse(raw[0]),raw[1],JSON.parse(raw[2])],inventoryPin=pins[1];
 demand(publication.complete===true&&publication.facts.bytes===custody.pins.source_facts.bytes&&publication.facts.sha256===custody.pins.source_facts.sha256&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>publication.inventory[k]===inventoryPin[k]),'Partial/drifted original source publication');
 demand(facts.execution_commit===spec.source_execution_commit&&same(facts.input_descriptors,[issued.report,...issued.source_rule.inputs,...issued.baseline.pins])&&same(facts.runtime,spec.source_runtime)&&same(facts.installed_modules,issued.installed_modules)&&same(facts.parent,request.parent)&&same(issued.baseline,request.baseline),'Original source execution closure differs');
 demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0&&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null&&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Unqualified original source operating proof');
 const lines=inventory.toString('utf8').split('\n');demand(lines.pop()==='','Truncated complete source inventory');const rows=lines.map(line=>JSON.parse(line));
 demand(same(rows.map(r=>r.component_id),issued.source_rule.expected_ids)&&rows.length===facts.components&&new Set(rows.map(r=>r.component_id)).size===rows.length,'Omitted/duplicate/reordered source inventory');
 const byId=new Map(rows.map(r=>[r.component_id,r]));
 for(const selected of custody.ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition))){const row=byId.get(selected.component_id);
  demand(row?.source_compatible===true&&row.disposition==='awaiting-native-exclusion'&&same(row.candidate,selected.geometry)&&row.target_id===selected.target_id&&row.target_geometry_sha256===selected.base_geometry_sha256,'Original selected primitive lacks complete source premise');
  demand(row.source_case?.source&&spec.inputs.some(p=>same(p,row.source_case.source)),'Whole proposal source-case custody omitted');
  for(const pin of [row.source_case?.source,row.original_record?.source])demand(pin&&issued.source_rule.inputs.some(p=>same(p,pin)),'Whole original source-case/record custody omitted');
 }
 const result=freeze({version:1,kind:'qualified-original-source-authority-v1',original:custody,pins,rows,complete_phase_bytes:reader.used,
  limitations:['Original retained source-relative qualification only. Physical authority/date/water truth remains unapproved; native proposal qualification and actual selected-bank conservation/rebind are separately mandatory.']});
 proof.qualifiedSource=result;return result;
}

// Authenticate a once-qualified original native proposal without replaying it.
// Its base remains historical until the selected hook proves currentness.
export function qualifyOriginalNativeAuthority(custody, pins) {
 const proof=originalAuthorities.get(custody);demand(proof,'Require actual original custody');
 const {reader,bodies}=proof,{native_request:issued,native_facts:facts}=bodies;
 demand(proof.qualifiedSource,'Native authority requires complete qualified source predecessor first');
 demand(pins&&Object.keys(pins).sort().join(',')==='assets,inventory,operating,publication'&&Array.isArray(pins.assets),'Require complete native proof roster');
 const all=[pins.publication,pins.inventory,pins.operating,...pins.assets];
 const retained=all.reduce((n,p)=>n+2*(p.bytes+(p.decoded_bytes??p.uncompressed_bytes??0)),0);
 demand(Number.isSafeInteger(retained)&&reader.used+retained<=PHASE,'Complete original native retained phase exceeds cap before reads');
 reader.used+=retained;
 const admitted=all.map(p=>{
  const q={...p,git_blob_oid:p.git_blob_oid??p.blob,decoded_bytes:p.decoded_bytes??p.uncompressed_bytes,decoded_sha256:p.decoded_sha256??p.uncompressed_sha256};pinCheck(q);
  let version=q.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(q.path,version);demand(actual.mode===q.mode&&actual.git_blob_oid===q.git_blob_oid&&actual.bytes===q.bytes,'Original native proof whole mode/OID differs');
  reader.admit(actual,q.decoded_bytes??0);return {q,version};
 });
 const raw=admitted.map(({q,version})=>{
  const body=reader.read(q.path,{version,expected:q.sha256,decoded:q.decoded_bytes??0});if(q.decoded_bytes===undefined)return body;
  const decoded=gunzipSync(body,{maxOutputLength:q.decoded_bytes});demand(decoded.length===q.decoded_bytes&&sha(decoded)===q.decoded_sha256,'Original whole native decoded proof differs');return decoded;
 });
 const publication=JSON.parse(raw[0]),operating=JSON.parse(raw[2]),inventoryPin=pins.inventory;
 demand(publication.complete===true&&publication.facts.bytes===custody.pins.native_facts.bytes&&publication.facts.sha256===custody.pins.native_facts.sha256&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>publication.inventory[k]===inventoryPin[k]),'Partial/drifted original native publication');
 demand(same(facts.input_descriptors,[issued.report,...issued.additive.inputs,...issued.baseline.pins])&&same(facts.installed_modules,issued.installed_modules),'Original native actual input/module closure differs');
 demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0&&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null&&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Unqualified original native operating proof');
 const lines=raw[1].toString('utf8').split('\n');demand(lines.pop()==='','Truncated whole native inventory');const rows=lines.map(s=>JSON.parse(s));
 const batch=facts.operation==='unactivated-additive-native-batch-v1',nativeScope=batch?custody.source_scope_ids:[issued.additive.component_id];
 demand(same(rows.map(r=>r.component_id),nativeScope)&&new Set(rows.map(r=>r.component_id)).size===rows.length&&(!batch||rows.length===facts.components),'Native inventory scope omitted/reordered');
 const byId=new Map(custody.ledger.rows.map(r=>[r.component_id,r]));
 for(const row of rows){const old=byId.get(row.component_id);demand(old&&(batch?row.disposition===old.disposition:['assigned','zero-cell'].includes(old.disposition))&&row.native_cells===(old.native_cells??0)&&row.target_id===(['assigned','zero-cell'].includes(old.disposition)?old.target_id:proof.qualifiedSource.rows.find(r=>r.component_id===row.component_id)?.target_id),'Native inventory disposition/contribution rebound');}
 demand(publication.assets.length===pins.assets.length&&new Set(pins.assets.map(p=>p.path)).size===pins.assets.length,'Incomplete/duplicate native asset roster');
 const nativePatches=[],nativeContracts=[];
 for(let i=0;i<pins.assets.length;i++){
  const p=pins.assets[i],declared=publication.assets[i];
  demand(p.path.endsWith('/'+declared.path)&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>p[k]===declared[k]),'Original native asset roster rebound');
  if(declared.path==='base-native-manifest.json'){const m=JSON.parse(raw[i+3]);nativeContracts.push(Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,m[k]])));}
  if(declared.path.startsWith('patch-')){const patch=JSON.parse(raw[i+3]);demand(patch.kind==='unassigned-native-cells-v1'&&patch.ledger_sha256===custody.pins.ledger.sha256,'Qualified original patch/ledger differs');nativePatches.push(patch);}
  if(p.sha256===custody.pins.ledger.sha256)demand(same(JSON.parse(raw[i+3]),custody.ledger),'Whole published native ledger differs');
 }
 demand(nativeContracts.length===1,'Original native publication omits complete base manifest');
 demand(pins.assets.some(p=>p.sha256===custody.pins.ledger.sha256),'Published native assets omit original complete ledger');
 return freeze({version:1,kind:'qualified-original-native-authority-v1',pins,scope_ids:custody.source_scope_ids,native_scope_ids:nativeScope,inventory_rows:rows,native_patches:nativePatches,native_contract:nativeContracts[0],rule_sha256:custody.rule_sha256,complete_phase_bytes:reader.used,
  limitations:['Original unactivated proposal custody/qualification only; selected current-bank applicability and immutable policy authority remain separately required.']});
}

// Comparison is conservation, not admission of new authorities. The caller
// must authenticate every whole registry preimage/source-authority body through
// the committed selector before using this view. A registry is not approval.
function authorityRegistry(registry) {
 demand(registry?.version===1&&registry.kind==='retained-rule-authority-registry-v1'&&Array.isArray(registry.entries)&&registry.entries.length>0,'Missing explicit retained authority registry');
 const byId=new Map();let previous='';
 for(const entry of registry.entries){
  demand(entry&&Object.keys(entry).sort().join(',')==='authority_sha256,policy_id,policy_version,rule_preimage,rule_sha256,source_authority'&&hash(entry.authority_sha256)&&entry.authority_sha256>previous&&hash(entry.rule_sha256)&&typeof entry.policy_id==='string'&&entry.policy_id&&Number.isSafeInteger(entry.policy_version)&&entry.policy_version>0,'Foreign/duplicate/unordered authority entry');
  pinCheck(entry.rule_preimage);pinCheck(entry.source_authority);
  demand(entry.rule_preimage.sha256===entry.rule_sha256,'Original full rule preimage differs');
  const {authority_sha256,...preimage}=entry;demand(valueSha(preimage)===authority_sha256,'Whole authority entry changed');
  byId.set(authority_sha256,entry);previous=authority_sha256;
 }
 return byId;
}
// One detached authority acquisition. The returned view cannot authorize a
// selected release: the committed hook must additionally authenticate the
// qualified native publication, operating proof and actual current bank.
export function readRetainedRegistryAuthority(reader, entry) {
 const singleton={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};
 authorityRegistry(singleton);
 const pins=[entry.rule_preimage,entry.source_authority];
 const retained=pins.reduce((n,p)=>n+2*p.bytes,0);
 demand(Number.isSafeInteger(retained)&&retained<=FILE,'Registry retained whole metadata bound');
 reader.metadataBytes+=retained;reader.phase();
 const admitted=pins.map(p=>{
  pinCheck(p);let version=p.commit;
  try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);
  demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Registry authority whole mode/OID differs');
  reader.admit(actual);return {p,version};
 });
 const [preimage,binding]=admitted.map(({p,version})=>JSON.parse(reader.read(p.path,{version,expected:p.sha256})));
 demand(valueSha(preimage)===entry.rule_sha256,'Complete original registry preimage differs');
 demand(binding?.version===1&&binding.kind==='original-issued-rule-source-custody-v1'&&Object.keys(binding).sort().join(',')==='kind,native_proof,original_pins,version','Unsupported original authority binding');
 const custody=readOriginalRuleAuthority(reader,binding.original_pins);
 demand(same(preimage,custody.rule_preimage)&&custody.rule_sha256===entry.rule_sha256,'Registry relabelled original executed rule');
 const original=originalAuthorities.get(custody).bodies;
 const supported=SUPPORTED_PROGRAMS.find(p=>p.preimage_version===preimage.version&&p.source_profile===(custody.source_rule.profile??null));
 const codeIdentity=rows=>rows.map(p=>{demand(Object.keys(p).sort().join(',')==='bytes,path,sha256','Unsupported original complete code roster shape');return {path:p.path,bytes:p.bytes,sha256:p.sha256};});
 demand(supported&&same(codeIdentity(original.source_request.executed_code),codeIdentity(supported.source_executed_code))&&same(codeIdentity(original.native_request.executed_code),codeIdentity(supported.native_executed_code)),'Unreviewed source/native policy program closure');
 const source=qualifyOriginalSourceAuthority(custody),native=qualifyOriginalNativeAuthority(custody,binding.native_proof);
 return freeze({version:1,kind:'authenticated-registry-source-custody-v1',authority_sha256:entry.authority_sha256,
  rule_sha256:entry.rule_sha256,original_program_authority:{accepted_head:supported.accepted_head,independent_review_comment:supported.independent_review_comment},policy_id:entry.policy_id,policy_version:entry.policy_version,
  pins,original_pins:binding.original_pins,source_scope_ids:custody.source_scope_ids,
  source_rows:source.rows,native_proof:native,original_ledger:custody.ledger,complete_phase_bytes:reader.used,
  limitations:['Whole original preimage, issued requests and qualified source predecessor authenticated. Policy semantics and actual current selected-bank applicability remain separately required; this view cannot authorize selection.']});
}

export function normaliseRetainedRepairLedger(ledger,registry) {
 const authorities=authorityRegistry(registry),legacy=ledger?.version===1&&ledger.kind==='native-additive-repair-ledger-v1';
 demand(legacy||ledger?.version===2&&ledger.kind==='native-additive-repair-ledger-v2'&&ledger.authority_registry_sha256===valueSha(registry),'Unsupported or unbound versioned repair ledger');
 demand(Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.scope_ids.length===ledger.rows.length&&new Set(ledger.scope_ids).size===ledger.rows.length,'Incomplete complete ledger scope');
 let legacyEntry;if(legacy){demand(hash(ledger.rule_sha256),'Missing original v1 rule');const matches=registry.entries.filter(e=>e.rule_sha256===ledger.rule_sha256);demand(matches.length===1,'Original v1 authority omitted or ambiguous');legacyEntry=matches[0];}
 const rows=new Map();let previous='';
 for(let i=0;i<ledger.rows.length;i++){
  const row=ledger.rows[i];demand(row.component_id===ledger.scope_ids[i]&&row.component_id>previous,'Foreign/duplicate/unordered component');previous=row.component_id;
  demand(['assigned','zero-cell','already-resolved','rejected','awaiting-evidence'].includes(row.disposition),'Unknown original ledger disposition');
  if(!['assigned','zero-cell'].includes(row.disposition))continue;
  const entry=legacy?legacyEntry:authorities.get(row.authority_sha256);demand(entry&&(!Object.hasOwn(row,'rule_sha256')||row.rule_sha256===entry.rule_sha256),'Per-component original authority rebound');
  demand(typeof row.target_id==='string'&&Number.isSafeInteger(row.pixelIndex)&&row.pixelIndex>0&&hash(row.base_geometry_sha256)&&hash(row.geometry_sha256)&&hash(row.source_receipt_sha256)&&valueSha(row.geometry)===row.geometry_sha256,'Missing complete original primitive identity');
  coordinateBounds(row.geometry);demand(Number.isSafeInteger(row.native_cells)&&(row.disposition==='assigned'?row.native_cells>0:row.native_cells===0),'False original native contribution');
  rows.set(row.component_id,{...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256});
 }
 return {rows,authorities,registry_sha256:valueSha(registry)};
}
export function compareVersionedRepairLedgers(before,after,{beforeRegistry,afterRegistry}) {
 const old=normaliseRetainedRepairLedger(before,beforeRegistry),next=normaliseRetainedRepairLedger(after,afterRegistry);
 for(const [id,entry]of old.authorities)demand(next.authorities.has(id)&&same(entry,next.authorities.get(id)),'Retained original authority removed/rebound');
 for(const [id,row]of old.rows)demand(next.rows.has(id)&&same(row,next.rows.get(id)),'Previously selected full component primitive/authority lost/rebound: '+id);
 return {preserved_components:old.rows.size,preserved_authorities:old.authorities.size,appended_authorities:next.authorities.size-old.authorities.size,limitations:['Registry and source bodies require independent committed-selector authentication; this comparison approves no appended row.']};
}

// Pure current-bank applicability stays in this already authenticated helper.
function rebindPolygonParts(g){coordinateBounds(g);return g.type==='Polygon'?[g.coordinates]:g.coordinates;}
function bits(value){const b=Buffer.allocUnsafe(8);b.writeDoubleBE(value);return b.toString('hex');}
function leastRotation(points){
  const n=points.length;let i=0,j=1,k=0;
  while(i<n&&j<n&&k<n){const a=points[(i+k)%n],b=points[(j+k)%n];
    if(a===b){k++;continue;}if(a>b){i+=k+1;if(i===j)i++;}else{j+=k+1;if(i===j)j++;}k=0;}
  const start=Math.min(i,j);return Array.from({length:n},(_,k)=>points[(start+k)%n]).join('');
}
function ringKey(ring){
  const points=ring.map(([x,y])=>bits(x)+bits(y));
  demand(points.length>=4&&points[0]===points.at(-1),'Ring binary64 closure changed');points.pop();
  const a=leastRotation(points),b=leastRotation([...points].reverse());return a<b?a:b;
}
function groupKey(polygon){return JSON.stringify([ringKey(polygon[0]),polygon.slice(1).map(ringKey).sort()]);}
export function preservedNativePolygonGroups(original,current){
  const old=rebindPolygonParts(original),next=rebindPolygonParts(current),remaining=new Map();
  for(const polygon of old){const key=groupKey(polygon);remaining.set(key,(remaining.get(key)??0)+1);}
  const added=[];
  for(const polygon of next){const key=groupKey(polygon),count=remaining.get(key)??0;
    if(count>0)remaining.set(key,count-1);else added.push({type:'Polygon',coordinates:polygon});}
  demand([...remaining.values()].every(count=>count===0),'Current bank loses/rebuilds an original full polygon group');
  return {preserved_polygons:old.length,added_polygons:added};
}
function conservativeBounds(geometry){
  const polygons=rebindPolygonParts(geometry),b=[Infinity,Infinity,-Infinity,-Infinity];let periodic=false;
  for(const polygon of polygons)for(const ring of polygon){
    for(let i=0;i<ring.length;i++){const [x,y]=ring[i];b[0]=Math.min(b[0],x);b[1]=Math.min(b[1],y);b[2]=Math.max(b[2],x);b[3]=Math.max(b[3],y);
      if(Math.abs(x)===180||(i&&Math.abs(x-ring[i-1][0])>180))periodic=true;}}
  if(periodic||b[2]-b[0]>180){b[0]=-180;b[2]=180;}
  return b;
}
export function requireDisjointAddedGeometry(original,current,primitives){
  demand(Array.isArray(primitives)&&primitives.length>0,'Missing complete retained primitives');
  const proof=preservedNativePolygonGroups(original,current);
  const additions=proof.added_polygons.map(conservativeBounds),candidates=primitives.map(conservativeBounds);
  for(const candidate of candidates)for(const addition of additions)
    demand(candidate[2]<addition[0]||addition[2]<candidate[0]||candidate[3]<addition[1]||addition[3]<candidate[1],
      'Current added polygon requires qualified exact continuous exclusion');
  return {preserved_polygons:proof.preserved_polygons,added_polygon_bounds:additions,primitive_bounds:candidates};
}

export function conserveCurrentNativeRows({originalPatches,currentRows,size}) {
  demand(Number.isSafeInteger(size)&&size>0&&Array.isArray(originalPatches)&&originalPatches.length>0,'Missing native rebind operands');
  const current=new Map();let previous=-1;
  const validate=(runs)=>{let end=0;demand(Array.isArray(runs),'Missing whole interval row');
    for(const run of runs){demand(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)
      &&run[0]>=end&&run[1]>run[0]&&run[1]<=size&&run[2]>0,'Invalid complete owner interval');end=run[1];}};
  for(const row of currentRows){demand(Number.isSafeInteger(row.y)&&row.y>previous&&row.y<size,'Duplicate/foreign current row');previous=row.y;
    validate(row.runs);current.set(row.y,row.runs);}
  const candidates=new Map();
  for(const patch of originalPatches){demand(patch.version===1&&patch.kind==='unassigned-native-cells-v1','Foreign original native patch');previous=-1;
    for(const row of patch.rows){demand(Number.isSafeInteger(row.y)&&row.y>previous&&row.y<size,'Invalid original row order');previous=row.y;validate(row.runs);
      demand(current.has(row.y),'Missing complete current native row');
      const all=candidates.get(row.y)??[];all.push(...row.runs.map(run=>[...run]));candidates.set(row.y,all);}}
  const rows=[...candidates].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>{
    runs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);const merged=[];
    for(const run of runs){const last=merged.at(-1);
      demand(!last||run[0]>=last[1]||run[2]===last[2],'Different retained component owners conflict');
      if(last&&run[2]===last[2]&&run[0]<=last[1])last[1]=Math.max(last[1],run[1]);else merged.push(run);}
    for(const run of merged)for(const old of current.get(y))demand(run[1]<=old[0]||run[0]>=old[1],'Original addition is already owned in current bank');
    return {y,runs:merged};});
  demand(current.size===candidates.size,'Current native window contains unrequested/missing rows');
  const effective=rows.map(row=>({y:row.y,runs:[...current.get(row.y).map(run=>[...run]),...row.runs.map(run=>[...run])].sort((a,b)=>a[0]-b[0])}));
  effective.forEach(row=>validate(row.runs));
  return {rows,current_rows:currentRows,effective_rows:effective,
    assigned_cells:rows.reduce((sum,row)=>sum+row.runs.reduce((n,run)=>n+run[1]-run[0],0),0)};
}

const rebindKeys=(v,w,m)=>demand(v&&Object.keys(v).sort().join(',')===w.split(',').sort().join(','),m);
export function nativeBaseSelection(selection) {
 demand(selection&&typeof selection==='object'&&!Array.isArray(selection),'Missing complete selected native identity');
 const {additive_release,...base}=selection;
 return base;
}

// Only the actual checker-consumed prior view can establish earlier additions.
// Conservation covers complete authority entries, primitives and exceptions;
// a caller-supplied prior ledger or an asserted qualified flag is insufficient.
export function requirePriorAdditiveConservation(snapshot,registry,ledger) {
 if(snapshot.selection.additive_release===undefined)return {prior_components:0,prior_authorities:0};
 const prior=snapshot.additive;
 demand(prior&&selectedAdditions.get(prior)?.snapshot===snapshot,
  'Require actual privately consumed prior additive selection');
 const proof=compareVersionedRepairLedgers(prior.ledger,ledger,{beforeRegistry:prior.registry,afterRegistry:registry});
 const byId=new Map(ledger.rows.map(row=>[row.component_id,row]));
 const literal=row=>{if(prior.ledger.version!==1)return row;const {authority_sha256,rule_sha256,...body}=row;return body;};
 for(const row of prior.ledger.rows)demand(byId.has(row.component_id)&&same(literal(byId.get(row.component_id)),literal(row)),
  'Previously selected complete row or exception changed');
 return {prior_components:proof.preserved_components,prior_authorities:proof.preserved_authorities};
}

export const CURRENT_REBIND_CODE=Object.freeze([
 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-geometry.mjs',
 'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-rebind.mjs',
 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
 'src/effective-footprint.js',
 'scripts/check-effective-geographic-regression.mjs',
 'src/ownership-codec.js',
 'package.json',
 'src/native-runtime.js',
 'scripts/native-ownership/compile-native-ownership.mjs',
 'src/native-grid.js',
 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/package.json',
 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/sha2.js',
 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/_md.js',
 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/_u64.js',
 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/utils.js',
 'scripts/audit-grid-intervals.mjs',
 'coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs',
 'coordination/engineering/additive-native-composition-20261009/run-current-rebind.mjs',
 'coordination/engineering/additive-native-composition-20261009/issue-current-rebind-execution.py',
 'coordination/engineering/additive-native-composition-20261009/supervise-current-rebind.py',
 'coordination/engineering/additive-native-composition-20261009/execution-contract.py',
 'coordination/engineering/additive-native-composition-20261009/owned-group-original.py',
 'coordination/engineering/additive-native-composition-20261009/owned-child-termination-original.py',
 'coordination/engineering/additive-native-composition-20261009/mac-execution-runtime-original.json',
 'coordination/engineering/additive-native-composition-20261009/execution-code-paths.json',
 'scripts/local-workspace.mjs',
 'scripts/worker-identity.mjs',
]);
export function currentRebindResult({baseSelection,registry,originalRows,originalPatches,currentTargets,currentRows,size}) {
 demand(Array.isArray(originalRows)&&originalRows.length>0&&Array.isArray(currentTargets)&&currentTargets.length>0,'Missing complete rebind geometry operands');
 const byTarget=new Map();let prior='';
 for(const target of currentTargets){rebindKeys(target,'target_id,pixelIndex,geometry,geometry_sha256','Foreign current target fields');
  demand(typeof target.target_id==='string'&&target.target_id>prior&&Number.isSafeInteger(target.pixelIndex)&&target.pixelIndex>0&&hash(target.geometry_sha256)&&valueSha(target.geometry)===target.geometry_sha256,'Foreign/duplicate/unordered current target');prior=target.target_id;byTarget.set(target.target_id,target);}
 const grouped=new Map();prior='';
 for(const row of originalRows){demand(row.component_id>prior&&['assigned','zero-cell'].includes(row.disposition),'Incomplete/unordered original supported rows');prior=row.component_id;
  const target=byTarget.get(row.target_id);demand(target&&target.pixelIndex===row.pixelIndex&&valueSha(row.base_geometry)===row.base_geometry_sha256&&valueSha(row.geometry)===row.geometry_sha256,'Original/current whole target identity differs');
  const members=grouped.get(row.target_id)??[];if(members.length)demand(same(members[0].base_geometry,row.base_geometry),'Conflicting original source bases for one target');members.push(row);grouped.set(row.target_id,members);}
 demand(grouped.size===byTarget.size,'Invented/unused current target');
 const geometry=currentTargets.map(target=>({target_id:target.target_id,...requireDisjointAddedGeometry(grouped.get(target.target_id)[0].base_geometry,target.geometry,originalRows.map(row=>row.geometry))}));
 const native=conserveCurrentNativeRows({originalPatches,currentRows,size});
 return {version:1,kind:'native-additive-current-bank-rebind-result-v1',base_selection:baseSelection,
  authority_registry_sha256:valueSha(registry),original_rows:originalRows,current_targets:currentTargets,
  original_patch_sha256s:originalPatches.map(valueSha),geometry,native,
  limits:['Current-bank applicability of unchanged original primitives only. Original source-relative policies remain unchanged; this result grants no physical authority or activation.']};
}
// These are retained external execution records, never a producer's qualified
// boolean. Full raw time/stdout and terminal/code custody are checked together.
export function verifyCurrentRebindExecution({request,operating,expectedCode,custody}) {
 demand(custody&&operating.execution_custody,'Missing complete external execution custody');
 const names=['code_source','terminal','stderr','stdout','issued_plan'];
 rebindKeys(operating.execution_custody,names.join(','),'Incomplete external execution roster');
 for(const name of names){const pin=operating.execution_custody[name];pinCheck(pin);demand(pin.decoded_bytes===undefined,'Execution custody must be whole ordinary bodies');const raw=custody[name];demand(Buffer.isBuffer(raw)&&raw.length===pin.bytes&&sha(raw)===pin.sha256,'External execution whole body differs: '+name);}
 demand(operating.execution_custody.code_source.bytes<=1048576&&operating.execution_custody.terminal.bytes<=131072&&operating.execution_custody.stderr.bytes<=40960&&operating.execution_custody.stdout.bytes<=8192&&operating.execution_custody.issued_plan.bytes<=1048576,'External execution metadata/log bound');
 const proof=JSON.parse(custody.code_source),terminal=JSON.parse(custody.terminal),output=JSON.parse(custody.stdout),plan=JSON.parse(custody.issued_plan);
 rebindKeys(request.execution,'command,pre_use','Missing issued actual execution contract');
 rebindKeys(proof,'version,kind,execution_commit,command,pre_use,post_use','Foreign whole execution source proof');
 demand(proof.version===1&&proof.kind==='whole-current-rebind-execution-custody-v1'&&proof.execution_commit===request.execution_commit&&same(proof.command,request.execution.command)&&same(proof.pre_use,request.execution.pre_use)&&same(proof.pre_use,proof.post_use),'Execution source/runtime changed before/after actual command');
 const before=proof.pre_use;rebindKeys(before,'runtime,code,entry,supervisor,plan','Incomplete actual executed closure');
 demand(same(before.code,expectedCode),'Whole actual executing code closure differs');
 const ordinary=(p,installedExecutable=false)=>{rebindKeys(p,'path,bytes,sha256,mode','Incomplete external executing body');demand(typeof p.path==='string'&&p.path.startsWith('/')&&!p.path.split('/').some((x,i)=>i>0&&(!x||x==='.'||x==='..'))&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&hash(p.sha256)&&(installedExecutable?[420,493,511]:[420,493]).includes(p.mode),'Unsafe/untyped external execution identity');};
 demand(Array.isArray(before.runtime)&&before.runtime.length>=4&&before.runtime.length<=512,'Missing complete actual runtime');const seen=new Set();let runtimeBytes=0;
 for(const p of before.runtime){rebindKeys(p,'role,path,bytes,sha256,mode','Foreign installed runtime identity');const {role,...body}=p;ordinary(body,['node','git','time','supervisor-python'].includes(role));demand(['node','git','time','supervisor-python','supervisor-stdlib','installed-dependency','process-inspector','resource-command'].includes(role)&&!seen.has(p.path),'Foreign/duplicate installed runtime');seen.add(p.path);runtimeBytes+=p.bytes;}
 demand(Number.isSafeInteger(runtimeBytes)&&runtimeBytes<request.limits.complete_phase_bytes&&['node','git','time','supervisor-python'].every(role=>before.runtime.filter(p=>p.role===role).length===1),'Incomplete installed runtime roles/complete admission');
 const dependencyRoot='coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/';
 const dependencies=expectedCode.filter(p=>p.path.startsWith(dependencyRoot));demand(dependencies.length===5&&before.runtime.filter(p=>p.role==='installed-dependency').length===5&&dependencies.every(p=>before.runtime.some(r=>r.role==='installed-dependency'&&r.path.endsWith('/node_modules/@noble/hashes/'+p.path.slice(dependencyRoot.length))&&r.bytes===p.bytes&&r.sha256===p.sha256&&r.mode===420)),'Actual installed hash import closure differs from whole source custody');
 for(const name of ['entry','supervisor','plan']){ordinary(before[name]);demand(before[name].bytes<=FILE,'Ordinary external body cap');}
 demand(before.plan.bytes===custody.issued_plan.length&&before.plan.sha256===sha(custody.issued_plan),'Actual invoked plan whole bytes differ');
 rebindKeys(plan,'version,kind,execution_commit,base_selection,authority_registry_sha256,original_rows_sha256,original_patch_sha256s,target_sources,predecessor_proof,executed_code,limits','Foreign actual issued plan');
 demand(plan.version===1&&plan.kind==='issued-current-rebind-acquisition-plan-v1'&&plan.execution_commit===request.execution_commit&&same(plan.base_selection,request.base_selection)&&plan.authority_registry_sha256===request.authority_registry_sha256&&plan.original_rows_sha256===valueSha(request.original_rows)&&same(plan.original_patch_sha256s,request.original_patch_sha256s)&&same(plan.target_sources,request.acquisition.target_sources)&&same(plan.predecessor_proof,request.acquisition.predecessor_proof)&&same(plan.executed_code,expectedCode)&&same(plan.limits,request.limits),'Actual cold issued input plan changes complete original/current operands or bounds');
 const command=proof.command;demand(Array.isArray(command)&&command.length===6&&command.every(p=>typeof p==='string')&&command[0]===before.runtime.find(p=>p.role==='time').path&&['-l','-v'].includes(command[1])&&command[2]===before.runtime.find(p=>p.role==='node').path&&command[3]===before.entry.path&&command[4]===before.plan.path&&command[5].startsWith('/')&&!command[5].split('/').some((x,i)=>i>0&&(!x||x==='.'||x==='..')),'Actual external command differs from bound runtime/entry/plan/destination');
 rebindKeys(terminal,'version,kind,execution_commit,command,request_sha256,publication_sha256,code_source_sha256,exit_code,signal,guard_reason,lifetime_rss_bytes,sampled_group_peak_bytes,sampled_stop_bytes,lifetime_ceiling_bytes,elapsed_seconds,wall_limit_seconds,owned_processes_remaining,termination_events','Foreign actual terminal roster');
 demand(terminal.version===1&&terminal.kind==='current-rebind-external-terminal-v1'&&terminal.execution_commit===request.execution_commit&&same(terminal.command,command)&&terminal.request_sha256===operating.request_sha256&&terminal.publication_sha256===operating.publication_sha256&&terminal.code_source_sha256===operating.execution_custody.code_source.sha256&&Number.isSafeInteger(terminal.exit_code)&&terminal.exit_code===0&&terminal.signal===null&&terminal.guard_reason===null&&Array.isArray(terminal.owned_processes_remaining)&&terminal.owned_processes_remaining.length===0&&Array.isArray(terminal.termination_events)&&terminal.termination_events.length===0,'Failed/foreign external command or surviving owned process');
 demand(Number.isSafeInteger(terminal.lifetime_rss_bytes)&&terminal.lifetime_rss_bytes>0&&terminal.lifetime_rss_bytes<=request.limits.rss_bytes&&Number.isFinite(terminal.elapsed_seconds)&&terminal.elapsed_seconds>=0&&terminal.elapsed_seconds<=request.limits.wall_seconds,'External actual lifetime/wall bound');
 demand(terminal.lifetime_rss_bytes===operating.lifetime_rss_bytes&&terminal.elapsed_seconds===operating.elapsed_seconds&&terminal.lifetime_ceiling_bytes===request.limits.rss_bytes&&terminal.wall_limit_seconds===request.limits.wall_seconds&&Number.isSafeInteger(terminal.sampled_stop_bytes)&&terminal.sampled_stop_bytes===request.limits.sampled_stop_bytes&&Number.isSafeInteger(terminal.sampled_group_peak_bytes)&&terminal.sampled_group_peak_bytes>0&&terminal.sampled_group_peak_bytes<terminal.sampled_stop_bytes,'External numeric journal differs from actual operating bounds');
 const stderr=custody.stderr.toString('utf8'),rss=command[1]==='-l'?[...stderr.matchAll(/^\s*(\d+)\s+maximum resident set size\s*$/gm)]:[...stderr.matchAll(/^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$/gm)];
 demand(rss.length===1&&Number(rss[0][1])*(command[1]==='-l'?1:1024)===terminal.lifetime_rss_bytes,'Raw external time lifetime RSS differs');
 const real=command[1]==='-l'?[...stderr.matchAll(/^\s*(\d+(?:\.\d+)?)\s+real\s+\d+(?:\.\d+)?\s+user\s+\d+(?:\.\d+)?\s+sys\s*$/gm)]:[...stderr.matchAll(/^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\d+(?::\d+){1,2}(?:\.\d+)?)\s*$/gm)];
 demand(real.length===1,'Missing/duplicate raw external time wall duration');
 const elapsed=real[0][1].split(':').reduce((n,x)=>n*60+Number(x),0);
 // External time prints centiseconds. The parent journal spans the entire
 // command; allow only that display rounding, not a relaxed wall deadline.
 demand(Number.isFinite(elapsed)&&elapsed>=0&&elapsed<=request.limits.wall_seconds&&elapsed<=terminal.elapsed_seconds+0.01,'Raw external time wall duration differs from actual journal/bound');
 rebindKeys(output,'version,kind,execution_commit,request_sha256,publication_sha256,result_sha256','Foreign actual child stdout');
 demand(output.version===1&&output.kind==='current-rebind-child-publication-v1'&&output.execution_commit===request.execution_commit&&output.request_sha256===operating.request_sha256&&output.publication_sha256===operating.publication_sha256&&output.result_sha256===custody.result_sha256,'Raw child publication/output identity differs');
 return {runtime:before.runtime,command,code_source_sha256:operating.execution_custody.code_source.sha256,terminal_sha256:operating.execution_custody.terminal.sha256};
}

// This checks complete products, not an asserted qualified flag. The selected
// reader supplies whole authenticated pins and actual trusted method bodies.
export function verifyCurrentRebindProducts({certificate,request,facts,publication,operating,result,baseSelection,registry,originalRows,originalPatches,size,expectedCode,bodyPins,acquired,executionCustody}) {
 for(const [name,body]of Object.entries({request,facts,publication,operating,result}))demand(body&&bodyPins[name]?.sha256===valueSha(body)&&bodyPins[name]?.bytes===valueBytes(body).length,'Whole canonical rebind product bytes differ: '+name);
 rebindKeys(certificate,'version,kind,execution_commit,base_selection,authority_registry_sha256,request,facts,publication,operating,result','Foreign current rebind certificate');
 demand(certificate.version===1&&/^[a-f0-9]{40}$/.test(certificate.execution_commit)&&certificate.execution_commit===request.execution_commit&&certificate.kind==='qualified-native-additive-current-bank-rebind-v1'&&same(certificate.base_selection,baseSelection)&&certificate.authority_registry_sha256===valueSha(registry),'Stale current rebind certificate');
 rebindKeys(request,'version,kind,execution_commit,executed_code,base_selection,authority_registry_sha256,original_rows,original_patch_sha256s,current_targets,current_rows,acquisition,execution,size,limits','Foreign issued rebind request');
 demand(request.version===1&&request.kind==='issued-native-additive-current-bank-rebind-v1'&&/^[a-f0-9]{40}$/.test(request.execution_commit)&&same(request.executed_code,expectedCode)&&same(request.base_selection,baseSelection)&&request.authority_registry_sha256===valueSha(registry)&&same(request.original_rows,originalRows)&&same(request.original_patch_sha256s,originalPatches.map(valueSha))&&request.size===size,'Issued rebind changes original authority, current base or trusted method');
 rebindKeys(request.limits,'complete_phase_bytes,descriptors,output_bytes,rss_bytes,sampled_stop_bytes,wall_seconds','Incomplete rebind operating limits');
 for(const k of Object.keys(request.limits))demand(Number.isSafeInteger(request.limits[k])&&request.limits[k]>0,'Untyped rebind limit');
 demand(request.limits.complete_phase_bytes<=268435456&&request.limits.descriptors<=512&&request.limits.output_bytes<=33554432&&request.limits.rss_bytes<=536870912&&request.limits.sampled_stop_bytes<=402653184&&request.limits.sampled_stop_bytes<=request.limits.rss_bytes,'Rebind admission exceeds existing bounds');
 demand(acquired&&same(acquired.base_selection,baseSelection)&&same(acquired.current_targets,request.current_targets)&&same(acquired.current_rows,request.current_rows),'Current operands differ from independently acquired selected bodies');
 rebindKeys(request.acquisition,'version,kind,target_sources,source_inputs,native_inputs,predecessor_proof,predecessor_rows,manifest_sha256','Incomplete current rebind acquisition custody');
 demand(request.acquisition.version===1&&request.acquisition.kind==='complete-selected-rebind-inputs-v1'&&same(request.acquisition,acquired.acquisition),'Issued acquisition is not the complete independently consumed source/native roster');
 demand(Array.isArray(acquired.acquisition_phases)&&acquired.acquisition_phases.length>0&&acquired.acquisition_phases.every(p=>Number.isSafeInteger(p.complete_phase_bytes)&&p.complete_phase_bytes>0&&p.complete_phase_bytes<=request.limits.complete_phase_bytes&&Number.isSafeInteger(p.descriptors)&&p.descriptors>0&&p.descriptors<=request.limits.descriptors),'Independent acquisition admission exceeds issued bounds');
 const expected=currentRebindResult({baseSelection,registry,originalRows,originalPatches,currentTargets:request.current_targets,currentRows:request.current_rows,size});
 demand(same(result,expected),'Complete current rebind result/inverse differs');
 rebindKeys(facts,'version,kind,execution_commit,request_sha256,result_sha256,complete_phase_bytes,descriptors,acquisition_sha256,acquisition_phases','Foreign rebind facts');
 demand(facts.version===1&&facts.kind==='native-additive-current-bank-rebind-facts-v1'&&facts.execution_commit===request.execution_commit&&facts.request_sha256===bodyPins.request.sha256&&facts.result_sha256===bodyPins.result.sha256&&Number.isSafeInteger(facts.complete_phase_bytes)&&facts.complete_phase_bytes>0&&facts.complete_phase_bytes<=request.limits.complete_phase_bytes&&Number.isSafeInteger(facts.descriptors)&&facts.descriptors>0&&facts.descriptors<=request.limits.descriptors,'Rebind facts do not bind actual request/result/admission');
 rebindKeys(publication,'version,kind,execution_commit,request_sha256,outputs','Foreign rebind publication');
 demand(facts.acquisition_sha256===valueSha(request.acquisition)&&Array.isArray(facts.acquisition_phases)&&facts.acquisition_phases.length===acquired.acquisition_phases.length&&facts.acquisition_phases.every((p,i)=>{const actual=acquired.acquisition_phases[i];const {complete_phase_bytes,descriptors,...scope}=p,{complete_phase_bytes:a,descriptors:b,...actualScope}=actual;return same(scope,actualScope)&&Number.isSafeInteger(complete_phase_bytes)&&complete_phase_bytes>0&&complete_phase_bytes<=request.limits.complete_phase_bytes&&Number.isSafeInteger(descriptors)&&descriptors>0&&descriptors<=request.limits.descriptors;}),'Original executed acquisition phases/whole input custody differ');
 demand(publication.version===1&&publication.kind==='native-additive-current-bank-rebind-publication-v1'&&publication.execution_commit===request.execution_commit&&publication.request_sha256===bodyPins.request.sha256&&same(publication.outputs,{facts:{path:'facts.json',bytes:bodyPins.facts.bytes,sha256:bodyPins.facts.sha256},result:{path:'result.json',bytes:bodyPins.result.bytes,sha256:bodyPins.result.sha256}}),'Incomplete rebind publication output bindings');
 rebindKeys(operating,'version,kind,execution_commit,request_sha256,publication_sha256,exit_code,signal,owned_processes_remaining,lifetime_rss_bytes,elapsed_seconds,execution_custody','Foreign rebind operating proof');
 demand(operating.version===1&&operating.kind==='native-additive-current-bank-rebind-operating-v1'&&operating.execution_commit===request.execution_commit&&operating.request_sha256===bodyPins.request.sha256&&operating.publication_sha256===bodyPins.publication.sha256&&Number.isSafeInteger(operating.exit_code)&&operating.exit_code===0&&operating.signal===null&&Array.isArray(operating.owned_processes_remaining)&&operating.owned_processes_remaining.length===0&&Number.isSafeInteger(operating.lifetime_rss_bytes)&&operating.lifetime_rss_bytes>0&&operating.lifetime_rss_bytes<=request.limits.rss_bytes&&Number.isFinite(operating.elapsed_seconds)&&operating.elapsed_seconds>=0&&operating.elapsed_seconds<=request.limits.wall_seconds,'Unqualified rebind operating custody');
 verifyCurrentRebindExecution({request,operating,expectedCode,custody:{...executionCustody,result_sha256:bodyPins.result.sha256}});
 demand(bodyPins.result.bytes<=request.limits.output_bytes,'Whole rebind output exceeds issued bound');
 return result;
}

// Decode the complete already-qualified Arctic window product. This is a
// word inverse and predecessor-conservation assertion, not a native operator.
export function retainedArcticNativeRows(proof) {
 demand(proof?.kind==='exact-selected-native-old-new-counterparty-proof'&&proof.full_owner_count===49625&&proof.checked_rows===60&&proof.unchanged_rows===262106&&proof.added_cells===141&&proof.removed_cells===0&&proof.reassigned_cells===0&&proof.source_approval===false&&proof.installation_ready===false&&Array.isArray(proof.windows)&&proof.windows.length===2,'Foreign/incomplete qualified Arctic predecessor');
 const out=[];let gains=0;
 for(const [i,w]of proof.windows.entries()){
  demand(w.row_start===(i?62146:48715)&&w.row_end===(i?62147:48774)&&Array.isArray(w.conservation)&&w.conservation.length===w.row_end-w.row_start,'Arctic predecessor window scope differs');
  const a=w.after;demand(a.size===262166&&a.coordinateBits===19&&a.method==='native-linear-evenodd-first-owner-v1'&&Array.isArray(a.rows)&&a.rows.length===(w.row_end-w.row_start)*2&&Array.isArray(a.runs)&&a.runs.length===a.total_runs*2,'Incomplete Arctic predecessor words');
  let offset=0;for(let y=w.row_start;y<w.row_end;y++){
   const j=y-w.row_start,count=a.rows[j*2+1],c=w.conservation[j];demand(a.rows[j*2]===offset&&Number.isSafeInteger(count)&&count>=0&&c.row===y&&Number.isSafeInteger(c.added_cells)&&c.added_cells>=0&&c.removed_cells===0&&c.reassigned_cells===0,'Arctic predecessor partition/conservation differs');
   const runs=[];let end=0;for(let k=offset*2;k<(offset+count)*2;k+=2){const x=a.runs[k],z=a.runs[k+1];demand(Number.isSafeInteger(x)&&x>=0&&x<=4294967295&&Number.isSafeInteger(z)&&z>=0&&z<=4294967295,'Untyped complete predecessor word');const run=[x&524287,(z&524287)+1,(x>>>19)+(z>>>19)*8192];demand(run[0]>=end&&run[1]>run[0]&&run[1]<=a.size&&run[2]>0&&run[2]<=49625,'Foreign predecessor owner/interval');end=run[1];runs.push(run);}
   out.push({y,runs});offset+=count;gains+=c.added_cells;
  }demand(offset*2===a.runs.length,'Omitted complete predecessor run words');
 }demand(gains===141&&out.length===60,'Omitted earlier Arctic gains');return out;
}

// Genuine current before-state acquisition. The original native row operator
// is never executed here: only complete selected words and source rows are read.
// A private selected resolver authenticates the bank; this API cannot select it.
export function acquireCurrentRebindOperands(snapshot,registry,originalRows,originalPatches,{targetSources,predecessorProof=null,carriedMetadataBytes=0}={}) {
 demand(snapshot?.reader instanceof ImmutableReader,'Require actual current selected reader');
 const resolver=new SelectedGeometrySources(snapshot),reader=snapshot.reader;
 demand(Number.isSafeInteger(carriedMetadataBytes)&&carriedMetadataBytes>=0&&carriedMetadataBytes<=PHASE,'Incomplete retained rebind reader metadata');
 // The private snapshot authenticates the selected base and optional additive
 // hook. Acquisition reads only its base manifest/source roster, never a delta.
 const baseSelection=nativeBaseSelection(snapshot.selection);
 const targets=new Map();for(const row of originalRows){demand(['assigned','zero-cell'].includes(row.disposition),'Unsupported original rebind row');const owner=snapshot.owners[row.pixelIndex-1];demand(owner?.id===row.target_id,'Current rebind target owner differs');targets.set(row.target_id,owner);}
 const phases=[],sourceInputs=[],nativeInputs=[],currentTargets=[];let predecessorRows=[];
 const bodyIdentity=({commit,...p})=>p;
 const sourceMetadata=valueBytes({bank:resolver.bank??null,paths:resolver.paths,sources:resolver.sources,release:resolver.release,replacements:[...resolver.replacements],image:resolver.image?{index:resolver.image.index,map:resolver.image.map}:null}).length;
 const retained=()=>carriedMetadataBytes+8*1024*1024+2*(snapshot.metadataBytes+sourceMetadata+valueBytes({registry,originalRows,originalPatches,currentTargets,sourceInputs,nativeInputs,predecessorRows,phases,receipt_provenance:snapshot.receiptProvenance??null,prior_acquisition_phases:snapshot.acquisitionPhases??null,reader_inventory:[...reader.inventory]}).length)+(snapshot.acquisition_buffer_bytes??0);
 const begin=extra=>{reader.metadataBytes=retained()+extra;reader.outputBytes=4*1024*1024;reader.phase();};
 // Each whole source frame completes before another starts. Only complete
 // selected targets and its exact whole input descriptor survive the frame.
 const sourceFrame=name=>{
  const actual=resolver.read(name),found=[];
  for(const feature of actual.collection.features){const id=feature.id??feature.properties?.id,owner=targets.get(id);if(!owner)continue;
   demand(sourceByTarget.get(id)===name&&feature.properties?.parent_id===owner.province_id,'Current target containing source/parent differs');coordinateBounds(feature.geometry);
   found.push({target_id:id,pixelIndex:owner.index,geometry:feature.geometry,geometry_sha256:valueSha(feature.geometry)});}
  return {found,input:{path:name,source:actual.source,whole_body_sha256:actual.whole_sha256,bytes:actual.body.length}};
 };
 // Explicit target-to-containing-source bindings avoid a world scan. The
 // actual whole selected bodies must contain every target exactly once; names
 // are never inferred from IDs, bounds or camera metadata.
 demand(Array.isArray(targetSources)&&targetSources.length===targets.size,'Missing complete target source bindings');
 const sourceByTarget=new Map();for(const entry of targetSources){rebindKeys(entry,'target_id,path','Foreign target source binding');demand(targets.has(entry.target_id)&&resolver.paths.includes(entry.path)&&!sourceByTarget.has(entry.target_id),'Foreign/duplicate target source');sourceByTarget.set(entry.target_id,entry.path);}
 const paths=resolver.paths.filter(name=>targetSources.some(entry=>entry.path===name));
 for(const name of paths){const declared=resolver.sources[resolver.paths.indexOf(name)];begin(declared.decoded_bytes??declared.bytes);const frame=sourceFrame(name);currentTargets.push(...frame.found);sourceInputs.push(frame.input);phases.push({kind:'complete-current-target-source',path:name,complete_phase_bytes:reader.used,descriptors:reader.charged.size});}
 currentTargets.sort((a,b)=>a.target_id.localeCompare(b.target_id));
 demand(currentTargets.length===targets.size&&new Set(currentTargets.map(t=>t.target_id)).size===targets.size,'Missing/duplicate complete current targets');
 const continuity=snapshot.manifest.provenance?.successor_continuation;
 if(continuity?.issue===1520){
  demand(continuity.selected_old_new_rows===60&&continuity.added_cells===141&&continuity.removed_cells===0&&continuity.reassigned_cells===0,'Foreign selected Arctic continuation');
  pinCheck(predecessorProof);demand(predecessorProof.bytes===1990604&&predecessorProof.sha256==='d8af3b2eaf77f4fa948c01937ccb107f3d7eaa833ea4bac1d4480c633d509794'&&predecessorProof.decoded_bytes===undefined,'Missing exact whole qualified Arctic predecessor proof');
  begin(2*predecessorProof.bytes);
  const predecessorFrame=()=>{let version=predecessorProof.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}const actual=reader.descriptor(predecessorProof.path,version);demand(actual.mode===predecessorProof.mode&&actual.git_blob_oid===predecessorProof.git_blob_oid&&actual.bytes===predecessorProof.bytes,'Predecessor whole original mode/OID/bytes differ');return retainedArcticNativeRows(JSON.parse(reader.read(predecessorProof.path,{version,expected:predecessorProof.sha256})));};
  predecessorRows=predecessorFrame();phases.push({kind:'complete-qualified-arctic-predecessor',path:predecessorProof.path,sha256:predecessorProof.sha256,complete_phase_bytes:reader.used,descriptors:reader.charged.size});
 }else demand(predecessorProof===null,'Invented predecessor conservation proof');
 const manifest=snapshot.manifest,root=snapshot.selection.manifest_path.slice(0,snapshot.selection.manifest_path.lastIndexOf('/')+1),image=snapshot.image;
 const load=pin=>{
  const name=root+pin.path,ordinary=reader.git('ls-tree','-z',reader.version,'--',name).length>0;
  const representations=pin.decoded_bytes*(ordinary?2:3);demand(reader.used+representations<=PHASE,'Current complete native representations exceed prospective bound');reader.used+=representations;
  if(!nativeInputs.some(p=>p.logical_path===name)){
   let custody;if(ordinary)custody={kind:'ordinary-native-body',pin:{...bodyIdentity(reader.descriptor(name)),sha256:pin.sha256}};
   else{demand(image instanceof NativeAssetImage,'Missing genuine selected native transport');const member=image.index.files.find(p=>p.path===pin.path);demand(member,'Missing complete native member');custody={kind:'selected-native-transport',index:manifest.native_asset_transport.index,member,fragments:image.index.parts.filter(p=>p.offset<member.offset+member.bytes&&member.offset<p.offset+p.decoded_bytes).map(p=>({...p,pin:bodyIdentity(reader.descriptor(image.directory+'/'+p.path))}))};}
   nativeInputs.push({logical_path:name,asset:pin,custody});
  }
  let encoded;if(ordinary)encoded=reader.read(name,{expected:pin.sha256,decoded:pin.decoded_bytes});
  else{demand(image instanceof NativeAssetImage,'Current native rebind requires selected ordinary or authenticated native image');encoded=image.logical(name,pin);}
  demand(encoded.length===pin.bytes&&sha(encoded)===pin.sha256,'Current native whole encoded body differs');
  const raw=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});demand(raw.length===pin.decoded_bytes,'Current native whole decoded body differs');
  const words=unshuffleOwnershipBytes(raw,pin.words),canonical=Buffer.alloc(words.byteLength);for(let i=0;i<words.length;i++)canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical)===pin.decoded_sha256,'Current native whole canonical words differ');return words;
 };
 const rowPins=manifest.parts.filter(p=>p.kind==='rows');demand(rowPins.length===1,'Unsupported split current row table');begin(0);const table=load(rowPins[0]);
 demand(table.length===manifest.size*2,'Incomplete current native row table');let offset=0;for(let y=0;y<manifest.size;y++){demand(table[y*2]===offset,'Current whole row partition differs');offset+=table[y*2+1];}demand(offset*2===manifest.runWords,'Current native row table omits runs');
 phases.push({kind:'complete-current-native-row-table',complete_phase_bytes:reader.used,descriptors:reader.charged.size});
 const neededRows=[...new Set(originalPatches.flatMap(p=>p.rows.map(row=>row.y)).concat(predecessorRows.map(row=>row.y)))].sort((a,b)=>a-b),currentRows=[],groups=new Map();
 for(const y of neededRows){demand(Number.isSafeInteger(y)&&y>=0&&y<manifest.size,'Foreign original row');const start=table[y*2]*2,end=start+table[y*2+1]*2;
  const parts=manifest.parts.filter(p=>p.kind==='runs'&&start<p.offset+p.words&&p.offset<end),key=valueSha(parts);
  if(!groups.has(key))groups.set(key,{parts,rows:[]});groups.get(key).rows.push({y,start,end});}
 // A whole containing-roster frame completes once for all its requested rows.
 // Only full primitive row intervals survive; decoded buffers do not escape.
 const groupFrame=group=>{
  const cache=new Map(group.parts.map(pin=>[pin.path,load(pin)]));
  return group.rows.map(({y,start,end})=>{const runs=[];for(const pin of group.parts){const words=cache.get(pin.path);for(let i=Math.max(start,pin.offset);i<Math.min(end,pin.offset+pin.words);i+=2){const x=words[i-pin.offset],z=words[i-pin.offset+1],bits=manifest.coordinateBits,mask=2**bits-1;const run=[x&mask,(z&mask)+1,(x>>>bits)+(z>>>bits)*2**(32-bits)];demand(run[1]<=manifest.size&&snapshot.owners[run[2]-1],'Current row has foreign coordinate/owner');runs.push(run);}}
   demand(runs.length===table[y*2+1],'Incomplete current containing word inverse');return {y,runs};});
 };
 for(const group of groups.values()){begin(table.byteLength+2*valueBytes(currentRows).length);
  const rowReserve=group.rows.reduce((n,{y})=>n+table[y*2+1]*24+64,0);demand(reader.used+rowReserve<=PHASE,'Current complete row output exceeds phase');reader.used+=rowReserve;
  const rows=groupFrame(group);currentRows.push(...rows);phases.push({kind:'complete-current-native-window-group',rows:group.rows.map(row=>row.y),parts:group.parts.map(pin=>pin.path),complete_phase_bytes:reader.used,descriptors:reader.charged.size});
 }
 currentRows.sort((a,b)=>a.y-b.y);
 const candidateIds=new Set(originalPatches.flatMap(p=>p.rows.map(row=>row.y))),candidateRows=currentRows.filter(row=>candidateIds.has(row.y));
 demand(predecessorRows.every(prior=>same(prior,currentRows.find(row=>row.y===prior.y))),'Current native bank loses/reassigns a complete earlier Arctic row');
 const result=currentRebindResult({baseSelection,registry,originalRows,originalPatches,currentTargets,currentRows:candidateRows,size:manifest.size});
 return freeze({base_selection:baseSelection,current_targets:currentTargets,current_rows:candidateRows,source_inputs:sourceInputs,acquisition:{version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:targetSources,source_inputs:sourceInputs,native_inputs:nativeInputs,predecessor_proof:predecessorProof,predecessor_rows:predecessorRows,manifest_sha256:valueSha(manifest)},acquisition_phases:phases,input_inventory:[...reader.inventory.values()],result,
  limits:['Actual selected before-state acquisition and exact applicability only. Original registry/source/native authority must also be authenticated by the committed reader; no activation or physical approval.','External cold operating qualification and repeated whole outputs remain mandatory before publishing a current_rebind certificate.']});
}

// A current rebind is complete data custody plus independently recomputed
// applicability. It never replaces the original registry/source authority.
export function readCurrentRebindCustody(reader,pin,{baseSelection,registry,originalRows,originalPatches,size,snapshot,carriedMetadataBytes=0}) {
 demand(reader instanceof ImmutableReader,'Require actual immutable custody reader');
 demand(snapshot?.reader===reader,'Current rebind custody requires the actual privately authenticated selected snapshot');
 demand(Number.isSafeInteger(carriedMetadataBytes)&&carriedMetadataBytes>=0&&carriedMetadataBytes<=PHASE,'Untyped retained rebind metadata');
 rebindKeys(pin,'commit,path,mode,git_blob_oid,bytes,sha256','Foreign ordinary current rebind pin');pinCheck(pin);demand(pin.decoded_bytes===undefined&&reader.used+2*pin.bytes<=PHASE,'Whole current rebind certificate exceeds prospective bound');reader.used+=2*pin.bytes;
 const descriptor=reader.descriptor(pin.path,pin.commit);demand(descriptor.mode===pin.mode&&descriptor.git_blob_oid===pin.git_blob_oid&&descriptor.bytes===pin.bytes,'Whole rebind certificate identity differs');
 const certificate=reader.json(pin.path,{version:pin.commit,expected:pin.sha256});
 demand(Object.keys(certificate).sort().join(',')==='authority_registry_sha256,base_selection,execution_commit,facts,kind,operating,publication,request,result,version','Foreign current rebind certificate roster');
 const names=['request','facts','publication','operating','result'];
 const roster=names.map(name=>{const p=certificate[name];pinCheck(p);demand(p.decoded_bytes===undefined,'Current rebind products require ordinary whole JSON');return {name,p};});
 const metadata=roster.reduce((n,{p})=>n+2*p.bytes,0)+2*pin.bytes;
 demand(reader.used+metadata<=PHASE,'Complete current rebind custody admission before body opens');reader.used+=metadata;
 for(const {p}of roster){const actual=reader.descriptor(p.path,p.commit);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Whole rebind product mode/OID/length differs');reader.admit(actual);}
 demand(/^[a-f0-9]{40}$/.test(certificate.execution_commit),'Missing actual rebind execution identity');
 const code=CURRENT_REBIND_CODE.map(path=>reader.descriptor(path));
 const historicalCode=CURRENT_REBIND_CODE.map(path=>reader.descriptor(path,certificate.execution_commit));
 for(const p of [...code,...historicalCode])reader.admit(p);
 const expectedCode=code.map(p=>({path:p.path,bytes:p.bytes,sha256:sha(reader.read(p.path))}));
 const bodies=Object.fromEntries(roster.map(({name,p})=>[name,JSON.parse(reader.read(p.path,{version:p.commit,expected:p.sha256}))]));
 // The historical execution code must be whole-byte identical to the actual
 // trusted method. Current unrelated wrapper vintages are not relabelled.
 for(const expected of expectedCode){const actual=historicalCode.find(p=>p.path===expected.path);demand(actual.bytes===expected.bytes,'Historical rebind method size differs');reader.read(actual.path,{version:actual.commit,expected:expected.sha256});}
 demand(snapshot?.reader===reader,'Current rebind custody requires the actual privately authenticated selected snapshot');
 const externalNames=['code_source','terminal','stderr','stdout','issued_plan'];rebindKeys(bodies.operating.execution_custody,externalNames.join(','),'Incomplete external execution roster');
 const externalRoster=externalNames.map(name=>({name,p:bodies.operating.execution_custody[name]}));
 for(const {p}of externalRoster){pinCheck(p);demand(p.decoded_bytes===undefined,'External execution whole ordinary custody required');}
 const externalCaps={code_source:1048576,terminal:131072,stderr:40960,stdout:8192,issued_plan:1048576};
 for(const {name,p}of externalRoster)demand(p.bytes<=externalCaps[name],'External metadata/log cap before read');
 const externalBytes=externalRoster.reduce((n,{p})=>n+2*p.bytes,0);demand(reader.used+externalBytes<=PHASE,'Complete external execution custody before opens');reader.used+=externalBytes;
 for(const {p}of externalRoster){const actual=reader.descriptor(p.path,p.commit);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'External execution ordinary identity differs');reader.admit(actual);}
 const executionCustody=Object.fromEntries(externalRoster.map(({name,p})=>[name,reader.read(p.path,{version:p.commit,expected:p.sha256})]));
 verifyCurrentRebindExecution({request:bodies.request,operating:bodies.operating,expectedCode,custody:{...executionCustody,result_sha256:roster.find(p=>p.name==='result').p.sha256}});
 const liveMetadata=carriedMetadataBytes+2*(valueBytes({certificate,bodies,code,historicalCode,roster,externalRoster}).length+externalBytes);

 const acquired=acquireCurrentRebindOperands(snapshot,registry,originalRows,originalPatches,{targetSources:bodies.request.acquisition?.target_sources,predecessorProof:bodies.request.acquisition?.predecessor_proof,carriedMetadataBytes:liveMetadata});
 return verifyCurrentRebindProducts({certificate,...bodies,baseSelection,registry,originalRows,originalPatches,size,expectedCode,acquired,executionCustody,bodyPins:Object.fromEntries(roster.map(({name,p})=>[name,p]))});
}

// Explicit committed data-only hook. This does not discover proposal files.
export function readSelectedAdditive(snapshot) {
 const {reader,selection,manifest,owners}=snapshot,hook=selection.additive_release;
 if(hook===undefined)return null;
 demand(hook&&Object.keys(hook).sort().join(',')==='bytes,path,sha256'&&Number.isSafeInteger(hook.bytes)&&hook.bytes>0&&hook.bytes<=FILE&&hash(hook.sha256),'Unsupported committed additive hook');
 const descriptor=reader.descriptor(hook.path);demand(descriptor.bytes===hook.bytes,'Committed additive sidecar whole length differs');
 const sidecar=reader.json(hook.path,{expected:hook.sha256});
 demand(sidecar?.version===2&&sidecar.kind==='retained-native-additive-selection-v2'&&Object.keys(sidecar).sort().join(',')==='authority_registry,base_selection,kind,logical_asset_map,runtime_envelope,version','Unsupported committed additive sidecar');
 const baseSelection=nativeBaseSelection(selection);
 demand(same(sidecar.base_selection,baseSelection),'Stale/foreign actual native base selection');
 const whole=p=>{
  pinCheck(p);let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Selected additive ordinary whole identity differs');
  reader.admit(actual,p.decoded_bytes??0);return {p,version};
 };
 demand(Object.keys(sidecar.logical_asset_map).sort().join(',')==='base_manifest,ledger,owner_roster,patch','Incomplete/foreign logical additive asset map');
 const roster=[sidecar.runtime_envelope,sidecar.authority_registry,...Object.values(sidecar.logical_asset_map)];
 const metadata=roster.reduce((n,p)=>n+2*(p.bytes+(p.decoded_bytes??0)),0);demand(Number.isSafeInteger(metadata)&&metadata<=PHASE&&reader.used+metadata<=PHASE,'Complete selected additive metadata admission before reads');reader.used+=metadata;
 const admitted=roster.map(whole),bodies=admitted.map(({p,version})=>{
  const raw=reader.read(p.path,{version,expected:p.sha256,decoded:p.decoded_bytes??0});if(p.decoded_bytes===undefined)return JSON.parse(raw);
  const decoded=gunzipSync(raw,{maxOutputLength:p.decoded_bytes});demand(decoded.length===p.decoded_bytes&&sha(decoded)===p.decoded_sha256,'Selected additive whole decoded inverse differs');return JSON.parse(decoded);
 });
 const [wrapped,registry,...assets]=bodies,envelope=wrapped.additiveRelease??wrapped;
 demand(envelope&&Object.keys(envelope).sort().join(',')==='base_manifest,base_reference,effective_reference,kind,ledger,owner_roster,patch,version'&&([1,2].includes(envelope.version))&&envelope.kind===(envelope.version===1?'retained-native-base-plus-delta-v1':'retained-native-base-plus-delta-v2'),'Unsupported explicit additive runtime envelope');
 const named=Object.fromEntries(Object.keys(sidecar.logical_asset_map).map((k,i)=>[k,assets[i]]));
 for(const key of Object.keys(named)){
  const p=sidecar.logical_asset_map[key],declared=envelope[key];
  demand(declared&&p.bytes===declared.bytes&&p.sha256===declared.sha256&&(p.decoded_bytes??p.bytes)===(declared.decoded_bytes??declared.bytes)&&(p.decoded_sha256??p.sha256)===(declared.decoded_sha256??declared.sha256),'Runtime logical asset differs from committed ordinary pin: '+key);
 }
 demand(sidecar.logical_asset_map.base_manifest.sha256===selection.sha256&&same(named.base_manifest,manifest),'Additive runtime rebinds actual selected native manifest');
 demand(sidecar.logical_asset_map.owner_roster.sha256===manifest.original_assets.bounds.sha256&&same(named.owner_roster,owners),'Additive owner roster differs from independent original native bounds');
 let resolver=snapshot.geometrySources;
 if(!resolver){
  // The source-bank metadata has been completely authenticated in this stage.
  // Retain its actual view for later whole-source phases; do not reopen it while
  // the current acquisition's complete input charges are still resident.
  resolver=new SelectedGeometrySources(snapshot);snapshot.geometrySources=resolver;
  const retainedSourceMetadata=valueBytes({...(resolver.bank?{bank:resolver.bank}:{}),sources:resolver.sources,release:resolver.release}).length;
  demand(reader.used+retainedSourceMetadata<=PHASE,'Complete selected source metadata exceeds acquisition phase');
  reader.used+=retainedSourceMetadata;reader.metadataBytes+=retainedSourceMetadata;snapshot.metadataBytes+=retainedSourceMetadata;
 }
 demand(envelope.base_reference.id===selection.release_id&&envelope.base_reference.footprints_sha256===resolver.release.footprints_sha256,'Additive effective baseline differs from actual selected source bank');
 const normalized=normaliseRetainedRepairLedger(named.ledger,registry),proofs=[];
 let retained=metadata;
 for(const entry of registry.entries){
  demand(entry.policy_id==='retained-source-literal-additions'&&entry.policy_version===1,'Unsupported source policy semantics/version');
  // Previous acquisition bodies have been discarded. Only the complete selected
  // metadata/proof views are live across genuine detached authority phases.
  const child=new ImmutableReader(reader.repo,reader.version,{runtimeBytes:reader.runtimeBytes,executionBytes:reader.executionBytes,outputBytes:4*1024*1024,metadataBytes:reader.metadataBytes+retained,gitExecutable:reader.gitExecutable});
  const proof=readRetainedRegistryAuthority(child,entry);
  demand(valueBytes(proof).length<=child.outputBytes,'Complete detached authority view exceeds prospective output reserve');
  for(const row of normalized.rows.values())if(row.authority_sha256===entry.authority_sha256){
   const original=proof.original_ledger.rows.find(r=>r.component_id===row.component_id);
   demand(original&&['assigned','zero-cell'].includes(original.disposition)&&same({...original,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256},row),'Selected component rebinds original full native/source primitive');
  }
  const view={authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256,source_scope_ids:proof.source_scope_ids,native_proof:proof.native_proof,original_ledger:proof.original_ledger,pins:proof.pins,original_pins:proof.original_pins};proofs.push(view);retained+=valueBytes(view).length;
 }

 const expectedScope=new Map();
 for(const proof of proofs){
  demand(same(named.ledger.parent_inventory,proof.original_ledger.parent_inventory),'Selected ledger changes complete original inventory denominator');
  for(const original of proof.original_ledger.rows){
   demand(!expectedScope.has(original.component_id),'Ambiguous repeated original authority component');expectedScope.set(original.component_id,{original,proof});
  }
 }
 demand(named.ledger.rows.length===expectedScope.size&&named.ledger.scope_ids.every(id=>expectedScope.has(id)),'Selected ledger omits/invents complete original native scope or exceptions');
 for(const row of named.ledger.rows){const {original,proof}=expectedScope.get(row.component_id);
  if(named.ledger.version===1)demand(same(row,original),'Selected original v1 row rebound');
  else{const {authority_sha256,rule_sha256,...literal}=row;demand(authority_sha256===proof.authority_sha256&&(rule_sha256===undefined||rule_sha256===proof.rule_sha256)&&same(literal,original),'Selected v2 row rebinds original full primitive/exception authority');}
 }
 demand(normalized.rows.size>0,'Selected additive hook contains no effective primitives');

 const reference=r=>demand(r&&Object.keys(r).sort().join(',')==='footprints_sha256,hierarchy_sha256,id'&&typeof r.id==='string'&&r.id.startsWith('geography:')&&hash(r.footprints_sha256)&&hash(r.hierarchy_sha256),'Unsupported complete effective reference');
 reference(envelope.base_reference);reference(envelope.effective_reference);
 demand(envelope.base_reference.hierarchy_sha256===resolver.release.hierarchy_sha256&&envelope.effective_reference.hierarchy_sha256===envelope.base_reference.hierarchy_sha256,'Effective release silently changes selected hierarchy');
 if(envelope.version===1)demand(proofs.length===1&&proofs[0].native_proof.native_patches.every(p=>same(p.effective_reference,envelope.effective_reference)),'Selected original v1 effective reference rebound');
 else demand(envelope.effective_reference.footprints_sha256===valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:envelope.base_reference,authority_registry_sha256:valueSha(registry),ledger_sha256:sidecar.logical_asset_map.ledger.sha256,components:[...normalized.rows.values()]}),'Selected explicit v2 effective domain differs from complete authority/component set');
 const patch=named.patch;
 demand(patch&&Object.keys(patch).sort().join(',')===(patch.version===1?'base_reference,effective_reference,kind,ledger_sha256,rows,rule_sha256,version':'authority_registry_sha256,base_reference,effective_reference,kind,ledger_sha256,rows,version')&&patch.kind==='unassigned-native-cells-v1'&&same(patch.base_reference,envelope.base_reference)&&same(patch.effective_reference,envelope.effective_reference)&&patch.ledger_sha256===sidecar.logical_asset_map.ledger.sha256,'Stale/foreign native additive patch');
 demand(named.ledger.version===1?patch.version===1&&patch.rule_sha256===named.ledger.rule_sha256:patch.version===2&&patch.authority_registry_sha256===valueSha(registry),'Native delta rule/registry binding differs');
 const selectedOwners=new Set([...normalized.rows.values()].map(r=>{demand(owners[r.pixelIndex-1]?.id===r.target_id,'Selected primitive owner identity differs');return r.pixelIndex;}));
 demand(Array.isArray(patch.rows),'Missing complete native delta rows');let previous=-1,total=0;
 for(const row of patch.rows){demand(row&&Object.keys(row).sort().join(',')==='runs,y'&&Number.isSafeInteger(row.y)&&row.y>previous&&row.y<manifest.size,'Foreign/duplicate/unordered delta row');previous=row.y;let end=0;
  for(const run of row.runs){demand(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end&&run[1]>run[0]&&run[1]<=manifest.size&&selectedOwners.has(run[2]),'Conflicting/foreign native delta interval');end=run[1];total+=run[1]-run[0];}
 }
 const originalPatches=proofs.flatMap(proof=>proof.native_proof.native_patches);
 let rebind=null;
 if(Object.hasOwn(named.ledger,'current_rebind')){
  demand(named.ledger.version===2&&envelope.version===2,'Current rebind is an explicit v2-only extension');
  const currentContract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,manifest[k]]));
  demand(proofs.every(p=>same(p.native_proof.native_contract,currentContract)),'Current rebind changes original native lattice/method/owner-parent contract');
  rebind=readCurrentRebindCustody(reader,named.ledger.current_rebind,{baseSelection,registry,originalRows:[...normalized.rows.values()],originalPatches,size:manifest.size,snapshot,carriedMetadataBytes:2*valueBytes({sidecar,admitted,bodies,envelope,named,proofs,patch}).length});
  demand(same(named.ledger.current_targets,rebind.current_targets),'Ledger current target pointsets differ from complete qualified rebind result');
 }else demand(!Object.hasOwn(named.ledger,'current_targets'),'Current targets require complete rebind custody');
 const expectedByRow=new Map();
 for(const original of originalPatches){
  demand(rebind||same(original.base_reference,envelope.base_reference),'Original delta requires an actual qualified current-bank rebind');
  for(const row of original.rows){const all=expectedByRow.get(row.y)??[];all.push(...row.runs.map(r=>[...r]));expectedByRow.set(row.y,all);}
 }
 const expectedRows=[...expectedByRow].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>{
  runs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);const merged=[];
  for(const run of runs){const last=merged.at(-1);if(last&&run[0]<last[1])demand(run[2]===last[2],'Different original authority native patches conflict');if(last&&run[2]===last[2]&&run[0]<=last[1])last[1]=Math.max(last[1],run[1]);else merged.push(run);}
  return {y,runs:merged};
 });
 demand(same(patch.rows,expectedRows),'Selected native patch omits/invents original qualified assignment cells');
 // Current-bank target pointsets and zero-owned native exclusion are checked by
 // the actual affected-source/interval callers, never inferred from this delta.
 // The whole encoded/decoded acquisition remains charged above while this
 // helper owns its body arrays. After return those arrays (including the second
 // owner-roster decode) are dead; only this complete view is carried onward.
 // The independently authenticated original owner roster remains in snapshot.
 const consumerRows=[...normalized.rows.values()].map(row=>{if(!rebind)return row;const target=rebind.current_targets.find(target=>target.target_id===row.target_id);demand(target&&owners[target.pixelIndex-1]?.id===target.target_id,'Current rebind owner roster differs');return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};});
 const carried={sidecar,registry,ledger:named.ledger,patch,envelope,normalized_rows:consumerRows,authority_proofs:proofs,assigned_cells:total,...(rebind?{current_rebind:rebind}:{})};
 const result=freeze({...carried,metadata_bytes:valueBytes(carried).length+4096});
 selectedAdditions.set(result,{snapshot});return result;
}
export function selectedAdditiveRows(view,row,base) {
 demand(selectedAdditions.has(view),'Require actual committed authenticated additive selection');
 const delta=view.patch.rows.find(r=>r.y===row)?.runs??[];
 if(view.current_rebind&&delta.length){const expected=view.current_rebind.native.current_rows.find(r=>r.y===row);demand(expected&&same(expected.runs,base),'Actual selected complete native row differs from qualified current rebind');}
 const all=[...base.map(r=>[...r]),...delta.map(r=>[...r])].sort((a,b)=>a[0]-b[0]);let end=0;
 for(const r of all){demand(r[0]>=end,'Selected additive delta overlaps preexisting assigned native cells');end=r[1];}
 return all;
}
