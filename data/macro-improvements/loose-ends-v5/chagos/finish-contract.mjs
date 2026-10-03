// Run only as the designated serialized heavy job. Source geometry is unchanged.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';import {fileURLToPath} from 'node:url';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';
import {validateGeometryMigrations} from '../../../../scripts/prepare-geographic-release.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../../..');
const data=path.resolve(process.argv[2]??path.join(root,'data')),stage=path.resolve(process.argv[3]??path.join(here,'prepared'));
const read=p=>JSON.parse(p.endsWith('.gz')?gunzipSync(fs.readFileSync(p)):fs.readFileSync(p));
const hash=b=>createHash('sha256').update(b).digest('hex');
const write=(p,v)=>{const b=Buffer.from(JSON.stringify(v));fs.writeFileSync(p,p.endsWith('.gz')?gzipSync(b,{mtime:0}):b);};
const patch=read(path.join(stage,'patch.json.gz')),old=read(path.join(stage,'before-features.json.gz'));
if(old.length!==1||old[0].id!=='IOT+00?'||patch.existing_location_updates.length!==1)throw Error('Unexpected Chagos identity inventory');
const before=old[0],after=patch.existing_location_updates[0],validation=read(path.join(stage,'validation.json'));
if(after.id!==before.id||JSON.stringify(after.properties.parent_id)!==JSON.stringify(before.properties.parent_id))throw Error('Unexpected reparent');
const wrapper=read(path.join(stage,'source-dry-land.geojson.gz'));
if(wrapper.features.length!==1||JSON.stringify(wrapper.features[0].geometry)!==JSON.stringify(after.geometry))throw Error('Exact source wrapper mismatch');
const queries=read(path.join(here,'source-coastline-index.json.gz'));
fs.mkdirSync(path.join(stage,'sources'),{recursive:true});
const evidence=queries.map(q=>{const raw=fs.readFileSync(path.join(here,q.original_path));
 if(hash(gunzipSync(raw))!==q.original_sha256)throw Error('Original XML changed');
 const relative='sources/'+path.basename(q.original_path);fs.writeFileSync(path.join(stage,relative),raw);
 return{url:q.url,source_sha256:q.original_sha256,archive_sha256:hash(raw),path:relative,
 wrapper_path:'source-dry-land.geojson.gz',wrapper_sha256:hash(fs.readFileSync(path.join(stage,'source-dry-land.geojson.gz'))),
 source_id:'IOT+00?',source_code:'IOT',license:'OpenStreetMap contributors ODbL1.0',
 attribution:'https://www.openstreetmap.org/copyright',supported_from:2026,supported_to:2027,
 status:'modern-reference',scope:q.name,source_interpretation:'71directed complete coastline rings plus1separately inspected exactclosednamed Anniversary islet polygon'};});
const index=read(path.join(data,'world-index.json')),features=index.parts.flatMap(p=>read(path.join(data,p)).features);
const current=features.find(f=>f.id===before.id);
if(JSON.stringify(current)!==JSON.stringify(before))throw Error('Original subject archive is stale');
const beforeHash=footprintHash(features),next=features.map(f=>f.id===after.id?after:f),afterHash=footprintHash(next);
const units=read(path.join(data,'hierarchy.json')),unitMap=new Map(units.map(u=>[u.id,u])),chain=[];
let parent=before.properties.parent_id;
for(const tier of ['province','area','region','subcontinent','continent']){const u=unitMap.get(parent);if(u?.level!==tier)throw Error('Invalid parent chain');chain.push(parent);parent=u.parent_id;}
if(parent!==null)throw Error('Invalid continental root');
patch.input_world_index_sha256=hash(fs.readFileSync(path.join(data,'world-index.json')));
patch.replacement_deltas=[{id:before.id,before_feature:before,after_feature:after}];
patch.source_wrappers=[{id:before.id,path:'source-dry-land.geojson.gz',sha256:hash(fs.readFileSync(path.join(stage,'source-dry-land.geojson.gz'))),identity:before.id,code:'IOT',geometry_method:'Exact source land union; no invented coordinates; source classes retained'}];
patch.source_evidence=evidence;patch.operations=[{id:before.id,name:before.properties.name,kind:'source-backed-replace',
 before_feature_sha256:hash(Buffer.from(JSON.stringify(before))),before_geometry_sha256:hash(Buffer.from(JSON.stringify(before.geometry))),
 after_geometry_sha256:hash(Buffer.from(JSON.stringify(after.geometry))),parent_chain:chain,
 before_area_m2:validation.before_area_km2*1e6,after_area_m2:validation.after_area_km2*1e6,
 added_source_land_m2:validation.new_land_km2*1e6,removed_generalized_coverage_m2:0,history_transfer:false}];
write(path.join(stage,'patch.json.gz'),patch);
const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,
 before_footprints_sha256:beforeHash,after_footprints_sha256:afterHash,changed_ids:[before.id],added_ids:[],removed_ids:[],
 reused_ids:features.filter(f=>f.id!==before.id).map(f=>f.id).sort(),archives:[{id:before.id,feature:before}],
 relationships:[{kind:'source-backed-replace',proposal_id:'chagos-dry-land-v5:'+before.id,before_ids:[before.id],after_ids:[before.id],history_transfer:false}],source_evidence:evidence};
if(receipt.reused_ids.length!==49622)throw Error('Baseline location inventory changed');
write(path.join(stage,'migration-receipt.json.gz'),receipt);
const files={};for(const file of fs.readdirSync(stage)){const p=path.join(stage,file);if(file==='index.json'||!fs.statSync(p).isFile())continue;files[file]={sha256:hash(fs.readFileSync(p))};}
for(const file of fs.readdirSync(path.join(stage,'sources')))files['sources/'+file]={sha256:hash(fs.readFileSync(path.join(stage,'sources',file)))};
const manifest={version:1,issue:540,history_transfer:false,before_footprints_sha256:beforeHash,after_footprints_sha256:afterHash,
 producer_sha256:hash(fs.readFileSync(fileURLToPath(import.meta.url))),installed_geography_changed:false,published:false,files};
write(path.join(stage,'index.json'),manifest);
const result=validateGeometryMigrations({features:next,baselineIds:features.map(f=>f.id),baselineFootprints:beforeHash,manifestFiles:[path.join(stage,'index.json')],units});
if(result.changedIds.size!==1||result.addedIds.size||result.retiredIds.size)throw Error('Unexpected production contract result');
console.log(JSON.stringify({production_migration_gate_passed:true,changed_ids:[before.id],reused_ids:receipt.reused_ids.length,before_footprints_sha256:beforeHash,after_footprints_sha256:afterHash,source_geometry_changed:false,history_transfer:false}));
