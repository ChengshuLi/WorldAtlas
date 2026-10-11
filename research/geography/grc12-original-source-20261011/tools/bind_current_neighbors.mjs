// Bind genuine current selection and whole possible-neighbor features.
// Whole-coordinate certificate reuse excludes disjoint boxes only; no GIS here.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const here=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(here,'../../../..');
const own=path.relative(repo,path.dirname(here)),script=path.relative(repo,fileURLToPath(import.meta.url));
const [head,vintage]=process.argv.slice(2),baseline='6a99a7606b9c2d11ac8cd093610653d4cd5d1382';
const FILE=32*1024**2,CAP=256*1024**2,OUTPUT=4*1024**2;
const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',repo,...args],{maxBuffer:FILE+1});
const sha=b=>createHash('sha256').update(b).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const bytes=v=>Buffer.from(JSON.stringify(canonical(v))+'\n'),digest=v=>sha(bytes(v));
const demand=(v,m)=>{if(!v)throw Error(m);};
demand(git('rev-parse','HEAD').toString().trim()===head,'Exact execution HEAD required');
demand(/^[a-z0-9][a-z0-9-]{0,63}$/.test(vintage??''),'Fresh vintage required');
const output=path.join(repo,own,'vintages',vintage);
function absent(){for(let p=output;p!==path.dirname(repo);p=path.dirname(p)){const s=fs.lstatSync(p,{throwIfNoEntry:false});demand(!s?.isSymbolicLink(),'Symlink destination');if(p===output)demand(!s,'Occupied destination');}}
absent();
const closure=[script,'scripts/check-effective-geographic-regression.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','src/ownership-codec.js'];
const code=closure.map(name=>{const raw=fs.readFileSync(path.join(repo,name));demand(raw.equals(git('show',head+':'+name)),'Unfrozen execution code: '+name);if(name!==script)demand(raw.equals(git('show',baseline+':'+name)),'Changed trusted selected reader');return{path:name,bytes:raw.length,sha256:sha(raw)};});
const runtimePath=fs.realpathSync(process.execPath),runtimeSize=fs.statSync(runtimePath).size;
const runtimeHash=createHash('sha256'),fd=fs.openSync(runtimePath,'r'),buffer=Buffer.alloc(1024**2);let n,total=0;
try{while((n=fs.readSync(fd,buffer,0,buffer.length,null))){runtimeHash.update(buffer.subarray(0,n));total+=n;}}finally{fs.closeSync(fd);}
demand(total===runtimeSize,'Runtime changed');
const runtime={path:runtimePath,bytes:total,sha256:runtimeHash.digest('hex'),version:process.version};
const {ImmutableReader,loadSelection}=await import(pathToFileURL(path.join(repo,closure[1])));
const reader=new ImmutableReader(repo,baseline,{runtimeBytes:total,executionBytes:code.reduce((s,p)=>s+p.bytes,0),outputBytes:OUTPUT});
const snapshot=loadSelection(reader);
demand(snapshot&&snapshot.geometrySources&&snapshot.additive,'Actual current selection missing');
demand(snapshot.additive.ledger.rows.length===55&&snapshot.additive.normalized_rows.length===47&&snapshot.additive.assigned_cells===1006,'Wrong 6a selected baseline');
const acquisitionPhases=snapshot.acquisitionPhases;
// Complete loadSelection frame has returned; carry its authenticated view only.
const carriedSnapshotBytes=snapshot.metadataBytes;
reader.metadataBytes=8*1024**2+carriedSnapshotBytes;
reader.phase();
const candidates=reader.json(own+'/vintages/candidate-custody-001/original-components.json',{version:head});
const plan=reader.json(own+'/tools/current-inputs.json',{version:head});
const ids=plan.components.map(r=>r.component_id);
demand(JSON.stringify(candidates.map(r=>r.id))===JSON.stringify(ids),'Changed twelve original candidates');
function bounds(g){const box=[Infinity,Infinity,-Infinity,-Infinity];function visit(v){if(Array.isArray(v)&&typeof v[0]==='number'){demand(v.length>=2&&v.every(Number.isFinite),'Nonfinite coordinates');box[0]=Math.min(box[0],v[0]);box[1]=Math.min(box[1],v[1]);box[2]=Math.max(box[2],v[0]);box[3]=Math.max(box[3],v[1]);}else if(Array.isArray(v))v.forEach(visit);}if(g.type==='GeometryCollection'){for(const child of g.geometries){const b=bounds(child);if(b){visit(b.slice(0,2));visit(b.slice(2));}}}else visit(g.coordinates);return box.every(Number.isFinite)?box:null;}
const intersects=(a,b)=>a&&b&&a[0]<=b[2]&&a[2]>=b[0]&&a[1]<=b[3]&&a[3]>=b[1];
const additions=snapshot.additive.normalized_rows.map(r=>({component_id:r.component_id,target_id:r.target_id,geometry:r.geometry,geometry_sha256:r.geometry_sha256,bounds:bounds(r.geometry)}));
const screens=candidates.map(c=>({component_id:c.id,candidate_bounds:bounds(c.geometry),additive_geometry_screen:additions.map(r=>({component_id:r.component_id,target_id:r.target_id,geometry_sha256:r.geometry_sha256,bounds:r.bounds,candidate_bbox_intersects:intersects(bounds(c.geometry),r.bounds)}))}));
const certificatePath='coordination/engineering/melanesia363-additive-delivery-20261010/selected-integration/current-f02-coordinate/certificate.json.gz';
function deriveCompleteNeighbors(){
 const encoded=reader.read(certificatePath,{expected:'23aef083ceeabff7d76e7da2a6d047e9dc30b40a3e9b03e122492c4d41c9cd7e',decoded:18414409});
 demand(encoded.length===7515239,'Certificate encoded size changed');
 const raw=gunzipSync(encoded,{maxOutputLength:18414409});
 demand(raw.length===18414409&&sha(raw)==='60cc10692d3133b8141e659b932fe1f1d6c14286a6b80009c47b324c6bcaaf23','Certificate decoded drift');
 const certificate=JSON.parse(raw),resolver=snapshot.geometrySources;
 demand(certificate.inputs.length===resolver.paths.length&&certificate.entries.length===snapshot.owners.length,'Incomplete selected certificate');
 demand(JSON.stringify(certificate.inputs.map(r=>r.path).sort())===JSON.stringify([...resolver.paths].sort()),'Certificate source roster differs');
 demand(certificate.binding.release.id===snapshot.selection.release_id&&certificate.binding.release.footprints_sha256===resolver.release.footprints_sha256,'Certificate release differs');
 for(const input of certificate.inputs){const source=resolver.sources[resolver.paths.indexOf(input.path)],p=input.source;
  demand(source.mode===p.mode&&source.git_blob_oid===p.git_blob_oid&&source.bytes===p.bytes&&(source.decoded_sha256??source.sha256)===input.whole_body_sha256,'Changed complete coordinate source');
  const actual=reader.descriptor(p.path);demand(actual.mode===p.mode&&actual.git_blob_oid===p.git_blob_oid&&actual.bytes===p.bytes,'Actual certificate source differs');
 }
 const seen=new Set(),owners=new Map(snapshot.owners.map(r=>[r.id,r]));
 for(const row of certificate.entries){demand(row.length===certificate.entry_fields.length&&!seen.has(row[0])&&owners.has(row[0]),'Malformed/missing/duplicate complete owner row');seen.add(row[0]);}
 const targets=new Map(plan.components.map(r=>[r.component_id,r.target_id]));
 const rows=screens.map(screen=>{const additionalOwners=new Set(screen.additive_geometry_screen.filter(r=>r.candidate_bbox_intersects).map(r=>r.target_id));if(targets.get(screen.component_id))additionalOwners.add(targets.get(screen.component_id));return{...screen,entries:certificate.entries.filter(r=>r[9].some(b=>intersects(screen.candidate_bounds,b))||additionalOwners.has(r[0]))};});
 const needed=new Set(rows.flatMap(r=>r.entries.map(e=>e[4])));
 return{rows,certificate_inputs:certificate.inputs.filter(r=>needed.has(r.path)),complete_owner_rows:seen.size,complete_source_parts:certificate.inputs.length,phase_bytes:reader.used};
}
const derived=deriveCompleteNeighbors();
// Certificate buffers and all irrelevant entries are gone; retain only hits.
const phases=[{kind:'coordinate-certificate-rebind',phase_bytes:derived.phase_bytes}],features=new Map();
const retained=bytes({derived,additions,candidates}).length;
for(const input of derived.certificate_inputs){
 reader.metadataBytes=8*1024**2+carriedSnapshotBytes+retained+bytes([...features.values()]).length;
 reader.phase();
 function selectWholeFeatures(){const data=snapshot.geometrySources.read(input.path);demand(data.whole_sha256===input.whole_body_sha256,'Whole selected geometry body changed');const wanted=new Map(derived.rows.flatMap(r=>r.entries).filter(r=>r[4]===input.path).map(r=>[r[0],r]));const selected=[];for(const row of wanted.values()){const f=data.collection.features[row[5]];demand(f?.id===row[0]&&f.properties.parent_id===row[2]&&digest(f)===row[6]&&digest(f.geometry)===row[7],'Whole actual neighbor differs');selected.push(f);}return selected;}
 for(const f of selectWholeFeatures())features.set(f.id,f);
 phases.push({kind:'whole-selected-source',path:input.path,phase_bytes:reader.used});
}
const rows=derived.rows.map((r,i)=>{const{entries,...screen}=r;return{...screen,derived_js_feature_sha256:digest(candidates[i]),derived_js_geometry_sha256:digest(candidates[i].geometry),candidate_neighbors:entries.map(e=>({certificate_entry:e,feature:features.get(e[0])}))};});
const result={baseline,execution_commit:head,scopeIds:ids,rows,current_additions:additions,actual_selection:snapshot.selection,actual_runtime_envelope:snapshot.additive.envelope,actual_ledger_sha256:snapshot.additive.sidecar.logical_asset_map.ledger.sha256,selected_active_primitives:47,selected_native_cells:1006,complete_owner_rows:derived.complete_owner_rows,complete_source_parts:derived.complete_source_parts,acquisition_phases:acquisitionPhases,context_phases:phases,source_inputs:[...reader.inventory.values()],authority_proofs:snapshot.additive.authority_proofs,code,runtime,carried_snapshot_bytes:carriedSnapshotBytes,method:'Genuine current loadSelection; unchanged complete-coordinate certificate bound to all actual selected source identities; whole possible-neighbor geometries and every active additive primitive retained for numerical predicates.',limits:['Bounding boxes exclude only disjoint envelopes. Every contact still requires the original numerical source/current predicates.','No source acceptance, native integration or current physical/legal truth is established.']};
const raw=bytes(result);demand(raw.length<=OUTPUT&&reader.used<=CAP&&process.resourceUsage().maxRSS*1024<=1024**3,'Output/logical/RSS admission exceeded');
absent();fs.mkdirSync(path.dirname(output),{recursive:true});fs.mkdirSync(output);
fs.writeFileSync(path.join(output,'result.json'),raw,{flag:'wx'});
fs.writeFileSync(path.join(output,'publication.json'),bytes({version:1,status:'complete',outputs:[{path:path.relative(repo,path.join(output,'result.json')),bytes:raw.length,sha256:sha(raw),hash_kind:'file-bytes'}]}),{flag:'wx'});
console.log(JSON.stringify({complete_owner_rows:derived.complete_owner_rows,source_parts:derived.complete_source_parts,neighbors:rows.map(r=>({component:r.component_id,ids:r.candidate_neighbors.map(n=>n.feature.id),additive_contacts:r.additive_geometry_screen.filter(x=>x.candidate_bbox_intersects).map(x=>x.component_id)})),output_bytes:raw.length,context_phases:phases,acquisition_phases:acquisitionPhases.map(p=>({kind:p.kind,complete_phase_bytes:p.complete_phase_bytes})),peak_rss_bytes:process.resourceUsage().maxRSS*1024}));
