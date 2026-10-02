// Independent inventory, exact predecessor-byte and complete-chain validation.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';import {fileURLToPath,pathToFileURL} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),sha=b=>createHash('sha256').update(b).digest('hex'),read=f=>JSON.parse(f.endsWith('.gz')?gunzipSync(fs.readFileSync(f)):fs.readFileSync(f));
export function checkMarcusPolicy(proposal){
 const a=proposal.macro_amendment,c=proposal.parent_chain;
 if(a.include.region_id!==c[2]||a.include.subcontinent_id!==c[3]||a.include.continent_id!==c[4]||a.reciprocal_exclusion.region_id!=='framework:region:japan:d79de169a905'||JSON.stringify(a.include.named_land)!==JSON.stringify(a.reciprocal_exclusion.named_land))throw Error('Finite named route and reciprocal exclusion disagree');
 if(c[2]!=='framework:region:northwestern-pacific:2357073b3888'||c[3]!=='framework:subcontinent:micronesia:44f839aaab87'||c[4]!=='framework:continent:oceania:48580dd0c4b4')throw Error('Marcus macro convention changed');
 if(proposal.history_transfer||proposal.live_operation||proposal.regional_interior_approval||!a.immutable_prior_certificates||a.regional_interiors_approved)throw Error('Candidate changes history, certificates or research readiness');
 if(proposal.new_groups.length!==2||proposal.new_groups[0].id!==c[0]||proposal.new_groups[0].parent_id!==c[1]||proposal.new_groups[0].level!=='province'||proposal.new_groups[1].id!==c[1]||proposal.new_groups[1].parent_id!==c[2]||proposal.new_groups[1].level!=='area')throw Error('Provisional lower-tier chain disagrees');
 for(const g of proposal.new_groups)if(!g.metadata.single_child_exception||!g.metadata.coextensive_tier_exception||g.metadata.semantic_review.status!=='open')throw Error('Unstated isolated-island lower-tier exception');
 if(proposal.political_reference_context.Japan.automatic_attribute_assignment)throw Error('Modern sovereignty cannot assign historical ownership or geographic parents');
}
export async function checkMarcus({root,stage}){
 const p=read(path.join(here,'proposal.json'));checkMarcusPolicy(p);
 const before=path.join(root,'data'),after=path.join(stage,'after'),idx=read(path.join(before,'world-index.json')),nextIdx=read(path.join(after,'world-index.json'));
 if(JSON.stringify(nextIdx.parts)!==JSON.stringify([...idx.parts,'geography/marcus-restoration.json']))throw Error('Geography part inventory changed');
 for(const part of idx.parts)if(sha(fs.readFileSync(path.join(before,part)))!==sha(fs.readFileSync(path.join(after,part))))throw Error('Original feature bytes changed');
 const old=idx.parts.flatMap(part=>read(path.join(before,part)).features),added=read(path.join(after,'geography/marcus-restoration.json')).features;
 if(added.length!==1||added[0].id!==p.location_id||added[0].properties.parent_id!==p.parent_chain[0]||added[0].properties.reference_owner!==null)throw Error('Candidate identity/owner differs');
 const oldUnits=read(path.join(before,'hierarchy.json')),units=read(path.join(after,'hierarchy.json')),map=new Map(units.map(u=>[u.id,u]));
 if(map.size!==units.length||units.length!==oldUnits.length+2)throw Error('Unexpected parent identities');
 const children=new Map();for(const row of [...old.map(f=>f.properties),...added.map(f=>f.properties),...units])if(row.parent_id)children.set(row.parent_id,(children.get(row.parent_id)??0)+1);
 const oldChildren=new Map();for(const row of [...old.map(f=>f.properties),...oldUnits])if(row.parent_id)oldChildren.set(row.parent_id,(oldChildren.get(row.parent_id)??0)+1);
 for(const original of oldUnits){const a=structuredClone(original),b=structuredClone(map.get(a.id));if(!b)throw Error('Original parent removed');if(a.metadata?.child_count!==b.metadata?.child_count){if(a.metadata.child_count!==oldChildren.get(a.id)||b.metadata.child_count!==children.get(a.id))throw Error('Child count is not independently derived');delete a.metadata.child_count;delete b.metadata.child_count;}if(JSON.stringify(a)!==JSON.stringify(b))throw Error('Original parent identity, source or metadata changed');}
 const members=new Map(units.map(u=>[u.id,0])),tiers=['province','area','region','subcontinent','continent'];
 for(const f of [...old,...added]){let parent=f.properties.parent_id;for(const level of tiers){const u=map.get(parent);if(u?.level!==level)throw Error('Incomplete adjacent-tier membership');members.set(parent,members.get(parent)+1);parent=u.parent_id;}if(parent!==null)throw Error('Continent has a parent');}
 if([...members.values()].some(n=>!n)||units.filter(u=>u.level==='continent').length!==6)throw Error('Empty groups or continent count changed');
 const receipt=read(path.join(stage,'migration/migration-receipt.json')),manifest=read(path.join(stage,'migration/index.json'));
 if(receipt.changed_ids.length||receipt.removed_ids.length||JSON.stringify(receipt.added_ids)!==JSON.stringify([p.location_id])||receipt.historical_claims_transferred!==false||receipt.relationships[0]?.before_ids.length||receipt.relationships[0]?.history_transfer!==false)throw Error('Creation moves predecessor/history');
 for(const [file,pin] of Object.entries(manifest.files))if(sha(fs.readFileSync(path.join(stage,'migration',file)))!==pin.sha256)throw Error('Immutable creation evidence changed');
 const {validateGeometryMigrations}=await import(pathToFileURL(path.join(root,'scripts/prepare-geographic-release.mjs'))),{footprintHash}=await import(pathToFileURL(path.join(root,'scripts/check-prepared.mjs')));
 validateGeometryMigrations({features:[...old,...added],baselineIds:old.map(f=>f.id),baselineFootprints:footprintHash(old),manifestFiles:[path.join(stage,'migration/index.json')],units});
 const grid=read(path.join(stage,'grid-report.json')),identity=read(path.join(stage,'identity-review.json')),measure=read(path.join(stage,'geometry-measurements.json'));
 if(grid.locations.length!==1||grid.locations[0].cell_center_count<=0||grid.locations[0].existing_owned_cell_conflicts||grid.ownership_recompilations_global!==0||grid.live_apply||identity.physical_predecessors.length||identity.retained_name_alias_matches.length||identity.private_live_registry_checked||measure[0].source_water_rings!==1)throw Error('Source, identity or canonical-cell representation invalid');
 for(const [file,pin] of Object.entries(identity.registry_byte_pins))if(sha(fs.readFileSync(path.join(root,file)))!==pin)throw Error('Retained identity registry changed');
 return {verified:true,before_locations:old.length,after_locations:old.length+1,unchanged_features:old.length,added_groups:2,complete_chains:old.length+1,archived_predecessors:identity.counts,grid: grid.locations[0],historical_transfer:false,private_preflight:false,regional_interior_approval:false,live_apply:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const arg=k=>{const value=process.argv.find(a=>a.startsWith('--'+k+'='))?.slice(k.length+3);if(!value)throw Error('Required --'+k);return value;};console.log(JSON.stringify(await checkMarcus({root:arg('root'),stage:arg('stage')})));
}
