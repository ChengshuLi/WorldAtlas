// Prepare a metadata-only reference install. Live files change only with --apply.
import fs from 'node:fs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {footprintHash} from './check-prepared.mjs';
import {validateMetadataRelationships} from './prepare-geographic-release.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';
import {prepareMacroReviewProjection} from './prepare-macro-review-projection.mjs';
import {readGeographicReleaseManifest,decodeGeographicReleaseBatch} from './read-geographic-release-manifest.mjs';
import {validateEvidenceRevalidationChain} from './validate-evidence-revalidation-chain.mjs';
import {prepareReferenceMacroBinding} from './prepare-reference-macro-binding.mjs';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const tiers=['location','province','area','region','subcontinent','continent'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const hashFile=p=>sha(fs.readFileSync(p));
const read=p=>JSON.parse(p.endsWith('.gz')?gunzipSync(fs.readFileSync(p)):fs.readFileSync(p));
const json=v=>Buffer.from(JSON.stringify(v)+'\n');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const equal=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
// Retain unchanged JSON text, including producer formatting and numeric lexemes.
export function patchJSONText(source,value){
 let cursor=0;const whitespace=()=>{while(/\s/.test(source[cursor]??'')&&cursor<source.length)cursor++;};
 const string=()=>{const start=cursor++;while(cursor<source.length){const c=source[cursor++];if(c==='\\')cursor++;else if(c==='"')return {start,end:cursor,value:JSON.parse(source.slice(start,cursor))};}throw Error('Unclosed JSON string');};
 function parse(){whitespace();const start=cursor,c=source[cursor];if(c==='"')return string();
  if(c==='{'||c==='['){cursor++;const object=c==='{',children=[],result=object?{}:[];whitespace();const close=object?'}':']';
   while(source[cursor]!==close){let key;if(object){key=string();whitespace();if(source[cursor++]!==':')throw Error('Invalid JSON field');}const child=parse();children.push({key:key?.value,node:child});if(object)result[key.value]=child.value;else result.push(child.value);whitespace();if(source[cursor]===close)break;if(source[cursor++]!==',')throw Error('Invalid JSON separator');whitespace();}
   cursor++;return {start,end:cursor,value:result,children,object};
  }
  while(cursor<source.length&&!/[\s,}\]]/.test(source[cursor]))cursor++;return {start,end:cursor,value:JSON.parse(source.slice(start,cursor))};
 }
 function render(node,next){if(equal(node.value,next))return source.slice(node.start,node.end);
  const object=next!==null&&!Array.isArray(next)&&typeof next==='object',array=Array.isArray(next);
  if(!node.children||node.object!==object||!object&&!array||object&&Object.keys(node.value).some(key=>!Object.hasOwn(next,key))||array&&next.length<node.children.length)return JSON.stringify(next);
  const edits=node.children.map((child,index)=>({start:child.node.start,end:child.node.end,text:render(child.node,object?next[child.key]:next[index])}));
  const added=object?Object.keys(next).filter(key=>!Object.hasOwn(node.value,key)).map(key=>`${JSON.stringify(key)}: ${JSON.stringify(next[key])}`):next.slice(node.children.length).map(row=>JSON.stringify(row));
  if(added.length){const last=node.children.at(-1),position=last?.node.end??node.start+1,example=node.children[0]?.node.start??node.start,lineStart=source.lastIndexOf('\n',example)+1,indent=/^\s*/.exec(source.slice(lineStart,example))[0],separator=source.slice(node.start,node.end).includes('\n')?'\n'+indent:'';edits.push({start:position,end:position,text:(last?',':'')+separator+added.join(','+separator)});}
  let result='',position=node.start;for(const edit of edits.sort((a,b)=>a.start-b.start)){result+=source.slice(position,edit.start)+edit.text;position=edit.end;}return result+source.slice(position,node.end);
 }
 const node=parse();whitespace();if(cursor!==source.length)throw Error('Trailing JSON text');return source.slice(0,node.start)+render(node,value)+source.slice(node.end);
}
export function safe(base,name){const p=path.resolve(base,name);if(!p.startsWith(path.resolve(base)+path.sep))throw Error('Unsafe relative asset path');return p;}
function tree(base,prefix=''){if(!fs.existsSync(base))return [];return fs.readdirSync(base,{withFileTypes:true}).flatMap(e=>{if(e.isSymbolicLink())throw Error('Symlinks are not accepted');return e.isDirectory()?tree(path.join(base,e.name),prefix+e.name+'/'):[prefix+e.name];});}
function geography(data){
 const index=read(path.join(data,'world-index.json')),units=read(path.join(data,'hierarchy.json')),features=index.parts.flatMap(p=>read(safe(data,p)).features),groups=new Map(units.map(u=>[u.id,u])),locations=new Map(features.map(f=>[f.id,f])),members=new Map();
 if(groups.size!==units.length||locations.size!==features.length)throw Error('Duplicate geographic identities');
 for(const f of features){if(f.id!==f.properties.id)throw Error('Mismatched location identity');let parent=f.properties.parent_id;for(const tier of tiers.slice(1)){const u=groups.get(parent);if(u?.level!==tier)throw Error('Incomplete adjacent-tier hierarchy');if(!members.has(parent))members.set(parent,[]);members.get(parent).push(f.id);parent=u.parent_id;}if(parent!==null)throw Error('Invalid continent parent');}
 if(units.some(u=>!members.has(u.id))||units.filter(u=>u.level==='continent').length!==6)throw Error('Empty group or wrong continent count');
 const proof={hierarchy_sha256:hashFile(path.join(data,'hierarchy.json')),location_index_sha256:hashFile(path.join(data,'world-index.json')),footprints_sha256:footprintHash(features)};
 return {index,units,features,groups,locations,members,proof};
}
export function validateMetadataStages(before,after,receiptFiles,{mode='macro'}={}){
 if(!['macro','reference-correction'].includes(mode))throw Error('Unknown metadata installation mode');
 if(mode==='macro'&&receiptFiles.length!==3)throw Error('Exactly three ordered macro receipts are required');
 if(mode==='reference-correction'&&receiptFiles.length!==1)throw Error('Exactly one rebased reference correction receipt required');
 if(before.proof.footprints_sha256!==after.proof.footprints_sha256||before.locations.size!==after.locations.size)throw Error('Metadata install changes canonical footprints/identities');
 for(const [id,f]of before.locations){const next=after.locations.get(id);if(!next||!equal(f.geometry,next.geometry)||!equal({...f.properties,parent_id:null},{...next.properties,parent_id:null}))throw Error('Non-parent location mutation');}
 const records=new Map(before.groups),groups=new Map(before.units.map(u=>[u.id,{...u,kind:u.level}])),locations=new Map(before.features.map(f=>[f.id,{...f.properties,kind:'location'}]));
 receiptFiles.forEach((file,i)=>{
  const receipt=read(file);
  if(mode==='macro'){
   if(receipt.stage!==['repairs','areas','regions'][i]||receipt.before_footprints_sha256!==before.proof.footprints_sha256||receipt.after_footprints_sha256!==after.proof.footprints_sha256)throw Error('Stale or unordered macro receipt');
  }else if(receipt.before_sha256!==before.proof.hierarchy_sha256||receipt.after_sha256!==after.proof.hierarchy_sha256||receipt.footprints_sha256_before!==before.proof.footprints_sha256||receipt.footprints_sha256_after!==after.proof.footprints_sha256||receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary?.geometry_changes!==0||!Array.isArray(receipt.relationships)){
   throw Error('Stale or incomplete reference correction receipt');
  }
  const repo=path.dirname(path.dirname(path.dirname(path.resolve(file))));for(const [p,pin]of Object.entries(receipt.decision_files_sha256??{}))if(hashFile(safe(repo,p))!==pin)throw Error('Macro source decision bytes changed after preparation');
  validateMetadataRelationships({beforeGroups:groups,beforeLocations:locations,beforeUnitRecords:records,receipt,receiptSha256:hashFile(file)});
  for(const d of receipt.group_changes){if(d.after){records.set(d.id,d.after);groups.set(d.id,{...d.after,kind:d.after.level});}else{records.delete(d.id);groups.delete(d.id);}}
  for(const d of receipt.changed_location_properties){const old=locations.get(d.location_id);if(!equal({...old,kind:null,parent_id:null},{...d.before_properties,kind:null,parent_id:null}))throw Error('Original location properties changed');locations.set(d.location_id,{...d.after_properties,kind:'location'});}
 });
 if(!equal([...records].sort(),[...after.groups].sort()))throw Error('Candidate hierarchy contains unreceipted metadata');
 for(const [id,f]of after.locations)if(locations.get(id)?.parent_id!==f.properties.parent_id)throw Error('Unreceipted location parent');
}
export function gridProjection(manifest,bounds,before,after){
 if(manifest.footprints_sha256!==before.proof.footprints_sha256||manifest.hierarchy_sha256!==before.proof.hierarchy_sha256||bounds.length!==after.locations.size)throw Error('Grid baseline is stale');
 const provinces=after.units.filter(u=>u.level==='province').map(u=>u.id).sort(),indices=new Map(provinces.map((id,i)=>[id,i+1])),seen=new Set(),seenIds=new Set(),membership=Buffer.alloc((bounds.length+1)*4);
 const projected=bounds.map(row=>{const prior=before.locations.get(row.id),next=after.locations.get(row.id);if(!prior||!next||row.province_id!==prior.properties.parent_id||!Number.isInteger(row.index)||row.index<1||row.index>bounds.length||seen.has(row.index)||seenIds.has(row.id))throw Error('Invalid original grid location/index');seen.add(row.index);seenIds.add(row.id);const province_index=indices.get(next.properties.parent_id);if(!province_index)throw Error('Missing grid province');membership.writeUInt32LE(province_index,row.index*4);return {...row,province_id:next.properties.parent_id,province_index};});
 return {provinces,bounds:projected,membership:gzipSync(membership,{mtime:0}),manifest:{...manifest,hierarchy_sha256:after.proof.hierarchy_sha256,provinces}};
}
function protectedFiles(data){
 const names=['hosted-catalog','ownership-history','ownership-runtime','reference-attributes','demographic-evidence','dated-reference-names','prepared-evidence'];
 const immutableReviews=['world-review.json','global-semantic-closure.json.gz',...tree(path.join(data,'geographic-semantic-followup')).map(p=>'geographic-semantic-followup/'+p)];
 return Object.fromEntries([...names.flatMap(name=>tree(path.join(data,name)).filter(p=>!(name==='prepared-evidence'&&['index.json','imports/index.json'].includes(p))&&!(['demographic-evidence','dated-reference-names'].includes(name)&&p==='revalidation.json')).map(p=>[name+'/'+p,hashFile(safe(data,name+'/'+p))])),...immutableReviews.map(p=>[p,hashFile(safe(data,p))])]);
}
function entityProof(geo,id){const f=geo.locations.get(id),ids=f?[id]:geo.members.get(id);if(!ids?.length)throw Error('Evidence subject removed: '+id);return {kind:f?'location':geo.groups.get(id).level,members:ids.length,sha256:sha(preparedEvidenceJSON([...ids].sort().map(id=>[id,geo.locations.get(id).geometry])))};}
export function composeEvidence(receipt,before,after,files){
 if(!equal(receipt.revalidated_geography,before.proof))throw Error('Previous evidence projection is stale');
 for(const file of receipt.source_product_files)if(hashFile(safe(files,file.path))!==file.sha256)throw Error('Original evidence source bytes changed');
 const entities=receipt.entities.map(row=>{const a=entityProof(before,row.entity_id),b=entityProof(after,row.entity_id);if(a.kind!==b.kind||a.members!==b.members||a.sha256!==b.sha256||a.sha256!==row.revalidated_footprint_sha256||row.original_footprint_sha256!==a.sha256)throw Error('Historical evidence territory changed: '+row.entity_id);return {...row,revalidated_footprint_sha256:b.sha256};});
 return {...receipt,revalidated_geography:after.proof,entities,historical_membership_assigned:false,
  projection:{method:'Previous immutable-footprint proof composed with exact current-to-candidate membership/footprint equality',previous_revalidation_sha256:sha(json(receipt)),installer_sha256:hashFile(fileURLToPath(import.meta.url))}};
}
export function appendRelease(old,next,load,{compressed=false}={}){
 const release=next.releases.at(-1);if(release.version<=old.releases.at(-1).version||old.releases.some(r=>r.id===release.id))throw Error('Candidate release must be a new version');
 const files=new Map(),batches=[];
 for(const batch of next.batches){const bytes=load(batch.path);if(sha(bytes)!==batch.sha256)throw Error('Candidate release batch hash mismatch');if(/^release-1\.json$|^1-/.test(batch.path))continue;
  let name=batch.path,raw=bytes;
  if(name==='sources.json'){name=`sources-${release.version}.json`;const payload=JSON.parse(bytes);raw=Buffer.from(JSON.stringify({...payload,sources:payload.sources.filter(s=>s.id===release.source_id)}));if(JSON.parse(raw).sources.length!==1)throw Error('New release source missing');}
  if(/^entities-/.test(name)){const match=/^entities-(\w+)-(\d+)\.json$/.exec(name);if(!match)throw Error('Invalid candidate entity batch');name=`entities-${match[1]}-v${release.version}-${match[2]}.json`;}
  if(compressed){
   const payload=encodeEvidenceJSON(JSON.parse(raw));
   raw=encodeEvidenceJSON(JSON.parse(raw),{gzip:true});name+='.gz';
   if(old.batches.some(b=>b.path===name)||files.has(name))throw Error('Release append would overwrite immutable batches');
   files.set(name,raw);batches.push({...batch,path:name,sha256:sha(raw),encoding:'gzip',payload_sha256:sha(payload)});
  }else{
   if(old.batches.some(b=>b.path===name)||files.has(name))throw Error('Release append would overwrite immutable batches');files.set(name,raw);batches.push({...batch,path:name,sha256:sha(raw)});
  }
 }
 return {files,index:{...old,releases:[...old.releases,release],batches:[...old.batches,...batches],new_entities:old.new_entities+next.new_entities,total_memberships:old.total_memberships+next.total_memberships,changes:old.changes+next.changes,validated_geometry:next.validated_geometry,sources_batches:[...(old.sources_batches??['sources.json']),`sources-${release.version}.json${compressed?'.gz':''}`]}};
}
export async function prepareInstall({data='data',geographyData='.cache/global-macro-foundation/after',releaseData='.cache/global-macro-foundation/release',stage='.cache/global-macro-reference-install',receipts=null,metadataMode='macro'}={}){
 data=path.resolve(data);geographyData=path.resolve(geographyData);releaseData=path.resolve(releaseData);stage=path.resolve(stage);if(stage===data||stage.startsWith(data+path.sep))throw Error('Install staging must be outside live data');
 receipts??=['repairs','areas','regions'].map(s=>path.join(data,'macro-foundation',`migration-${s}.json.gz`));
 const before=geography(data),after=geography(geographyData);validateMetadataStages(before,after,receipts,{mode:metadataMode});
 const release=read(path.join(releaseData,'index.json')),latest=release.releases.at(-1);if(latest.hierarchy_sha256!==after.proof.hierarchy_sha256||latest.footprints_sha256!==after.proof.footprints_sha256)throw Error('Candidate release/geography mismatch');
 const migrationPins=new Set(Object.values(latest.metadata?.metadata_migration_sha256??{}));if(receipts.some(p=>!migrationPins.has(hashFile(p))))throw Error('Candidate release does not pin every current metadata receipt');
 const oldReleases=readGeographicReleaseManifest(path.join(data,'geographic-releases'));for(const b of oldReleases.batches)decodeGeographicReleaseBatch(fs.readFileSync(safe(path.join(data,'geographic-releases'),b.path)),b);
 const preserved=protectedFiles(data),writes=new Map(),put=(name,value)=>{const original=safe(data,name);writes.set(name,Buffer.isBuffer(value)?value:name.endsWith('.json')&&fs.existsSync(original)?Buffer.from(patchJSONText(fs.readFileSync(original,'utf8'),value)):json(value));};
 for(const batch of oldReleases.batches)preserved['geographic-releases/'+batch.path]=batch.sha256;
 if(fs.existsSync(path.join(data,'geographic-releases/current-manifest.json'))){
  preserved['geographic-releases/index.json']=hashFile(path.join(data,'geographic-releases/index.json'));
  const pointer=read(path.join(data,'geographic-releases/current-manifest.json'));
  preserved['geographic-releases/'+pointer.path]=pointer.sha256;
 }
 for(const p of ['hierarchy.json','world-index.json',...after.index.parts])put(p,fs.readFileSync(safe(geographyData,p)));
 const grid=read(path.join(data,'canonical-grid/manifest.json'));for(const part of grid.parts)if(hashFile(safe(path.join(data,'canonical-grid'),part.path))!==part.sha256)throw Error('Immutable ownership-grid part changed');
 if(hashFile(safe(path.join(data,'canonical-grid'),grid.bounds.path))!==grid.bounds.sha256||hashFile(safe(path.join(data,'canonical-grid'),grid.province_membership.path))!==grid.province_membership.sha256)throw Error('Grid metadata byte mismatch');
 const priorBounds=read(safe(path.join(data,'canonical-grid'),grid.bounds.path)),priorMembership=gunzipSync(fs.readFileSync(safe(path.join(data,'canonical-grid'),grid.province_membership.path)));if(priorMembership.length!==(priorBounds.length+1)*4||priorBounds.some(r=>priorMembership.readUInt32LE(r.index*4)!==r.province_index||grid.provinces[r.province_index-1]!==r.province_id))throw Error('Original province LUT disagrees with bounds');
 const projection=gridProjection(grid,priorBounds,before,after),bounds=gzipSync(json(projection.bounds),{mtime:0});
 put('canonical-grid/'+grid.bounds.path,bounds);put('canonical-grid/'+grid.province_membership.path,projection.membership);
 projection.manifest.bounds={...grid.bounds,sha256:sha(bounds)};projection.manifest.province_membership={...grid.province_membership,sha256:sha(projection.membership)};put('canonical-grid/manifest.json',projection.manifest);
 const pixel=read(path.join(data,'pixel-audit.json'));if(pixel.footprints_sha256!==before.proof.footprints_sha256||pixel.hierarchy_sha256!==before.proof.hierarchy_sha256)throw Error('Pixel audit stale');put('pixel-audit.json',{...pixel,hierarchy_sha256:after.proof.hierarchy_sha256,metadata_only_revalidation:{footprints_unchanged:true,grid_ownership_bytes_unchanged:true,semantic_complete:false}});
 const audit=read(path.join(data,'granularity-audit.json'));if(audit.input_sha256['hierarchy.json']!==before.proof.hierarchy_sha256)throw Error('Granularity baseline stale');
 for(const key of ['locations_audited','coarse_units','small_units'])audit[key]=audit[key].map(r=>({...r,province_id:after.locations.get(r.id)?.properties.parent_id??r.province_id}));
 audit.counts=Object.fromEntries(tiers.slice(1).map(t=>[t,after.units.filter(u=>u.level===t).length]));for(const p of ['hierarchy.json','world-index.json',...after.index.parts])audit.input_sha256[p]=sha(writes.get(p));
 const inventory=after.units.map(u=>({id:u.id,name:u.name,level:u.level,parent_id:u.parent_id,member_location_ids:[...after.members.get(u.id)].sort()}));const inv=gzipSync(json(inventory),{mtime:0});put('macro-foundation/current-membership-inventory.json.gz',inv);audit.current_membership_inventory={path:'macro-foundation/current-membership-inventory.json.gz',sha256:sha(inv),semantic_complete:false};put('granularity-audit.json',audit);
 const appended=appendRelease(oldReleases,release,p=>fs.readFileSync(safe(releaseData,p)),{compressed:metadataMode==='reference-correction'});for(const [p,b]of appended.files)put('geographic-releases/'+p,b);
 if(fs.existsSync(path.join(data,'geographic-releases/current-manifest.json'))){
  const name=`releases-v${latest.version}-gzip.json.gz`;
  if(fs.existsSync(path.join(data,'geographic-releases',name)))throw Error('Release extension already exists');
  const packed=encodeEvidenceJSON(appended.index,{gzip:true});
  put('geographic-releases/'+name,packed);
  put('geographic-releases/current-manifest.json',{path:name,sha256:sha(packed),predecessor_index_sha256:hashFile(path.join(data,'geographic-releases/index.json'))});
 }else put('geographic-releases/index.json',appended.index);
 const prefix='reference-migrations/global-macro-reference-v'+latest.version+'/before';
 const evidence=read(path.join(data,'prepared-evidence/index.json'));for(const key of Object.keys(before.proof))if(evidence[key]!==before.proof[key])throw Error('Prepared evidence baseline stale');
 for(const product of evidence.products){
  const name=product.directory+'/revalidation.json',raw=fs.readFileSync(safe(data,name)),old=JSON.parse(raw),next=composeEvidence(old,before,after,safe(data,product.directory));
  next.projection.previous_revalidation_sha256=sha(raw);
  next.prior_revalidation={sha256:sha(raw),archive_path:'data/'+prefix+'/'+name+'.archive.gz',archive_sha256:sha(gzipSync(raw,{mtime:0})),compression:'gzip',revalidated_geography:old.revalidated_geography};
  next.migration_receipts=[...(old.migration_receipts??[]),...receipts.map(file=>({path:path.relative(path.dirname(data),file),sha256:hashFile(file)}))];
  put(name,next);const pin=sha(writes.get(name));product.revalidation.sha256=pin;for(const input of product.inputs)if(input.path==='revalidation.json')input.sha256=pin;
 }
 const imports=read(path.join(data,'prepared-evidence/imports/index.json'));put('prepared-evidence/imports/index.json',{...imports,...after.proof});evidence.imports.sha256=sha(writes.get('prepared-evidence/imports/index.json'));put('prepared-evidence/index.json',{...evidence,...after.proof});
 for(const [p,b]of await prepareMacroReviewProjection({data,before,after,receipts})){if(writes.has(p)||p in preserved)throw Error('Review projection overwrites an existing or immutable asset');safe(data,p);put(p,b);}
 let macroCompatibility=null;
 if(metadataMode==='reference-correction'){
  const macro=prepareReferenceMacroBinding({data,before,after,release:latest,receiptSha256:hashFile(receipts[0])});
  for(const [p,b]of macro.files){if(writes.has(p)||p in preserved)throw Error('Macro binding overwrites another staged or immutable asset');put(p,b);}
  macroCompatibility={groups:macro.binding.groups.length,macro_conventions_changed:false,published:false,new_approval_created:false};
 }
 const archives=[];
 for(const [name]of [...writes])if(fs.existsSync(safe(data,name))&&!name.startsWith('geography/')){const archive=prefix+'/'+name+'.archive.gz',raw=fs.readFileSync(safe(data,name));put(archive,gzipSync(raw,{mtime:0}));archives.push({original_path:name,original_sha256:sha(raw),archive_path:archive,archive_sha256:sha(writes.get(archive))});}
 const evidenceChains={};
 if(metadataMode==='reference-correction')for(const product of evidence.products){
  const name=product.directory+'/revalidation.json';
  evidenceChains[product.id]=validateEvidenceRevalidationChain(JSON.parse(writes.get(name)),{root:path.dirname(data),readFile:p=>{
   const absolute=safe(path.dirname(data),p);
   if(!absolute.startsWith(data+path.sep))throw Error('Evidence chain must remain within preserved atlas data');
   const relative=path.relative(data,absolute);
   return writes.get(relative)??fs.readFileSync(absolute);
  }});
 }
 const originals=Object.fromEntries([...writes.keys()].map(p=>[p,fs.existsSync(safe(data,p))?hashFile(safe(data,p)):null]));
 const report={version:1,reference_only:true,release_id:latest.id,before_geography:before.proof,after_geography:after.proof,receipts:receipts.map(p=>({path:p,sha256:hashFile(p)})),writes:Object.fromEntries([...writes].map(([p,b])=>[p,sha(b)])),originals,archives,preserved,evidence_chains:evidenceChains,macro_compatibility:macroCompatibility,immutable_grid_parts:grid.parts.map(p=>({path:'canonical-grid/'+p.path,sha256:p.sha256})),counts:latest.expected_counts,ownership_recompiled:false,historical_records_changed:false,semantic_complete:false};
 const validation=sha(json(report));fs.mkdirSync(stage,{recursive:true});for(const [p,b]of writes){const target=safe(path.join(stage,'after'),p);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,b);}fs.writeFileSync(path.join(stage,'report.json'),json({...report,validation_sha256:validation}));
 return {data,stage,report,validation_sha256:validation};
}
export function applyInstall(prepared,{expectedValidation,failAfter=Infinity}={}){
 if(!expectedValidation||expectedValidation!==prepared.validation_sha256)throw Error('Apply requires the exact reviewed validation hash');
 const {data,stage,report}=prepared,lock=path.join(data,'.macro-reference-install.lock');const fd=fs.openSync(lock,'wx'),backup=path.join(stage,'rollback-'+randomUUID()),done=[];fs.mkdirSync(backup,{recursive:true});
 try{
  for(const asset of report.immutable_grid_parts)if(hashFile(safe(data,asset.path))!==asset.sha256)throw Error('Grid ownership bytes changed after preparation');
  for(const [p,pin]of Object.entries(report.preserved))if(hashFile(safe(data,p))!==pin)throw Error('Historical bytes changed after preparation');
  for(const [p,pin]of Object.entries(report.originals))if((fs.existsSync(safe(data,p))?hashFile(safe(data,p)):null)!==pin)throw Error('Original metadata changed after preparation');
  for(const [p,pin]of Object.entries(report.writes))if(hashFile(safe(path.join(stage,'after'),p))!==pin)throw Error('Staged install bytes changed');
  // Retain every original before the first live replacement; a crash leaves
  // a lock and a durable journal identifying exact originals and staged bytes.
  for(const p of Object.keys(report.writes)){const target=safe(data,p),old=safe(backup,p);if(fs.existsSync(target)){fs.mkdirSync(path.dirname(old),{recursive:true});fs.copyFileSync(target,old);}}
  const journal={validation_sha256:expectedValidation,state:'committing',originals:report.originals,writes:report.writes,installed:done};const journalFile=path.join(backup,'journal.json');fs.writeFileSync(journalFile,json(journal));
  for(const [p]of Object.entries(report.writes)){const target=safe(data,p),temporary=target+'.macro-tmp';fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(safe(path.join(stage,'after'),p),temporary);fs.renameSync(temporary,target);done.push(p);fs.writeFileSync(journalFile,json(journal));if(done.length===failAfter)throw Error('Injected metadata install failure');}

  for(const [p,pin]of Object.entries(report.preserved))if(hashFile(safe(data,p))!==pin)throw Error('Historical bytes changed during install');
  fs.writeFileSync(path.join(backup,'commit.json'),json({validation_sha256:expectedValidation,installed:done,history_unchanged:true}));journal.state='committed';fs.writeFileSync(journalFile,json(journal));return {applied:true,validation_sha256:expectedValidation,rollback_archive:backup};
 }catch(error){for(const p of Object.keys(report.writes))fs.rmSync(safe(data,p)+'.macro-tmp',{force:true});for(const p of done.reverse()){const old=safe(backup,p),target=safe(data,p);if(fs.existsSync(old))fs.copyFileSync(old,target);else fs.rmSync(target,{force:true});}throw error;}finally{fs.closeSync(fd);fs.rmSync(lock,{force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const options={},apply=process.argv.includes('--apply');let expected;for(let i=2;i<process.argv.length;i++){const arg=process.argv[i];if(arg==='--apply')continue;const value=process.argv[++i];if(!value)throw Error('Missing installer argument');if(arg==='--expected-validation')expected=value;else if(arg==='--data')options.data=value;else if(arg==='--geography-data')options.geographyData=value;else if(arg==='--release-data')options.releaseData=value;else if(arg==='--stage')options.stage=value;else throw Error('Unknown installer argument: '+arg);}
 const prepared=await prepareInstall(options);console.log(JSON.stringify(apply?applyInstall(prepared,{expectedValidation:expected}):{dry_run:true,validation_sha256:prepared.validation_sha256,counts:prepared.report.counts,changed_files:Object.keys(prepared.report.writes).length,report:path.join(prepared.stage,'report.json')}));
}
