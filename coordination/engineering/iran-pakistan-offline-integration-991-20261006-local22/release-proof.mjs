// Validate the last migration against the actual version-six world. No imports.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
import {validateGeometryMigrations} from '../../../scripts/prepare-geographic-release.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const options={};
for(let i=2;i<process.argv.length;i+=2){
  if(!['--stage','--out'].includes(process.argv[i])||!process.argv[i+1]||options[process.argv[i]])throw Error('Explicit stage and fresh output required');
  options[process.argv[i]]=process.argv[i+1];
}
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const stage=path.resolve(root,options['--stage']),out=path.resolve(root,options['--out']);
for(const file of [stage,out])if(!file.startsWith(path.join(root,prefix)+path.sep))throw Error('Owned stage/output required');
if(fs.existsSync(out))throw Error('Fresh output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const read=(commit,name)=>execFileSync('git',['-C',root,'show',commit+':'+name],{maxBuffer:32*1024*1024});
const executed=[path.relative(root,fileURLToPath(import.meta.url)),'scripts/check-prepared.mjs','scripts/prepare-geographic-release.mjs'];
const producer=executed.map(name=>{
  const raw=read(head,name);if(!raw.equals(fs.readFileSync(path.join(root,name))))throw Error('Commit executed producer before generation');
  return {path:name,sha256:digest(raw),bytes:raw.length};
});
const summary=JSON.parse(fs.readFileSync(path.join(stage,'summary.json')));
if(summary.status!=='no-new-regression'||summary.regressions!==0||summary.changed_ids.length!==2||summary.complete_world_locations!==49625)throw Error('Full-world stage did not pass');
const inputs=[];
const load=name=>{
  const raw=read(summary.baseline_commit,name);inputs.push({path:name,sha256:digest(raw),bytes:raw.length});
  return JSON.parse(name.endsWith('.gz')?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
};
const world=load('data/world-index.json'),before=world.parts.flatMap(name=>load('data/'+name).features);
const pointer=load('data/geographic-releases/current-manifest.json');
const releaseRaw=read(summary.baseline_commit,'data/geographic-releases/'+pointer.path);
if(digest(releaseRaw)!==pointer.sha256)throw Error('Current release pointer differs');
const release=JSON.parse(gunzipSync(releaseRaw)).releases.at(-1);
const oldHash=footprintHash(before);
if(release.version!==6&&release.id!=='geography:review:831aada26a8c7fe8c75553caf4432a22dc9c2cf458b14221a1135addb475f186')throw Error('Unexpected predecessor release');
if(oldHash!==release.footprints_sha256||before.length!==release.expected_counts.location)throw Error('Complete predecessor geometry differs');
const proposalRaw=read(summary.candidate_geometry_commit,summary.candidate_geometry_file.path);
if(digest(proposalRaw)!==summary.candidate_geometry_file.sha256)throw Error('Reviewed candidate differs');
const proposals=JSON.parse(proposalRaw),changed=summary.changed_ids;
if(JSON.stringify(Object.keys(proposals).sort())!==JSON.stringify([...changed].sort()))throw Error('Target roster differs');
const after=before.map(f=>proposals[f.id]?{...f,geometry:proposals[f.id]}:f),newHash=footprintHash(after);
const archives=before.filter(f=>changed.includes(f.id)).map(feature=>({id:feature.id,feature}));
const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,
  before_footprints_sha256:oldHash,after_footprints_sha256:newHash,
  changed_ids:changed,removed_ids:[],added_ids:[],reused_ids:before.filter(f=>!changed.includes(f.id)).map(f=>f.id).sort(),archives,
  relationships:[{before_ids:changed,after_ids:changed,kind:'source-backed-shared-seam-reference',proposal_id:'991-joint-native-partition',history_transfer:false,
    identity_pairs:changed.map(id=>({before_id:id,after_id:id,evidence:'Retained exact ID, name, tier and parent; complete before feature archived; authored crosswalk in reviewed source packet #1121.'}))}],
  source_evidence:[
    {url:'https://api.openstreetmap.org/api/0.6/relation/6555069/full.json',source_sha256:'abf435a64b61fd7f678f149adee6468d99e14edc769ec6e8e43d464ec6ed579d'},
    {url:'https://api.openstreetmap.org/api/0.6/relation/3229274/full.json',source_sha256:'7057f7488622c5a5c086b094205978fffe5d25ca514a89a72f2d45c1f0ff31be'}],
  source_policy:{reference_only:true,changed_component:'gap:10c95e9f3b4b8d93b3ce3145916de2de656527cc706a5f64b323aa680406cefb',
    outside_component:'Preserved existing native footprint membership; no whole-county source replacement.',
    new_coordinates:'OSM snapshots retrieved 2026-10-05; relation edit dates are not effective dates.',
    attribution:'© OpenStreetMap contributors; https://www.openstreetmap.org/copyright; ODbL 1.0.',
    retained_base:'Existing geoBoundaries features and country citation/underlying source notices unchanged.',
    unknown:['physical water','legal/historical boundary','positional accuracy','PAK underlying source-license detail']},
  independent_partition_review:{pr:1119,head:'4cf21a3ba689b4ea5fb307f50070eb09bfa864cd',comment:6013529006},
  independent_source_review:{pr:1121,head:'170a0a0ac8fc92f2ab046c58d17282c9f02a92ab',comment:6013645700},
  installed:false,published:false,geographic_approval:false};
fs.mkdirSync(out,{recursive:false});
const write=(name,value)=>{
  const raw=Buffer.from(JSON.stringify(value)+'\n');if(raw.length>32*1024*1024)throw Error('Oversized migration product');
  fs.writeFileSync(path.join(out,name),raw,{flag:'wx'});return {archive_path:name,bytes:raw.length,sha256:digest(raw)};
};
const pin=write('migration-receipt.json',receipt);
const manifest={version:1,history_transfer:false,before_footprints_sha256:oldHash,after_footprints_sha256:newHash,files:{'migration-receipt.json':pin}};
write('index.json',manifest);
const proof=validateGeometryMigrations({features:after,baselineIds:before.map(f=>f.id),baselineFootprints:oldHash,manifestFiles:[path.join(out,'index.json')]});
if(proof.changedIds.size!==2||proof.retiredIds.size||proof.addedIds.size||proof.pairs.some(pair=>pair.old_entity_id!==pair.new_entity_id||pair.history_transfer!=='none'))throw Error('History/identity preservation differs');
write('validation.json',{version:1,evaluation_commit:head,producer,inputs,stage_summary_sha256:digest(fs.readFileSync(path.join(stage,'summary.json'))),
  predecessor_release_id:release.id,before_footprints_sha256:oldHash,after_footprints_sha256:newHash,
  complete_reconstructed_features:proof.baselineFeatures.length,changed_ids:[...proof.changedIds].sort(),
  exact_original_features_restored:true,identity_pairs:proof.pairs.map(({old_entity_id,new_entity_id,history_transfer})=>({old_entity_id,new_entity_id,history_transfer})),
  historical_claims_transferred:false,installed:false,published:false,
  limits:['Last-step reference migration validation only; complete predecessor proof chronology retained separately.','No new geographic release, certificate, content import scope or ownership package is certified by this result.']});
console.log(JSON.stringify({status:'last-step-migration-validated',locations:before.length,changed:2,before:oldHash,after:newHash}));
