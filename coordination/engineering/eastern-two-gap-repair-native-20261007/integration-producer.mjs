// Exactly the reviewed two-target successor, using retained completed native science.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync,gzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {restoreWholeImage} from './whole-image.mjs';
import {immutableReader,loadSuccessor,TARGETS,BEFORE,AFTER} from './native-producer.mjs';
import {releaseInputs} from './release-inputs.mjs';
import {appendCompleteSuccessor} from './fast-release-append.mjs';
import {continueContent} from './content-continuation.mjs';
import {disposeCertificates} from './certificate-disposition.mjs';
import {validateBuildContextStage} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {readBuildOwnershipSelection,selectBuildOwnership} from '../../../scripts/select-build-ownership.mjs';
import {requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
export const BASE='913db0624b8aa79b188ff17a7f5c4ae0c0f63965';
export const NS='coordination/engineering/eastern-two-gap-repair-native-20261007';
const sha=b=>createHash('sha256').update(b).digest('hex'),json=x=>Buffer.from(JSON.stringify(x)+'\n');
export function codeClosure(repo,entry){
 const seen=new Set(['package.json']);
 function visit(p){if(seen.has(p))return;seen.add(p);const raw=fs.readFileSync(repo+'/'+p);for(const m of raw.toString().matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g))if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));}
 visit(entry);return [...seen].sort();
}
export function prepareInputClosure(repo,out){
 const restored=out+'/source-view',transport=repo+'/'+NS+'/complete-input-transport';
 const raw=fs.readFileSync(transport+'/index.json');restoreWholeImage(transport,restored,{expectedIndexSha:sha(raw)});
 const declared=JSON.parse(fs.readFileSync(repo+'/'+NS+'/complete-input-index.json'));
 const restoredIndex=fs.readFileSync(restored+'/'+NS+'/complete-input-index.json');assert(restoredIndex.equals(fs.readFileSync(repo+'/'+NS+'/complete-input-index.json')));
 assert.equal(declared.files.length,202);const storage=new Map();
 for(const pin of declared.files)storage.set(pin.original.commit+':'+pin.original.path,{...pin,alias:{...pin.alias,path:path.relative(repo,restored+'/'+pin.alias.path)}});
 const readers=new Map(),budget=candidateBudget([]);
 for(const pin of declared.files){const c=pin.original.commit;if(!readers.has(c))readers.set(c,immutableReader(repo,c,storage));const body=readers.get(c).read(pin.original.path);budget.add({bytes:body.length});}
 return {storage,input_only:{status:'PASS',files:declared.files.length,source_index_sha256:sha(restoredIndex),budget:budget.snapshot(),pins:[...readers.values()].flatMap(r=>r.pins())}};
}
export async function integrate(repo,out,{inputOnly=false}={}){
 requirePlainExecution();assert(path.isAbsolute(repo)&&fs.realpathSync(repo)===repo);assert(path.isAbsolute(out)&&!fs.existsSync(out));fs.mkdirSync(out,{recursive:true});
 const head=execFileSync('git',['-C',repo,'rev-parse','HEAD'],{encoding:'utf8'}).trim();assert.match(head,/^[a-f0-9]{40}$/);
 const code=codeClosure(repo,NS+'/integration-producer.mjs');code.push(NS+'/serialize-release.py',NS+'/audit-continuation.py',NS+'/original-audit-recipe.py.txt','scripts/evidence/immutable.py','.github/package-inputs.json');
 const modules=[...new Set(code)].sort().map(p=>{const local=fs.readFileSync(repo+'/'+p),committed=execFileSync('git',['-C',repo,'cat-file','blob',head+':'+p],{maxBuffer:32*1024*1024});assert(local.equals(committed),'Actual executed code differs '+p);return{path:p,bytes:local.length,sha256:sha(local)};});
 const {storage,input_only}=prepareInputClosure(repo,out);fs.writeFileSync(out+'/input-only.json',json(input_only));console.log('ALL202 original inputs loaded',input_only.budget);
 if(inputOnly)return input_only;
 const image=out+'/delivery';fs.mkdirSync(image);const put=(p,b)=>{assert(b.length<=32*1024*1024);const target=image+'/'+p;fs.mkdirSync(path.dirname(target),{recursive:true});assert(!fs.existsSync(target));fs.writeFileSync(target,b);return{path:p,bytes:b.length,sha256:sha(b)};};
 const original=await releaseInputs(repo,BASE,{storage,nativeStorage:storage});console.log('Complete84833 membership release loaded');
 const next=await appendCompleteSuccessor(original.registry,original.result,out+'/release-tail');assert.equal(next.pins.length,343);
 for(const p of next.pins)put('data/geographic-releases/'+p.path,fs.readFileSync(out+'/release-tail/'+p.path));
 const releases=put('data/geographic-releases/releases-v8.json.gz',gzipSync(json(next.index),{level:9}));
 const baseline=immutableReader(repo,BASE,storage);
 put('data/geographic-releases/current-manifest.json',json({path:'releases-v8.json.gz',sha256:releases.sha256,predecessor_index_sha256:sha(baseline.read('data/geographic-releases/index.json'))}));
 const native=loadSuccessor(repo,BASE,{storage}),manifestDir='data/canonical-grid/eastern-v8';
 function copyTree(p){for(const row of fs.readdirSync(repo+'/'+p,{withFileTypes:true})){const s=p+'/'+row.name;if(row.isDirectory())copyTree(s);else{assert(row.isFile());put(s,fs.readFileSync(repo+'/'+s));}}}
 copyTree(manifestDir);copyTree(NS+'/prior-v1');
 put('.github/package-inputs.json',fs.readFileSync(repo+'/.github/package-inputs.json'));put('data/canonical-grid/bounds.json.gz',baseline.read('data/canonical-grid/bounds.json.gz'));
 for(const p of [NS+'/native-selection-receipt.json',NS+'/native-proposal.json','data/ownership-selection.json','scripts/native-ownership/verified-candidates.json'])put(p,fs.readFileSync(repo+'/'+p));
 const gmPath='data/reference-migrations/eastern-two-gap-repair-20261006/index.json',gm=JSON.parse(baseline.read(gmPath)),gmPin=put(gmPath,baseline.read(gmPath)),geometryFiles=[];
 for(const [name,pin]of Object.entries(gm.files)){const p=path.posix.dirname(gmPath)+'/'+(pin.archive_path??name);geometryFiles.push(put(p,baseline.read(p)));}
 const pin=p=>{const b=fs.readFileSync(image+'/'+p);return{path:p,bytes:b.length,sha256:sha(b)};};
 const closure=codeClosure(repo,'scripts/native-ownership/validate-build-context-stage.mjs');for(const p of closure)if(!fs.existsSync(image+'/'+p))put(p,fs.readFileSync(repo+'/'+p));
 const stage={version:2,issue:1295,kind:'retained-identity-context-continuation-v2',lane:'engineering',subject_ids:[...TARGETS],prior_stage_sha256:'471e6a71856c13b5856cd74f24b79cc9961b3b091980e8b9106a19c1f32a2765',prior_image:pin(NS+'/prior-v1/index.json'),releases,predecessor_release_id:next.index.releases.at(-2).id,successor_release_id:next.index.releases.at(-1).id,after_context:pin(manifestDir+'/context-index.json'),after_context_image:pin(manifestDir+'/context-transport/index.json'),native_comparison:pin(NS+'/native-selection-receipt.json'),native_manifest:pin(manifestDir+'/manifest.json'),native_proposal:pin(NS+'/native-proposal.json'),geometry_manifest:gmPin,geometry_files:geometryFiles,validator_sources:closure.map(pin)};
 put('data/native-context-migration/manifest.json',json(stage));
 const previousCwd=process.cwd(),previousMarker=process.env.WORLDATLAS_PACKAGE_STAGE;process.chdir(image);process.env.WORLDATLAS_PACKAGE_STAGE=image;
 let selection;try{selection=await selectBuildOwnership({...await readBuildOwnershipSelection(),expectedReference:next.index.releases.at(-1)});}finally{process.chdir(previousCwd);if(previousMarker===undefined)delete process.env.WORLDATLAS_PACKAGE_STAGE;else process.env.WORLDATLAS_PACKAGE_STAGE=previousMarker;}
 put(NS+'/combined-selection-receipt.json',json({status:'PASS',manifest_sha256:selection.sha256,verification:selection.verification,source:selection.source}));
 console.log('Starting actual unchanged v1 replay and full successor context validation');
 const context=await validateBuildContextStage({root:image,expectedReference:next.index.releases.at(-1)});assert.equal(context.receipt.status,'verified');put(NS+'/combined-context-receipt.json',json(context.receipt));
 console.log('Full49625 context continuation PASS');
 const contentRoot=out+'/content';fs.mkdirSync(contentRoot);const plan=JSON.parse(fs.readFileSync(repo+'/'+NS+'/content-source-plan.json'));
 const content=continueContent(repo,BASE,contentRoot,plan,{storage});assert.equal(content.claim_rows,3984);
 const productPrefix='data/reference-migrations/eastern-two-gap-repair-20261006/products/';
 function copyOutput(source,p){for(const row of fs.readdirSync(source+'/'+p,{withFileTypes:true})){const s=p+'/'+row.name;if(row.isDirectory())copyOutput(source,s);else put(s,fs.readFileSync(source+'/'+s));}}
 copyOutput(contentRoot,productPrefix.slice(0,-1));copyOutput(contentRoot,'data/prepared-evidence');put(NS+'/combined-content-receipt.json',json(content));
 const certificate=disposeCertificates(repo,BASE,{hierarchy:baseline.object('data/hierarchy.json'),before:native.old,after:native.features,release:next.index.releases.at(-1),storage});for(const[p,b]of certificate.files)put(p,b);
 put(NS+'/combined-certificate-receipt.json',json({disposition:certificate.disposition,input_pins:certificate.input_pins,closed_consumer_controls:certificate.closed_consumer_controls}));
 const proposal=storage.get('b4b7db357ba92d19df513f188bbd046fe66a35e4:coordination/engineering/eastern-two-gap-repair-20261007/run-one/proposed-part-29.json.gz');
 const proposedRaw=gunzipSync(gunzipSync(fs.readFileSync(repo+'/'+proposal.alias.path),{maxOutputLength:32*1024*1024}),{maxOutputLength:32*1024*1024});put('data/geography/part-29.json',proposedRaw);
 const auditRaw=baseline.read('data/granularity-audit.json'),audit=JSON.parse(auditRaw),recipePath=NS+'/original-audit-recipe.py.txt';
 const originalRecipe=execFileSync('git',['-C',repo,'cat-file','blob',BASE+':scripts/audit-granularity.py'],{maxBuffer:32*1024*1024});assert(originalRecipe.equals(fs.readFileSync(repo+'/'+recipePath)),'Unchanged original area recipe required');
 const auditInput={audit,targets:[...TARGETS],before:native.old.filter(f=>f.properties.reference_owner==='Canada'),after:native.features.filter(f=>f.properties.reference_owner==='Canada'),proposed_part_sha256:sha(proposedRaw),original_audit_sha256:sha(auditRaw),binding:{issue:1295,release_id:native.releaseId,footprints_sha256:AFTER,changed_subject_ids:[...TARGETS],locations:49625,topology_profile:'worldatlas-prepared-antimeridian-cut-v1',all_other_full_pointsets_preserved:49623,source_approval_scope:'Two physical-region retained-envelope processing corrections only',geographic_factual_approval:false}};
 const nextAudit=execFileSync(process.env.ATLAS_PYTHON,[repo+'/'+NS+'/audit-continuation.py',repo+'/'+recipePath],{input:json(auditInput),maxBuffer:32*1024*1024});
 put('data/granularity-audit.json',nextAudit);
 const outputs=[];function inventory(p){for(const row of fs.readdirSync(image+'/'+p,{withFileTypes:true})){const s=p?p+'/'+row.name:row.name;if(row.isDirectory()){if(s!=='.cache')inventory(s);}else outputs.push(pin(s));}}inventory('');
 const report={version:1,issue:1295,status:'PASS',execution_commit:head,executed_modules:modules,input_only,complete_memberships:84833,new_payloads:next.pins,release:next.index.releases.at(-1),context_receipt_sha256:sha(json(context.receipt)),content_claim_rows:content.claim_rows,closed_consumer_controls:certificate.closed_consumer_controls,outputs,limits:['Completed native science remains original5b32388 vintage; this is the combined release/context/content/certificate execution.','No deployment, factual source expansion, water classification or historical approval.']};
 fs.writeFileSync(out+'/report.json',json(report));console.log('COMBINED PASS',outputs.length);
 return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const out=path.resolve(process.argv[2]);await integrate(process.cwd(),out,{inputOnly:process.argv.includes('--input-only')});}
