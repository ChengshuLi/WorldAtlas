import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
const P='coordination/engineering/additive-native-gap-batch-20261008',OLD='coordination/engineering/additive-native-gap-repair-20261008';
const geo='research/geography/alaska-thirteen-geometry-measurement-20261008',fitness='research/geography/alaska-thirteen-source-fitness-20261008';
const sha=body=>createHash('sha256').update(body).digest('hex'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const pin=(commit,name,gzip=false)=>{const tree=execFileSync('git',['ls-tree','-z',commit,'--',name],{encoding:'utf8'}),match=/^(100644|100755) blob ([a-f0-9]{40})\t/.exec(tree);
 if(!match||tree.slice(tree.indexOf('\t')+1)!==name+'\0')throw Error('Missing whole immutable operand: '+name);
 const raw=execFileSync('git',['cat-file','blob',match[2]],{maxBuffer:32*1024*1024});
 return {commit,path:name,mode:match[1],blob:match[2],bytes:raw.length,sha256:sha(raw),...(gzip?(()=>{const body=gunzipSync(raw,{maxOutputLength:32*1024*1024});return {uncompressed_bytes:body.length,uncompressed_sha256:sha(body)};})():{})};};
const read=name=>JSON.parse(fs.readFileSync(name));
const previous=read(OLD+'/add031-release-request-v3-run2.json'),admission=read(geo+'/phase-admission.json'),measurement=read(geo+'/vintages/run-fourteen/measurement.json');
const names=previous.executed_code.map(pin=>pin.path),project=committedPreparationFiles(process.cwd(),head,names);
const installed=previous.installed_modules.map(original=>{const raw=fs.readFileSync(original.path);if(sha(raw)!==original.sha256)throw Error('Actual installed dependency differs');return {...original,bytes:raw.length};});
const sourceCommit='ffa32416fd946ac89da621d02b554ca27733e688',inputs=[],seen=new Set();
const add=(name,commit=sourceCommit,gzip=false)=>{if(seen.has(name))return;seen.add(name);inputs.push(pin(commit,name,gzip));};
for(const original of measurement.inputs.files)add(original.path);
for(const original of admission.project_code)add(original.path);
for(const name of [geo+'/vintages/run-fourteen/measurement.json',geo+'/vintages/run-fourteen/publication.json',geo+'/execution/measure-alaska-run-fourteen-operating-receipt.json'])add(name);
for(const part of ['43500','45000','46500'])add(P+'/current-v8/context/part-'+part+'.json.gz',head,true);
add(P+'/current-v8/context-index.json',head);
const request={version:1,operation:'retained-land-source-premises-v1',executed_code:project,installed_modules:installed,
 report:previous.report,parent:previous.parent,baseline:previous.baseline,destination:'.cache/native-grid-candidates/alaska13-source-premises-v1',output_reserve:2*1024*1024,
 source_rule:{version:1,profile:'retained-USA-ADM2-counties-2018',inputs,expected_ids:measurement.assigned_scope.component_ids,
 original_code:admission.project_code,cases_path:geo+'/vintages/run-fourteen/measurement.json',publication_path:geo+'/vintages/run-fourteen/publication.json',
 operating_path:geo+'/execution/measure-alaska-run-fourteen-operating-receipt.json',admission_path:geo+'/phase-admission.json',candidate_path:fitness+'/sources/candidate-components.geojson',
 original_targets_path:fitness+'/sources/native-atlas-target-features.geojson',records_path:fitness+'/sources/physical-query-rows.jsonl',
 native_receipt_path:geo+'/sources/native-selected/receipt.json',native_body_path:geo+'/sources/native-selected/records.bin',
 neighbor_path:geo+'/sources/atlas-neighbors/features.geojson',contact_path:geo+'/sources/contact-authority/contact-authority-receipt.json',
 context_index_path:P+'/current-v8/context-index.json',target_banks:['43500','45000','46500'].map(part=>P+'/current-v8/context/part-'+part+'.json.gz')}};
const raw=Buffer.from(JSON.stringify(request)+'\n');
const cost=pin=>[{bytes:pin.bytes},...(pin.uncompressed_bytes===undefined?[]:[{bytes:pin.uncompressed_bytes}])];
const runtime=fs.statSync(process.execPath).size,budget=candidateBudget([...project,...installed,{bytes:raw.length},...cost(request.report),...inputs.flatMap(cost),...request.baseline.pins.flatMap(cost)],{reserveBytes:runtime+request.output_reserve+131072});
const name=P+'/source-premises-request-v1.json';if(fs.existsSync(name))throw Error('Fresh source request only');fs.writeFileSync(name,raw,{flag:'wx'});
process.stdout.write(JSON.stringify({request_path:name,request_bytes:raw.length,request_sha256:sha(raw),admission:budget.snapshot(),runtime_bytes:runtime,source_components:13,assigned_cells:0,activation:false})+'\n');
