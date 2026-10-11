// Existing pure SOURCE predicates. This is not operator qualification or approval.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {retainedAdministrativeSourcePremises} from '../../../../scripts/additive-gap-repair.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(here,'../../../..'),own=path.relative(repo,path.dirname(here));
const [head,vintage]=process.argv.slice(2),git=(...a)=>execFileSync('git',['-C',repo,...a],{maxBuffer:32*1024**2}),sha=b=>createHash('sha256').update(b).digest('hex');
const need=(v,m)=>{if(!v)throw Error(m);};
need(git('rev-parse','HEAD').toString().trim()===head&&/^[a-z0-9-]+$/.test(vintage),'Exact execution head and safe fresh vintage required');
const output=path.join(repo,own,'vintages',vintage);for(let p=output;p!==path.dirname(repo);p=path.dirname(p)){const s=fs.lstatSync(p,{throwIfNoEntry:false});need(!s?.isSymbolicLink()&&(p!==output||!s),'Occupied or symlink output');}
const names=[path.relative(repo,fileURLToPath(import.meta.url)),own+'/vintages/source-premise-input-001/premise-input.json','scripts/additive-gap-repair.mjs','src/effective-footprint.js'];
const inputs=names.map(p=>{const b=fs.readFileSync(path.join(repo,p));need(b.equals(git('show',head+':'+p)),'Unfrozen input');return{path:p,commit:head,bytes:b.length,sha256:sha(b)};});
const methodRequest='coordination/engineering/congo-ago2018-delivery-20261011/source-request-002.json', method=JSON.parse(git('show','6a99a7606b9c2d11ac8cd093610653d4cd5d1382:'+methodRequest)).executed_code;
need(method.length===17,'Changed method17 roster');for(const d of method){const b=git('show',head+':'+d.path);need(b.length===d.bytes&&sha(b)===d.sha256&&fs.readFileSync(path.join(repo,d.path)).equals(b),'Changed actual trusted SOURCE body: '+d.path);}
const scope=JSON.parse(fs.readFileSync(path.join(repo,names[1]))),rows=[];
need(scope.scopeIds.length===20&&new Set(scope.scopeIds).size===20,'Changed exact20scope');
for(const c of scope.candidate_source_native_bindings){const p=scope.original_physical_comparison_bindings.find(r=>r.component_id===c.component_id),target=scope.current_neighbor_binding.rows.find(r=>r.component_id===c.component_id).candidate_neighbors.find(r=>r.feature.id===c.retained_payload.target_stable_location_id).feature;try{rows.push(retainedAdministrativeSourcePremises({record:p.physical_comparison.row,candidate:c.original_candidate_feature.geometry,sourceCase:c,sourceScope:scope,target}));}catch(e){rows.push({component_id:c.component_id,source_compatible:false,error:e.message});}}
const result={execution_commit:head,source_baseline:'6a99a7606b9c2d11ac8cd093610653d4cd5d1382',inputs,rows,source_compatible_count:rows.filter(r=>r.source_compatible).length,limits:['Actual unchanged pure retainedAdministrativeSourcePremises only.','This result does not establish source acceptance, native operator qualification, same-owner native conservation or selected delivery.']};const raw=Buffer.from(JSON.stringify(result,null,2)+'\n');
need(raw.length<4*1024**2&&process.resourceUsage().maxRSS*1024<512*1024**2,'Output/RSS reservation exceeded');fs.mkdirSync(output,{recursive:false});fs.writeFileSync(path.join(output,'result.json'),raw,{flag:'wx'});fs.writeFileSync(path.join(output,'publication.json'),JSON.stringify({version:1,status:'complete',outputs:[{path:path.relative(repo,path.join(output,'result.json')),bytes:raw.length,sha256:sha(raw),hash_kind:'file-bytes'}]})+'\n',{flag:'wx'});console.log(JSON.stringify({source_compatible_count:result.source_compatible_count,rows:rows.map(r=>({component:r.component_id,source_compatible:r.source_compatible,failed:r.failed_premises,error:r.error})),peak_rss_bytes:process.resourceUsage().maxRSS*1024}));
