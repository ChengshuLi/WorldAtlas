// #1569 prevention helper. Input pins/binding must be derived by the trusted
// selected-bank resolver. These functions do not select/activate a release.
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader, SelectedGeometrySources} from '../../../scripts/check-effective-geographic-regression.mjs';
const FILE=33554432, PHASE=268435456, SLOT=512;
const certificates=new WeakMap(), originalAuthorities=new WeakMap();
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
 demand(certificates.has(certificate)&&certificate.kind==='selected-coordinate-neighbor-certificate-v1','Incomplete/unqualified neighbor certificate');
 demand(typeof targetId==='string'&&certificate.entries.some(r=>r.id===targetId),'Require exact SELF target identity; no arbitrary exclusions');
 const boxes=coordinateBounds(changedGeometry),skip=new Set([targetId]);const hit=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
 return certificate.entries.filter(r=>!skip.has(r.id)&&r.boxes.some(a=>boxes.some(b=>hit(a,b))));
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
 const retained=valueBytes({binding,owners:snapshot.owners,image:resolver.image?{index:resolver.image.index,map:resolver.image.map}:null,bank:resolver.bank??null,priorShards}).length;
 demand(retained<=FILE,'Retained coordinate certificate metadata exceeds ordinary bound');
 reader.metadataBytes=8*1024*1024+2*retained;reader.phase();
 const roster=new Map(snapshot.owners.map(r=>[r.id,r])),entries=[],seen=new Set(),inputFacts=[],phases=[];
 for(const name of sourcePaths){
  reader.metadataBytes=8*1024*1024+2*(retained+valueBytes({entries,inputFacts}).length);reader.phase();const actual=resolver.read(name);inputFacts.push({path:name,source:actual.source,whole_body_sha256:actual.whole_sha256,bytes:actual.body.length});
  for(let ordinal=0;ordinal<actual.collection.features.length;ordinal++){
   const f=actual.collection.features[ordinal],id=f.id??f.properties?.id,owner=roster.get(id);
   demand(f.type==='Feature'&&owner&&!seen.has(id)&&f.properties?.parent_id===owner.province_id,'Foreign/duplicate/misparented whole selected row');seen.add(id);
   entries.push({id,index:owner.index,parent_id:owner.province_id,parent_index:owner.province_index,source:name,ordinal,whole_feature_sha256:valueSha(f),geometry_sha256:valueSha(f.geometry),boxes:coordinateBounds(f.geometry)});
   if(onFeature!==undefined){demand(typeof onFeature==='function','Require trusted source digest callback');onFeature(f);}
  }
  phases.push({source:name,complete_phase_bytes:reader.used,descriptors:reader.charged.size});
 }
 const result={version:1,kind:'selected-complete-coordinate-shard-v1',binding,paths:sourcePaths,inputs:inputFacts,entries,phases};
 demand(valueBytes(result).length<=reader.outputBytes,'Selected coordinate shard exceeds prospective output');freeze(result);certificates.set(result,{binding,resolver});return result;
}
export function joinSelectedCoordinateCertificate(resolver,shards,{outputReserve=32*1024*1024}={}) {
 demand(resolver instanceof SelectedGeometrySources&&Array.isArray(shards)&&shards.length>0,'Missing actual selected coordinate shards');
 const expected=new Set(resolver.paths),seenPaths=new Set(),seenIds=new Set(),entries=[],inputs=[];
 let binding;for(const shard of shards){
  const proof=certificates.get(shard);demand(proof&&proof.resolver===resolver&&shard.kind==='selected-complete-coordinate-shard-v1','Unqualified/foreign selected coordinate stage');
  if(!binding)binding=shard.binding;demand(same(binding,shard.binding),'Mixed selected coordinate vintage');
  for(const p of shard.paths){demand(expected.has(p)&&!seenPaths.has(p),'Foreign/duplicate source containing closure');seenPaths.add(p);}
  inputs.push(...shard.inputs);for(const row of shard.entries){demand(!seenIds.has(row.id),'Duplicate complete location join');seenIds.add(row.id);entries.push(row);}
 }
 demand(seenPaths.size===expected.size&&seenIds.size===resolver.snapshot.owners.length&&resolver.snapshot.owners.every(o=>seenIds.has(o.id)),'Incomplete canonical source/owner roster; exclusion forbidden');
 const retained=2*valueBytes({shards,owners:resolver.snapshot.owners,binding}).length;
 const reader=resolver.reader;demand(Number.isSafeInteger(outputReserve)&&outputReserve>0&&outputReserve<=FILE,'Bounded complete certificate output reserve required');reader.outputBytes=outputReserve;reader.metadataBytes=8*1024*1024+retained;reader.phase();
 demand(shards.length+inputs.length<=SLOT,'Complete coordinate join descriptor cap');entries.sort((a,b)=>a.index-b.index);
 const result={version:1,kind:'selected-coordinate-neighbor-certificate-v1',binding,entries,inputs,complete_phase_bytes:reader.used,limitations:['Conservative exclusion only. Actual whole geometry and original polygon predicates are mandatory for every possible neighbor.']};
 demand(valueBytes(result).length<=reader.outputBytes,'Complete selected certificate exceeds prospective output');freeze(result);certificates.set(result,{binding,resolver});return result;
}
// Qualification of a persisted cold product uses the independently retained
// live trusted child acknowledgement, plus the actual selected resolver. The
// acknowledgement is issued by the parent invocation, never read from candidate
// files or inferred from the product's own facts.
export function acceptColdCoordinateCertificate(resolver,certificate,{facts,expectedPublication,publication,encoded_sha256,decoded_sha256}) {
 demand(resolver instanceof SelectedGeometrySources&&same(publication,expectedPublication)&&publication.complete===true&&publication.kind==='trusted-selected-coordinate-stage-v1','Missing actual issued cold-stage acknowledgement');
 demand(encoded_sha256===publication.certificate.sha256&&decoded_sha256===publication.certificate.decoded_sha256,'Cold complete certificate bytes differ');
 demand(facts.kind===publication.kind&&facts.selected_commit===resolver.reader.version&&facts.candidate_code_executed===false&&certificate.kind==='selected-coordinate-neighbor-certificate-v1','Foreign cold certificate execution/input');
 demand(same(certificate.binding.selection,resolver.snapshot.selection)&&same(certificate.binding.release,resolver.release)&&same(certificate.binding.sources,resolver.sources)&&certificate.binding.owners_sha256===valueSha(resolver.snapshot.owners)&&same(facts.binding,certificate.binding),'Cold certificate selected source/owner binding differs');
 const paths=new Set(resolver.paths),owners=new Map(resolver.snapshot.owners.map(r=>[r.id,r])),seen=new Set(),sources=new Set();
 demand(Array.isArray(certificate.inputs)&&certificate.inputs.length===paths.size&&Array.isArray(certificate.entries)&&certificate.entries.length===owners.size,'Incomplete cold source/owner certificate');
 for(const input of certificate.inputs)demand(paths.has(input.path)&&!sources.has(input.path)&&sources.add(input.path)&&hash(input.whole_body_sha256)&&Number.isSafeInteger(input.bytes)&&input.bytes>0&&input.bytes<=FILE,'Foreign/duplicate complete cold source');
 for(const row of certificate.entries){const owner=owners.get(row.id);demand(owner&&!seen.has(row.id)&&seen.add(row.id)&&row.index===owner.index&&row.parent_id===owner.province_id&&row.parent_index===owner.province_index&&paths.has(row.source)&&Number.isSafeInteger(row.ordinal)&&row.ordinal>=0&&hash(row.whole_feature_sha256)&&hash(row.geometry_sha256)&&Array.isArray(row.boxes)&&row.boxes.length>0,'Foreign/duplicate/drifted cold owner record');
  for(const box of row.boxes)demand(Array.isArray(box)&&box.length===4&&box.every(Number.isFinite)&&box[0]>=-180&&box[2]<=180&&box[1]>=-90&&box[3]<=90&&box[0]<=box[2]&&box[1]<=box[3],'Invalid complete coordinate exclusion bound');
 }
 demand(facts.complete_owners===owners.size&&facts.complete_sources===paths.size,'Cold scope denominator differs');
 freeze(certificate);certificates.set(certificate,{binding:certificate.binding,resolver});return certificate;
}

export function selectedCertificateAffectedPlan(before,after) {
 demand(certificates.has(before)&&certificates.has(after),'Require both complete cold source certificates');
 const old=new Map(before.entries.map(r=>[r.id,r])),next=new Map(after.entries.map(r=>[r.id,r]));
 demand(old.size===next.size&&[...old].every(([id,row])=>next.has(id)&&row.index===next.get(id).index&&row.parent_id===next.get(id).parent_id&&row.parent_index===next.get(id).parent_index),'Selected continuous identity/owner/parent roster changed');
 const changed=[...old.keys()].filter(id=>old.get(id).geometry_sha256!==next.get(id).geometry_sha256).sort(),needed=new Set(changed),pairs=new Set();
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
 demand(certificates.has(certificate)&&certificate.kind==='selected-coordinate-neighbor-certificate-v1'&&Array.isArray(changes)&&changes.length>0,'Missing qualified complete selected certificate');
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
 for(let i=0;i<pins.assets.length;i++){
  const p=pins.assets[i],declared=publication.assets[i];
  demand(p.path.endsWith('/'+declared.path)&&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(k=>p[k]===declared[k]),'Original native asset roster rebound');
  if(p.sha256===custody.pins.ledger.sha256)demand(same(JSON.parse(raw[i+3]),custody.ledger),'Whole published native ledger differs');
 }
 demand(pins.assets.some(p=>p.sha256===custody.pins.ledger.sha256),'Published native assets omit original complete ledger');
 return freeze({version:1,kind:'qualified-original-native-authority-v1',pins,scope_ids:custody.source_scope_ids,native_scope_ids:nativeScope,inventory_rows:rows,rule_sha256:custody.rule_sha256,complete_phase_bytes:reader.used,
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
 const source=qualifyOriginalSourceAuthority(custody),native=qualifyOriginalNativeAuthority(custody,binding.native_proof);
 return freeze({version:1,kind:'authenticated-registry-source-custody-v1',authority_sha256:entry.authority_sha256,
  rule_sha256:entry.rule_sha256,policy_id:entry.policy_id,policy_version:entry.policy_version,
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
