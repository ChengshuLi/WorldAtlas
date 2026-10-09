import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
const P='coordination/engineering/additive-native-gap-batch-20261008',OLD='coordination/engineering/additive-native-gap-repair-20261008';
const sha=body=>createHash('sha256').update(body).digest('hex'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const pin=(commit,name,gzip=false)=>{const tree=execFileSync('git',['ls-tree','-z',commit,'--',name],{encoding:'utf8'}),match=/^(100644|100755) blob ([a-f0-9]{40})\t/.exec(tree);
 if(!match||tree.slice(tree.indexOf('\t')+1)!==name+'\0')throw Error('Missing whole immutable operand: '+name);
 const raw=execFileSync('git',['cat-file','blob',match[2]],{maxBuffer:32*1024*1024});
 return {commit,path:name,mode:match[1],blob:match[2],bytes:raw.length,sha256:sha(raw),...(gzip?(()=>{const body=gunzipSync(raw,{maxOutputLength:32*1024*1024});return {uncompressed_bytes:body.length,uncompressed_sha256:sha(body)};})():{})};};
const read=name=>JSON.parse(fs.readFileSync(name));
const previous=read(OLD+'/add031-release-request-v3-run2.json'),source=read(P+'/source-premises-request-v1.json'),facts=read(P+'/qualified-source-premises-v1/facts.json');
const project=committedPreparationFiles(process.cwd(),head,previous.executed_code.map(pin=>pin.path));
const inputs=[],seen=new Set(),add=(name,commit=head,gzip=false)=>{if(seen.has(name))return;seen.add(name);inputs.push(pin(commit,name,gzip));};
for(const name of ['publication.json','facts.json','operating-receipt.json'])add(P+'/qualified-source-premises-v1/'+name);
add(P+'/qualified-source-premises-v1/inventory.jsonl.gz',head,true);add(P+'/source-premises-request-v1.json',facts.execution_commit);
inputs.push(source.source_rule.inputs.find(pin=>pin.path===source.source_rule.cases_path));seen.add(source.source_rule.cases_path);
for(const name of source.source_rule.target_banks)inputs.push(source.source_rule.inputs.find(pin=>pin.path===name));
const bounds=P+'/current-v8/bounds.json.gz';add(bounds,head,true);
const latitudes=previous.additive.inputs.find(pin=>pin.path===previous.additive.latitudes_path);if(!latitudes)throw Error('Missing original literal latitude pin');inputs.push(latitudes);
const manifestPin=previous.baseline.pins.find(pin=>pin.path===previous.additive.manifest_path);
const manifest=JSON.parse(execFileSync('git',['show',manifestPin.commit+':'+manifestPin.path],{maxBuffer:32*1024*1024}));
const partNames=['rows-0','runs-6291456','runs-7340032','runs-8388608','runs-9437184','runs-10485760','runs-11534336','runs-12582912'];
const parts=partNames.map(name=>{const descriptor=manifest.parts.find(part=>part.path==='native-v1/ownership/'+name+'.bin.gz');if(!descriptor)throw Error('Whole current containing native part missing');
 const nameInPacket=P+'/current-v8/'+name+'.bin.gz';add(nameInPacket,head,true);
 return {path:nameInPacket,manifest_path:descriptor.path,manifest_descriptor:descriptor};});
const outputs=[];
for(const ordinal of [1,2]){
 const request={version:1,operation:'unactivated-additive-native-batch-v1',executed_code:project,installed_modules:source.installed_modules,report:source.report,
 parent:source.parent,baseline:source.baseline,destination:'.cache/native-grid-candidates/alaska13-batch-v1-run'+ordinal,output_reserve:18*1024*1024,
 additive:{inputs,scope_ids:source.source_rule.expected_ids,publication_path:P+'/qualified-source-premises-v1/publication.json',facts_path:P+'/qualified-source-premises-v1/facts.json',
 inventory_path:P+'/qualified-source-premises-v1/inventory.jsonl.gz',operating_path:P+'/qualified-source-premises-v1/operating-receipt.json',
 source_request_path:P+'/source-premises-request-v1.json',source_execution_commit:facts.execution_commit,source_runtime:facts.runtime,
 manifest_path:previous.additive.manifest_path,bounds_path:bounds,original_bounds:manifest.original_assets.bounds,latitudes_path:latitudes.path,owner_parts:parts}};
 const raw=Buffer.from(JSON.stringify(request)+'\n'),cost=pin=>[{bytes:pin.bytes},...(pin.uncompressed_bytes===undefined?[]:[{bytes:pin.uncompressed_bytes}])];
 const budget=candidateBudget([...project,...source.installed_modules,{bytes:raw.length},...cost(source.report),...inputs.flatMap(cost),...source.baseline.pins.flatMap(cost)],{reserveBytes:fs.statSync(process.execPath).size+request.output_reserve+131072});
 const name=P+'/batch-request-v1-run'+ordinal+'.json';if(fs.existsSync(name))throw Error('Fresh independently frozen batch requests only');fs.writeFileSync(name,raw,{flag:'wx'});
 outputs.push({request_path:name,bytes:raw.length,sha256:sha(raw),admission:budget.snapshot(),scope:13,activation:false});
}
process.stdout.write(JSON.stringify(outputs)+'\n');
