// Reproduce the bounded #501 candidate without mutating the atlas or live records.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {stageLandCreations} from './stage-land-creations.mjs';
import {footprintHash} from './check-prepared.mjs';
import {createGridIndex,rasterize,GRID_ZOOM,GRID_WIDTH} from '../src/pixel-grid.js';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const save=(file,value)=>fs.writeFileSync(file,JSON.stringify(value));
function safe(root,relative){const file=path.resolve(root,relative);if(!file.startsWith(path.resolve(root)+path.sep))throw Error('Unsafe source path');return file;}
export function representation(feature){
 const index=createGridIndex([feature]),bounds=index[0].bounds;
 const x=Math.floor(bounds[0]),y=Math.floor(bounds[1]),width=Math.ceil(bounds[2])-x+1,height=Math.ceil(bounds[3])-y+1;
 if(width*height>8_000_000)throw Error('Named territory exceeds bounded pixel screen');
 const pixels=rasterize(index,{x,y,width,height});let count=0;const samples=[];
 for(let i=0;i<pixels.length;i++)if(pixels[i]){count++;if(samples.length<16)samples.push([x+i%width,y+Math.floor(i/width)]);}
 return {canonical_grid_zoom:GRID_ZOOM,canonical_size:GRID_WIDTH,projected_bounds:bounds,cell_center_count:count,example_cells:samples};
}
export function prepareOceaniaLand({root,output,evidence=fileURLToPath(new URL('../data/macro-improvements/oceania-restoration',import.meta.url))}){
 root=path.resolve(root);output=path.resolve(output);
 if(fs.existsSync(output)||output===root||output.startsWith(root+path.sep)||root.startsWith(output+path.sep))throw Error('Output must be fresh and separate from source checkout');
 const own=path.resolve(evidence),source=path.join(root,'data/macro-improvements/macro-coverage-oceania');
 const inputs=read(path.join(own,'inputs.json')),plan=read(path.join(own,'source-identity-plan.json.gz')),scan=read(path.join(own,'retained-identity-scan.json.gz'));
 for(const row of inputs.files){const file=row.path.startsWith('data/macro-improvements/oceania-restoration/')?safe(own,row.path.split('/').slice(3).join('/')):safe(root,row.path);if(sha(fs.readFileSync(file))!==row.sha256)throw Error('Immutable source bytes changed: '+row.path);}
 const before=path.join(root,'data'),hierarchyBytes=fs.readFileSync(path.join(before,'hierarchy.json'));
 if(sha(hierarchyBytes)!==inputs.baseline_hierarchy_sha256||inputs.baseline_geographic_version!==3)throw Error('Candidate must use its reviewed release-3 hierarchy');
 for(const row of [...scan.files,...scan.catalog_file_hashes,...scan.published_file_hashes])if(sha(fs.readFileSync(safe(root,row.path)))!==row.sha256)throw Error('Retained identity/archive pin changed: '+row.path);
 const index=read(path.join(before,'world-index.json')),old=index.parts.flatMap(p=>read(safe(before,p)).features),units=JSON.parse(hierarchyBytes);
 if(old.length!==scan.counts['current-world-index'])throw Error('Predecessor inventory changed');
 const sourceFeatures=read(path.join(source,'grouped-named-land-restoration-candidates.geojson.gz')).features;
 const maps={features:new Map(sourceFeatures.map(f=>[f.properties.name,f])),scans:new Map(scan.candidates.map(r=>[r.name,r]))};
 const task=plan.candidates.filter(c=>!['Palmerston','Manihiki'].includes(c.name));
 if(task.length!==30||new Set(task.map(c=>c.proposed_location_id)).size!==30)throw Error('Expected exactly 30 distinct task candidates');
 const rawSources=new Map(read(path.join(source,'osm-sources.json')).map(s=>[s.name,s]));
 const gazetteers=new Map([...read(path.join(source,'gazetteers.json')),...read(path.join(source,'supplement-gazetteers.json'))].map(s=>[s.name,s]));
 const originalIDs=new Set(old.map(f=>f.id));
 const catalogIDs=new Set();
 for(const row of scan.catalog_file_hashes)for(const e of read(safe(root,row.path)).entities??[])catalogIDs.add(e.id);
 // Geographic release entity batches supplement the immutable original catalog.
 for(const filename of fs.readdirSync(path.join(before,'geographic-releases')).filter(n=>/^entities-.*\.json$/.test(n)))for(const e of read(path.join(before,'geographic-releases',filename)).entities??[])catalogIDs.add(e.id);
 const prepared=[];
 for(const candidate of task){
  const sourceFeature=maps.features.get(candidate.name),previous=maps.scans.get(candidate.name),raw=rawSources.get(candidate.name),gaz=gazetteers.get(candidate.name);
  if(!sourceFeature||!previous||!raw||!gaz||previous.spatial_predecessors.length||originalIDs.has(candidate.proposed_location_id)||catalogIDs.has(candidate.proposed_location_id))throw Error('Candidate identity is not established as distinct: '+candidate.name);
  const xml=gunzipSync(fs.readFileSync(safe(source,raw.path)));
  if(sha(xml)!==raw.sha256||raw.sha256!==candidate.source_raw_sha256||sourceFeature.properties.source_sha256!==raw.sha256)throw Error('Raw coastline source pin changed');
  if(sha(gunzipSync(fs.readFileSync(safe(source,gaz.path))))!==gaz.sha256)throw Error('Identity gazetteer pin changed');
  const sourceIdentity='osm:named-land:'+candidate.canonical_semantic_key;
  const feature={type:'Feature',id:candidate.proposed_location_id,geometry:sourceFeature.geometry,properties:{id:candidate.proposed_location_id,name:candidate.name,parent_id:candidate.parent_chain[1].id,reference_owner:null,metadata:{source_id:'osm-api-2026-10-02',source_identity:sourceIdentity,source_name:'OpenStreetMap named dry-land coastline union',source_url:raw.url,license:'ODbL 1.0',attribution:'© OpenStreetMap contributors',source_raw_sha256:raw.sha256,source_way_ids:sourceFeature.properties.source_way_ids,reference_year:2026,supported_from:2026,supported_to:2027,source_role:candidate.role,parent_match:candidate.parent_basis,semantic_review:{status:'open',scope:'regional interior'},historical_claims_transferred:false}}};
  const grid=representation(feature);
  if(grid.cell_center_count!==candidate.pixel_representation.cell_center_count)throw Error('Canonical cell-center outcome changed: '+candidate.name);
  prepared.push({candidate,feature,sourceFeature:{...sourceFeature,id:sourceIdentity},raw,gaz,grid});
 }
 const eligible=prepared.filter(p=>p.grid.cell_center_count>0),held=prepared.filter(p=>!p.grid.cell_center_count);
 if(eligible.length!==28||held.length!==2)throw Error('Reviewed 28 additions / two grid holds changed');
 fs.mkdirSync(path.dirname(output),{recursive:true});const temporary=fs.mkdtempSync(path.join(path.dirname(output),'.oceania-restoration-'));
 try{
  const after=path.join(temporary,'after'),proofInput=path.join(temporary,'proof-input');fs.mkdirSync(after);fs.mkdirSync(proofInput);
  for(const filename of index.parts){const dest=safe(after,filename);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.copyFileSync(safe(before,filename),dest);}
  const needed=new Set(eligible.flatMap(p=>p.candidate.parent_chain.slice(1).map(u=>u.id))),existingUnits=new Set(units.map(u=>u.id));
  const newGroups=plan.new_parent_groups.filter(u=>needed.has(u.id)&&!existingUnits.has(u.id));
  for(const u of newGroups){if(catalogIDs.has(u.id))throw Error('New parent identity already retained');units.push({id:u.id,name:u.name,level:u.level,parent_id:u.parent_id,metadata:{source:'Named geographic/administrative island-group review',source_url:u.source_url,basis:u.role,kind:'geographic',framework_status:'source-backed',single_child_exception:u.single_child_exception,semantic_review:{status:'open',scope:'regional interior'},history_transfer:false}});}
  if(newGroups.length!==4)throw Error('Only four parents apply to the 28 eligible territories');
  const all=[...old,...eligible.map(p=>p.feature)],children=new Map();
  for(const row of [...all.map(f=>f.properties),...units])if(row.parent_id)children.set(row.parent_id,(children.get(row.parent_id)??0)+1);
  const touched=new Set(eligible.map(p=>p.feature.properties.parent_id));for(const g of newGroups)touched.add(g.parent_id);
  for(const u of units)if(touched.has(u.id)||newGroups.some(g=>g.id===u.id))u.metadata={...u.metadata,child_count:children.get(u.id)??0};
  save(path.join(after,'hierarchy.json'),units);const additionsPart='geography/oceania-restoration.json';save(safe(after,additionsPart),{type:'FeatureCollection',features:eligible.map(p=>p.feature)});save(path.join(after,'world-index.json'),{...index,parts:[...index.parts,additionsPart]});
  const proofs=[];
  for(const [i,p] of eligible.entries()){
   const filename=`source-${i}.geojson`,bytes=Buffer.from(JSON.stringify(p.sourceFeature));fs.writeFileSync(path.join(proofInput,filename),bytes);
   proofs.push({location_id:p.feature.id,parent_chain:p.candidate.parent_chain.slice(1).map(u=>u.id),source:{path:filename,sha256:sha(bytes),identity:p.sourceFeature.id,url:p.raw.url,license:'ODbL 1.0',attribution:'© OpenStreetMap contributors',supported_from:2026,supported_to:2027,original_archive:{path:'data/macro-improvements/macro-coverage-oceania/'+p.raw.path,raw_sha256:p.raw.sha256}},identity_review:{status:'distinct-new-territory',evidence_url:p.gaz.url,rationale:'Whole named source territory; exact current and archived land scan finds no physical predecessor. Retained same-name units are explicit geographic homonyms, with no land overlap; no homonym identity is reused. Private live preflight remains a publication gate.',same_name_existing_ids:old.filter(f=>f.properties.name.toLowerCase()===p.candidate.name.toLowerCase()).map(f=>f.id).sort(),retained_name_matches:maps.scans.get(p.candidate.name).exact_name_or_alias_registry_matches,gazetteer_raw_sha256:p.gaz.sha256}});
  }
  const proofFile=path.join(proofInput,'proofs.json');save(proofFile,proofs);
  // The existing generic creation contract independently checks exact source land,
  // overlap, complete parents and reconstructs every predecessor unchanged.
  const migration=stageLandCreations({before,after,proofs:proofFile,output:path.join(temporary,'migration')});
  const archivedFiles=scan.files.filter(f=>f.path.includes('archive'));
  execFileSync('python3',[fileURLToPath(new URL('./validate-oceania-land-restoration.py',import.meta.url))],{input:JSON.stringify({root,candidates:eligible.map(p=>p.feature),archives:archivedFiles}),maxBuffer:4*1024*1024});
  const henderson=old.find(f=>f.id==='PCN+00?'),evidence=gazetteers.get('Henderson');
  if(!henderson||!evidence||sha(gunzipSync(fs.readFileSync(safe(source,evidence.path))))!==evidence.sha256)throw Error('Retained Henderson source crosswalk evidence absent');
  const unknown=Object.fromEntries(['owner','culture','religion','population','rank','habitation','topography','vegetation','climate'].map(key=>[key,null]));
  const report={version:1,issue:501,baseline_geographic_version:3,baseline_hierarchy_sha256:inputs.baseline_hierarchy_sha256,before_footprints_sha256:footprintHash(old),after_footprints_sha256:footprintHash(all),before_locations:old.length,after_locations:all.length,added_locations:eligible.length,added_groups:newGroups.length,unchanged_location_ids:old.map(f=>f.id).sort(),new_group_ids:newGroups.map(g=>g.id),creation_manifest_sha256:migration.manifest_sha256,candidates:prepared.map(p=>({id:p.feature.id,name:p.candidate.name,parent_chain:p.candidate.parent_chain.slice(1).map(u=>u.id),geometry:p.feature.geometry,source_identity:p.sourceFeature.id,source_raw_sha256:p.raw.sha256,grid:p.grid,action:p.grid.cell_center_count?'staged-addition':'held-no-source-land-cell',initial_attributes:unknown,historical_claims_transferred:false})),retained_identity_crosswalks:[{id:henderson.id,old_reference_name:henderson.properties.name,proposed_reference_name:'Henderson Island',before_feature:henderson,geometry_changed:false,history_transfer:false,source_url:evidence.url,source_raw_sha256:evidence.sha256,source_path:'data/macro-improvements/macro-coverage-oceania/'+evidence.path,source_supported_interval:[2026,2027],applied:false,method:'Same retained physical footprint; proposed modern reference label only. Preserve source identity and all original claims; do not relocate or reuse PCN for newly added Pitcairn.'}],record_changes:0,historical_claims_transferred:false,private_live_registry_and_claims_checked:false,global_grid_recompiled:false,published:false,regional_interior_approved:false,publication_gates:['Authorized live registry/claim preflight','Separate retained-ID Henderson reference-label receipt','Combined ordered geometry/metadata migration chain and claim applicability review','New cached grid and exhaustive unique ownership/representation checks','Rebuild bottom-up envelopes and validate approved macro neighbor/source-gap routes','Matched static/hosted prepared assets and hosting limits; designated publisher']};
  save(path.join(temporary,'candidate-report.json'),report);fs.renameSync(temporary,output);
  return {output,before_locations:old.length,after_locations:all.length,added_locations:28,added_groups:4,held_names:held.map(p=>p.candidate.name),report_sha256:sha(fs.readFileSync(path.join(output,'candidate-report.json'))),creation_manifest_sha256:migration.manifest_sha256};
 }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const arg=key=>{const value=process.argv.find(a=>a.startsWith(`--${key}=`))?.slice(key.length+3);if(!value)throw Error('Required --'+key+'=path');return value;};
 console.log(JSON.stringify(prepareOceaniaLand({root:arg('root'),output:arg('output')})));
}
