/* Whole original Germany request with explicit official GF2 water-role holds.
 * No source atom, owner ancestry or physical veto is rewritten. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const [R,C,O]=process.argv.slice(2);
const H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611';
const P='coordination/engineering/germany-original-repair-20261017';
const need=(x,m)=>{if(!x)throw Error(m)}, sha=b=>createHash('sha256').update(b).digest('hex');
need(process.argv.length===5&&/^[a-f0-9]{40}$/.test(C),'Exact arguments');
for(const root of [R,O])for(let p=path.resolve(root);;p=path.dirname(p)){
 need(!fs.lstatSync(p,{throwIfNoEntry:false})?.isSymbolicLink(),'Symlink');if(p===path.dirname(p))break;
}
need(fs.statSync(path.dirname(O)).isDirectory()&&!fs.lstatSync(O,{throwIfNoEntry:false}),'Fresh output');
const {pinReader}=await import(pathToFileURL(path.join(R,'scripts/prepare-delivery-handoff.mjs')));
const reader=pinReader(R),pins=new Map();
function pin(p,c=H){const q=reader.pin(c,p);pins.set(c+':'+p,q);return q}
function read(p,c=H){return reader.read(pin(p,c))}
function json(p,c=H){const b=read(p,c);if(!p.endsWith('.gz'))return JSON.parse(b);const decoded=gunzipSync(b);pins.set(c+':'+p,{...pins.get(c+':'+p),decoded_bytes:decoded.length,decoded_sha256:sha(decoded)});return JSON.parse(decoded)}
need(read(P+'/probes/prepare-native-config.mjs',C).equals(fs.readFileSync(fileURLToPath(import.meta.url))),'Method drift');
const stages=json(P+'/source-stage-001/original-stage-inputs.json',C);
const membership=json(P+'/source-stage-001/source-target-membership.json',C);
const original=json(P+'/source-stage-001/original-intervals.json.gz',C);
const originalPatch=json(P+'/source-stage-001/original-native-patch.json',C);
const roles=json(P+'/source-review/independent-provenance-001/retained-role-map.json',C);
const foreign=json(P+'/foreign-bounds-001/complete-foreign-bounds.json',C);
const periodic=json(P+'/periodic-negatives-001/retained-periodic-negative-reconciliation.json',C);
for(const q of foreign.executed_stock_method_closure)need(fs.readFileSync(path.join(R,q.path)).equals(read(q.path,q.commit)),'Stock method drift');
need(stages.length===100&&membership.length===100&&original.length===7499&&roles.owners===82&&roles.consumed_atoms===100,'Complete domestic scope');
need(foreign.complete_foreign_features===73085&&foreign.selected_foreign_features===186&&periodic.unresolved_foreign_bound_features===0&&periodic.retained_periodic_frame_disjoint_features===3,'Complete foreign scope');
const roleByAtom=new Map(),heldOwners=new Set();
for(const owner of roles.consumed_owner_map){
 need(owner.atoms.length>0,'Empty owner atoms');
 if(owner.atoms.every(a=>a.official_gf==='2'))heldOwners.add(owner.owner);
 for(const atom of owner.atoms){const id='gb:DEU:ADM3:'+atom.shape_id;need(!roleByAtom.has(id)&&['2','4'].includes(atom.official_gf),'Unique supported official role');roleByAtom.set(id,{...atom,owner:owner.owner,target_id:owner.target_id});}
}
need([...heldOwners].sort((a,b)=>a-b).join(',')==='16266,16269,16286,16307,16503','Exact GF2-only owners');
const wanted=new Map(),allKeys=new Set(),holdKeys=new Set(),priorRows=new Map();
for(const [y,a,z,oo,ss,kind] of original){
 need(oo.length===1&&['land','inland-water'].includes(kind),'Exact original class');const owner=oo[0];
 for(let x=a;x<z;x++){const key=`${y}:${x}:${owner}`;need(!allKeys.has(key),'Duplicate original');allKeys.add(key);if(heldOwners.has(owner))holdKeys.add(key);}
 if(heldOwners.has(owner)){
  need(kind==='land','Water-only owner prior hold must be actual land request');
  const runs=priorRows.get(y)??[];runs.push([a,z,owner,'unsupported_GF2_water_extension_land_role']);priorRows.set(y,runs);continue;
 }
 const ys=wanted.get(owner)??new Map(),runs=ys.get(y)??[];runs.push([a,z,kind==='land'?'mapped_land_support':'mapped_inland_water_support']);ys.set(y,runs);wanted.set(owner,ys);
}
const merge=rr=>{const out=[];for(const r of rr.toSorted((a,b)=>a[0]-b[0]||a[1]-b[1])){const last=out.at(-1);if(last&&last[1]===r[0]&&JSON.stringify(last.slice(2))===JSON.stringify(r.slice(2)))last[1]=r[1];else out.push([...r]);}need(out.every((r,i)=>!i||out[i-1][1]<=r[0]),'Overlapping rows');return out;};
const patchKeys=new Set();for(const r of originalPatch.rows)for(const[a,z,owner]of r.runs)for(let x=a;x<z;x++)patchKeys.add(`${r.y}:${x}:${owner}`);
need(allKeys.size===27555&&holdKeys.size===94&&wanted.size===77&&patchKeys.size===allKeys.size&&[...allKeys].every(k=>patchKeys.has(k)),'Complete original partition');
const requested={rows:originalPatch.rows.map(r=>({y:r.y,runs:r.runs.filter(run=>!heldOwners.has(run[2]))})).filter(r=>r.runs.length)};
const prior={rows:[...priorRows].sort(([a],[b])=>a-b).map(([y,runs])=>({y,runs:merge(runs)}))};
const cataloguePath='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
const catalogue=json(cataloguePath),source=catalogue.products.find(r=>r.key==='gb:DEU:ADM3');
need(source.feature_count===428,'Complete domestic source family');
const parts=source.parts.map(p=>({...pin(p.path),decoded_bytes:p.uncompressed_bytes,decoded_sha256:p.uncompressed_sha256}));
const physicalPath=P+'/physical-001/whole-target-support.json',physical=json(physicalPath,C),physicalPin=pins.get(C+':'+physicalPath);
const byPhysical=new Map(physical.results.map(r=>[r.target,r]));need(byPhysical.size===100,'Complete physical atoms');
const world=pin('data/world-index.json'),projectionPath='data/macro-foundation/world-review-projection.json',projection=json(projectionPath);
need(projection.current_pins.location_index_sha256===world.sha256,'Current projection identity');
const cohort=[],cohortParts=[];for(const n of projection.location_parts){cohort.push(...json('data/'+n));cohortParts.push(pins.get(H+':data/'+n));}
need(cohort.length===49625&&new Set(cohort.map(r=>r.id)).size===49625,'Whole world owner inventory');
const geographyPaths=[6,28,29].map(n=>'data/geography/part-'+n+'.json'),canonical=[];
for(const p of geographyPaths)canonical.push(...json(p).features.filter(f=>f.properties.reference_owner==='Germany'));
const german=cohort.filter(r=>r.owner==='Germany');
need(canonical.length===409&&german.length===409&&canonical.every(f=>german.some(r=>r.id===f.id)),'Complete German canonical cohort');
const members=new Map(membership.map(m=>[m.source_id,m])),targets=[],roleDecisions=[];
for(const s of stages){
 const m=members.get(s.target),role=roleByAtom.get(s.target),support=byPhysical.get(s.target).support;
 need(m&&role&&m.pixelIndex===role.owner&&m.target_id===role.target_id&&m.target_id===s.selected.id,'Exact atom owner role join');
 const ys=wanted.get(m.pixelIndex);
 if(!ys){roleDecisions.push({source_id:s.target,pixelIndex:m.pixelIndex,official_gf:role.official_gf,positive_classes:[],decision:'Prior hold: original land request has only an official water-extension atom.'});continue;}
 const requestedClasses=[...new Set([...ys.values()].flat().map(r=>r[2]))].sort();
 const allowed=requestedClasses.filter(k=>role.official_gf==='4'||k==='mapped_inland_water_support');
 const classes=allowed.filter(k=>support[k]?.coordinates?.length);
 need(role.official_gf==='2'||classes.length===requestedClasses.length,'GF4 physical support class unexpectedly missing');
 roleDecisions.push({source_id:s.target,pixelIndex:m.pixelIndex,official_gf:role.official_gf,official_nuts_code:role.official_nuts_code,requested_classes:requestedClasses,positive_classes:classes,decision:classes.length?'Role-qualified positive classes; complete physical vetoes retained.':'Negative-only measured sibling; no permitted requested positive support.'});
 if(!classes.length)continue;
 targets.push({id:s.target,target_id:m.target_id,pixelIndex:m.pixelIndex,base_geometry:s.selected.geometry,source_family:'gb:DEU:ADM3',source_receipt_sha256:physicalPin.sha256,coverage_classes:classes,coverage_rows:[...ys].sort(([a],[b])=>a-b).map(([y,runs])=>({y,runs:merge(runs)})),territorial_exclusions:[]});
}
need(targets.length===78&&new Set(targets.map(t=>t.pixelIndex)).size===77,'Exact eligible atom and owner counts');
need(targets.filter(t=>roleByAtom.get(t.id).official_gf==='2').every(t=>t.pixelIndex===5755&&t.coverage_classes.join(',')==='mapped_inland_water_support'),'GF2 cannot qualify land');
const config={version:1,compact_territorial_exclusions:true,territorial_exclusion_families:foreign.whole_bounds_candidate_families,selector:{commit:H,path:'data/ownership-selection.json'},source_evidence:{version:1,kind:'source-target-native-evidence-v1',catalogue:pins.get(H+':'+cataloguePath),families:[{source_id:'gb:DEU:ADM3',parts}],physical_evidence:physicalPin,physical_input:pin(P+'/source-stage-001/original-stage-inputs.json',C),physical_reproduction:pin('scripts/qualify-source-cohort.py'),source_membership:{index:world,lineage:pin('data/semantic-report.json'),parts:geographyPaths.map(p=>pins.get(H+':'+p)),cohort_inventory:{index:pins.get(H+':'+projectionPath),parts:cohortParts}},targets}};
const assessment={kind:'Germany-complete-original-native-request',baseline:H,input_commit:C,original_cells:27555,original_intervals:7499,original_owners:82,original_atoms:100,native_requested_cells:27461,native_requested_owners:77,positive_atoms:78,prior_held_cells:94,prior_held_owners:[...heldOwners],role_decisions:roleDecisions,whole_physical_members:100,physical_issues:physical.results.reduce((n,r)=>n+r.issues.length,0),whole_domestic_source_features:428,complete_Germany_canonical_owners:409,complete_world_owner_ids:49625,foreign_original_features:73085,territorial_negative_families:foreign.whole_bounds_candidate_families,inputs:[...pins.values()],limits:['All 27,555 original keys remain exactly in requested plus explicit prior-held partitions.','GF2 administrative water extensions supply no positive land coverage. Actual inland-water support remains class-specific.','All 100 measured atoms and physical issues remain available, including omitted positive siblings as stock veto operands.','Native and selected authority remain pending.']};
const products={'source-evidence-config.json':config,'native-requested-patch.json':requested,'prior-source-role-holds.json':prior,'native-request-accounting.json':assessment};
need(!fs.lstatSync(O,{throwIfNoEntry:false}),'Fresh output');fs.mkdirSync(O);const outputs={};
for(const[n,v]of Object.entries(products)){const b=Buffer.from(JSON.stringify(v)+'\n');fs.writeFileSync(path.join(O,n),b,{flag:'wx'});outputs[n]={bytes:b.length,sha256:sha(b)};}
fs.writeFileSync(path.join(O,'preparation.json'),JSON.stringify({complete:true,method_commit:C,outputs})+'\n',{flag:'wx'});
console.log(JSON.stringify({original:27555,requested:27461,prior_held:94,owners:77,positive_atoms:78,outputs}));
