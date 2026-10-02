// Independent complete-inventory check of the real staged candidate; no live writes.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {fileURLToPath} from 'node:url';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),read=file=>JSON.parse(fs.readFileSync(file)),json=JSON.stringify;
export function checkOceaniaLand({before,stage}){
 const after=path.join(stage,'after'),report=read(path.join(stage,'candidate-report.json'));
 const oldIndex=read(path.join(before,'world-index.json')),nextIndex=read(path.join(after,'world-index.json'));
 const old=oldIndex.parts.flatMap(p=>read(path.join(before,p)).features),next=nextIndex.parts.flatMap(p=>read(path.join(after,p)).features);
 const all=new Map(next.map(f=>[f.id,f])),previous=new Set(old.map(f=>f.id));
 if(all.size!==next.length||old.length!==49589||next.length!==49617||old.some(f=>json(all.get(f.id))!==json(f)))throw Error('Original feature identity, metadata or footprint changed');
 for(const p of oldIndex.parts)if(sha(fs.readFileSync(path.join(before,p)))!==sha(fs.readFileSync(path.join(after,p))))throw Error('Original geography part bytes changed');
 const units=read(path.join(after,'hierarchy.json')),oldUnits=read(path.join(before,'hierarchy.json')),groups=new Map(units.map(u=>[u.id,u]));
 if(groups.size!==units.length||units.length!==oldUnits.length+4)throw Error('Candidate group inventory invalid');
 for(const u of oldUnits){const now=groups.get(u.id);if(!now||['id','name','level','parent_id'].some(key=>u[key]!==now[key]))throw Error('Original parent identity/name/membership changed');const a=structuredClone(u),b=structuredClone(now);if(a.metadata)delete a.metadata.child_count;if(b.metadata)delete b.metadata.child_count;if(json(a)!==json(b))throw Error('Original parent source evidence changed');}
 const tiers=['province','area','region','subcontinent','continent'],members=new Map(units.map(u=>[u.id,0]));
 for(const f of next){let parent=f.properties.parent_id;for(const level of tiers){const u=groups.get(parent);if(u?.level!==level)throw Error('Incomplete adjacent-tier chain: '+f.id);members.set(parent,members.get(parent)+1);parent=u.parent_id;}if(parent!==null)throw Error('Continent has a parent');}
 if([...members.values()].some(n=>!n)||units.filter(u=>u.level==='continent').length!==6)throw Error('Empty active group or continent inventory changed');
 const additions=next.filter(f=>!previous.has(f.id)),migration=read(path.join(stage,'migration/migration-receipt.json'));
 if(additions.length!==28||migration.added_ids.length!==28||migration.changed_ids.length||migration.removed_ids.length||migration.historical_claims_transferred!==false||migration.relationships.some(r=>r.kind!=='source-backed-create'||r.before_ids.length||r.after_ids.length!==1||r.history_transfer!==false))throw Error('Migration changes a predecessor or transfers history');
 if(report.candidates.length!==30||report.record_changes!==0||report.published||report.private_live_registry_and_claims_checked||report.global_grid_recompiled)throw Error('Report claims unperformed operations');
 const eligible=report.candidates.filter(c=>c.action==='staged-addition'),holds=report.candidates.filter(c=>c.action==='held-no-source-land-cell');
 if(eligible.length!==28||holds.length!==2||holds.some(c=>all.has(c.id)||c.grid.cell_center_count!==0)||eligible.some(c=>!all.has(c.id)||c.grid.cell_center_count<=0||json(c.geometry)!==json(all.get(c.id).geometry)))throw Error('Whole source territory / pixel-hold inventory inconsistent');
 for(const c of report.candidates)if(Object.values(c.initial_attributes).some(v=>v!==null)||c.historical_claims_transferred!==false)throw Error('Unsupported new attributes were assigned');
 const crosswalk=report.retained_identity_crosswalks[0];
 if(report.retained_identity_crosswalks.length!==1||crosswalk.id!=='PCN+00?'||crosswalk.applied||crosswalk.geometry_changed||crosswalk.history_transfer||json(crosswalk.before_feature)!==json(all.get(crosswalk.id)))throw Error('Henderson crosswalk moved original land/history');
 for(const [p,pin] of Object.entries(read(path.join(stage,'migration/index.json')).files))if(sha(fs.readFileSync(path.join(stage,'migration',p)))!==pin.sha256)throw Error('Creation evidence bytes changed');
 return {verified:true,before_locations:old.length,after_locations:next.length,added_locations:28,added_groups:4,complete_chains_checked:next.length,unchanged_features_checked:old.length,retained_history_transfer:false,held_names:holds.map(c=>c.name),current_grid_representation:'source-cell-center screening only; full ownership grid publication remains pending',private_live_preflight:false,report_sha256:sha(fs.readFileSync(path.join(stage,'candidate-report.json')))};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const arg=key=>{const value=process.argv.find(a=>a.startsWith(`--${key}=`))?.slice(key.length+3);if(!value)throw Error('Required --'+key+'=path');return value;};console.log(json(checkOceaniaLand({before:arg('before'),stage:arg('stage')})));
}
