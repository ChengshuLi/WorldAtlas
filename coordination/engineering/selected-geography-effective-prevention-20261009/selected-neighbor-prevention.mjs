// #1569 prevention helper. Input pins/binding must be derived by the trusted
// selected-bank resolver. These functions do not select/activate a release.
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader, SelectedGeometrySources, NativeAssetImage, selectedBaseAssetAlias, selectedGeometrySourceAlias, selectedReferenceOwners, selectedNativeSourceMembership} from '../../../scripts/check-effective-geographic-regression.mjs';
import {nativeOnlyComponent, deriveSourceTargetNativeDelta, nativePolygonIntervals, polygonParts, witnessCellEffects, validateWitnessGeometry} from '../../../src/native-grid.js';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {scientificNativeSelection} from '../../../src/reference-metadata.js';
const certificates=new WeakMap(), originalAuthorities=new WeakMap(), selectedAdditions=new WeakMap();
// Original accepted source/native programs. Case rosters are not policy IDs.
// Changing a complete program requires ordinary trusted-code/rule review.
const PROGRAMME_CATALOGUE='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const PROGRAMME_MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
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
// The executing checkout supplies policy authority. reader.version can be an
// untrusted candidate and therefore must never choose the catalogue. Policy is
// ordinary consumed data, separately inventoried from the executed code.
export function validateSupportedProgrammeCatalogue(catalogue) {
 demand(catalogue&&Object.keys(catalogue).sort().join(',')==='current_rebind_migrations,kind,programs,version'
  &&catalogue.version===1&&catalogue.kind==='trusted-source-native-programmes-v1'
  &&Array.isArray(catalogue.programs)&&catalogue.programs.length>0
  &&Array.isArray(catalogue.current_rebind_migrations),'Malformed trusted programme catalogue');
 const vector=rows=>{demand(Array.isArray(rows)&&rows.length>0&&new Set(rows.map(p=>p?.path)).size===rows.length,'Incomplete/duplicate programme code vector');
  for(const p of rows)demand(p&&Object.keys(p).sort().join(',')==='bytes,path,sha256'&&typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..')&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&hash(p.sha256),'Malformed programme code descriptor');};
 const keys=new Set();
 for(const p of catalogue.programs){
  demand(p&&Object.keys(p).sort().join(',')==='accepted_head,independent_review_comment,native_executed_code,preimage_version,source_executed_code,source_profile'
   &&[2,3].includes(p.preimage_version)&&(p.source_profile===null||typeof p.source_profile==='string'&&p.source_profile.length>0)
   &&/^[a-f0-9]{40}$/.test(p.accepted_head)&&Number.isSafeInteger(p.independent_review_comment)&&p.independent_review_comment>0,'Malformed reviewed programme');
  vector(p.source_executed_code);vector(p.native_executed_code);
  const key=valueSha([p.preimage_version,p.source_profile,p.source_executed_code,p.native_executed_code]);demand(!keys.has(key),'Ambiguous programme registration');keys.add(key);
 }
 const migrations=new Set();
 for(const p of catalogue.current_rebind_migrations){
  demand(p&&Object.keys(p).sort().join(',')==='current_code,execution_commit,historical_code,independent_review_comment'
   &&/^[a-f0-9]{40}$/.test(p.execution_commit)&&Number.isSafeInteger(p.independent_review_comment)&&p.independent_review_comment>0,'Malformed exact rebind migration');
  vector(p.historical_code);vector(p.current_code);
  currentRebindCodePaths(p.historical_code);currentRebindCodePaths(p.current_code);
  demand(!same(p.historical_code,p.current_code),'Incomplete/identity rebind migration');
  const key=valueSha([p.execution_commit,p.historical_code,p.current_code]);demand(!migrations.has(key),'Ambiguous exact rebind migration');migrations.add(key);
 }
 return catalogue;
}
export function readSupportedProgrammeCatalogue(reader) {
 demand(reader instanceof ImmutableReader,'Require actual immutable policy reader');
 const moduleRoot=fileURLToPath(new URL('../../../',import.meta.url));
 const version=execFileSync(reader.gitExecutable,['-c','core.hooksPath=/dev/null','-C',moduleRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 demand(/^[a-f0-9]{40}$/.test(version),'Missing executing trusted policy checkout');
 const modulePin=reader.descriptor(PROGRAMME_MODULE,version);
 const moduleBody=fs.readFileSync(fileURLToPath(import.meta.url));
 demand(moduleBody.length===modulePin.bytes&&sha(moduleBody)===sha(reader.read(PROGRAMME_MODULE,{version})),'Executing policy helper differs from trusted checkout');
 const descriptor=reader.descriptor(PROGRAMME_CATALOGUE,version);
 demand(descriptor.mode==='100644','Trusted policy body must be an ordinary file');
 const body=reader.read(PROGRAMME_CATALOGUE,{version});
 return {catalogue:validateSupportedProgrammeCatalogue(JSON.parse(body)),pin:{...reader.inventory.get(version+':'+PROGRAMME_CATALOGUE)}};
}
export function matchSupportedProgramme(catalogue,{preimageVersion,sourceProfile,sourceCode,nativeCode}) {
 validateSupportedProgrammeCatalogue(catalogue);
 const methods=catalogue.programs.filter(p=>p.preimage_version===preimageVersion&&p.source_profile===sourceProfile);
 // Each complete executed closure needs its own historical admission. Pairing
 // two already reviewed closures does not create a new method registration.
 const source=methods.find(p=>same(sourceCode,p.source_executed_code));
 const native=methods.find(p=>same(nativeCode,p.native_executed_code));
 demand(source&&native,'Unknown/ambiguous original source/native policy program closure');return {source,native};
}

// Only the compact reviewed authority escapes the catalogue lookup.
export function readSupportedProgrammeAuthority(reader,request) {
 const policy=readSupportedProgrammeCatalogue(reader),supported=matchSupportedProgramme(policy.catalogue,request);
 const review=p=>({accepted_head:p.accepted_head,independent_review_comment:p.independent_review_comment});
 const authority={source:review(supported.source),native:review(supported.native),catalogue:policy.pin};
 return authority;
}

function pinCheck(p){
 demand(p&&/^[a-f0-9]{40}$/.test(p.commit)&&['100644','100755'].includes(p.mode)&&/^[a-f0-9]{40}$/.test(p.git_blob_oid),'Missing immutable body identity');
 demand(typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..'),'Unsafe immutable path');
 demand(Number.isSafeInteger(p.bytes)&&p.bytes>=0&&hash(p.sha256),'Ordinary encoded body size/hash');
 if(p.decoded_bytes!==undefined)demand(Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>=0&&hash(p.decoded_sha256),'Ordinary decoded body size/hash');
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
export function selectedCoordinateShard(resolver,sourcePaths,{priorShards=[],onFeature}={}) {
 demand(resolver instanceof SelectedGeometrySources&&Array.isArray(sourcePaths)&&sourcePaths.length>0&&new Set(sourcePaths).size===sourcePaths.length,'Require actual selected source resolver and unique whole containing scope');
 demand(sourcePaths.every(p=>resolver.paths.includes(p)),'Foreign selected source shard');
 const snapshot=resolver.snapshot;
 const binding={version:1,kind:'selected-complete-coordinate-binding-v1',selection:snapshot.selection,release:resolver.release,
   sources:resolver.sources,owners_sha256:valueSha(selectedReferenceOwners(snapshot)),coordinate_domain:'complete-original-pointset-bounds:v1'};
 for(const shard of priorShards)demand(certificates.has(shard)&&same(shard.binding,binding),'Unqualified or foreign retained coordinate shard');
 const roster=new Map(selectedReferenceOwners(snapshot).map(r=>[r.id,r])),entries=[],seen=new Set(),inputFacts=[];
 for(const name of sourcePaths){
  const actual=resolver.read(name);inputFacts.push({path:name,source:actual.source,whole_body_sha256:actual.whole_sha256,bytes:actual.body.length});
  for(let ordinal=0;ordinal<actual.collection.features.length;ordinal++){
   const f=actual.collection.features[ordinal],id=f.id??f.properties?.id,owner=roster.get(id);
   demand(f.type==='Feature'&&owner&&!seen.has(id)&&f.properties?.parent_id===owner.province_id,'Foreign/duplicate/misparented whole selected row');seen.add(id);
   const additions=(snapshot.additive?.normalized_rows??[]).filter(r=>r.target_id===id);
   for(const addition of additions)demand(addition.base_geometry_sha256===valueSha(f.geometry),'Effective addition target pointsets are stale against complete selected source');
   const effective={base_geometry_sha256:valueSha(f.geometry),additions};
   const allBounds=[...coordinateBounds(f.geometry),...additions.flatMap(r=>nativeOnlyComponent(r,valueSha)?[r.native_bounds]:coordinateBounds(r.geometry))];
   // One conservative rectangle contains every original member/addition bound.
   // A seam member already spans all longitude; merging can only widen exclusion.
   const boxes=[allBounds.reduce((a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])])];
   entries.push(coordinateRow({id,index:owner.index,parent_id:owner.province_id,parent_index:owner.province_index,source:name,ordinal,whole_feature_sha256:valueSha(f),geometry_sha256:valueSha(f.geometry),effective_geometry_sha256:valueSha(effective),boxes}));
   if(onFeature!==undefined){demand(typeof onFeature==='function','Require trusted source digest callback');onFeature(f);}
  }
 }
 const result={version:2,kind:'selected-complete-coordinate-shard-v2',entry_fields:COORDINATE_FIELDS,binding,paths:sourcePaths,inputs:inputFacts,entries};
 freeze(result);certificates.set(result,{binding,resolver});return result;
}
export function joinSelectedCoordinateCertificate(resolver,shards) {
 demand(resolver instanceof SelectedGeometrySources&&Array.isArray(shards)&&shards.length>0,'Missing actual selected coordinate shards');
 const expected=new Set(resolver.paths),seenPaths=new Set(),seenIds=new Set(),entries=[],inputs=[];
 let binding;for(const shard of shards){
  const proof=certificates.get(shard);demand(proof&&proof.resolver===resolver&&shard.kind==='selected-complete-coordinate-shard-v2','Unqualified/foreign selected coordinate stage');
  if(!binding)binding=shard.binding;demand(same(binding,shard.binding),'Mixed selected coordinate vintage');
  for(const p of shard.paths){demand(expected.has(p)&&!seenPaths.has(p),'Foreign/duplicate source containing closure');seenPaths.add(p);}
  for(const input of shard.inputs){demand(input.path===resolver.paths[inputs.length]&&same(input.source,{...resolver.sources[inputs.length],...(input.source.whole_encoded_alias?{whole_encoded_alias:input.source.whole_encoded_alias}:{})}), 'Complete selected source input order or whole binding differs');inputs.push(input);}for(const row of shard.entries){demand(!seenIds.has(row.id),'Duplicate complete location join');seenIds.add(row.id);entries.push(row);}
 }
 demand(seenPaths.size===expected.size&&seenIds.size===resolver.snapshot.owners.length&&resolver.snapshot.owners.every(o=>seenIds.has(o.id)),'Incomplete canonical source/owner roster; exclusion forbidden');
 entries.sort((a,b)=>a.index-b.index);
 const result={version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:COORDINATE_FIELDS,binding,entries,inputs,limitations:['Certificate projects complete owner identity/index/parent tuples and merged coordinate bounds. Full original camera metadata remains authenticated source custody; it is not duplicated as certificate geometry.','Conservative exclusion only. Actual whole geometry and original polygon predicates are mandatory for every possible neighbor.']};
 freeze(result);certificates.set(result,{binding,resolver});return result;
}
// Qualification of a persisted cold product uses the independently retained
// live trusted child acknowledgement, plus the actual selected resolver. The
// acknowledgement is issued by the parent invocation, never read from candidate
// files or inferred from the product's own facts.
// Pure body/inventory join; does not issue a selected snapshot or certificate.
export function validateColdSourceBody(input,expected,facts){
  if(expected.kind==='ordinary-immutable-git-source'&&!hash(expected.sha256)){
   const consumed=facts.inputs?.filter(row=>row.commit===expected.commit&&row.path===expected.path);
   demand(Array.isArray(consumed)&&consumed.length===1,'Missing or duplicate genuine whole ordinary source inventory');
   const row=consumed[0];demand(row.mode===expected.mode&&row.git_blob_oid===expected.git_blob_oid&&row.bytes===expected.bytes&&row.whole_body_consumed===true&&hash(row.sha256)&&input.whole_body_sha256===row.sha256&&input.bytes===row.bytes,'Whole ordinary source differs from independently selected Git identity and acknowledged consumption');
  }else{
  const rawHash=expected.decoded_sha256??expected.sha256,rawBytes=expected.decoded_bytes??expected.bytes;demand(input.whole_body_sha256===rawHash&&input.bytes===rawBytes,'Whole cold selected source body differs from independent source bank');
  }
}
export function acceptColdCoordinateCertificate(resolver,certificate,{facts,expectedPublication,publication,encoded_sha256,decoded_sha256}) {
 demand(resolver instanceof SelectedGeometrySources&&same(publication,expectedPublication)&&publication.complete===true&&publication.kind==='trusted-selected-coordinate-stage-v1','Missing actual issued cold-stage acknowledgement');
 demand(encoded_sha256===publication.certificate.sha256&&decoded_sha256===publication.certificate.decoded_sha256,'Cold complete certificate bytes differ');
 demand(publication.facts&&valueSha(facts)===publication.facts.sha256,'Cold facts differ from genuine acknowledged publication');
 demand(facts.kind===publication.kind&&facts.selected_commit===resolver.reader.version&&facts.candidate_code_executed===false&&certificate.kind==='selected-coordinate-neighbor-certificate-v2','Foreign cold certificate execution/input');
 demand(same(certificate.binding.selection,resolver.snapshot.selection)&&same(certificate.binding.release,resolver.release)&&same(certificate.binding.sources,resolver.sources)&&certificate.binding.owners_sha256===valueSha(selectedReferenceOwners(resolver.snapshot))&&same(facts.binding,certificate.binding),'Cold certificate selected source/owner binding differs');
 bindCoordinateRows(certificate);
 const paths=new Set(resolver.paths),owners=new Map(selectedReferenceOwners(resolver.snapshot).map(r=>[r.id,r])),seen=new Set(),sources=new Set();
 demand(Array.isArray(certificate.inputs)&&certificate.inputs.length===paths.size&&Array.isArray(certificate.entries)&&certificate.entries.length===owners.size,'Incomplete cold source/owner certificate');
 for(let i=0;i<certificate.inputs.length;i++){const input=certificate.inputs[i],expected=resolver.sources[i];
  demand(input.path===resolver.paths[i]&&!sources.has(input.path)&&sources.add(input.path)&&same(input.source,{...expected,...(input.source?.whole_encoded_alias?{whole_encoded_alias:input.source.whole_encoded_alias}:{})})&&hash(input.whole_body_sha256)&&Number.isSafeInteger(input.bytes)&&input.bytes>0,'Foreign/duplicate/reordered/drifted complete cold source');
  validateColdSourceBody(input,expected,facts);
 }
 for(let i=0;i<certificate.entries.length;i++){const row=certificate.entries[i],owner=owners.get(row.id);demand(row.id===resolver.snapshot.owners[i].id&&owner&&!seen.has(row.id)&&seen.add(row.id)&&row.index===owner.index&&row.parent_id===owner.province_id&&row.parent_index===owner.province_index&&paths.has(row.source)&&Number.isSafeInteger(row.ordinal)&&row.ordinal>=0&&hash(row.whole_feature_sha256)&&hash(row.geometry_sha256)&&hash(row.effective_geometry_sha256)&&Array.isArray(row.boxes)&&row.boxes.length>0,'Foreign/duplicate/drifted cold owner record');
  const additions=(resolver.snapshot.additive?.normalized_rows??[]).filter(r=>r.target_id===row.id);
  demand(row.effective_geometry_sha256===valueSha({base_geometry_sha256:row.geometry_sha256,additions})&&additions.every(r=>r.base_geometry_sha256===row.geometry_sha256),'Cold effective primitive set differs from independently authenticated selection');
  for(const box of row.boxes)demand(Array.isArray(box)&&box.length===4&&box.every(Number.isFinite)&&box[0]>=-180&&box[2]<=180&&box[1]>=-90&&box[3]<=90&&box[0]<=box[2]&&box[1]<=box[3],'Invalid complete coordinate exclusion bound');
 }
 demand(facts.complete_owners===owners.size&&facts.complete_sources===paths.size,'Cold scope denominator differs');
 freeze(certificate);certificates.set(certificate,{binding:certificate.binding,resolver,accepted:{publication_sha256:valueSha(publication),facts_sha256:valueSha(facts),encoded_sha256,decoded_sha256}});return certificate;
}

// A persisted receipt is issued only after the genuine resolver has validated
// every complete source/owner row. It holds custody, never the resolver, native
// image, camera roster, or live certificate. Reopening requires the exact whole
// originally validated product; a serializable copy cannot issue this authority.
const coldReceipts=new WeakMap();
export function sealColdCoordinateCertificate(certificate,product) {
 const proof=certificates.get(certificate);
 demand(proof?.resolver instanceof SelectedGeometrySources&&certificate.kind==='selected-coordinate-neighbor-certificate-v2','Require genuine complete cold validation before detachment');
 demand(proof.accepted&&valueSha(product.publication)===proof.accepted.publication_sha256&&valueSha(product.facts)===proof.accepted.facts_sha256&&product.encoded_sha256===proof.accepted.encoded_sha256&&product.decoded_sha256===proof.accepted.decoded_sha256,'Persisted custody differs from privately accepted whole product');
 demand(valueSha(certificate)===product.decoded_sha256&&same(product.publication.certificate,{path:'certificate.json.gz',bytes:product.publication.certificate.bytes,sha256:product.encoded_sha256,decoded_bytes:product.publication.certificate.decoded_bytes,decoded_sha256:product.decoded_sha256})&&valueSha(product.facts)===product.publication.facts.sha256,'Validated persisted cold product changed');
 const inventory=[...proof.resolver.reader.inventory.values()].filter(pin=>pin.whole_body_consumed===true);
 demand(inventory.length>0,'Missing complete persisted cold acquisition custody');
 const receipt=JSON.parse(valueBytes({version:1,kind:'privately-validated-persisted-coordinate-receipt-v1',binding:certificate.binding,publication:product.publication,facts:product.facts,inventory,effective_additions:proof.resolver.snapshot.additive?.normalized_rows??[]}));
 const metadataApplication={scientific_selection:nativeBaseSelection(proof.resolver.snapshot.selection),
  projected:!!proof.resolver.snapshot.selection.reference_projection};
 freeze(receipt);coldReceipts.set(receipt,{decoded_sha256:product.decoded_sha256,encoded_sha256:product.encoded_sha256,metadataApplication});
 // Shard proofs retain their resolver identity. Only the fully validated cold
// certificate proof relinquishes the selected snapshot after its helper ends.
 certificates.set(certificate,{binding:certificate.binding,persisted:true,metadataApplication});return receipt;
}
export function reopenColdCoordinateCertificate(receipt,product) {
 const proof=coldReceipts.get(receipt);
 demand(proof&&same(product.publication,receipt.publication)&&same(product.facts,receipt.facts)&&product.encoded_sha256===proof.encoded_sha256&&product.decoded_sha256===proof.decoded_sha256&&valueSha(product.certificate)===proof.decoded_sha256&&same(product.certificate.binding,receipt.binding),'Missing private persisted custody or changed whole cold product');
 bindCoordinateRows(product.certificate);freeze(product.certificate);certificates.set(product.certificate,{binding:receipt.binding,persisted:true,metadataApplication:proof.metadataApplication});return product.certificate;
}

export function selectedCertificateAffectedPlan(before,after) {
 demand(certificates.has(before)&&certificates.has(after),'Require both complete cold source certificates');
 const old=new Map(before.entries.map(r=>[r.id,r])),next=new Map(after.entries.map(r=>[r.id,r]));
 demand(old.size===next.size&&[...old].every(([id,row])=>next.has(id)&&row.index===next.get(id).index),
  'Selected continuous stable identity/owner roster changed');
 const parentChanges=[...old].some(([id,row])=>row.parent_id!==next.get(id).parent_id||row.parent_index!==next.get(id).parent_index);
 if(parentChanges){
  const applicability=certificate=>{const proof=certificates.get(certificate);return proof.metadataApplication??{
   scientific_selection:nativeBaseSelection(proof.resolver.snapshot.selection),
   projected:!!proof.resolver.snapshot.selection.reference_projection};};
  const prior=applicability(before),current=applicability(after);
  demand((prior.projected||current.projected)&&same(prior.scientific_selection,current.scientific_selection),
   'Selected continuous parent change lacks a validated metadata-only application');
 }

 const changed=[...old.keys()].filter(id=>old.get(id).effective_geometry_sha256!==next.get(id).effective_geometry_sha256).sort(),needed=new Set(changed),pairs=new Set();
 const intersects=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
 for(const id of changed){const bounds=[...old.get(id).boxes,...next.get(id).boxes];
  for(const certificate of [before,after])for(const row of certificate.entries)if(row.id!==id&&row.boxes.some(a=>bounds.some(b=>intersects(a,b)))){needed.add(row.id);pairs.add([id,row.id].sort().join('\0'));}
 }
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
 return {version:1,kind:'complete-selected-affected-plan-v1',binding:certificate.binding,changed_ids:[...targets.keys()].sort(),required_ids:[...needed].sort(),pairs:[...pairs].sort().map(p=>p.split('\0')),
  source_paths:[...new Set(certificate.entries.filter(r=>needed.has(r.id)).map(r=>r.source))].sort(),limitations:['Original strict polygon predicates still required; this plan is not geographic approval.']};
}

// Authenticate original executed rule bodies before deriving their preimage.
// This is historical authority custody, not source approval or bank activation.
// Completed products retain their original issued tuple; publication aliases
// authenticate exact ordinary Git bodies without rewriting historical requests.
function originalSourceAliases(reader, request, aliases) {
 demand(Array.isArray(aliases)&&aliases.length<=3,'Unsupported original source output alias roster');
 const byPath=new Map();
 for(const alias of aliases){
  demand(alias&&Object.keys(alias).sort().join(',')==='original,published','Unsupported completed output alias shape');
  const {original:p,published:q}=alias;
  demand(p?.kind==='completed-inventory-body'&&p.mode==='100644'&&/^\.cache\/native-grid-candidates\/[a-zA-Z0-9._-]+\/(facts\.json|publication\.json|inventory\.jsonl\.gz)$/.test(p.path)&&!byPath.has(p.path),'Invalid/duplicate completed output alias');
  demand(request.additive.inputs.filter(x=>x.path===p.path).length===1&&same(request.additive.inputs.find(x=>x.path===p.path),p),'Completed alias changed original issued tuple');
  demand([request.additive.facts_path,request.additive.publication_path,request.additive.inventory_path].includes(p.path),'Unconsumed completed alias');
  pinCheck({...q,git_blob_oid:q.git_blob_oid??q.blob});
  demand(q.mode==='100644'&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>q[k]===p[k]),'Completed alias whole encoded/decoded pins differ');
  const actual=reader.descriptor(q.path,q.commit);
  demand(actual.mode===q.mode&&actual.git_blob_oid===(q.git_blob_oid??q.blob)&&actual.bytes===q.bytes,'Completed alias actual Git identity differs');
  const decoded=p.uncompressed_bytes??0;
  demand(Number.isSafeInteger(decoded)&&decoded>=0,'Invalid completed alias decoded byte length');
  const encoded=reader.read(q.path,{version:q.commit,expected:q.sha256});
  if(p.uncompressed_bytes!==undefined){demand(hash(p.uncompressed_sha256),'Missing completed decoded hash');const raw=gunzipSync(encoded,{maxOutputLength:decoded});demand(raw.length===decoded&&sha(raw)===p.uncompressed_sha256,'Completed alias decoded body differs');}
  byPath.set(p.path,q);
 }
 return byPath;
}
function currentOriginalManifest(request, native, spec) {
 if(request.baseline?.version!==2)return request.baseline?.pins?.find(p=>p.path===spec.manifest_path);
 demand(request.baseline.kind==='current-selected-native-baseline-v1'&&request.baseline.pins?.length===1&&request.baseline.pins[0].path==='data/ownership-selection.json','Unsupported current original baseline');
 const p=spec.inputs?.find(p=>p.path===spec.manifest_path),a=native.baseline_acquisition;
 demand(p&&a?.manifest_sha256===p.sha256&&a.input_inventory?.filter(r=>r.path===p.path&&r.whole_body_consumed===true&&r.mode===p.mode&&r.git_blob_oid===(p.git_blob_oid??p.blob)&&r.bytes===p.bytes&&r.sha256===p.sha256).length===1,'Original current whole manifest acquisition differs');
 return p;
}
export function readOriginalRuleAuthority(reader, pins, sourceOutputAliases=[]) {
 demand(reader instanceof ImmutableReader&&pins&&Object.keys(pins).sort().join(',')==='ledger,native_facts,native_manifest,native_request,source_facts,source_request','Require exact original rule body roster');
 const normal=p=>({...p,git_blob_oid:p.git_blob_oid??p.blob});
 const identity=p=>{const q=normal(p);return {commit:q.commit,path:q.path,mode:q.mode,git_blob_oid:q.git_blob_oid,bytes:q.bytes,sha256:q.sha256};};
 const admitted=new Map();
 // Authenticate every whole body before interpreting the original rule.
 for(const [key,p]of Object.entries(pins)){
  pinCheck(normal(p));let version=p.commit;
  try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);
  demand(actual.mode===p.mode&&actual.git_blob_oid===normal(p).git_blob_oid&&actual.bytes===p.bytes,'Original authority body mode/OID differs');
  admitted.set(key,{pin:p,version});
 }
 const bodies={};for(const [key,{pin,version}]of admitted)bodies[key]=JSON.parse(reader.read(pin.path,{version,expected:pin.sha256}));
 const {ledger,native_facts:native, native_manifest:manifest,native_request:request,source_facts:source,source_request:issued}=bodies;
 demand(same(identity(native.request),identity(pins.native_request))&&same(identity(source.request),identity(pins.source_request)),'Original facts rebound issued request');
 demand(same(native.executed_code,request.executed_code)&&same(source.executed_code,issued.executed_code),'Original executed code differs from issued closure');
 demand(source.operation==='retained-land-source-premises-v1'&&issued.operation===source.operation&&same(issued.source_rule,source.source_rule),'Original whole source rule differs');
 demand(request.operation===native.operation&&['unactivated-additive-native-release-v1','unactivated-additive-native-batch-v1'].includes(native.operation),'Unsupported original proposal operation');
 const spec=request.additive;demand(spec&&same(spec,native.source_predecessor),'Original proposal source predecessor changed');
 const aliases=originalSourceAliases(reader,request,sourceOutputAliases);
 for(const [key,name]of [['source_request','source_request_path'],['source_facts','facts_path']]){
  const pin=spec.inputs?.find(p=>p.path===spec[name]);
  demand(pin&&same(identity(aliases.get(pin.path)??pin),identity(pins[key])),'Original proposal omits/rebinds complete predecessor: '+key);
 }
 const manifestOriginal=currentOriginalManifest(request,native,spec);
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
  source_scope_ids:ledger.scope_ids,...(sourceOutputAliases.length?{source_output_aliases:sourceOutputAliases}:{}),limitations:['Historical whole executed rule custody only. Full predecessor publication/operating/source closure and current-bank rebind are independently required before selection. No physical authority or activation approval.']});
 originalAuthorities.set(result,{reader,bodies,aliases});return result;
}

// Reuse the actually qualified source predecessor; never infer permission from
// a hash-shaped receipt or caller-written approval boolean. No source method is
// rerun here. Original whole case/source pins remain in the retained closure.
// Only independently reviewed administrative SOURCE and NATIVE closures may retain
// an older source selector. Both selectors and their complete unchanged source-map
// identity are authenticated; current selected-bank conservation remains later.
function originalAdministrativeBaseline(reader, issued, request, native) {
 if(same(issued.baseline,request.baseline))return true;
 const profile='retained-consumed-administrative-source';
 demand(issued.source_rule?.profile===profile&&request.additive?.source_profile===profile,
  'Unreviewed original administrative baseline split');
 matchSupportedProgramme(readSupportedProgrammeCatalogue(reader).catalogue,{preimageVersion:3,sourceProfile:profile,
  sourceCode:issued.executed_code,nativeCode:request.executed_code});
 const read=p=>{pinCheck({...p,git_blob_oid:p.git_blob_oid??p.blob});
  const actual=reader.descriptor(p.path,p.commit);
  demand(actual.mode===p.mode&&actual.git_blob_oid===(p.git_blob_oid??p.blob)&&actual.bytes===p.bytes,'Original selector/source-map Git identity differs');
  return JSON.parse(reader.read(p.path,{version:p.commit,expected:p.sha256}));};
 for(const baseline of [issued.baseline,request.baseline])demand(baseline?.version===2
  &&baseline.kind==='current-selected-native-baseline-v1'&&Object.keys(baseline).sort().join(',')==='kind,pins,version'
  &&Array.isArray(baseline.pins)&&baseline.pins.length===1&&baseline.pins[0].kind===undefined
  &&baseline.pins[0].path==='data/ownership-selection.json','Foreign original administrative selector');
 const historical=read(issued.baseline.pins[0]),selected=read(request.baseline.pins[0]),a=native.baseline_acquisition;
 demand(a?.kind==='current-selected-native-baseline-custody-v1'&&same(a.baseline_pin,request.baseline.pins[0])
  &&same(a.selection,selected)&&a.manifest_sha256===selected.sha256&&a.source_map_sha256===selected.selected_geography?.sha256,
  'Original native selector acquisition differs');
 demand(['method','manifest_path','sha256','release_id'].every(key=>historical[key]===selected[key])
  &&same(historical.selected_geography,selected.selected_geography),'Original historical/current base geometry differs');
 const descriptor=selected.selected_geography;
 demand(descriptor?.kind==='complete-world-index-with-exact-encoded-overrides','Unsupported original selected source map');
 const actual=reader.descriptor(descriptor.path,request.baseline.pins[0].commit);
 demand(actual.bytes===descriptor.bytes,'Original selected source-map size differs');
 const map=read({...actual,sha256:descriptor.sha256});
 demand(map.kind===descriptor.kind&&map.native_manifest_sha256===selected.sha256&&map.release_id===selected.release_id,
  'Original selected source-map binding differs');
 const names=issued.source_rule.target_banks;
 demand(Array.isArray(names)&&names.length>0&&new Set(names).size===names.length&&Array.isArray(a.source_bindings),'Incomplete original target-bank roster');
 for(const name of names){const expected=issued.source_rule.inputs.filter(p=>p.path===name),acquired=a.source_bindings.filter(p=>p.path===name),mapped=map.unchanged_files.filter(p=>p.path===name);
  demand(expected.length===1&&acquired.length===1&&mapped.length===1&&expected[0].kind===undefined
   &&acquired[0].kind==='ordinary-immutable-git-source'&&['mode','bytes','sha256'].every(k=>expected[0][k]===acquired[0][k]&&expected[0][k]===mapped[0][k])
   &&expected[0].blob===acquired[0].git_blob_oid&&expected[0].blob===mapped[0].git_blob_oid
   &&acquired[0].commit===mapped[0].commit,'Original complete administrative target bank differs');}
 return true;
}

export function qualifyOriginalSourceAuthority(custody) {
 const proof=originalAuthorities.get(custody);demand(proof,'Require actual authenticated original rule custody');
 const {reader,bodies}=proof,{native_request:request,source_request:issued,source_facts:facts}=bodies,spec=request.additive;
 const keys=['publication_path','inventory_path','operating_path'];
 const pins=keys.map(key=>{const original=spec.inputs.find(p=>p.path===spec[key]);const p=proof.aliases.get(original?.path)??original;demand(p,'Omitted qualified source proof '+key);pinCheck({...p,git_blob_oid:p.git_blob_oid??p.blob});return p;});
 const admitted=pins.map(p=>{let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);demand(actual.mode===p.mode&&actual.git_blob_oid===(p.git_blob_oid??p.blob)&&actual.bytes===p.bytes,'Qualified original proof mode/OID differs');return {p,version};});
 const raw=admitted.map(({p,version})=>{const encoded=reader.read(p.path,{version,expected:p.sha256});if(p.uncompressed_bytes===undefined)return encoded;
  demand(hash(p.uncompressed_sha256),'Missing complete decoded proof hash');const decoded=gunzipSync(encoded,{maxOutputLength:p.uncompressed_bytes});demand(decoded.length===p.uncompressed_bytes&&sha(decoded)===p.uncompressed_sha256,'Whole decoded original proof differs');return decoded;});
 const [publication,inventory,operating]=[JSON.parse(raw[0]),raw[1],JSON.parse(raw[2])],inventoryPin=pins[1];
 demand(publication.complete===true&&publication.facts.bytes===custody.pins.source_facts.bytes&&publication.facts.sha256===custody.pins.source_facts.sha256&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>publication.inventory[k]===inventoryPin[k]),'Partial/drifted original source publication');
 demand(facts.execution_commit===spec.source_execution_commit&&same(facts.input_descriptors,[issued.report,...issued.source_rule.inputs,...issued.baseline.pins])&&same(facts.runtime,spec.source_runtime)&&same(facts.installed_modules,issued.installed_modules)&&same(facts.parent,request.parent)&&originalAdministrativeBaseline(reader,issued,request,bodies.native_facts),'Original source execution closure differs');
 demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0&&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null&&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Unqualified original source operating proof');
 const lines=inventory.toString('utf8').split('\n');demand(lines.pop()==='','Truncated complete source inventory');const rows=lines.map(line=>JSON.parse(line));
 demand(same(rows.map(r=>r.component_id),issued.source_rule.expected_ids)&&rows.length===facts.components&&new Set(rows.map(r=>r.component_id)).size===rows.length,'Omitted/duplicate/reordered source inventory');
 const byId=new Map(rows.map(r=>[r.component_id,r]));
 for(const selected of custody.ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition))){const row=byId.get(selected.component_id);
  demand(row?.source_compatible===true&&row.disposition==='awaiting-native-exclusion'&&same(row.candidate,selected.geometry)&&row.target_id===selected.target_id&&row.target_geometry_sha256===selected.base_geometry_sha256,'Original selected primitive lacks complete source premise');
  demand(row.source_case?.source&&spec.inputs.some(p=>same(p,row.source_case.source)),'Whole proposal source-case custody omitted');
  for(const pin of [row.source_case?.source,row.original_record?.source])demand(pin&&issued.source_rule.inputs.some(p=>same(p,pin)),'Whole original source-case/record custody omitted');
 }
 const result=freeze({version:1,kind:'qualified-original-source-authority-v1',original:custody,pins,rows,
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
 const held={publication:null,operating:null,rows:[],nativePatches:[],nativeContracts:[]};
 const finishedMember=(p,consume)=>{
  const q={...p,git_blob_oid:p.git_blob_oid??p.blob,decoded_bytes:p.decoded_bytes??p.uncompressed_bytes,decoded_sha256:p.decoded_sha256??p.uncompressed_sha256};pinCheck(q);
  let version=q.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(q.path,version);demand(actual.mode===q.mode&&actual.git_blob_oid===q.git_blob_oid&&actual.bytes===q.bytes,'Original native proof whole mode/OID differs');
  const encoded=reader.read(q.path,{version,expected:q.sha256});
  let raw=encoded;
  if(q.decoded_bytes!==undefined){raw=gunzipSync(encoded,{maxOutputLength:q.decoded_bytes});demand(raw.length===q.decoded_bytes&&sha(raw)===q.decoded_sha256,'Original whole native decoded proof differs');}
  consume(raw);
 };
 finishedMember(pins.publication,raw=>{held.publication=JSON.parse(raw);});
 finishedMember(pins.inventory,raw=>{const lines=raw.toString('utf8').split('\n');demand(lines.pop()==='','Truncated whole native inventory');held.rows=lines.map(s=>JSON.parse(s));});
 finishedMember(pins.operating,raw=>{held.operating=JSON.parse(raw);});
 const {publication,operating,rows,nativePatches,nativeContracts}=held,inventoryPin=pins.inventory;
 demand(publication.complete===true&&publication.facts.bytes===custody.pins.native_facts.bytes&&publication.facts.sha256===custody.pins.native_facts.sha256&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>publication.inventory[k]===inventoryPin[k]),'Partial/drifted original native publication');
 demand(same(facts.input_descriptors,[issued.report,...issued.additive.inputs,...issued.baseline.pins])&&same(facts.installed_modules,issued.installed_modules),'Original native actual input/module closure differs');
 demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0&&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null&&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Unqualified original native operating proof');
 const batch=facts.operation==='unactivated-additive-native-batch-v1',nativeScope=batch?custody.source_scope_ids:[issued.additive.component_id];
 demand(same(rows.map(r=>r.component_id),nativeScope)&&new Set(rows.map(r=>r.component_id)).size===rows.length&&(!batch||rows.length===facts.components),'Native inventory scope omitted/reordered');
 const byId=new Map(custody.ledger.rows.map(r=>[r.component_id,r]));
 for(const row of rows){const old=byId.get(row.component_id);demand(old&&(batch?row.disposition===old.disposition:['assigned','zero-cell'].includes(old.disposition))&&row.native_cells===(old.native_cells??0)&&row.target_id===(['assigned','zero-cell'].includes(old.disposition)?old.target_id:proof.qualifiedSource.rows.find(r=>r.component_id===row.component_id)?.target_id),'Native inventory disposition/contribution rebound');}
 demand(publication.assets.length===pins.assets.length&&new Set(pins.assets.map(p=>p.path)).size===pins.assets.length,'Incomplete/duplicate native asset roster');
 for(let i=0;i<pins.assets.length;i++){
  const p=pins.assets[i],declared=publication.assets[i];
  demand(p.path.endsWith('/'+declared.path)&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>p[k]===declared[k]),'Original native asset roster rebound');
  finishedMember(p,raw=>{
  if(declared.path==='base-native-manifest.json'){const m=JSON.parse(raw);nativeContracts.push(Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,m[k]])));}
  if(declared.path.startsWith('patch-')){const patch=JSON.parse(raw);demand(patch.kind==='unassigned-native-cells-v1'&&patch.ledger_sha256===custody.pins.ledger.sha256,'Qualified original patch/ledger differs');nativePatches.push(patch);}
  if(p.sha256===custody.pins.ledger.sha256)demand(same(JSON.parse(raw),custody.ledger),'Whole published native ledger differs');
  });
 }
 demand(nativeContracts.length===1,'Original native publication omits complete base manifest');
 demand(pins.assets.some(p=>p.sha256===custody.pins.ledger.sha256),'Published native assets omit original complete ledger');
 return freeze({version:1,kind:'qualified-original-native-authority-v1',pins,scope_ids:custody.source_scope_ids,native_scope_ids:nativeScope,inventory_rows:rows,native_patches:nativePatches,native_contract:nativeContracts[0],rule_sha256:custody.rule_sha256,
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
// Admit retained whole query semantics before projecting any witness to cells.
// Coverage shortcuts refer to the complete candidate/source record; no empty
// replacement geometry is invented. Repeated source IDs require distinct frames.
function physicalQueryAdmission(result, required) {
 const present=Object.hasOwn(result,'source_id_queries')||Object.hasOwn(result,'query_relations');
 demand(present||!required,'Unsupported original native geometry without complete source query evidence; Unresolved contradictory or hierarchy physical support');
 if(!present)return;
 const ids=result.source_id_queries,queries=result.query_relations;
 demand(Array.isArray(ids)&&ids.length>0&&ids.every(Number.isSafeInteger)
  &&new Set(ids).size===ids.length&&Array.isArray(queries)&&queries.length>0,
 'Incomplete physical source query roster');
 const expected=new Set(ids),seen=new Set(),joined=new Set();
 for(const q of queries){
  demand(q&&expected.has(q.source_id)&&[-360,0,360].includes(q.periodic_offset)
   &&q.status==='checked','Unknown or missing physical source query');
  demand(!required||q.periodic_offset===0,'Unqualified periodic physical conflict frame');
  const identity=q.source_id+':'+q.periodic_offset;
  demand(!seen.has(identity),'Duplicate physical source query frame');seen.add(identity);joined.add(q.source_id);
  const bools=['source_covers_candidate','candidate_covers_source','intersects','disjoint'];
  demand(bools.every(k=>typeof q[k]==='boolean')&&q.intersects!==q.disjoint
   &&(!(q.source_covers_candidate||q.candidate_covers_source)||q.intersects),
  'Contradictory physical source query predicates');
  const witness=q.source_covers_candidate?'complete-candidate-reconstruction':
   q.candidate_covers_source?'complete-source-record-reconstruction':
   !q.intersects?'disjoint-after-explicit-predicate':'complete-operation-pointset';
  demand(q.witness===witness,'Inconsistent physical source query witness precedence');
  const keys=['source_id','periodic_offset','status',...bools,'witness'];
  if(witness==='complete-operation-pointset')keys.push('witness_geometry');
  demand(Object.keys(q).sort().join(',')===keys.sort().join(','),'Incomplete or foreign physical source query fields');
  if(witness==='complete-operation-pointset')
   demand(!validateWitnessGeometry(q.witness_geometry).empty,'Empty physical source query intersection');
 }
 demand(joined.size===expected.size,'Incomplete physical source query identity join');
}
function reconstructionResidualPointsets(result, dated = false) {
 demand(Array.isArray(result?.issues)&&result.support&&typeof result.support==='object',
  'Missing qualified physical source interpretation');
 const support=result.support,residualKeys=['missing_reconstruction','extra_reconstruction'];
 const hierarchyKeys=['L2-outside-L1','L3-outside-L2','L4-outside-L3'];
 const conflictKeys=[...residualKeys,'contradictory_land_water_support',...hierarchyKeys];
 const hierarchy=support.hierarchy_disagreements;
 const empty=g=>validateWitnessGeometry(g).empty;
 const witness=(role,geometry)=>({source_id:result.target,role,geometry});
 // Mapped water remains distinct positive water evidence. It cannot supersede
 // exterior context and blocks the dated-land exception at any actual contact.
 const waterContext=()=>dated&&support.mapped_inland_water_support&&!empty(support.mapped_inland_water_support)
  ?[witness('mapped_inland_water_support',support.mapped_inland_water_support)]:[];
 const observed=[...residualKeys,'contradictory_land_water_support'].some(key=>
  Object.hasOwn(support,key)&&!empty(support[key]))
  ||Object.hasOwn(support,'hierarchy_disagreements')&&(!hierarchy||typeof hierarchy!=='object'
   ||Object.keys(hierarchy).sort().join(',')!==hierarchyKeys.join(',')
   ||Object.values(hierarchy).some(g=>!empty(g)));
 physicalQueryAdmission(result,false);
 // Preserve genuine legacy issue-free evidence, while admitting every present
 // query/support primitive before returning. Unknown fields cannot hide issues.
 if(result.issues.length===0&&!observed){
  const allowed=['mapped_land_support','mapped_inland_water_support','outside_mapped_L1_context',
   'hierarchy_disagreements',...residualKeys,'contradictory_land_water_support'];
  demand(Object.keys(support).every(k=>allowed.includes(k)),'Incomplete physical residual operation roster');
  for(const [key,g]of Object.entries(support))if(key!=='hierarchy_disagreements')validateWitnessGeometry(g);
  return [...(support.outside_mapped_L1_context&&!empty(support.outside_mapped_L1_context)
   ?[witness('outside_mapped_L1_context',support.outside_mapped_L1_context)]:[]),...waterContext()];
 }
 const supportKeys=['mapped_land_support','mapped_inland_water_support','outside_mapped_L1_context',
  'hierarchy_disagreements',...residualKeys,'contradictory_land_water_support'];
 demand(Object.keys(support).sort().join(',')===supportKeys.sort().join(',')
  &&hierarchy&&typeof hierarchy==='object'&&Object.keys(hierarchy).sort().join(',')===hierarchyKeys.join(','),
 'Incomplete physical residual operation roster');
 const operations=Object.fromEntries([...supportKeys.filter(k=>k!=='hierarchy_disagreements'),...hierarchyKeys]
  .map(k=>[k,support[k]??hierarchy[k]]));
 for(const geometry of Object.values(operations))validateWitnessGeometry(geometry);
 const general=conflictKeys.some(k=>!empty(operations[k])&&(!residualKeys.includes(k)
  ||!['Polygon','MultiPolygon'].includes(operations[k].type)));
 physicalQueryAdmission(result,general);
 const issues=new Map();
 for(const issue of result.issues){
  demand(issue&&Object.keys(issue).sort().join(',')==='geometry,reason'
   &&conflictKeys.includes(issue.reason)&&!issues.has(issue.reason),'Unknown or duplicate physical residual issue');
  issues.set(issue.reason,issue.geometry);
 }
 const pointsets=[];
 for(const key of conflictKeys){
  const geometry=operations[key];
  if(empty(geometry)){demand(!issues.has(key),'Empty physical residual has an issue witness');continue;}
  demand(issues.has(key)&&same(issues.get(key),geometry),
   'Missing or mismatched complete physical residual witness; Unresolved contradictory or hierarchy physical support');
  pointsets.push(witness(key,geometry));
 }
 // Preserve the context role and original member; it is never positive land.
 if(!empty(operations.outside_mapped_L1_context))
  pointsets.push(witness('outside_mapped_L1_context',operations.outside_mapped_L1_context));
 return [...pointsets,...waterContext()];
}

// Source-target evidence uses the same retained registry and literal native
// patch route. It has no invented original-gap inventory or addition polygon.
export function qualifySourceTargetNativeAuthority(reader, preimage, binding, {snapshot}={}) {
 return evaluateSourceTargetNativeAuthority(reader, preimage, binding, false, snapshot);
}

// Same authenticated preparation and predicates as qualification. This returns
// observations only, before any authority ledger or native proof construction.
export function diagnoseSourceTargetNativeAuthority(reader, preimage, binding) {
 return evaluateSourceTargetNativeAuthority(reader, preimage, binding, true);
}

function evaluateSourceTargetNativeAuthority(reader, preimage, binding, diagnostic, snapshot) {
 demand(preimage?.version===1&&preimage.kind==='source-target-native-rule-v1'
  &&Object.keys(preimage).sort().join(',')==='kind,native_patch,source_evidence,version'
  &&binding?.version===1&&binding.kind==='source-target-native-custody-v1'
  &&Object.keys(binding).sort().join(',')==='kind,native_patch,source_evidence,version'
  &&same(preimage.source_evidence,binding.source_evidence)&&same(preimage.native_patch,binding.native_patch),
 'Source-target authority inputs differ');
 const read=p=>{
  pinCheck(p);let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const d=reader.descriptor(p.path,version);
  demand(d.mode===p.mode&&d.git_blob_oid===p.git_blob_oid&&d.bytes===p.bytes,'Source-target whole identity differs');
  const raw=reader.read(p.path,{version,expected:p.sha256});
  if(p.decoded_bytes===undefined)return raw;
  const decoded=gunzipSync(raw,{maxOutputLength:p.decoded_bytes});
  demand(decoded.length===p.decoded_bytes&&sha(decoded)===p.decoded_sha256,'Source-target decoded body differs');return decoded;
 };
 const evidence=JSON.parse(read(binding.source_evidence)), proposed=JSON.parse(read(binding.native_patch));
 const dated = evidence?.version===2&&evidence.kind==='source-target-native-evidence-v2';
 demand((dated||evidence?.version===1&&evidence.kind==='source-target-native-evidence-v1')
  &&(dated?evidence.dated_land_support!==undefined:evidence.dated_land_support===undefined)
  &&Array.isArray(evidence.targets)&&evidence.targets.length>0&&Array.isArray(proposed.rows)
  &&Object.keys(proposed).join(',')==='rows',
 'Incomplete source-target evidence');
 // The catalogue is the retained consumed-byte inventory, not an author supplied
 // geometry subset. Each complete original product is rejoined below.
 demand(evidence.catalogue.path==='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',
 'Require retained original source catalogue');
 const currentCatalogue=reader.descriptor(evidence.catalogue.path);
 demand(currentCatalogue.git_blob_oid===evidence.catalogue.git_blob_oid,'Source catalogue differs from the selected retained corpus');
 const catalogue=JSON.parse(read(evidence.catalogue));
 const physicalInputs=JSON.parse(read(evidence.physical_input));read(evidence.physical_reproduction);
 demand(evidence.native_latitudes.sha256===evidence.native_contract.native_latitudes.sha256
  &&evidence.native_latitudes.decoded_sha256===evidence.native_contract.native_latitudes.decoded_sha256,
 'Native source-target latitude contract differs');
 const latitudeRaw=read(evidence.native_latitudes);
 const physical=JSON.parse(read(evidence.physical_evidence));
 demand(evidence.native_contract.size===262166&&latitudeRaw.length===262166*8,
 'Unsupported source-target native lattice');
 const latitudes=Float64Array.from({length:262166},(_,i)=>latitudeRaw.readDoubleLE(i*8));
 for(let y=0;y<latitudes.length;y++)demand(Number.isFinite(latitudes[y])&&Math.abs(latitudes[y])<90
  &&(y===0||latitudes[y]<latitudes[y-1]),'Invalid decreasing source-target native latitude table');
 demand(evidence.owner_roster.sha256===evidence.native_contract.original_assets.bounds.sha256,
 'Source-target owner roster differs from original native identity asset');
 const roster=JSON.parse(read(evidence.owner_roster));
 demand(Array.isArray(roster),'Missing original owner roster');
 const owners=new Map();
 for(const [i,owner]of roster.entries()){
  demand(typeof owner.id==='string'&&owner.id&&!owners.has(owner.id)&&(owner.index??i+1)===i+1,
   'Duplicate or noncanonical original owner roster');owners.set(owner.id,i+1);
 }
 // Optional reconciliation uses existing complete aggregation lineage, not an
 // authored source-to-owner guess. Canonical parts retain the accepted members
 // and base geometry; the complete lineage exposes omitted competing owners.
 const memberOwners=new Map(), canonicalOwners=new Map();
 if(evidence.source_membership!==undefined){
  const membership=evidence.source_membership;
  demand(membership&&Object.keys(membership).sort().join(',')==='index,lineage,parts'
   &&Array.isArray(membership.parts)&&membership.parts.length>0,'Incomplete accepted source membership');
  const current=p=>{
   pinCheck(p);const actual=reader.descriptor(p.path);
   const exact=actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes;
   if(!exact){
    // A current metadata application does not alter original aggregation
    // membership or pointsets. Use only the privately validated N source view;
    // actual M bytes and all non-parent properties were checked in full first.
    demand(snapshot?.selection.reference_projection,'Source membership differs from selected canonical bytes');
    demand(snapshot.reader.repo===reader.repo&&snapshot.reader.version===reader.version,
     'Source membership belongs to another actual selected reader');
    selectedNativeSourceMembership(snapshot,p);
   }
   return JSON.parse(read(p));
  };
  demand(membership.lineage.path==='data/semantic-report.json'&&membership.index.path==='data/world-index.json',
   'Require complete accepted aggregation lineage and world index');
  const lineage=current(membership.lineage),index=current(membership.index);
  demand(Array.isArray(lineage.changes)&&Array.isArray(index.parts)&&index.parts.length>0
   &&new Set(index.parts).size===index.parts.length,'Incomplete accepted membership inventory');
  for(const change of lineage.changes)if(Array.isArray(change.replaces))for(const member of change.replaces){
   const changes=memberOwners.get(member)??[];changes.push(change);memberOwners.set(member,changes);
  }
  const paths=new Set();
  for(const pin of membership.parts){
   demand(index.parts.includes(pin.path.slice(5))&&pin.path.startsWith('data/')&&!paths.has(pin.path),
    'Foreign or duplicate accepted membership part');paths.add(pin.path);
   const collection=current(pin);
   demand(collection.type==='FeatureCollection'&&Array.isArray(collection.features),'Incomplete accepted membership part');
   for(const feature of collection.features){
    demand(owners.has(feature.id)&&!canonicalOwners.has(feature.id),'Foreign or duplicate accepted membership owner');
    canonicalOwners.set(feature.id,feature);
   }
  }
 }
 const reconcile=(id,originals)=>{
  const changes=memberOwners.get(id)??[],direct=owners.get(id);
  if(direct){
   demand(changes.length===0||changes.length===1&&changes[0].id===id,
    'Source member conflicts with a direct native owner');
   if(changes.length===0||changes[0].replaces.length===1)return {id,pixelIndex:direct};
  }
  demand(changes.length===1,'Missing or ambiguous accepted source membership');
  const change=changes[0],accepted=canonicalOwners.get(change.id),members=accepted?.properties?.metadata?.source_member_ids;
  demand(accepted&&owners.has(change.id)&&Array.isArray(members)&&members.length>0
   &&members.every(member=>typeof member==='string'&&member)&&new Set(members).size===members.length
   &&same([...members].sort(),[...change.replaces].sort()),'Incomplete accepted aggregation member set');
  for(const member of members){
   const reverse=memberOwners.get(member);
   demand(originals.has(member)&&(!owners.has(member)||member===change.id)&&reverse?.length===1&&reverse[0]===change,
    'Missing or conflicting complete source aggregation member');
  }
  return {id:change.id,pixelIndex:owners.get(change.id),feature:accepted};
 };

 // The executing accepted tree, not reader.version or a caller's review flag,
 // anchors the typed interpretation. Upstream public bodies retain their pins.
 const datedCentres=[];
 if(dated){
  const pin=evidence.dated_land_support;pinCheck(pin);
  const moduleRoot=fileURLToPath(new URL('../../../',import.meta.url));
  const currentVersion=execFileSync(reader.gitExecutable,['-c','core.hooksPath=/dev/null','-C',moduleRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
  const current=reader.descriptor(pin.path,currentVersion);
  demand(current.mode===pin.mode&&current.git_blob_oid===pin.git_blob_oid&&current.bytes===pin.bytes,
   'Dated land support differs from executing accepted input');
  const data=JSON.parse(read(pin));
  const keys=(v,list)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===list.split(',').sort().join(',');
  demand(keys(data,'version,kind,native_contract_sha256,provenance,records')&&data.version===1
   &&data.kind==='adopted-dated-native-centre-land-support-v1'
   &&data.native_contract_sha256===valueSha(evidence.native_contract)
   &&Array.isArray(data.provenance)&&data.provenance.length>0
   &&Array.isArray(data.records)&&data.records.length>0,'Incomplete adopted dated land support');
  const pointer=(body,name)=>{
   demand(typeof name==='string'&&name.startsWith('/')&&!/~(?![01])/.test(name),'Invalid dated evidence pointer');
   let value=body;
   for(const part of name.slice(1).split('/').map(p=>p.replace(/~1/g,'/').replace(/~0/g,'~'))){
    demand(value&&typeof value==='object'&&Object.hasOwn(value,part),'Missing dated evidence record');value=value[part];
   }
   return value;
  };
  const relative=(base,name,levels=1)=>{
   demand(typeof name==='string'&&!name.includes('\\')&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'),
    'Unsafe dated evidence relative path');
   return [...base.split('/').slice(0,-levels),...name.split('/')].join('/');
  };
  const instant=value=>{
   const m=typeof value==='string'&&/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z$/.exec(value);
   demand(m&&Number.isFinite(Date.parse(value))&&new Date(value).toISOString().slice(0,19)===m[1],
    'Invalid dated acquisition instant');
   const fraction=(m[2]??'').replace(/0+$/,'');return m[1]+(fraction?'.'+fraction:'')+'Z';
  };
  // Authenticate native PNG context as complete encoded bytes. It is not JSON
  // and no pixel-decoding or scientific reinterpretation is performed here.
  const readFrame=p=>{
   pinCheck(p);demand(p.decoded_bytes===undefined,'Native PNG context must be an ordinary encoded body');
   let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
   const d=reader.descriptor(p.path,version);
   demand(d.mode===p.mode&&d.git_blob_oid===p.git_blob_oid&&d.bytes===p.bytes,'Dated frame whole identity differs');
   return reader.read(p.path,{version,expected:p.sha256});
  };
  const provenance=new Map(),loaded=new Map(),used=new Set();
  for(const item of data.provenance){
   demand(item&&typeof item.id==='string'&&item.id&&!provenance.has(item.id)
    &&['adoption','review','observation','frame'].includes(item.role)
    &&keys(item,item.role==='frame'?'id,role,pin,observation,block_pointer,display_pointer,channels,display_base':'id,role,pin'),
   'Foreign or duplicate dated evidence role');
   pinCheck(item.pin);const identity=item.pin.commit+':'+item.pin.path;
   let content=loaded.get(identity);
   if(content)demand(same(content.pin,item.pin)&&content.frame===(item.role==='frame'),'Conflicting dated evidence body role');
   else{
    const frame=item.role==='frame',raw=frame?readFrame(item.pin):read(item.pin);
    demand(!frame||raw.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])),'Missing native PNG context');
    content={pin:item.pin,frame,body:frame?null:JSON.parse(raw)};loaded.set(identity,content);
   }
   provenance.set(item.id,{...item,body:content.body});
  }
  const reference=(ref,role,fields='id,pointer')=>{
   demand(keys(ref,fields),'Malformed dated evidence reference');const item=provenance.get(ref.id);
   demand(item?.role===role,'Missing dated evidence role: '+role);used.add(item.id);
   return {item,value:pointer(item.body,ref.pointer)};
  };
  const seen=new Set();
  for(const record of data.records){
   demand(keys(record,'source_id,pixelIndex,y,x,longitude,latitude,adoption,review,observations')
    &&typeof record.source_id==='string'&&record.source_id&&Number.isSafeInteger(record.pixelIndex)&&record.pixelIndex>0
    &&Number.isSafeInteger(record.y)&&record.y>=0&&record.y<262166
    &&Number.isSafeInteger(record.x)&&record.x>=0&&record.x<262166
    &&record.longitude===(record.x+.5)/262166*360-180&&record.latitude===latitudes[record.y],
   'Dated land native centre differs');
   const identity=record.pixelIndex+':'+record.y+':'+record.x;
   demand(!seen.has(identity),'Duplicate dated land centre');seen.add(identity);
   const target=evidence.targets.find(t=>t.id===record.source_id);
   demand(target?.pixelIndex===record.pixelIndex&&target.coverage_classes?.includes('mapped_land_support'),
    'Dated land lacks exact requested source member and land class');
   const key={owner:record.pixelIndex,y:record.y,x:record.x};
   const adoption=reference(record.adoption,'adoption'),a=adoption.value;
   demand(a&&same(a.original_key,key)&&same(a.centre_unchanged,{...key,longitude:record.longitude,latitude:record.latitude})
    &&a.original_record_unchanged&&['owner','y','x'].every(k=>a.original_record_unchanged[k]===key[k])
    &&Number.isSafeInteger(a.original_source_array_index)&&a.original_source_array_index>=0
    &&Number.isSafeInteger(a.plan_index)&&a.plan_index>=0&&a.adopted_bounded_answer===true
    &&a.category==='dated-terrestrial-body-location'&&a.remaining_physical_question===null
    &&typeof a.actual_answer==='string'&&a.actual_answer.trim()&&typeof a.source_review_kind==='string'&&a.source_review_kind
    &&Array.isArray(a.answer_dates)&&a.answer_dates.length>0,'Missing adopted terrestrial centre interpretation');
   const review=reference(record.review,'review','id,pointer,interpretation_pointer'),r=review.value;
   demand(a.review&&review.item.pin.path===relative(adoption.item.pin.path,a.review.path)
    &&r&&same(r.original_key,key)&&r.index===a.review.record_index
    &&r.original_source_array_index===a.original_source_array_index
    &&(review.item.body.records?.includes(r)||review.item.body.points?.includes(r))
    &&pointer(r,record.review.interpretation_pointer)===a.source_review_kind,
   'Dated centre substantive review differs');
   const dates=a.answer_dates.map(value=>{
    if(typeof value==='string'&&/^\d{4}-\d\d-\d\d$/.test(value)){instant(value+'T00:00:00Z');return value;}
    return instant(value);
   }),observed=new Set();
   demand(new Set(dates).size===dates.length&&Array.isArray(record.observations)&&record.observations.length===dates.length,
    'Incomplete dated centre observation dates');
   for(const ref of record.observations){
    const observation=reference(ref,'observation','id,pointer,frames'),o=observation.value,body=observation.item.body;
    const date=instant(body.acquisition_datetime);
    const matched=dates.filter(d=>d===date||d.length===10&&date.startsWith(d+'T'));
    demand(matched.length===1&&!observed.has(matched[0])&&typeof body.item==='string'&&body.item
     &&o&&same(o.original_key,key)&&o.index===a.plan_index&&o.longitude===record.longitude&&o.latitude===record.latitude
     &&Array.isArray(body.points)&&body.points.includes(o)&&Array.isArray(o.physical_block)
     &&Array.isArray(ref.frames)&&ref.frames.length===2,'Dated centre observation or scene differs');observed.add(matched[0]);
    const channels=new Set();
    for(const id of ref.frames){
     const f=provenance.get(id);demand(f?.role==='frame'&&f.observation===ref.id
      &&['rgb','nir-red-green'].includes(f.channels)&&!channels.has(f.channels),'Dated centre native frame differs');
     used.add(id);channels.add(f.channels);
     const block=pointer(body,f.block_pointer),display=pointer(body,f.display_pointer);
     demand(Array.isArray(body.blocks)&&body.blocks.includes(block)&&same(block.block,o.physical_block)
      &&Array.isArray(block.indices)&&block.indices.includes(o.index)&&Array.isArray(block.displays)&&block.displays.includes(display)
      &&typeof display.path==='string'&&display.path.split('/').includes(body.item)
      &&display.path.endsWith('/'+f.channels+'-native.png')
      &&typeof f.display_base==='string'&&!f.display_base.includes('\\')
      &&f.display_base.split('/').every(p=>p&&p!=='.'&&p!=='..')
      &&f.pin.path===relative(f.display_base+'/_',display.path)
      &&display.bytes===f.pin.bytes&&display.sha256===f.pin.sha256,'Dated native frame registration differs');
    }
   }
   datedCentres.push({source_id:record.source_id,pixelIndex:record.pixelIndex,y:record.y,x:record.x});
  }
  demand(used.size===provenance.size,'Unused dated evidence provenance');
 }
 const targets=new Map(), resolvedTargets=new Map(), residualsByOwner=new Map(), generalOwners=new Set();
 for(const target of evidence.targets){
  const ownerId=target.target_id??target.id;
  demand(typeof target.id==='string'&&target.id&&!targets.has(target.id)&&owners.get(ownerId)===target.pixelIndex&&hash(target.source_receipt_sha256),
   'Foreign or duplicate source-target identity');
  const supports=physical.results.filter(result=>result.target===target.id);
  demand(supports.length===1,'Missing or duplicate physical source member');const support=supports[0];
  demand(target.source_receipt_sha256===evidence.physical_evidence.sha256,
   'Missing qualified physical source interpretation');
  const residuals=reconstructionResidualPointsets(support,dated);
  const generalIssues=support.issues.some(i=>!['missing_reconstruction','extra_reconstruction'].includes(i.reason)
   ||!['Polygon','MultiPolygon'].includes(i.geometry?.type));
  if(generalIssues)generalOwners.add(target.pixelIndex);
  if(residuals.length){
   const item=residualsByOwner.get(target.pixelIndex)??{index:target.pixelIndex,witnesses:[]};
   item.witnesses.push(...residuals);
   residualsByOwner.set(target.pixelIndex,item);
  }
  demand(Array.isArray(target.coverage_classes)&&target.coverage_classes.length>0
   &&target.coverage_classes.every(kind=>['mapped_land_support','mapped_inland_water_support'].includes(kind))
   &&new Set(target.coverage_classes).size===target.coverage_classes.length,
   'Unresolved physical support cannot qualify a repair');
  const hasDated=datedCentres.some(p=>p.source_id===target.id);
  const polygons=target.coverage_classes.flatMap(kind=>{const geometry=support.support[kind];
   if(hasDated&&validateWitnessGeometry(geometry).empty)return [];coordinateBounds(geometry);
   return geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;});
  target.coverage_geometry={type:'MultiPolygon',coordinates:polygons};
  coordinateBounds(target.base_geometry);
  targets.set(target.id,target);
  const prior=resolvedTargets.get(ownerId);
  demand(!prior||prior.pixelIndex===target.pixelIndex&&prior.source_family===target.source_family
   &&same(prior.base_geometry,target.base_geometry),'Conflicting accepted target base or source family');
  if(!prior)resolvedTargets.set(ownerId,{...target,id:ownerId});
 }
 const rowsByOwner=new Map();let previous=-1;
 for(const row of proposed.rows){
  demand(Number.isSafeInteger(row.y)&&row.y>previous&&row.y<262166&&Array.isArray(row.runs),
   'Invalid source-target native row');previous=row.y;let end=0;
  for(const run of row.runs){
   demand(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end
    &&run[1]>run[0]&&run[1]<=262166&&[...targets.values()].some(t=>t.pixelIndex===run[2]),
   'Foreign or conflicting proposed source-target interval');end=run[1];
   const list=rowsByOwner.get(run[2])??[];let item=list.at(-1);
   if(item?.y!==row.y){item={y:row.y,runs:[]};list.push(item);}item.runs.push(run);rowsByOwner.set(run[2],list);
  }
 }
 // Optional explicit class rows bind land/water identity at each requested
 // centre. They partition the complete owner patch and cannot introduce cells.
 const coverageRowsByOwner=new Map();
 const unionRows=rows=>rows.map(row=>{const runs=[];for(const run of row.runs){
  const prior=runs.at(-1);if(prior&&prior[1]===run[0])prior[1]=run[1];else runs.push(run.slice(0,2));
 }return {y:row.y,runs};});
 for(const target of targets.values())if(target.coverage_rows!==undefined){
  const rows=target.coverage_rows;demand(Array.isArray(rows)&&rows.length>0,'Missing native coverage class rows');
  let priorY=-1;
  for(const row of rows){demand(row&&Object.keys(row).sort().join(',')==='runs,y'
   &&Number.isSafeInteger(row.y)&&row.y>priorY&&row.y<262166&&Array.isArray(row.runs)&&row.runs.length>0,
  'Invalid native coverage class row');priorY=row.y;let end=0;
   for(const run of row.runs){demand(Array.isArray(run)&&run.length===3
    &&Number.isSafeInteger(run[0])&&Number.isSafeInteger(run[1])&&run[0]>=end&&run[1]>run[0]&&run[1]<=262166
    &&['mapped_land_support','mapped_inland_water_support'].includes(run[2]),'Invalid native coverage class interval');end=run[1];}
  }
  demand(same(unionRows(rows),unionRows(rowsByOwner.get(target.pixelIndex)??[])),
   'Native coverage classes differ from complete requested owner cells');
  const prior=coverageRowsByOwner.get(target.pixelIndex);
  demand(!prior||same(prior,rows),'Conflicting sibling native coverage class bindings');
  coverageRowsByOwner.set(target.pixelIndex,rows);
 }
 const diagnosticRows=new Map(); let firstFailure=null;
 const recordDiagnostic=(y,start,end,owner,reason)=>{
  const runs=diagnosticRows.get(y)??[],prior=runs.at(-1);
  if(prior&&prior[1]===start&&prior[2]===owner&&prior[3]===reason)prior[1]=end;
  else runs.push([start,end,owner,reason]);diagnosticRows.set(y,runs);
 };
 const checked=new Set(),families=new Set(),physicalContextHits=[];
 for(const family of evidence.families){
  demand(typeof family.source_id==='string'&&!families.has(family.source_id),'Duplicate source family');families.add(family.source_id);
  const record=catalogue.products.find(product=>product.key===family.source_id);
  demand(record&&family.parts.length===record.parts.length,'Missing complete original source family');
  const pieces=family.parts.map((pin,i)=>{
   const expected=record.parts[i];demand(pin.path===expected.path&&pin.sha256===expected.sha256
    &&pin.bytes===expected.bytes&&pin.decoded_bytes===expected.uncompressed_bytes
    &&pin.decoded_sha256===expected.uncompressed_sha256,'Source family part differs from retained catalogue');return read(pin);
  });
  const raw=Buffer.concat(pieces);demand(raw.length===record.original_bytes&&sha(raw)===record.original_sha256,
   'Whole original consumed source product differs');
  const product=JSON.parse(raw);demand(product.features?.length===record.feature_count,'Incomplete original source feature roster');
  const originals=new Map();
  for(const feature of product.features){
   const sourceId=feature.properties?.shapeID;
   demand(typeof sourceId==='string'&&sourceId&&!originals.has(family.source_id+':'+sourceId),
    'Duplicate or missing original source feature identity');originals.set(family.source_id+':'+sourceId,feature);
  }
  const selected=evidence.targets.filter(target=>target.source_family===family.source_id);
  demand(selected.length>0,'Unused source family');
  for(const target of selected){const original=originals.get(target.id),owner=reconcile(target.id,originals);
   const measured=physicalInputs.filter(input=>input.target===target.id);
   demand(owner.id===(target.target_id??target.id)&&owner.pixelIndex===target.pixelIndex,
    'Source member differs from accepted target mapping');
   demand(!owner.feature||same(owner.feature.geometry,target.base_geometry),'Accepted aggregate base geometry differs');
   demand(original&&measured.length===1&&same(measured[0].consumed.geometry,original.geometry)
    &&measured[0].selected.id===owner.id&&same(measured[0].selected.geometry,target.base_geometry),
    'Physical source query or selected target differs from measured whole inputs');
  }
  // A retained measured sibling cannot escape its owner's veto by being
  // omitted from the positive selected-target roster. Its complete source and
  // canonical base joins remain mandatory; it supplies no borrowed coverage.
  const selectedOwners=new Set(selected.map(t=>t.pixelIndex));
  for(const [id,original]of originals)if(!targets.has(id)){
   const candidateOwner=selectedOwners.has(owners.get(id))
    ||(memberOwners.get(id)??[]).some(change=>selected.some(t=>(t.target_id??t.id)===change.id));
   if(!candidateOwner)continue;
   const measured=physicalInputs.filter(input=>input.target===id);
   const results=physical.results.filter(result=>result.target===id);
   if(!measured.length&&!results.length)continue;
   const owner=reconcile(id,originals),target=resolvedTargets.get(owner.id);
   demand(selectedOwners.has(owner.pixelIndex)&&target
    &&measured.length===1&&results.length===1,'Missing or duplicate measured sibling physical interpretation');
   demand(same(measured[0].consumed.geometry,original.geometry)&&measured[0].selected.id===owner.id
    &&same(measured[0].selected.geometry,target.base_geometry)
    &&(!owner.feature||same(owner.feature.geometry,target.base_geometry)),
   'Measured sibling differs from complete original or accepted owner base');
   const witnesses=reconstructionResidualPointsets(results[0],dated);
   if(results[0].issues.some(i=>!['missing_reconstruction','extra_reconstruction'].includes(i.reason)
    ||!['Polygon','MultiPolygon'].includes(i.geometry?.type)))generalOwners.add(owner.pixelIndex);
   if(witnesses.length){const item=residualsByOwner.get(owner.pixelIndex)??{index:owner.pixelIndex,witnesses:[]};
    item.witnesses.push(...witnesses);residualsByOwner.set(owner.pixelIndex,item);}
  }
  for(const target of selected)if(generalOwners.has(target.pixelIndex)){
   demand(target.coverage_classes.length===1||coverageRowsByOwner.has(target.pixelIndex),
    'Mixed physical conflict coverage requires explicit native class rows');
   demand(Array.isArray(target.territorial_exclusions),
    'General physical conflict qualification requires explicit territorial exclusions');
  }
  const bounds=selected.flatMap(target=>coordinateBounds(datedCentres.some(p=>p.source_id===target.id)
   ?originals.get(target.id).geometry:target.coverage_geometry));
  const intersects=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
  const sourceFeatures=product.features.filter(feature=>coordinateBounds(feature.geometry).some(part=>bounds.some(box=>intersects(part,box))))
   .map(feature=>{const id=family.source_id+':'+feature.properties.shapeID;
    const owner=reconcile(id,originals);
    return {id,target_id:owner.id,pixelIndex:owner.pixelIndex,geometry:feature.geometry};});
  const coverageFeatures=selected.filter(t=>t.coverage_geometry.coordinates.length).map(target=>({id:target.target_id??target.id,source_id:target.id,pixelIndex:target.pixelIndex,geometry:target.coverage_geometry}));
  let exclusions=selected.flatMap(target=>(target.territorial_exclusions??[]).map(geometry=>({id:target.target_id??target.id,pixelIndex:target.pixelIndex,geometry})));
  // Qualification requires coverage; discard only whole exclusions proven
  // disjoint from every complete coverage part. Keep diagnostic reasons intact.
  if(!diagnostic)exclusions=exclusions.filter(feature=>coordinateBounds(feature.geometry)
   .some(part=>bounds.some(box=>intersects(part,box))));
  const blocks=new Map();
  for(const row of proposed.rows)if(row.runs.some(run=>selectedOwners.has(run[2]))){
   const block=Math.floor(row.y/4096);const list=blocks.get(block)??[];list.push(row);blocks.set(block,list);
  }
  for(const [block,rows]of blocks){
   const rowStart=block*4096,rowEnd=Math.min(262166,rowStart+4096);
   // Preserve every actual role/member contact. Only exact exterior interiors
   // can be considered below, after the unchanged native source/owner guards.
   const residualHits=new Set(),waterHits=new Set(),exteriorHits=[];
   for(const item of residualsByOwner.values())if(selectedOwners.has(item.index)){
    const requestedRows=rows.map(row=>({y:row.y,runs:row.runs.filter(run=>run[2]===item.index)}))
     .filter(row=>row.runs.length);
    for(const witness of item.witnesses){
     validateWitnessGeometry(witness.geometry);
     const effects=witnessCellEffects(witness.geometry,{size:262166,latitudes,requestedRows,nativePolygonIntervals});
     for(const hit of effects.hits){
      const key=item.index+':'+hit.y+':'+hit.x;
      if(witness.role==='mapped_inland_water_support')waterHits.add(key);
      else if(witness.role==='outside_mapped_L1_context')exteriorHits.push({
       source_id:witness.source_id,pixelIndex:item.index,role:witness.role,...hit});
      else residualHits.add(key);
     }
    }
   }
   // Class masks share the complete source/exclusion scan below, but retain
   // independent member coverage and boundary adjudication.
   const blockCentres=datedCentres.filter(p=>selected.some(t=>t.id===p.source_id)&&p.y>=rowStart&&p.y<rowEnd);
   // Actual mapped water contradicts this typed terrestrial-centre claim even
   // when no exterior context is present. Other mapped-water class cells retain
   // their existing semantics; only exact authenticated dated-land keys veto.
   for(const point of blockCentres){
    const key=point.pixelIndex+':'+point.y+':'+point.x;
    if(waterHits.has(key))residualHits.add(key);
   }
   const classes=[],coverageFeatureGroups=[],coverageCentreGroups=[];
   for(const kind of ['mapped_land_support','mapped_inland_water_support'])
    if(selected.some(t=>coverageRowsByOwner.has(t.pixelIndex))){
     if(selected.every(t=>t.coverage_classes.length===1&&t.coverage_classes[0]===kind)){
      classes.push({kind,combined:true});continue;
     }
     const features=selected.filter(t=>t.coverage_classes.includes(kind)).flatMap(t=>{
      const geometry=physical.results.find(r=>r.target===t.id).support[kind];
      if(datedCentres.some(p=>p.source_id===t.id)&&validateWitnessGeometry(geometry).empty)return [];
      return [{id:t.target_id??t.id,source_id:t.id,pixelIndex:t.pixelIndex,geometry}];
     });
     const centres=kind==='mapped_land_support'?blockCentres:[];
     if(features.length===0&&centres.length===0){classes.push({kind,empty:true});continue;}
     classes.push({kind,group:coverageFeatureGroups.length});coverageFeatureGroups.push(features);coverageCentreGroups.push(centres);
    }
   if(coverageFeatureGroups.length)for(const feature of [...sourceFeatures,...exclusions,...coverageFeatureGroups.flat()])
    validateWitnessGeometry(feature.geometry);
   // Empty rows here derive the permitted source/coverage domain, not a claim
   // about actual ownership. Actual current owner zero is enforced separately
   // by selectedAdditiveRows and the emitted native patch application.
   const allowed=deriveSourceTargetNativeDelta({targets:[...resolvedTargets.values()].filter(target=>target.source_family===family.source_id).map(({id,pixelIndex})=>({id,pixelIndex})),
    sourceFeatures,coverageFeatures,territorialExclusions:exclusions,size:262166,latitudes,rowStart,rowEnd,
    ...(dated?{coverageCentres:blockCentres}:{}),
    ...(coverageFeatureGroups.length?{coverageFeatureGroups,...(dated?{coverageCentreGroups}:{})}:{}),
    ...(diagnostic?{diagnosticRows:rows.map(row=>({y:row.y,runs:row.runs.filter(r=>selectedOwners.has(r[2]))})).filter(row=>row.runs.length)}:{}),
    ownerRows:Array.from({length:rowEnd-rowStart},(_,i)=>({y:rowStart+i,complete_owner_intervals:[]}))});
   const allowedRows=new Map(allowed.rows.map(row=>[row.y,row.runs]));
   // The native view reuses its existing complete source scan and decision;
   // owner equality alone never lets an active sibling lend its dated support.
   const matchedCentres=new Set((allowed.source_matched_coverage_centres??[])
    .map(p=>JSON.stringify([p.source_id,p.pixelIndex,p.y,p.x])));
   for(const hit of exteriorHits){
    const key=hit.pixelIndex+':'+hit.y+':'+hit.x;
    const superseded=hit.kind==='interior'&&!waterHits.has(key)
     &&matchedCentres.has(JSON.stringify([hit.source_id,hit.pixelIndex,hit.y,hit.x]));
    if(!superseded)residualHits.add(key);
    if(dated)physicalContextHits.push({...hit,resolution:superseded
     ?'superseded-by-adopted-dated-terrestrial-centre':'retained-exterior-veto'});
   }
   const decisionRows=diagnostic?new Map(allowed.diagnostic_rows.map(row=>[row.y,row.runs])):null;
   const classAllowed=new Map(classes.map(item=>[item.kind,item.combined?allowedRows:item.empty?new Map()
    :new Map(allowed.coverage_groups[item.group].rows.map(row=>[row.y,row.runs]))]));
   for(const row of rows)for(const run of row.runs)if(selectedOwners.has(run[2])){
    if(diagnostic){
     const cellReasons=[];
     for(let x=run[0];x<run[1];x++){
      const sourceDecision=(decisionRows.get(row.y)??[]).find(span=>span[2]===run[2]&&span[0]<=x&&x<span[1]);
      demand(sourceDecision,'Incomplete requested native diagnostic trace');
      let reason=residualHits.has(run[2]+':'+row.y+':'+x)?'physical-reconstruction-residual-or-conflict':sourceDecision[3];
      const segment=coverageRowsByOwner.get(run[2])?.find(r=>r.y===row.y)?.runs.find(span=>span[0]<=x&&x<span[1]);
      if(reason==='assigned_cells'&&segment&&!(classAllowed.get(segment[2])?.get(row.y)??[])
       .some(span=>span[2]===run[2]&&span[0]<=x&&x<span[1]))reason='declared-land-water-class-support';
      recordDiagnostic(row.y,x,x+1,run[2],reason);cellReasons.push(reason);
     }
     if(!firstFailure){
      const residual=cellReasons.includes('physical-reconstruction-residual-or-conflict');
      const covered=(allowedRows.get(row.y)??[]).some(span=>span[2]===run[2]&&span[0]<=run[0]&&span[1]>=run[1]);
      const classFailure=cellReasons.includes('declared-land-water-class-support');
      if(residual||!covered||classFailure)firstFailure={y:row.y,run:[...run],predicate:residual
       ?'physical-reconstruction-residual-or-conflict':!covered?'unique-source-target-coverage':'declared-land-water-class-support'};
     }
     checked.add(row.y+':'+run.join(':'));continue;
    }
    for(let x=run[0];x<run[1];x++)demand(!residualHits.has(run[2]+':'+row.y+':'+x),
     'Requested native cells intersect a physical reconstruction residual or conflict witness');
    demand((allowedRows.get(row.y)??[]).some(span=>span[2]===run[2]&&span[0]<=run[0]&&span[1]>=run[1]),
     'Proposed native cells lack unique source-target coverage');
    for(const segment of coverageRowsByOwner.get(run[2])?.find(r=>r.y===row.y)?.runs??[]){
     const start=Math.max(segment[0],run[0]),end=Math.min(segment[1],run[1]);if(start>=end)continue;
     demand((classAllowed.get(segment[2])?.get(row.y)??[]).some(span=>span[2]===run[2]&&span[0]<=start&&span[1]>=end),
      'Requested native cells lack declared land/water class support');
    }checked.add(row.y+':'+run.join(':'));
   }
  }
 }
 demand(checked.size===proposed.rows.reduce((n,row)=>n+row.runs.length,0),'Unqualified proposed native intervals');
 if(diagnostic){
  const decisions=[...diagnosticRows].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>({y,runs:runs.sort((a,b)=>a[0]-b[0])}));
  const partition=accepted=>decisions.map(row=>{const runs=[];
   for(const [start,end,owner,reason]of row.runs)if((reason==='assigned_cells')===accepted){
    const prior=runs.at(-1);if(prior&&prior[1]===start&&prior[2]===owner)prior[1]=end;else runs.push([start,end,owner]);
   }return {y:row.y,runs};}).filter(row=>row.runs.length);
  const supported=partition(true),held=partition(false),count=rows=>rows.reduce((n,row)=>n+row.runs.reduce((m,r)=>m+r[1]-r[0],0),0);
  const requested=count(proposed.rows),supportedCells=count(supported),heldCells=count(held);
  demand(supportedCells+heldCells===requested,'Incomplete native diagnostic partition');
  const result={version:1,kind:'source-target-native-diagnostic-v1',requested_rows:proposed.rows,
   supported_rows:supported,held_rows:held,decision_rows:decisions,first_failure:firstFailure,
   requested_cells:requested,supported_cells:supportedCells,held_cells:heldCells,
   original_pins:{source_evidence:binding.source_evidence,native_patch:binding.native_patch},
   ...(dated?{physical_context_hits:physicalContextHits}:{}),
   rule_sha256:valueSha(preimage),native_contract:evidence.native_contract,
   limitations:['Native diagnostic screening only; no authority products, current-owner-zero, acceptance or whole-source clearance.',
    'All original source, physical, query, witness and territorial limits remain retained.']};
  return result;
 }
 const ledgerRows=[...resolvedTargets.values()].map(target=>{
  const native_rows=rowsByOwner.get(target.pixelIndex)??[];demand(native_rows.length>0,'Zero-cell source-target repair');
  let west=262166,east=0;for(const row of native_rows)for(const run of row.runs){west=Math.min(west,run[0]);east=Math.max(east,run[1]-1);}
  const native_bounds=[(west+.5)/262166*360-180,latitudes[native_rows.at(-1).y],
   (east+.5)/262166*360-180,latitudes[native_rows[0].y]];
  return {representation:'native-cells',component_id:'source-target:'+valueSha({target_id:target.id,evidence:binding.source_evidence.sha256}),
   target_id:target.id,pixelIndex:target.pixelIndex,disposition:'assigned',base_geometry:target.base_geometry,
   base_geometry_sha256:valueSha(target.base_geometry),source_receipt_sha256:target.source_receipt_sha256,
   native_rows,native_bounds,native_cells:native_rows.reduce((n,row)=>n+row.runs.reduce((n,run)=>n+run[1]-run[0],0),0)};
 }).sort((a,b)=>a.component_id.localeCompare(b.component_id));
 return {source_scope_ids:ledgerRows.map(row=>row.component_id),original_ledger:{version:2,kind:'native-additive-repair-ledger-v2',
  scope_ids:ledgerRows.map(row=>row.component_id),rows:ledgerRows},source_rows:ledgerRows,
  native_proof:{native_contract:evidence.native_contract,native_patches:[{base_reference:evidence.base_reference,rows:proposed.rows}]},
  original_pins:{source_evidence:binding.source_evidence,native_patch:binding.native_patch},
  ...(dated?{physical_context_hits:physicalContextHits}:{}),
  limitations:['Physical interpretation and semantic reconciliation are retained reviewed source evidence; actual current owner-zero is checked by native consumers.',
   'Witness exclusion applies only to requested native centres. Original whole-source physical/hierarchy issues and historical source/resource limits remain retained; no whole-parent certification or acceptance is inferred.']};
}

// One detached authority acquisition. The returned view cannot authorize a
// selected release: the committed hook must additionally authenticate the
// qualified native publication, operating proof and actual current bank.
export function readRetainedRegistryAuthority(reader, entry, observationReader, {snapshot}={}) {
 // Retain every actual whole input consumed by a detached authority reader.
 const observed=proof=>{
  if(observationReader!==undefined){
   demand(observationReader instanceof ImmutableReader&&observationReader.repo===reader.repo,'Require an actual immutable authority observer');
   for(const pin of reader.inventory.values())if(pin.whole_body_consumed===true){
    const key=pin.commit+':'+pin.path,prior=observationReader.inventory.get(key);
    demand(!prior||['commit','path','mode','git_blob_oid','bytes'].every(field=>prior[field]===pin[field])
     &&(prior.sha256===undefined||prior.sha256===pin.sha256),'Detached consumed-input custody differs');
    observationReader.inventory.set(key,{...pin});
   }
   if(typeof observationReader.captureSelectedInputs==='function')
    observationReader.captureSelectedInputs([...reader.inventory.values()].filter(pin=>pin.whole_body_consumed===true));
  }
  return proof;
 };
 const singleton={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};
 authorityRegistry(singleton);
 const pins=[entry.rule_preimage,entry.source_authority];
 const admitted=pins.map(p=>{
  pinCheck(p);let version=p.commit;
  try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);
  demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Registry authority whole mode/OID differs');
  return {p,version};
 });
 const [preimage,binding]=admitted.map(({p,version})=>JSON.parse(reader.read(p.path,{version,expected:p.sha256})));
 demand(valueSha(preimage)===entry.rule_sha256,'Complete original registry preimage differs');
 if(binding?.kind==='source-target-native-custody-v1'){
  const proof=qualifySourceTargetNativeAuthority(reader,preimage,binding,{snapshot});
  return observed(freeze({...proof,version:1,kind:'authenticated-registry-source-custody-v1',authority_sha256:entry.authority_sha256,
   rule_sha256:entry.rule_sha256,policy_id:entry.policy_id,policy_version:entry.policy_version,pins}));
 }
 demand(binding?.version===1&&binding.kind==='original-issued-rule-source-custody-v1'&&['kind,native_proof,original_pins,version','kind,native_proof,original_pins,source_output_aliases,version'].includes(Object.keys(binding).sort().join(',')),'Unsupported original authority binding');
 const custody=readOriginalRuleAuthority(reader,binding.original_pins,binding.source_output_aliases??[]);
 demand(same(preimage,custody.rule_preimage)&&custody.rule_sha256===entry.rule_sha256,'Registry relabelled original executed rule');
 const original=originalAuthorities.get(custody).bodies;
 const codeIdentity=rows=>rows.map(p=>{demand(Object.keys(p).sort().join(',')==='bytes,path,sha256','Unsupported original complete code roster shape');return {path:p.path,bytes:p.bytes,sha256:p.sha256};});
 const programmeAuthority=readSupportedProgrammeAuthority(reader,{preimageVersion:preimage.version,sourceProfile:custody.source_rule.profile??null,sourceCode:codeIdentity(original.source_request.executed_code),nativeCode:codeIdentity(original.native_request.executed_code)});
 const source=qualifyOriginalSourceAuthority(custody),native=qualifyOriginalNativeAuthority(custody,binding.native_proof);
 return observed(freeze({version:1,kind:'authenticated-registry-source-custody-v1',authority_sha256:entry.authority_sha256,
  rule_sha256:entry.rule_sha256,original_program_authority:programmeAuthority,policy_id:entry.policy_id,policy_version:entry.policy_version,
  pins,original_pins:binding.original_pins,source_scope_ids:custody.source_scope_ids,
  source_rows:source.rows,native_proof:native,original_ledger:custody.ledger,
  limitations:['Whole original preimage, issued requests and qualified source predecessor authenticated. Policy semantics and actual current selected-bank applicability remain separately required; this view cannot authorize selection.']}));
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
  if(nativeOnlyComponent({...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256},valueSha)){rows.set(row.component_id,{...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256});continue;}
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
// Historical observations remain authenticated receipt content. New products
// need only their actual input/output and execution-outcome custody.
const rebindReceiptKeys=(v,required,historical,m)=>{
 const fields=required.split(','),optional=historical.split(',');
 demand(v&&fields.every(key=>Object.hasOwn(v,key))&&Object.keys(v).every(key=>fields.includes(key)||optional.includes(key)),m);
};
export function nativeBaseSelection(selection) {
 demand(selection&&typeof selection==='object'&&!Array.isArray(selection),'Missing complete selected native identity');
 return scientificNativeSelection(selection);
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

// Literal historical execution vectors retain their original path inventory.
// Current production adds the metadata reader and its pure projection helper.
export const LEGACY_CURRENT_REBIND_CODE=Object.freeze([
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
export const CURRENT_REBIND_CODE=Object.freeze([...LEGACY_CURRENT_REBIND_CODE,
 'scripts/selected-reference-metadata.mjs','src/reference-metadata.js']);
// Historical requests select only a known complete literal profile. Their
// actual bytes are still authenticated at the original execution commit;
// recognizing a path vector never repins or requalifies that execution.
export function currentRebindCodePaths(code,{requireCurrent=false}={}) {
 demand(Array.isArray(code)&&code.every(pin=>pin&&typeof pin.path==='string'),'Foreign/incomplete current rebind execution code profile');
 const paths=code.map(pin=>pin.path);
 const profiles=requireCurrent?[CURRENT_REBIND_CODE]:[LEGACY_CURRENT_REBIND_CODE,CURRENT_REBIND_CODE];
 const profile=profiles.find(expected=>same(paths,expected));
 demand(profile,'Foreign/incomplete current rebind execution code profile');return profile;
}
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
 const proof=JSON.parse(custody.code_source),terminal=JSON.parse(custody.terminal),output=JSON.parse(custody.stdout),plan=JSON.parse(custody.issued_plan);
 rebindKeys(request.execution,'command,pre_use','Missing issued actual execution contract');
 rebindKeys(proof,'version,kind,execution_commit,command,pre_use,post_use','Foreign whole execution source proof');
 demand(proof.version===1&&proof.kind==='whole-current-rebind-execution-custody-v1'&&proof.execution_commit===request.execution_commit&&same(proof.command,request.execution.command)&&same(proof.pre_use,request.execution.pre_use)&&same(proof.pre_use,proof.post_use),'Execution source/runtime changed before/after actual command');
 const before=proof.pre_use;rebindKeys(before,'runtime,code,entry,supervisor,plan','Incomplete actual executed closure');
 demand(same(before.code,expectedCode),'Whole actual executing code closure differs');
 const ordinary=(p,installedExecutable=false,emptyStdlib=false)=>{rebindKeys(p,'path,bytes,sha256,mode','Incomplete external executing body');demand(typeof p.path==='string'&&p.path.startsWith('/')&&!p.path.split('/').some((x,i)=>i>0&&(!x||x==='.'||x==='..'))&&Number.isSafeInteger(p.bytes)&&(p.bytes>0||(emptyStdlib&&p.bytes===0&&p.sha256==='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))&&hash(p.sha256)&&(installedExecutable?[420,493,511]:[420,493]).includes(p.mode),'Unsafe/untyped external execution identity');};
 demand(Array.isArray(before.runtime)&&before.runtime.length>=3,'Missing complete actual runtime');const seen=new Set();
 for(const p of before.runtime){rebindKeys(p,'role,path,bytes,sha256,mode','Foreign installed runtime identity');const {role,...body}=p;ordinary(body,['node','git','time','supervisor-python'].includes(role),role==='supervisor-stdlib');demand(['node','git','time','supervisor-python','supervisor-stdlib','installed-dependency','process-inspector','resource-command'].includes(role)&&!seen.has(p.path),'Foreign/duplicate installed runtime');seen.add(p.path);}
 demand(['node','git','supervisor-python'].every(role=>before.runtime.filter(p=>p.role===role).length===1),'Incomplete installed runtime roles');
 const dependencyRoot='coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/';
 const dependencies=expectedCode.filter(p=>p.path.startsWith(dependencyRoot));demand(dependencies.length===5&&before.runtime.filter(p=>p.role==='installed-dependency').length===5&&dependencies.every(p=>before.runtime.some(r=>r.role==='installed-dependency'&&r.path.endsWith('/node_modules/@noble/hashes/'+p.path.slice(dependencyRoot.length))&&r.bytes===p.bytes&&r.sha256===p.sha256&&r.mode===420)),'Actual installed hash import closure differs from whole source custody');
 for(const name of ['entry','supervisor','plan'])ordinary(before[name]);
 demand(before.plan.bytes===custody.issued_plan.length&&before.plan.sha256===sha(custody.issued_plan),'Actual invoked plan whole bytes differ');
 const explicitInputs=Object.hasOwn(plan,'original_inputs');
 rebindReceiptKeys(plan,'version,kind,execution_commit,base_selection,authority_registry_sha256,original_rows_sha256,original_patch_sha256s,target_sources,predecessor_proof,executed_code'+(explicitInputs?',original_inputs':''),'limits','Foreign actual issued plan');
 if(explicitInputs)demand(Array.isArray(plan.original_inputs)&&plan.original_inputs.length===2&&new Set(plan.original_inputs.map(p=>p?.path)).size===2&&plan.original_inputs.every(p=>p&&Object.keys(p).sort().join(',')==='bytes,commit,git_blob_oid,mode,path,sha256'&&p.mode==='100644'&&typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..')&&/^[a-f0-9]{40}$/.test(p.commit)&&/^[a-f0-9]{40}$/.test(p.git_blob_oid)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&/^[a-f0-9]{64}$/.test(p.sha256)),'Missing complete original input descriptors');
 demand(plan.version===1&&plan.kind==='issued-current-rebind-acquisition-plan-v1'&&plan.execution_commit===request.execution_commit&&same(plan.base_selection,request.base_selection)&&plan.authority_registry_sha256===request.authority_registry_sha256&&plan.original_rows_sha256===valueSha(request.original_rows)&&same(plan.original_patch_sha256s,request.original_patch_sha256s)&&same(plan.target_sources,request.acquisition.target_sources)&&same(plan.predecessor_proof,request.acquisition.predecessor_proof)&&same(plan.executed_code,expectedCode)&&Object.hasOwn(plan,'limits')===Object.hasOwn(request,'limits')&&(!Object.hasOwn(plan,'limits')||same(plan.limits,request.limits)),'Actual cold issued input plan changes complete original/current operands');
 const command=proof.command,plain=Array.isArray(command)&&command.length===4;
 demand(plain||Array.isArray(command)&&(command.length===6||command.length===7&&command[3]==='--expose-gc'),'Foreign external rebind command shape');
 const destination=command.at(-1);
 demand(command.every(p=>typeof p==='string')&&destination.startsWith('/')&&!destination.split('/').some((x,i)=>i>0&&(!x||x==='.'||x==='..')),'Unsafe external rebind command destination');
 if(plain)demand(command[0]===before.runtime.find(p=>p.role==='node').path&&command[1]===before.entry.path&&command[2]===before.plan.path,'Actual external command differs from bound runtime/entry/plan/destination');
 else{
  const boundCommand=command.length===7?command.toSpliced(3,1):command;
  demand(before.runtime.filter(p=>p.role==='time').length===1&&boundCommand[0]===before.runtime.find(p=>p.role==='time').path&&['-l','-v'].includes(command[1])&&boundCommand[2]===before.runtime.find(p=>p.role==='node').path&&boundCommand[3]===before.entry.path&&boundCommand[4]===before.plan.path,'Historical external command differs from bound runtime/entry/plan/destination');
 }
 rebindReceiptKeys(terminal,'version,kind,execution_commit,command,request_sha256,publication_sha256,code_source_sha256,exit_code,signal,guard_reason,elapsed_seconds,owned_processes_remaining,termination_events','lifetime_rss_bytes,sampled_group_peak_bytes,sampled_stop_bytes,lifetime_ceiling_bytes,wall_limit_seconds','Foreign actual terminal roster');
 demand(terminal.version===1&&terminal.kind==='current-rebind-external-terminal-v1'&&terminal.execution_commit===request.execution_commit&&same(terminal.command,command)&&terminal.request_sha256===operating.request_sha256&&terminal.publication_sha256===operating.publication_sha256&&terminal.code_source_sha256===operating.execution_custody.code_source.sha256&&Number.isSafeInteger(terminal.exit_code)&&terminal.exit_code===0&&terminal.signal===null&&terminal.guard_reason===null&&Array.isArray(terminal.owned_processes_remaining)&&terminal.owned_processes_remaining.length===0&&Array.isArray(terminal.termination_events)&&terminal.termination_events.length===0,'Failed/foreign external command or surviving owned process');
 demand(Number.isFinite(terminal.elapsed_seconds)&&terminal.elapsed_seconds>=0&&terminal.elapsed_seconds===operating.elapsed_seconds,'External elapsed journal differs from actual operating observation');
 // Old immutable timed receipts retain their original observation identity.
 // New plain launches bind monotonic elapsed time in the terminal only.
 if(!plain){
  const stderr=custody.stderr.toString('utf8'),rss=command[1]==='-l'?[...stderr.matchAll(/^\s*(\d+)\s+maximum resident set size\s*$/gm)]:[...stderr.matchAll(/^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$/gm)];
  if(Object.hasOwn(terminal,'lifetime_rss_bytes'))demand(Number.isSafeInteger(terminal.lifetime_rss_bytes)&&terminal.lifetime_rss_bytes>0&&terminal.lifetime_rss_bytes===operating.lifetime_rss_bytes&&rss.length===1&&Number(rss[0][1])*(command[1]==='-l'?1:1024)===terminal.lifetime_rss_bytes,'Historical raw external time RSS observation differs');
  const real=command[1]==='-l'?[...stderr.matchAll(/^\s*(\d+(?:\.\d+)?)\s+real\s+\d+(?:\.\d+)?\s+user\s+\d+(?:\.\d+)?\s+sys\s*$/gm)]:[...stderr.matchAll(/^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\d+(?::\d+){1,2}(?:\.\d+)?)\s*$/gm)];
  demand(real.length===1,'Missing/duplicate raw external time wall duration');
  const elapsed=real[0][1].split(':').reduce((n,x)=>n*60+Number(x),0);
  // External time prints centiseconds. The parent journal spans the entire
  // command; allow only that display rounding.
  demand(Number.isFinite(elapsed)&&elapsed>=0&&elapsed<=terminal.elapsed_seconds+0.01,'Raw external time wall duration differs from actual journal');
 }
 rebindKeys(output,'version,kind,execution_commit,request_sha256,publication_sha256,result_sha256','Foreign actual child stdout');
 demand(output.version===1&&output.kind==='current-rebind-child-publication-v1'&&output.execution_commit===request.execution_commit&&output.request_sha256===operating.request_sha256&&output.publication_sha256===operating.publication_sha256&&output.result_sha256===custody.result_sha256,'Raw child publication/output identity differs');
 return {runtime:before.runtime,command,code_source_sha256:operating.execution_custody.code_source.sha256,terminal_sha256:operating.execution_custody.terminal.sha256};
}

// This checks complete products, not an asserted qualified flag. The selected
// reader supplies whole authenticated pins and actual trusted method bodies.
// Mutable reader consumption history is retained in the actual inventories,
// not part of the immutable containing-member identity compared across reads.
export function currentRebindAcquisitionIdentity(acquisition) {
 return {...acquisition,native_inputs:acquisition.native_inputs.map(input=>{
  if(input.custody.kind!=='selected-native-transport')return input;
  return {...input,custody:{...input.custody,fragments:input.custody.fragments.map(fragment=>{
   const p=fragment.pin;
   rebindKeys(p,'bytes,git_blob_oid,mode,path'+(Object.hasOwn(p,'sha256')?',sha256':'')+(Object.hasOwn(p,'whole_body_consumed')?',whole_body_consumed':''),'Foreign native fragment descriptor fields');
   if(Object.hasOwn(p,'sha256'))demand(hash(p.sha256)&&p.sha256===fragment.sha256,'Native fragment optional whole SHA differs');
   if(Object.hasOwn(p,'whole_body_consumed'))demand(p.whole_body_consumed===true,'Native fragment false consumption claim');
   const {sha256,whole_body_consumed,...identity}=p;
   return {...fragment,pin:identity};
  })}};
 })};
}

export function verifyCurrentRebindProducts({certificate,request,facts,publication,operating,result,baseSelection,registry,originalRows,originalPatches,size,expectedCode,bodyPins,acquired,executionCustody}) {
 for(const [name,body]of Object.entries({request,facts,publication,operating,result}))demand(body&&bodyPins[name]?.sha256===valueSha(body)&&bodyPins[name]?.bytes===valueBytes(body).length,'Whole canonical rebind product bytes differ: '+name);
 rebindKeys(certificate,'version,kind,execution_commit,base_selection,authority_registry_sha256,request,facts,publication,operating,result','Foreign current rebind certificate');
 demand(certificate.version===1&&/^[a-f0-9]{40}$/.test(certificate.execution_commit)&&certificate.execution_commit===request.execution_commit&&certificate.kind==='qualified-native-additive-current-bank-rebind-v1'&&same(certificate.base_selection,baseSelection)&&certificate.authority_registry_sha256===valueSha(registry),'Stale current rebind certificate');
 rebindReceiptKeys(request,'version,kind,execution_commit,executed_code,base_selection,authority_registry_sha256,original_rows,original_patch_sha256s,current_targets,current_rows,acquisition,execution,size','limits','Foreign issued rebind request');
 demand(request.version===1&&request.kind==='issued-native-additive-current-bank-rebind-v1'&&/^[a-f0-9]{40}$/.test(request.execution_commit)&&same(request.executed_code,expectedCode)&&same(request.base_selection,baseSelection)&&request.authority_registry_sha256===valueSha(registry)&&same(request.original_rows,originalRows)&&same(request.original_patch_sha256s,originalPatches.map(valueSha))&&request.size===size,'Issued rebind changes original authority, current base or trusted method');
 demand(acquired&&same(acquired.base_selection,baseSelection)&&same(acquired.current_targets,request.current_targets)&&same(acquired.current_rows,request.current_rows),'Current operands differ from independently acquired selected bodies');
 rebindKeys(request.acquisition,'version,kind,target_sources,source_inputs,native_inputs,predecessor_proof,predecessor_rows,manifest_sha256','Incomplete current rebind acquisition custody');
 demand(request.acquisition.version===1&&request.acquisition.kind==='complete-selected-rebind-inputs-v1'&&same(currentRebindAcquisitionIdentity(request.acquisition),currentRebindAcquisitionIdentity(acquired.acquisition)),'Issued acquisition is not the complete independently consumed source/native roster');
 demand(Array.isArray(acquired.acquisition_phases)&&acquired.acquisition_phases.length>0,'Missing independent complete acquisition custody');
 const expected=currentRebindResult({baseSelection,registry,originalRows,originalPatches,currentTargets:request.current_targets,currentRows:request.current_rows,size});
 demand(same(result,expected),'Complete current rebind result/inverse differs');
 rebindReceiptKeys(facts,'version,kind,execution_commit,request_sha256,result_sha256,acquisition_sha256,acquisition_phases','complete_phase_bytes,descriptors','Foreign rebind facts');
 demand(facts.version===1&&facts.kind==='native-additive-current-bank-rebind-facts-v1'&&facts.execution_commit===request.execution_commit&&facts.request_sha256===bodyPins.request.sha256&&facts.result_sha256===bodyPins.result.sha256,'Rebind facts do not bind actual request/result');
 rebindKeys(publication,'version,kind,execution_commit,request_sha256,outputs','Foreign rebind publication');
 demand(facts.acquisition_sha256===valueSha(request.acquisition)&&Array.isArray(facts.acquisition_phases)&&facts.acquisition_phases.length===acquired.acquisition_phases.length&&facts.acquisition_phases.every((p,i)=>{const actual=acquired.acquisition_phases[i];const {complete_phase_bytes,descriptors,...scope}=p,{complete_phase_bytes:a,descriptors:b,...actualScope}=actual;return same(scope,actualScope);}),'Original executed acquisition phases/whole input custody differ');
 demand(publication.version===1&&publication.kind==='native-additive-current-bank-rebind-publication-v1'&&publication.execution_commit===request.execution_commit&&publication.request_sha256===bodyPins.request.sha256&&same(publication.outputs,{facts:{path:'facts.json',bytes:bodyPins.facts.bytes,sha256:bodyPins.facts.sha256},result:{path:'result.json',bytes:bodyPins.result.bytes,sha256:bodyPins.result.sha256}}),'Incomplete rebind publication output bindings');
 rebindReceiptKeys(operating,'version,kind,execution_commit,request_sha256,publication_sha256,exit_code,signal,owned_processes_remaining,elapsed_seconds,execution_custody','lifetime_rss_bytes','Foreign rebind operating proof');
 demand(operating.version===1&&operating.kind==='native-additive-current-bank-rebind-operating-v1'&&operating.execution_commit===request.execution_commit&&operating.request_sha256===bodyPins.request.sha256&&operating.publication_sha256===bodyPins.publication.sha256&&Number.isSafeInteger(operating.exit_code)&&operating.exit_code===0&&operating.signal===null&&Array.isArray(operating.owned_processes_remaining)&&operating.owned_processes_remaining.length===0&&Number.isFinite(operating.elapsed_seconds)&&operating.elapsed_seconds>=0,'Unqualified rebind operating custody');
 verifyCurrentRebindExecution({request,operating,expectedCode,custody:{...executionCustody,result_sha256:bodyPins.result.sha256}});
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
export function currentRebindSourceView(snapshot) {
 demand(snapshot?.reader instanceof ImmutableReader,'Require actual current selected reader');
 if(snapshot.selection.selected_geography)return selectedGeometrySourceAlias(snapshot);
 return new SelectedGeometrySources(snapshot);
}
export function acquireCurrentRebindOperands(snapshot,registry,originalRows,originalPatches,{targetSources,predecessorProof=null}={}) {
 demand(snapshot?.reader instanceof ImmutableReader,'Require actual current selected reader');
 const resolver=currentRebindSourceView(snapshot),reader=snapshot.reader;
 // The private snapshot authenticates the selected base and optional additive
 // hook. Acquisition reads only its base manifest/source roster, never a delta.
 const baseSelection=nativeBaseSelection(snapshot.selection);
 const targets=new Map();for(const row of originalRows){demand(['assigned','zero-cell'].includes(row.disposition),'Unsupported original rebind row');const owner=snapshot.owners[row.pixelIndex-1];demand(owner?.id===row.target_id,'Current rebind target owner differs');targets.set(row.target_id,owner);}
 const phases=[],sourceInputs=[],nativeInputs=[],currentTargets=[];let predecessorRows=[];
 const bodyIdentity=({commit,...p})=>p;
 // Each whole source frame completes before another starts. Only complete
 // selected targets and its exact whole input descriptor survive the frame.
 const sourceFrame=name=>{
  const actual=resolver.readNativeReferenceSource(name),found=[];
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
 for(const name of paths){const frame=sourceFrame(name);currentTargets.push(...frame.found);sourceInputs.push(frame.input);phases.push({kind:'complete-current-target-source',path:name});}
 currentTargets.sort((a,b)=>a.target_id<b.target_id?-1:a.target_id>b.target_id?1:0);
 demand(currentTargets.length===targets.size&&new Set(currentTargets.map(t=>t.target_id)).size===targets.size,'Missing/duplicate complete current targets');
 const continuity=snapshot.manifest.provenance?.successor_continuation;
 if(continuity?.issue===1520){
  demand(continuity.selected_old_new_rows===60&&continuity.added_cells===141&&continuity.removed_cells===0&&continuity.reassigned_cells===0,'Foreign selected Arctic continuation');
  pinCheck(predecessorProof);demand(predecessorProof.bytes===1990604&&predecessorProof.sha256==='d8af3b2eaf77f4fa948c01937ccb107f3d7eaa833ea4bac1d4480c633d509794'&&predecessorProof.decoded_bytes===undefined,'Missing exact whole qualified Arctic predecessor proof');
  const predecessorFrame=()=>{let version=predecessorProof.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}const actual=reader.descriptor(predecessorProof.path,version);demand(actual.mode===predecessorProof.mode&&actual.git_blob_oid===predecessorProof.git_blob_oid&&actual.bytes===predecessorProof.bytes,'Predecessor whole original mode/OID/bytes differ');return retainedArcticNativeRows(JSON.parse(reader.read(predecessorProof.path,{version,expected:predecessorProof.sha256})));};
  predecessorRows=predecessorFrame();phases.push({kind:'complete-qualified-arctic-predecessor',path:predecessorProof.path,sha256:predecessorProof.sha256});
 }else demand(predecessorProof===null,'Invented predecessor conservation proof');
 const manifest=snapshot.manifest,root=snapshot.selection.manifest_path.slice(0,snapshot.selection.manifest_path.lastIndexOf('/')+1),image=snapshot.image;
 const load=pin=>{
  const name=root+pin.path,ordinary=reader.git('ls-tree','-z',reader.version,'--',name).length>0;
  if(!nativeInputs.some(p=>p.logical_path===name)){
   let custody;if(ordinary)custody={kind:'ordinary-native-body',pin:{...bodyIdentity(reader.descriptor(name)),sha256:pin.sha256}};
   else{demand(image instanceof NativeAssetImage,'Missing genuine selected native transport');const member=image.index.files.find(p=>p.path===pin.path);demand(member,'Missing complete native member');custody={kind:'selected-native-transport',index:manifest.native_asset_transport.index,member,fragments:image.index.parts.filter(p=>p.offset<member.offset+member.bytes&&member.offset<p.offset+p.decoded_bytes).map(p=>({...p,pin:bodyIdentity(reader.descriptor(image.directory+'/'+p.path))}))};}
   nativeInputs.push({logical_path:name,asset:pin,custody});
  }
  let encoded;if(ordinary)encoded=reader.read(name,{expected:pin.sha256});
  else{demand(image instanceof NativeAssetImage,'Current native rebind requires selected ordinary or authenticated native image');encoded=image.logical(name,pin);}
  demand(encoded.length===pin.bytes&&sha(encoded)===pin.sha256,'Current native whole encoded body differs');
  const raw=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});demand(raw.length===pin.decoded_bytes,'Current native whole decoded body differs');
  const words=unshuffleOwnershipBytes(raw,pin.words),canonical=Buffer.alloc(words.byteLength);for(let i=0;i<words.length;i++)canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical)===pin.decoded_sha256,'Current native whole canonical words differ');return words;
 };
 const rowPins=manifest.parts.filter(p=>p.kind==='rows');demand(rowPins.length===1,'Unsupported split current row table');const table=load(rowPins[0]);
 demand(table.length===manifest.size*2,'Incomplete current native row table');let offset=0;for(let y=0;y<manifest.size;y++){demand(table[y*2]===offset,'Current whole row partition differs');offset+=table[y*2+1];}demand(offset*2===manifest.runWords,'Current native row table omits runs');
 phases.push({kind:'complete-current-native-row-table'});
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
 for(const group of groups.values()){
  const rows=groupFrame(group);currentRows.push(...rows);phases.push({kind:'complete-current-native-window-group',rows:group.rows.map(row=>row.y),parts:group.parts.map(pin=>pin.path)});
 }
 currentRows.sort((a,b)=>a.y-b.y);
 const candidateIds=new Set(originalPatches.flatMap(p=>p.rows.map(row=>row.y))),candidateRows=currentRows.filter(row=>candidateIds.has(row.y));
 demand(predecessorRows.every(prior=>same(prior,currentRows.find(row=>row.y===prior.y))),'Current native bank loses/reassigns a complete earlier Arctic row');
 const result=currentRebindResult({baseSelection,registry,originalRows,originalPatches,currentTargets,currentRows:candidateRows,size:manifest.size});
 return freeze({base_selection:baseSelection,current_targets:currentTargets,current_rows:candidateRows,source_inputs:sourceInputs,acquisition:{version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:targetSources,source_inputs:sourceInputs,native_inputs:nativeInputs,predecessor_proof:predecessorProof,predecessor_rows:predecessorRows,manifest_sha256:valueSha(manifest)},acquisition_phases:phases,input_inventory:[...reader.inventory.values()].filter(pin=>pin.whole_body_consumed===true).map(pin=>({...pin})),result,
  limits:['Actual selected before-state acquisition and exact applicability only. Original registry/source/native authority must also be authenticated by the committed reader; no activation or physical approval.','External cold operating qualification and repeated whole outputs remain mandatory before publishing a current_rebind certificate.']});
}

// A current rebind is complete data custody plus independently recomputed
// applicability. It never replaces the original registry/source authority.
export function readCurrentRebindCustody(reader,pin,{baseSelection,registry,originalRows,originalPatches,size,snapshot}) {
 demand(reader instanceof ImmutableReader,'Require actual immutable custody reader');
 demand(snapshot?.reader===reader,'Current rebind custody requires the actual privately authenticated selected snapshot');
 rebindKeys(pin,'commit,path,mode,git_blob_oid,bytes,sha256','Foreign ordinary current rebind pin');pinCheck(pin);demand(pin.decoded_bytes===undefined,'Current rebind certificate requires whole ordinary JSON');
 const descriptor=reader.descriptor(pin.path,pin.commit);demand(descriptor.mode===pin.mode&&descriptor.git_blob_oid===pin.git_blob_oid&&descriptor.bytes===pin.bytes,'Whole rebind certificate identity differs');
 const certificate=reader.json(pin.path,{version:pin.commit,expected:pin.sha256});
 demand(Object.keys(certificate).sort().join(',')==='authority_registry_sha256,base_selection,execution_commit,facts,kind,operating,publication,request,result,version','Foreign current rebind certificate roster');
 const names=['request','facts','publication','operating','result'];
 const roster=names.map(name=>{const p=certificate[name];pinCheck(p);demand(p.decoded_bytes===undefined,'Current rebind products require ordinary whole JSON');return {name,p};});
 const earlyRoster=roster.filter(({name})=>name!=='result');
 for(const {name,p}of roster){const actual=reader.descriptor(p.path,p.commit);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Whole rebind product mode/OID/length differs');}
 demand(/^[a-f0-9]{40}$/.test(certificate.execution_commit),'Missing actual rebind execution identity');
 const bodies=Object.fromEntries(earlyRoster.map(({name,p})=>[name,JSON.parse(reader.read(p.path,{version:p.commit,expected:p.sha256}))]));
 const historicalPaths=currentRebindCodePaths(bodies.request.executed_code);
 const historicalCode=historicalPaths.map(path=>reader.descriptor(path,certificate.execution_commit));
 // Authenticate the complete vector that actually executed. Current wrapper
 // bytes never relabel a historical generation; current operands and results
 // are independently recomputed below under the current trusted validator.
 const expectedCode=historicalCode.map(p=>({path:p.path,bytes:p.bytes,sha256:sha(reader.read(p.path,{version:p.commit}))}));
 // External custody verifies the original vector; current acquisition below
 // executes the current trusted closure without relabelling historical runs.
 demand(snapshot?.reader===reader,'Current rebind custody requires the actual privately authenticated selected snapshot');
 const externalNames=['code_source','terminal','stderr','stdout','issued_plan'];rebindKeys(bodies.operating.execution_custody,externalNames.join(','),'Incomplete external execution roster');
 const externalRoster=externalNames.map(name=>({name,p:bodies.operating.execution_custody[name]}));
 for(const {p}of externalRoster){pinCheck(p);demand(p.decoded_bytes===undefined,'External execution whole ordinary custody required');}
 for(const {p}of externalRoster){const actual=reader.descriptor(p.path,p.commit);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'External execution ordinary identity differs');}
 const executionCustody=Object.fromEntries(externalRoster.map(({name,p})=>[name,reader.read(p.path,{version:p.commit,expected:p.sha256})]));
 verifyCurrentRebindExecution({request:bodies.request,operating:bodies.operating,expectedCode,custody:{...executionCustody,result_sha256:roster.find(p=>p.name==='result').p.sha256}});
 // Reauthenticate the exact issued explicit operands through the same whole
 // immutable reader. Historical plans without this field retain their route.
 const issuedOriginalInputs=JSON.parse(executionCustody.issued_plan).original_inputs;
 if(issuedOriginalInputs!==undefined)for(const p of issuedOriginalInputs){
  const actual=reader.descriptor(p.path,p.commit);
  demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Issued original input mode/OID/bytes differ');
  reader.read(p.path,{version:p.commit,expected:p.sha256});
 }

 const acquired=acquireCurrentRebindOperands(snapshot,registry,originalRows,originalPatches,{
  targetSources:bodies.request.acquisition?.target_sources,predecessorProof:bodies.request.acquisition?.predecessor_proof});
 const resultPin=roster.find(row=>row.name==='result').p;
 bodies.result=JSON.parse(reader.read(resultPin.path,{version:resultPin.commit,expected:resultPin.sha256}));
 const result=verifyCurrentRebindProducts({certificate,...bodies,baseSelection,registry,originalRows,originalPatches,size,expectedCode,acquired,executionCustody,bodyPins:Object.fromEntries(roster.map(({name,p})=>[name,p]))});
 return result;
}

// Explicit committed data-only hook. This does not discover proposal files.
export function readSelectedAdditive(snapshot) {
 const {reader,selection,manifest,owners}=snapshot,hook=selection.additive_release;
 if(hook===undefined)return null;
 demand(hook&&Object.keys(hook).sort().join(',')==='bytes,path,sha256'&&Number.isSafeInteger(hook.bytes)&&hook.bytes>0&&hash(hook.sha256),'Unsupported committed additive hook');
 const descriptor=reader.descriptor(hook.path);demand(descriptor.bytes===hook.bytes,'Committed additive sidecar whole length differs');
 const sidecar=reader.json(hook.path,{expected:hook.sha256});
 demand(sidecar?.version===2&&sidecar.kind==='retained-native-additive-selection-v2'&&Object.keys(sidecar).sort().join(',')==='authority_registry,base_selection,kind,logical_asset_map,runtime_envelope,version','Unsupported committed additive sidecar');
 const baseSelection=nativeBaseSelection(selection);
 demand(same(sidecar.base_selection,baseSelection),'Stale/foreign actual native base selection');
 const whole=({p,alias,role})=>{
  pinCheck(p);let version=p.commit;try{reader.git('cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const actual=reader.descriptor(p.path,version);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Selected additive ordinary whole identity differs');
  return {p,version,...(alias?{alias:true,role}:{})};
 };
 demand(Object.keys(sidecar.logical_asset_map).sort().join(',')==='base_manifest,ledger,owner_roster,patch','Incomplete/foreign logical additive asset map');
 const roster=[{p:sidecar.runtime_envelope},{p:sidecar.authority_registry},...Object.entries(sidecar.logical_asset_map).map(([role,p])=>({p,...(['base_manifest','owner_roster'].includes(role)?(selectedBaseAssetAlias(snapshot,role,p),{alias:true,role}):{})}))];
 const admitted=roster.map(whole);
 // Every ordinary encoded alias is whole authenticated here; only privately
 // accepted base graphs skip duplicate decoded acquisition. Retain ledger/patch.
 const assetFrame=()=>{
  const bodies=admitted.map(({p,version,alias,role})=>{
  const raw=reader.read(p.path,{version,expected:p.sha256});if(alias)return selectedBaseAssetAlias(snapshot,role,p);if(p.decoded_bytes===undefined)return JSON.parse(raw);
  const decoded=gunzipSync(raw,{maxOutputLength:p.decoded_bytes});demand(decoded.length===p.decoded_bytes&&sha(decoded)===p.decoded_sha256,'Selected additive whole decoded inverse differs');return JSON.parse(decoded);
 });
  const [wrapped,registry,...assets]=bodies,envelope=wrapped.additiveRelease??wrapped;
  demand(envelope&&Object.keys(envelope).sort().join(',')==='base_manifest,base_reference,effective_reference,kind,ledger,owner_roster,patch,version'&&([1,2].includes(envelope.version))&&envelope.kind===(envelope.version===1?'retained-native-base-plus-delta-v1':'retained-native-base-plus-delta-v2'),'Unsupported explicit additive runtime envelope');
  const named=Object.fromEntries(Object.keys(sidecar.logical_asset_map).map((k,i)=>[k,assets[i]]));
  for(const key of Object.keys(named)){
  const p=sidecar.logical_asset_map[key],declared=envelope[key];
  demand(declared&&p.bytes===declared.bytes&&p.sha256===declared.sha256&&(p.decoded_bytes??p.bytes)===(declared.decoded_bytes??declared.bytes)&&(p.decoded_sha256??p.sha256)===(declared.decoded_sha256??declared.sha256),'Runtime logical asset differs from committed ordinary pin: '+key);
 }
  demand(sidecar.logical_asset_map.base_manifest.sha256===selection.sha256&&named.base_manifest===manifest,'Additive runtime rebinds actual selected native manifest');
  demand(sidecar.logical_asset_map.owner_roster.sha256===manifest.original_assets.bounds.sha256&&named.owner_roster===owners,'Additive owner roster differs from independent original native bounds');
  return {registry,envelope,named:{ledger:named.ledger,patch:named.patch}};
 };
 const {registry,envelope,named}=assetFrame();
 let resolver=snapshot.geometrySources;
 if(!resolver){
  resolver=new SelectedGeometrySources(snapshot);snapshot.geometrySources=resolver;
 }
 demand(envelope.base_reference.id===resolver.release.id&&envelope.base_reference.footprints_sha256===resolver.release.footprints_sha256,'Additive effective baseline differs from actual selected source bank');
 const normalized=normaliseRetainedRepairLedger(named.ledger,registry),proofs=[];
 for(const entry of registry.entries){
  demand(entry.policy_id==='retained-source-literal-additions'&&entry.policy_version===1,'Unsupported source policy semantics/version');
  const child=new ImmutableReader(reader.repo,reader.version,{gitExecutable:reader.gitExecutable,invocation:reader.invocation});
  const proof=readRetainedRegistryAuthority(child,entry,reader,{snapshot});
  for(const row of normalized.rows.values())if(row.authority_sha256===entry.authority_sha256){
   const original=proof.original_ledger.rows.find(r=>r.component_id===row.component_id);
   demand(original&&['assigned','zero-cell'].includes(original.disposition)&&same({...original,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256},row),'Selected component rebinds original full native/source primitive');
  }
  const view={authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256,source_scope_ids:proof.source_scope_ids,native_proof:proof.native_proof,original_ledger:proof.original_ledger,pins:proof.pins,original_pins:proof.original_pins};proofs.push(view);
 }

 const expectedScope=new Map();
 for(const proof of proofs){
  if(proof.original_ledger.parent_inventory!==undefined)demand(same(named.ledger.parent_inventory,proof.original_ledger.parent_inventory),'Selected ledger changes complete original inventory denominator');
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
 const currentContract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,manifest[k]]));
 demand(proofs.every(p=>same(p.native_proof.native_contract,currentContract)),'Selected additions change native lattice/method/owner-parent contract');
 let rebind=null;
 if(Object.hasOwn(named.ledger,'current_rebind')){
  demand(named.ledger.version===2&&envelope.version===2,'Current rebind is an explicit v2-only extension');
  // Complete original scope/pointset/contract checks above have finished.
  // Retain only native patches/contracts and custody before current acquisition.
  expectedScope.clear();
  for(const proof of proofs){delete proof.original_ledger;proof.native_proof={native_contract:proof.native_proof.native_contract,native_patches:proof.native_proof.native_patches};}
  const legacyAuthorities=new Set(proofs.filter(proof=>proof.original_pins.source_evidence===undefined).map(proof=>proof.authority_sha256));
  const legacyRegistry={...registry,entries:registry.entries.filter(entry=>legacyAuthorities.has(entry.authority_sha256))};
  rebind=readCurrentRebindCustody(reader,named.ledger.current_rebind,{baseSelection,registry:legacyRegistry,originalRows:[...normalized.rows.values()].filter(row=>row.representation!=='native-cells'),originalPatches:proofs.filter(p=>p.original_pins.source_evidence===undefined).flatMap(p=>p.native_proof.native_patches),size:manifest.size,snapshot});
  demand(same(named.ledger.current_targets,rebind.current_targets),'Ledger current target pointsets differ from complete qualified rebind result');
 }else demand(!Object.hasOwn(named.ledger,'current_targets'),'Current targets require complete rebind custody');
 const expectedByRow=new Map();
 for(const original of originalPatches){
  demand(rebind||same(original.base_reference,envelope.base_reference)
    ||(snapshot.selection.reference_projection&&same(original.base_reference,{id:resolver.nativeRelease.id,footprints_sha256:resolver.nativeRelease.footprints_sha256,hierarchy_sha256:resolver.nativeRelease.hierarchy_sha256})),
    'Original delta requires an actual qualified current-bank rebind or validated metadata application');
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
 // The independently authenticated original owner roster remains in snapshot.
 const consumerRows=[...normalized.rows.values()].map(row=>{if(!rebind||row.representation==='native-cells')return row;const target=rebind.current_targets.find(target=>target.target_id===row.target_id);demand(target&&owners[target.pixelIndex-1]?.id===target.target_id,'Current rebind owner roster differs');return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};});
 const legacy_native_rows=[...new Set(proofs.filter(proof=>proof.original_pins.source_evidence===undefined)
  .flatMap(proof=>proof.native_proof.native_patches.flatMap(patch=>patch.rows.map(row=>row.y))))].sort((a,b)=>a-b);
 const carried={sidecar,registry,ledger:named.ledger,patch,envelope,legacy_native_rows,normalized_rows:consumerRows,authority_proofs:proofs.map(proof=>({authority_sha256:proof.authority_sha256,rule_sha256:proof.rule_sha256,source_scope_ids:proof.source_scope_ids,pins:proof.pins,original_pins:proof.original_pins})),assigned_cells:total,...(rebind?{current_rebind:rebind}:{})};
 const result=freeze(carried);
 selectedAdditions.set(result,{snapshot});return result;
}
export function selectedAdditiveRows(view,row,base) {
 demand(selectedAdditions.has(view),'Require actual committed authenticated additive selection');
 const delta=view.patch.rows.find(r=>r.y===row)?.runs??[];
 if(view.current_rebind&&delta.length&&view.legacy_native_rows.includes(row)){const expected=view.current_rebind.native.current_rows.find(r=>r.y===row);demand(expected&&same(expected.runs,base),'Actual selected complete native row differs from qualified current rebind');}
 const all=[...base.map(r=>[...r]),...delta.map(r=>[...r])].sort((a,b)=>a[0]-b[0]);let end=0;
 for(const r of all){demand(r[0]>=end,'Selected additive delta overlaps preexisting assigned native cells');end=r[1];}
 return all;
}
