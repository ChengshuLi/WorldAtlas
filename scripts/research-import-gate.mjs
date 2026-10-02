import fs from 'node:fs';
import {fileURLToPath} from 'node:url';

const paused=()=>Error('Research imports are paused pending approved upper-level boundaries and complete regional hierarchy approval. Continue source-only research/staging; dry-run is available.');
const text=value=>typeof value==='string'&&value.trim().length>0;
const pinsValid=release=>release&&text(release.release_id)&&['hierarchy_sha256','footprints_sha256'].every(key=>/^[a-f0-9]{64}$/.test(release[key]));
const samePins=(a,b)=>['release_id','hierarchy_sha256','footprints_sha256'].every(key=>a?.[key]===b?.[key]);
const idsValid=ids=>Array.isArray(ids)&&ids.length>0&&ids.every(text)&&new Set(ids).size===ids.length;

function selectedRegions(gate,{regionIds}={}){
 if(gate?.version!==2||gate.ready_for_location_attributes!==true||gate.macro_boundaries?.approved!==true||!Number.isSafeInteger(gate.macro_boundaries.approval_issue)||gate.macro_boundaries.approval_issue<1||!text(gate.macro_boundaries.approval_evidence)||!/^[a-f0-9]{64}$/.test(gate.macro_boundaries.boundary_sha256))throw paused();
 if(!idsValid(regionIds)||!Array.isArray(gate.regions))throw Error('Research requires an explicit bounded list of approved region IDs');
 if(gate.regions.some(region=>!text(region?.region_id))||new Set(gate.regions.map(region=>region.region_id)).size!==gate.regions.length)throw Error('Invalid or duplicate region approval identities');
 const selected=regionIds.map(id=>{
  const region=gate.regions.find(row=>row.region_id===id);
  if(!region||region.semantic_complete!==true||!Number.isSafeInteger(region.approval_issue)||region.approval_issue<1||!text(region.approval_evidence)||region.macro_boundary_sha256!==gate.macro_boundaries.boundary_sha256||!pinsValid(region.approved_release)||!idsValid(region.approved_location_ids)||!idsValid(region.approved_subject_ids)||region.approved_location_ids.some(id=>!region.approved_subject_ids.includes(id)))throw Error(`Region ${id} is not approved for location research imports`);
  return region;
 });
 if(selected.some(region=>!samePins(region.approved_release,selected[0].approved_release)))throw Error('Selected regions do not share one exact approved geographic release; request engineering revalidation');
 // Ambiguous membership is never interpreted as permission to cross regions.
 const owners=new Map();
 for(const region of gate.regions){
  if(region.semantic_complete!==true)continue;
  if(!Array.isArray(region.approved_subject_ids))throw Error('Invalid regional subject inventory');
  for(const id of region.approved_subject_ids){if(owners.has(id))throw Error(`Subject ${id} has conflicting regional approvals`);owners.set(id,region.region_id);}
 }
 return selected;
}

export function assertResearchImportsReady(gate,options){
 if(gate?.version===1){
  if(gate.ready_for_location_attributes!==true||gate.semantic_complete!==true||!gate.approved_release?.release_id||!gate.approved_release?.hierarchy_sha256||!gate.approved_release?.footprints_sha256||!gate.approval_evidence)throw paused();
  return gate.approved_release;
 }
 return selectedRegions(gate,options)[0].approved_release;
}
export function readResearchImportGate(){return JSON.parse(fs.readFileSync(fileURLToPath(new URL('../data/research-geography-gate.json',import.meta.url)),'utf8'));}

function scopedTargets(regions,options){
 const subjects=new Set(regions.flatMap(region=>region.approved_subject_ids)),locations=new Set(regions.flatMap(region=>region.approved_location_ids));
 const check=(id,allowed=subjects)=>{if(!text(id)||!allowed.has(id))throw Error(`Research target ${String(id)} is outside the explicitly approved regional scope`);};
 const evidence=new Map();
 for(const region of regions)for(const row of region.approved_evidence_ids??[]){
  if(!['records','names','relationships','media_links'].includes(row?.collection)||!text(row.id)||!idsValid(row.subject_ids))throw Error('Invalid approved correction evidence inventory');
  row.subject_ids.forEach(id=>check(id,new Set(region.approved_subject_ids)));
  const key=`${row.collection}/${row.id}`;if(evidence.has(key))throw Error('Duplicate approved correction evidence');evidence.set(key,row.subject_ids);
 }
 let inputs=[];
 if(options.input!==undefined)inputs.push(options.input);
 if(options.batches!==undefined){
  if(!Array.isArray(options.batches)||!options.batches.length)throw Error('Supply the verified nonempty research bundle batches');
  inputs.push(...options.batches.map(batch=>{if(batch.part?.endpoint||batch.endpoint)throw Error('Regional content workers cannot import geographic memberships or existence changes');return batch.raw!==undefined?JSON.parse(batch.raw.toString()):batch.payload??batch;}));
 }
 if(!inputs.length&&!idsValid(options.subjectIds))throw Error('Regional research approval requires verified input or explicit target subject IDs');
 options.subjectIds?.forEach(id=>check(id));
 const retirements=[];
 for(const input of inputs){
  if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Invalid scoped research input');
  for(const [collection,rows] of Object.entries(input)){
   if(collection==='ingestion_id')continue;
   if(!['sources','records','names','relationships','media_links','retirements'].includes(collection))throw Error(`Regional imports do not permit ${collection}; shared identities and geographic changes require engineering approval`);
   if(!Array.isArray(rows))throw Error('Invalid scoped research collection');
   for(const row of rows){
    if(!row||typeof row!=='object'||Array.isArray(row))throw Error('Invalid scoped research row');
    let ids=[];
    if(collection==='records'){check(row.location_id,locations);ids=[row.location_id];}
    if(collection==='names'||collection==='media_links')ids=[row.entity_id];
    if(collection==='relationships')ids=[row.source_entity_id,row.target_entity_id];
    ids.forEach(id=>check(id));
    const certified=evidence.get(`${collection}/${row.id}`);
    if(certified&&(certified.length!==ids.length||certified.some(id=>!ids.includes(id))))throw Error('Evidence row does not match its approved territorial crosswalk');
    if(collection==='retirements')retirements.push(row);
   }
  }
 }
 for(const row of retirements){
  // Existing evidence IDs alone reveal no territorial scope. Require an explicit
  // engineering-certified subject crosswalk. A caller-supplied row cannot
  // prove an existing ID because the content service retains first-write IDs.
  const key=`${row.collection}/${row.target_id}`,target=evidence.get(key);
  if(!target)throw Error(`Correction target ${key} lacks approved territorial evidence`);
  target.forEach(id=>check(id));
  if(row.replacement_id){const replacement=evidence.get(`${row.collection}/${row.replacement_id}`);if(!replacement||target.length!==replacement.length||target.some(id=>!replacement.includes(id)))throw Error('A correction cannot transfer evidence between regional subjects');}
 }
 return {subject_ids:[...subjects],location_ids:[...locations]};
}

export function assertResearchBundleApproved(gate,geography,options={}){
 const approved=assertResearchImportsReady(gate,options);
 if((geography?.id??geography?.release_id)!==approved.release_id||geography.hierarchy_sha256!==approved.hierarchy_sha256||geography.footprints_sha256!==approved.footprints_sha256)throw Error('Research bundle does not match the approved geographic release; preserve it and request engineering revalidation');
 if(gate.version===2)scopedTargets(selectedRegions(gate,options),options);
 return approved;
}
