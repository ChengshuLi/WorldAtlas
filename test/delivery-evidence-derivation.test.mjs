import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {pinReader, prepareEvidence, digest, jsonBytes} from '../scripts/prepare-delivery-handoff.mjs';
import {validateEvidence, repositoryReader} from '../scripts/evidence-quality.mjs';
import {validatePremergeManifest} from '../scripts/premerge-evidence.mjs';
const entry=fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url));
function fixture(t, paddingBytes=0, twoGroups=false) {
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'delivery-evidence-')));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const git=(...args)=>execFileSync('git',args,{cwd:root,stdio:['ignore','pipe','pipe']});
 git('init','-q');git('config','user.name','Evidence fixture');git('config','user.email','fixture@example.invalid');
 const write=(name,value)=>{const p=path.join(root,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,jsonBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','metadata fixture');return git('rev-parse','HEAD').toString().trim();};
 const pin=(c,name)=>pinReader(root).pin(c,name);
 const prefix='coordination/engineering/fixture/';
 const old={component_id:'old',target_id:'target:old',native_cells:1};
 write(prefix+'ledger-old.json',{rows:[old],padding:' '.repeat(paddingBytes)});write(prefix+'registry-old.json',{entries:[]});
 const bodies=commit();
 const baseSelection={version:1,sha256:'a'.repeat(64)};
 const sidecar=(c,suffix)=>({version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,
   authority_registry:pin(c,prefix+'registry-'+suffix+'.json'),logical_asset_map:{ledger:pin(c,prefix+'ledger-'+suffix+'.json')}});
 write(prefix+'sidecar-old.json',sidecar(bodies,'old'));const side=commit();
 const oldSide=pin(side,prefix+'sidecar-old.json');
 write('data/ownership-selection.json',{...baseSelection,additive_release:{path:oldSide.path,bytes:oldSide.bytes,sha256:oldSide.sha256}});
 write('.github/package-inputs.json',{version:1,inputs:['data/']});const baseline=commit();
 const newRow={component_id:'new',target_id:'target:new',native_cells:2},secondRow={component_id:'new-two',target_id:'target:new-two',native_cells:3};
 const constructed=row=>({version:1,component_ids:[row.component_id],rule_sha256:'d'.repeat(64),ledger_rows:[row]});
 const selected=row=>({...row,authority_sha256:'e'.repeat(64),rule_sha256:'d'.repeat(64)});
 git('checkout','-qb','unmerged-original');write('original/constructor.json',constructed(newRow));
 if(twoGroups)write('original/constructor-two.json',constructed(secondRow));
 const originalCommit=commit(),original=pin(originalCommit,'original/constructor.json');git('checkout','-q','--detach',baseline);
 write(prefix+'ledger-new.json',{rows:[old,selected(newRow),...(twoGroups?[selected(secondRow)]:[])]});write(prefix+'registry-new.json',{entries:[]});
 write(prefix+'retained-input.json',{source:'unchanged complete source body'});
 write(prefix+'control.json',{method_id:'retained-selected-delivery',kind:'negative-control',outcome:'passed'});const newBodies=commit();
 const newSide=sidecar(newBodies,'new');write(prefix+'sidecar-new.json',newSide);
 const raw=jsonBytes(newSide);write('data/ownership-selection.json',{...baseSelection,additive_release:{path:prefix+'sidecar-new.json',bytes:raw.length,sha256:digest(raw)}});
 write(prefix+'evidence-quality.json',{descriptive:'old invalid receipt, manifest self excluded'});const candidate=commit();
 const config={version:1,preparation_allowance:{phaseBytes:536870912,rssBytes:536870912},metric_sources:[],delivery:{version:1,
  baseline_commit:baseline,candidate_commit:candidate,manifest_path:prefix+'evidence-quality.json',issue:1930,worker_id:'independent-evidence-fixture',
  subject_ids:['target:new'],limits:['Original source, territorial and failed-operating limitations remain; no clearance.'],
  qualified_constructor_pins:[{id:'retained-original',pin:original}],sources:[{id:'retained-original',url:'https://example.invalid/original',
   role:'Original full constructor checkpoint custody',vintage:'Original qualification',retrieved_at:'2026-10-15',
   license:{status:'unknown',terms:'Original terms and limits remain unchanged'},retention:'restoration-only',verification:'unverified',
   temporal_status:'reference',restoration:'Read original immutable checkpoint body',limit:'Not ancestor baseline; no new source certification',original_pin:original}]}};
 if(twoGroups){const second=pin(originalCommit,'original/constructor-two.json');config.delivery.subject_ids.push(secondRow.target_id);
  config.delivery.qualified_constructor_pins.push({id:'retained-second',pin:second});
  config.delivery.sources.push({...config.delivery.sources[0],id:'retained-second',original_pin:second});}
 return {root,git,write,commit,pin,baseline,candidate,config,prefix,old,original};
}
test('existing evidence entry derives real ancestor pins and complete immutable candidate bytes without metrics',t=>{
 const f=fixture(t),m=JSON.parse(prepareEvidence(f.config,pinReader(f.root))['evidence-quality.json']);
 assert.equal(m.baseline.files.length,4);assert.equal(m.baseline.commit,f.baseline);
 assert.deepEqual(Object.keys(m.baseline.pins).sort(),['baseline_authority_registry','baseline_package_inputs','baseline_selected_ledger','baseline_selector']);
 const names=f.git('diff','--name-only',f.baseline,f.candidate).toString().trim().split('\n').filter(x=>x!==f.config.delivery.manifest_path);
 assert.deepEqual(m.outputs.map(x=>x.path).sort(),names.sort());assert(!m.outputs.some(x=>x.path===f.config.delivery.manifest_path));
 assert.deepEqual(m.metrics,[]);assert.deepEqual(m.metric_bindings,[]);assert.deepEqual(m.qualified_constructor_pins,f.config.delivery.qualified_constructor_pins);
 assert(!m.baseline.files.some(x=>x.path===f.original.path));assert.equal(m.sources[0].retention,'restoration-only');
 const result=validateEvidence(m,{readFile:repositoryReader(f.root),expectedIssue:1930,expectedSubjects:['target:new'],expectedPins:m.baseline.pins});
 assert.equal(result.checked.length,4+m.outputs.length);assert(result.limits.length>0);
});
test('existing entry rejects unmerged constructor hashes as issue ancestral baseline pins',t=>{
 const f=fixture(t);f.config.delivery.pins={original_constructor:f.original.sha256};
 assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/Issue baseline pins differ/);
 f.config.delivery.baseline_commit=f.original.commit;delete f.config.delivery.pins;
 assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/merge-base/);
});
test('existing entry refuses false scope and omitted or drifted original source custody',t=>{
 const f=fixture(t);f.config.delivery.subject_ids=['target:foreign'];assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/subjects differ/);
 f.config.delivery.subject_ids=['target:new'];f.config.delivery.sources=[];assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/checkpoint citation/);
 f.config.delivery.sources=[{...fixtureSource(f),original_pin:{...f.original,sha256:'0'.repeat(64)}}];
 assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/checkpoint citation/);
 function fixtureSource(f){return {id:'retained-original',retention:'restoration-only'};}
});
test('existing entry rejects mutation of an inherited row and changed complete original pin',t=>{
 const f=fixture(t);f.write(f.prefix+'ledger-new.json',{rows:[{...f.old,native_cells:99},{component_id:'new',target_id:'target:new',native_cells:2}]});
 f.config.delivery.candidate_commit=f.commit();assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/Selected original role differs/);
 const changed=f.config.delivery.candidate_commit;
 const sidecar=JSON.parse(fs.readFileSync(path.join(f.root,f.prefix+'sidecar-new.json')));
 sidecar.logical_asset_map.ledger=f.pin(changed,f.prefix+'ledger-new.json');f.write(f.prefix+'sidecar-new.json',sidecar);
 const bytes=jsonBytes(sidecar);f.write('data/ownership-selection.json',{version:1,sha256:'a'.repeat(64),
  additive_release:{path:f.prefix+'sidecar-new.json',bytes:bytes.length,sha256:digest(bytes)}});
 f.config.delivery.candidate_commit=f.commit();assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/Inherited delivery row changed/);
 f.config.delivery.candidate_commit=f.candidate;f.config.delivery.qualified_constructor_pins[0].pin.sha256='0'.repeat(64);
 assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/Whole body hash differs/);
});
test('actual evidence CLI stages derived bytes and resumes exactly through the existing writer',t=>{
 const f=fixture(t);fs.writeFileSync(path.join(f.root,'config.json'),jsonBytes(f.config));const dest='.cache/delivery-handoff/evidence';
 const run=(...flags)=>execFileSync(process.execPath,[entry,'evidence','config.json',dest,...flags],{cwd:f.root,encoding:'utf8',env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',GIT_NO_LAZY_FETCH:'1'}});
 assert.equal(JSON.parse(run()).resumed,false);const p=path.join(f.root,dest,'evidence-quality.json'),raw=fs.readFileSync(p);
 assert.equal(JSON.parse(run('--resume')).resumed,true);assert(fs.readFileSync(p).equals(raw));
 fs.appendFileSync(p,' ');assert.throws(()=>run('--resume'),/Resumed bytes\/binding changed/);
});

test('actual entry carries parsed metadata above one virtual whole-file limit without changing actual body cap',t=>{
 const f=fixture(t,3*1024*1024);
 const m=JSON.parse(prepareEvidence(f.config,pinReader(f.root))['evidence-quality.json']);
 assert(m.baseline.files.some(file=>file.bytes>3*1024*1024));assert.equal(m.metrics.length,0);
});
test('legacy evidence entry keeps typed measured extraction and refuses empty or fabricated fields',()=>{
 const objects=new Map();let n=0;const add=(name,value)=>{const raw=jsonBytes(value);const pin={path:name,commit:'a'.repeat(40),mode:'100644',git_blob_oid:(++n).toString(16).padStart(40,'0'),bytes:raw.length,sha256:digest(raw)};objects.set(pin.sha256,raw);return pin;};
 const reader={read:pin=>{const raw=objects.get(pin.sha256);assert(raw);return raw;},json(pin){return JSON.parse(this.read(pin));}};
 const base=add('base.json',{base:true}),input=add('owned/request.json',{request:true}),facts=add('owned/facts.json',{assigned_cells:2,request_sha256:input.sha256});
 const descriptor=pin=>({path:pin.path,bytes:pin.bytes,sha256:pin.sha256,hash_kind:'file-bytes'});
 const template=add('owned/template.json',{version:1,issue:1930,lane:'engineering',worker_id:'legacy',subject_ids:[],subject_ids_sha256:digest(Buffer.from('[]')),
  baseline:{version:2,commit:'a'.repeat(40),files:[{...descriptor(base),commit:base.commit}],pins:{}},sources:[],outputs:[descriptor(input),descriptor(facts)],
  methods:[],metrics:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'proposed',geographic_approval:'unapproved'},commands:[]});
 const config={version:1,template,metric_sources:[{measurement:facts,input,input_file:{path:input.path,commit:'candidate'},evaluation_commit:'a'.repeat(40),vintage:'archived',fields:[{id:'assigned',field:'assigned_cells'}]}]};
 const m=JSON.parse(prepareEvidence(config,reader)['evidence-quality.json']);assert.equal(m.metrics[0].value,2);assert.equal(m.metrics[0].unit,'native cells');
 config.metric_sources[0].fields[0].field='invented_count';assert.throws(()=>prepareEvidence(config,reader),/Unknown delivery metric field/);
 config.metric_sources=[];assert.throws(()=>prepareEvidence(config,reader),/Explicit measured delivery sources required/);
});

test('actual entry preserves supplied controls and rejects silently ignored evidence fields',t=>{
 const f=fixture(t);f.config.delivery.validation=[{method_id:'retained-selected-delivery',kind:'negative-control',outcome:'passed',evidence_path:f.prefix+'control.json'}];
 const check=m=>validatePremergeManifest(m,{readFile:repositoryReader(f.root),files:f.git('diff','--name-status',f.baseline,f.candidate).toString().trim().split('\n').map(line=>{
  const [status,filename]=line.split('\t');return {filename,status:status==='A'?'added':'modified'};}),manifestPath:f.config.delivery.manifest_path,
  issue:{number:1930},spec:{mode:'engineering',evidence_quality:{subject_ids:['target:new'],pins:m.baseline.pins}},reservation:{owned_paths:[f.prefix,'data/ownership-selection.json']},
  branch:'engineering/fixture',pr:{base:{sha:f.baseline}}});
 const m=JSON.parse(prepareEvidence(f.config,pinReader(f.root))['evidence-quality.json']);assert.deepEqual(m.validation,f.config.delivery.validation);assert.equal(check(m).status,'limited');
 f.config.delivery.validation[0].kind='positive-control';
 const falseClaim=JSON.parse(prepareEvidence(f.config,pinReader(f.root))['evidence-quality.json']);assert.throws(()=>check(falseClaim),/Control bytes do not match receipt/);
 f.config.delivery.baseline_pins={constructor:f.original.sha256};
 assert.throws(()=>prepareEvidence(f.config,pinReader(f.root)),/Unknown delivery evidence field/);
});

test('two actual original groups refuse coherent removal of constructor and matching citation',t=>{
 const f=fixture(t,0,true);const run=()=>JSON.parse(prepareEvidence(f.config,pinReader(f.root))['evidence-quality.json']);
 assert.equal(run().qualified_constructor_pins.length,2);
 f.config.delivery.qualified_constructor_pins.pop();f.config.delivery.sources.pop();
 assert.throws(run,/Incomplete original constructor coverage/);
});
