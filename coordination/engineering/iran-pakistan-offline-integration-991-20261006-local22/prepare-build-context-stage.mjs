// Declare exact migrated build inputs and retained predecessor snapshots.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {BUILD_CONTEXT_VALIDATOR_SOURCES} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=process.cwd(),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const output=process.argv[2];
if(!output?.startsWith(prefix+'/')||fs.existsSync(output)||!path.resolve(output).startsWith(path.resolve(root,prefix)+path.sep))throw Error('Fresh owned stage required');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(root,head,[...BUILD_CONTEXT_VALIDATOR_SOURCES,prefix+'/prepare-build-context-stage.mjs']);
const budget=candidateBudget(code),sha=raw=>createHash('sha256').update(raw).digest('hex'),inputs=[],products=[];
const pin=name=>{const raw=fs.readFileSync(name),p={path:name,bytes:raw.length,sha256:sha(raw)};budget.add(p);inputs.push(p);return p;};
const oldDir='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1';
const original_stage=pin(oldDir+'/evidence-quality.json'),original=JSON.parse(fs.readFileSync(original_stage.path));
fs.mkdirSync(output);
const aliases=[],seen=new Map();
for(const snapshot of original.immutable_snapshots.filter(pin=>['data/geography/part-11.json','data/geography/part-17.json','data/geographic-releases/current-manifest.json'].includes(pin.path))){
 const name=output+'/snapshots/'+snapshot.path,raw=execFileSync('git',['show',snapshot.commit+':'+snapshot.path],{maxBuffer:32*1024*1024});
 if(raw.length!==snapshot.bytes||sha(raw)!==snapshot.sha256)throw Error('Original snapshot differs');
 if(!seen.has(name)){fs.mkdirSync(path.dirname(name),{recursive:true});fs.writeFileSync(name,raw,{flag:'wx'});budget.add({bytes:raw.length});products.push({path:name,bytes:raw.length,sha256:sha(raw)});seen.set(name,true);}
 aliases.push({commit:snapshot.commit,original_path:snapshot.path,path:name,bytes:snapshot.bytes,sha256:snapshot.sha256});
}
const before_context=pin(oldDir+'/inputs.json'),after_context=pin(prefix+'/repaired-context-v2/inputs.json');
for(const p of [before_context,after_context])for(const part of JSON.parse(fs.readFileSync(p.path)).parts)pin(path.posix.dirname(p.path)+'/'+part.path);
const native_proposal=pin('coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json');
const geometry_manifest=pin(prefix+'/release-proof-v3/index.json'),geometry=JSON.parse(fs.readFileSync(geometry_manifest.path));
const geometry_files=Object.entries(geometry.files).map(([name,p])=>pin(path.posix.dirname(geometry_manifest.path)+'/'+(p.archive_path??name)));
const releases=pin(prefix+'/successor-release-v1/releases-v7-gzip.json.gz');
const releaseProof=JSON.parse(fs.readFileSync(prefix+'/repaired-context-verification-v2.json'));
const binding=JSON.parse(fs.readFileSync(prefix+'/successor-verification-v2.json'));
// IDs come from the actual full source release registry, not diagnostic wording.
const {gunzipSync}=await import('node:zlib');const registry=JSON.parse(gunzipSync(fs.readFileSync(releases.path)));
const stage={version:1,issue:991,kind:'retained-identity-context-migration-v1',execution_commit:head,
 validator_sources:code.filter(p=>BUILD_CONTEXT_VALIDATOR_SOURCES.includes(p.path)),original_stage,
 original_snapshot_overrides:aliases,before_context,after_context,native_proposal,geometry_manifest,geometry_files,releases,
 predecessor_release_id:registry.releases.at(-2).id,successor_release_id:registry.releases.at(-1).id,
 installed:false,published:false,scientific_approval:false};
const raw=Buffer.from(JSON.stringify(stage)+'\n');budget.add({bytes:raw.length});fs.writeFileSync(output+'/manifest.json',raw,{flag:'wx'});products.push({path:output+'/manifest.json',bytes:raw.length,sha256:sha(raw)});
fs.writeFileSync(output+'/preparation-verification.json',JSON.stringify({execution_commit:head,producer:code,inputs,products,budget:budget.snapshot(),original_context_stage_separately_mandatory:true,installed:false,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({products:products.length,budget:budget.snapshot()}));
