// Offline, source-pinned composition. Never install, import, deploy or rewrite live data.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';
import {validateGeometryMigrations} from '../../../../scripts/prepare-geographic-release.mjs';
import {replaceFeatureSpans} from './raw-feature-spans.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const read = file => JSON.parse(file.endsWith('.gz') ? gunzipSync(fs.readFileSync(file)) : fs.readFileSync(file));
const save = (file, value) => { fs.mkdirSync(path.dirname(file), {recursive:true}); fs.writeFileSync(file, JSON.stringify(value)); };
const hash = file => sha(fs.readFileSync(file));
const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
const safe = (base, relative) => {
 const file = path.resolve(base,relative);
 if(!file.startsWith(path.resolve(base)+path.sep)) throw Error('Evidence path escapes its directory');
 return file;
};
const load = directory => read(path.join(directory,'world-index.json')).parts.flatMap(p=>read(safe(directory,p)).features);
const pinnedCopy = (input,output) => {
 const manifest=read(input),base=path.dirname(input);
 fs.mkdirSync(output,{recursive:true});
 for(const [name,pin] of Object.entries(manifest.files??{})) {
  const source=safe(base,pin.archive_path??name),target=safe(output,pin.archive_path??name);
  if(hash(source)!==pin.sha256) throw Error('Replacement manifest source changed: '+name);
  fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(source,target);
 }
 fs.copyFileSync(input,path.join(output,'index.json'));
};

export function compose({root,output,replacementPatches,replacementManifests,creationPatches=[]}) {
 root=path.resolve(root);output=path.resolve(output);
 if(fs.existsSync(output)||output===root||output.startsWith(root+path.sep)||root.startsWith(output+path.sep)) throw Error('Fresh staging directory outside checkout required');
 const baseline=path.join(root,'data'),index=read(path.join(baseline,'world-index.json')),units=read(path.join(baseline,'hierarchy.json'));
 if(!replacementPatches?.length||replacementPatches.length!==replacementManifests?.length) throw Error('One replacement manifest per patch required');
 const patches=replacementPatches.map(read),receipts=[],updates=new Map(),archives=new Map();
 for(let i=0;i<patches.length;i++) {
 const patch=patches[i],replacementManifest=replacementManifests[i],manifest=read(replacementManifest),receiptFile=Object.keys(manifest.files).find(k=>/^migration-receipt\.json(?:\.gz)?$/.test(k));
 if(!receiptFile) throw Error('Replacement manifest has no receipt');
 const receipt=read(safe(path.dirname(replacementManifest),manifest.files[receiptFile].archive_path??receiptFile));
 if(receipt.geometry_stage_validated!==true||receipt.historical_claims_transferred!==false||receipt.added_ids.length||receipt.removed_ids.length) throw Error('Only validated retained-ID replacements are supported');
 if(patch.history_transfer!==false||patch.supported_from!==2026||patch.supported_to!==2027||patch.input_hierarchy_sha256!==hash(path.join(baseline,'hierarchy.json'))||patch.input_world_index_sha256!==hash(path.join(baseline,'world-index.json'))) throw Error('Replacement support interval or input release pins differ');
 if(patch.added_features.length||patch.added_groups.length||patch.existing_group_updates.length) throw Error('Replacement patch may not change hierarchy or create land');
 const local=new Map(patch.existing_location_updates.map(f=>[f.id,f])),old=new Map(receipt.archives.map(r=>[r.id,r.feature]));
 if(local.size!==patch.existing_location_updates.length||local.size!==receipt.changed_ids.length||receipt.changed_ids.some(id=>!local.has(id)||!old.has(id))) throw Error('Replacement scope differs from receipt');
 for(const [id,f] of local) {if(updates.has(id)) throw Error('Overlapping replacement scope');updates.set(id,f);archives.set(id,old.get(id));}
 receipts.push(receipt);
 }
 for(const phase of ['baseline','replacement','creation']) fs.mkdirSync(path.join(output,phase,'geography'),{recursive:true});
 const oldIds=new Set(),beforeById=new Map(),parts=[];let beforeCount=0;
 for(const part of index.parts) {
  const source=safe(baseline,part);
  if(patches.some(p=>p.input_part_sha256[part]!==hash(source))) throw Error('Baseline geographic part changed: '+part);
  const rows=read(source).features;let changed=false;
  const after=rows.map(f=>{
   if(oldIds.has(f.id)||f.id!==f.properties?.id) throw Error('Invalid baseline identity');
   oldIds.add(f.id);beforeCount++;
   if(!updates.has(f.id)) return f;
   if(!same(f,archives.get(f.id))) throw Error('Archived original differs from installed location: '+f.id);
   const candidate=updates.get(f.id);
   const identity=p=>Object.fromEntries(Object.entries(p).filter(([key])=>key!=='metadata'));
   if(!same(identity(f.properties),identity(candidate.properties))||candidate.id!==f.id) throw Error('Retained replacement may change only geometry/source metadata: '+f.id);
   beforeById.set(f.id,f);changed=true;return candidate;
  });
  fs.symlinkSync(source,safe(path.join(output,'baseline'),part));
  const target=safe(path.join(output,'replacement'),part);
  if(changed) {
   const rewritten=replaceFeatureSpans(fs.readFileSync(source,'utf8'),updates);
   if(rewritten.changed_ids.length!==rows.filter(f=>updates.has(f.id)).length) throw Error('Raw replacement scope mismatch');
   fs.writeFileSync(target,rewritten.raw);
  }else fs.symlinkSync(source,target);
  fs.symlinkSync(target,safe(path.join(output,'creation'),part));
  parts.push({path:part,before_sha256:hash(source),after_sha256:hash(target),linked_unchanged:!changed});
 }
 if(beforeById.size!==updates.size) throw Error('Replacement identity missing from baseline');
 for(const phase of ['baseline','replacement','creation']) {
  save(path.join(output,phase,'world-index.json'),index);
  fs.symlinkSync(path.join(baseline,'hierarchy.json'),path.join(output,phase,'hierarchy.json'));
 }
 for(let i=0;i<replacementManifests.length;i++) pinnedCopy(replacementManifests[i],path.join(output,'replacement-inputs',String(i)));
 save(path.join(output,'replacement-input-receipts.json'),receipts);
 const additions=[],newUnits=[],proofs=[],inputs=[],seenIds=new Set(oldIds),groupIds=new Set(units.map(u=>u.id));
 const proofBase=path.join(output,'proof-input');fs.mkdirSync(path.join(proofBase,'sources'),{recursive:true});
 for(const filename of creationPatches) {
  const candidate=read(filename),base=path.dirname(path.resolve(filename));
  const supported=(key,year)=>Object.hasOwn(candidate,key)?candidate[key]===year:(candidate.creation_proofs?.length>0&&candidate.creation_proofs.every(p=>p.source?.[key]===year));
  if(candidate.history_transfer!==false||!supported('supported_from',2026)||!supported('supported_to',2027)) throw Error('Creation patch must explicitly be modern-reference-only with no history transfer');
  if(candidate.input_hierarchy_sha256!==hash(path.join(baseline,'hierarchy.json'))) throw Error('Creation hierarchy baseline differs');
  if(candidate.existing_location_updates?.length||candidate.existing_group_updates?.length||candidate.changed_features?.length||candidate.removed_ids?.length) throw Error('Creation input may not alter existing territories or groups');
  const inputFeatures=candidate.added_features??[],inputProofs=candidate.creation_proofs??[];
  if(inputFeatures.length!==inputProofs.length||!inputFeatures.length) throw Error('Exact creation proof inventory required');
  for(const u of candidate.added_groups??[]) {
   if(groupIds.has(u.id)||!['province','area'].includes(u.level)) throw Error('Only distinct new local groups supported');
   groupIds.add(u.id);newUnits.push(u);
  }
  for(const feature of inputFeatures) {
   if(seenIds.has(feature.id)||feature.id!==feature.properties?.id) throw Error('Duplicate or conflicting creation identity');
   seenIds.add(feature.id);additions.push(feature);
   const matches=inputProofs.filter(p=>p.location_id===feature.id);
   if(matches.length!==1) throw Error('Exactly one proof per created location required');
   const proof=structuredClone(matches[0]),source=safe(base,proof.source.path),raw=fs.readFileSync(source);
   if(sha(raw)!==proof.source.sha256||proof.source.supported_from!==2026||proof.source.supported_to!==2027) throw Error('Creation source bytes/support interval differ');
   const name=`sources/${proofs.length}.geojson`;fs.writeFileSync(safe(proofBase,name),raw);proof.source.path=name;proofs.push(proof);
  }
  inputs.push({path:path.resolve(filename),sha256:hash(filename),added_locations:inputFeatures.length});
 }
 if(additions.length) {
  const groups=structuredClone(units).concat(newUnits),byId=new Map(groups.map(u=>[u.id,u])),counts=new Map(groups.map(u=>[u.id,0]));
  for(const u of groups) if(u.parent_id!==null) counts.set(u.parent_id,(counts.get(u.parent_id)??0)+1);
  for(const part of index.parts) for(const f of read(safe(path.join(output,'replacement'),part)).features) counts.set(f.properties.parent_id,(counts.get(f.properties.parent_id)??0)+1);
  for(const f of additions) {
   let parent=f.properties.parent_id;counts.set(parent,(counts.get(parent)??0)+1);
   for(const tier of ['province','area','region','subcontinent','continent']) {
    const unit=byId.get(parent);if(unit?.level!==tier) throw Error('Incomplete creation parent chain');parent=unit.parent_id;
   }
   if(parent!==null) throw Error('Continent has parent');
  }
  const touched=new Set([...additions.map(f=>f.properties.parent_id),...newUnits.flatMap(u=>[u.id,u.parent_id])]);
  for(const u of groups) if(touched.has(u.id)&&counts.get(u.id)!==u.metadata?.child_count) u.metadata={...u.metadata,child_count:counts.get(u.id)};
  fs.unlinkSync(path.join(output,'creation','hierarchy.json'));save(path.join(output,'creation','hierarchy.json'),groups);
  const part='geography/macro-loose-ends-v5-additions.json';save(path.join(output,'creation',part),{type:'FeatureCollection',features:additions});
  save(path.join(output,'creation','world-index.json'),{...index,parts:[...index.parts,part]});
 }
 save(path.join(proofBase,'proofs.json'),proofs);
 const result={version:1,before_locations:beforeCount,after_locations:seenIds.size,retained_geometry_changes:updates.size,added_locations:additions.length,added_groups:newUnits.length,changed_ids:[...updates.keys()].sort(),added_ids:additions.map(f=>f.id).sort(),replacement_inputs:replacementPatches.map((p,i)=>({path:path.resolve(p),sha256:hash(p),manifest_path:path.resolve(replacementManifests[i]),manifest_sha256:hash(replacementManifests[i])})),creation_inputs:inputs,source_part_preservation:parts,before_hierarchy_sha256:hash(path.join(baseline,'hierarchy.json')),after_hierarchy_sha256:hash(path.join(output,'creation','hierarchy.json')),history_transfer:false,published:false,canonical_grid_compiled:false,source_catalog_mutated:false};
 save(path.join(output,'composition.json'),result);return result;
}

export function verify({root,stage}) {
 stage=path.resolve(stage);root=path.resolve(root);
 const composition=read(path.join(stage,'composition.json')),before=load(path.join(stage,'baseline')),after=load(path.join(stage,'replacement')),units=read(path.join(stage,'replacement','hierarchy.json'));
 const inputs=read(path.join(stage,'replacement-input-receipts.json')),old=new Map(before.map(f=>[f.id,f])),next=new Map(after.map(f=>[f.id,f]));
 for(let i=0;i<inputs.length;i++) {
  const ids=new Set(inputs[i].changed_ids),individual=before.map(f=>ids.has(f.id)?next.get(f.id):f);
  validateGeometryMigrations({features:individual,baselineIds:before.map(f=>f.id),baselineFootprints:footprintHash(before),manifestFiles:[path.join(stage,'replacement-inputs',String(i),'index.json')],units});
 }
 const changed=new Set(composition.changed_ids),receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,before_footprints_sha256:footprintHash(before),after_footprints_sha256:footprintHash(after),changed_ids:[...changed].sort(),removed_ids:[],added_ids:[],reused_ids:[...old.keys()].filter(id=>!changed.has(id)).sort(),archives:inputs.flatMap(r=>r.archives),relationships:inputs.flatMap(r=>r.relationships),source_evidence:inputs.flatMap(r=>r.source_evidence)};
 const proofdir=path.join(stage,'replacement-migration');if(fs.existsSync(proofdir)) throw Error('Fresh verification proof directory required');fs.mkdirSync(proofdir);
 save(path.join(proofdir,'migration-receipt.json'),receipt);fs.copyFileSync(path.join(stage,'replacement','hierarchy.json'),path.join(proofdir,'after-hierarchy.json'));
 const files=Object.fromEntries(['migration-receipt.json','after-hierarchy.json'].map(name=>[name,{sha256:hash(path.join(proofdir,name))}]));
 for(let i=0;i<inputs.length;i++) {
  const base=path.join(stage,'replacement-inputs',String(i)),original=read(path.join(base,'index.json'));
  for(const name of ['index.json',...Object.values(original.files).map(pin=>pin.archive_path??'').filter(Boolean),...Object.entries(original.files).filter(([,pin])=>!pin.archive_path).map(([name])=>name)]) {
   const key=`inputs/${i}/${name}`,target=safe(proofdir,key);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(safe(base,name),target);files[key]={sha256:hash(target)};
  }
 }
 save(path.join(proofdir,'index.json'),{version:1,history_transfer:false,before_footprints_sha256:receipt.before_footprints_sha256,after_footprints_sha256:receipt.after_footprints_sha256,files});
 const replacement=path.join(proofdir,'index.json');
 validateGeometryMigrations({features:after,baselineIds:before.map(f=>f.id),baselineFootprints:footprintHash(before),manifestFiles:[replacement],units});
 const manifests=['replacement-migration/index.json'];
 if(composition.added_locations) {
  execFileSync(process.execPath,['--max-old-space-size=4096',path.join(root,'scripts/stage-land-creations.mjs'),`--before=${stage}/replacement`,`--after=${stage}/creation`,`--proofs=${stage}/proof-input/proofs.json`,`--output=${stage}/creation-migration`],{stdio:'inherit'});
  manifests.push('creation-migration/index.json');
 }
 const original=read(path.join(stage,'replacement-migration',Object.keys(read(replacement).files).find(k=>/^migration-receipt\.json(?:\.gz)?$/.test(k))));
 const creation=composition.added_locations?read(path.join(stage,'creation-migration/migration-receipt.json')):null;
 if(creation&&creation.before_footprints_sha256!==original.after_footprints_sha256) throw Error('Geometry proof order disagrees');
 const proofs=(creation?.creation_proofs??[]).map(p=>({...p,source:{...p.source,path:'creation-migration/'+p.source.path}}));
 const aggregate={...original,before_hierarchy_sha256:composition.before_hierarchy_sha256,after_hierarchy_sha256:composition.after_hierarchy_sha256,after_footprints_sha256:creation?.after_footprints_sha256??original.after_footprints_sha256,added_ids:creation?.added_ids??[],added_features:creation?.added_features??[],creation_proofs:proofs,relationships:[...original.relationships,...(creation?.relationships??[])],source_evidence:[...original.source_evidence,...(creation?.source_evidence??[])],ordered_geometry_manifest_required:true};
 const descriptor={version:1,before_footprints_sha256:aggregate.before_footprints_sha256,after_footprints_sha256:aggregate.after_footprints_sha256,manifests:manifests.map(name=>({path:name,sha256:hash(path.join(stage,name))})),metadata_receipts:[]};
 save(path.join(stage,'aggregate-source-receipt.json'),aggregate);save(path.join(stage,'geometry-proofs.json'),descriptor);
 const result={version:1,verified:true,before_locations:before.length,after_locations:composition.after_locations,changed_ids:aggregate.changed_ids.length,added_ids:aggregate.added_ids.length,removed_ids:0,before_footprints_sha256:aggregate.before_footprints_sha256,after_footprints_sha256:aggregate.after_footprints_sha256,aggregate_receipt_sha256:hash(path.join(stage,'aggregate-source-receipt.json')),geometry_proofs_sha256:hash(path.join(stage,'geometry-proofs.json')),history_transfer:false,published:false};
 save(path.join(stage,'integration-validation.json'),result);return result;
}

export function repairNumeric({root,stage}) {
 root=path.resolve(root);stage=path.resolve(stage);
 if(stage===root||stage.startsWith(root+path.sep)||root.startsWith(stage+path.sep))throw Error('Repair must target an independent stage');
 const composition=read(path.join(stage,'composition.json')),updates=new Map(),changes=[];
 for(const input of composition.replacement_inputs){
  if(hash(input.path)!==input.sha256||hash(input.manifest_path)!==input.manifest_sha256)throw Error('Pinned replacement input changed');
  for(const feature of read(input.path).existing_location_updates){if(updates.has(feature.id))throw Error('Duplicate replacement scope');updates.set(feature.id,feature);}
 }
 for(const row of composition.source_part_preservation){
  if(row.linked_unchanged)continue;
  const baseline=safe(path.join(root,'data'),row.path),target=safe(path.join(stage,'replacement'),row.path),creation=safe(path.join(stage,'creation'),row.path);
  if(hash(baseline)!==row.before_sha256||hash(target)!==row.after_sha256||fs.lstatSync(target).isSymbolicLink()||!fs.lstatSync(creation).isSymbolicLink()||fs.realpathSync(creation)!==fs.realpathSync(target))throw Error('Staged source part/link pins changed');
  const previous=fs.readFileSync(target,'utf8'),rewritten=replaceFeatureSpans(fs.readFileSync(baseline,'utf8'),updates).raw;
  const before=JSON.parse(previous),after=JSON.parse(rewritten);
  if(footprintHash(before.features)!==footprintHash(after.features)||!same(before.features,after.features))throw Error('Numeric restoration changed feature meaning');
  changes.push({path:row.path,before_sha256:row.after_sha256,after_sha256:sha(rewritten),bytes:Buffer.from(rewritten)});
 }
 // Inspect every target before writing any; creation keeps the original link target.
 for(const change of changes){fs.writeFileSync(safe(path.join(stage,'replacement'),change.path),change.bytes);composition.source_part_preservation.find(r=>r.path===change.path).after_sha256=change.after_sha256;}
 const receipt={version:1,canonical_geometry_changed:false,source_scope_changed:false,parts:changes.map(({bytes,...row})=>row)};
 composition.numeric_spelling_restoration=receipt;save(path.join(stage,'composition.json'),composition);save(path.join(stage,'numeric-spelling-restoration.json'),receipt);return receipt;
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 const args=process.argv.slice(2),get=k=>{const i=args.indexOf('--'+k);if(i<0||!args[i+1]) throw Error('Required --'+k);return args[i+1];};
 if(args.includes('--repair-numeric')) console.log(JSON.stringify(repairNumeric({root:get('root'),stage:get('stage')})));
 else if(args.includes('--verify')) console.log(JSON.stringify(verify({root:get('root'),stage:get('stage')})));
 else {const all=k=>args.flatMap((v,i)=>v==='--'+k?[args[i+1]]:[]);console.log(JSON.stringify(compose({root:get('root'),output:get('output'),replacementPatches:all('replacement-patch'),replacementManifests:all('replacement-manifest'),creationPatches:all('creation-patch')})));}
}
