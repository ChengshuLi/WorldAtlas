import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {pinReader, jsonBytes, digest} from '../scripts/prepare-delivery-handoff.mjs';

const repository=new URL('../',import.meta.url).pathname;
const script=new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url).pathname;
const size=262166,y=size/2,x=size/2,family='gb:TST:ADM2',target=family+':A';
const rectangle=(right)=>({type:'Polygon',coordinates:[[[-.03,-.02],[right,-.02],[right,.02],[-.03,.02],[-.03,-.02]]]});
const latitudeBytes=Buffer.alloc(size*8);
for(const [i,latitude] of nativeRowLatitudes(size).entries())latitudeBytes.writeDoubleLE(latitude,i*8);

// Small real Git inputs exercise the public CLI and authenticated reader, not a
// country producer, fabricated returned diagnostic or alternate coverage method.
function fixture(t,{support='all',changeEvidence=()=>{}}={}) {
  const cache=path.join(repository,'.cache');fs.mkdirSync(cache,{recursive:true});
  const root=fs.mkdtempSync(path.join(cache,'native-diagnostic-entry-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const save=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),raw);};
  const git=(...args)=>execFileSync('git',args,{cwd:root,encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:10000}).trim();
  git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  const source=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',properties:{shapeID:'A'},geometry:rectangle(.03)}]}));
  const files={
    'source.json':source,'owners.json':jsonBytes([{id:target,index:1}]),
    'physical.json':jsonBytes({results:[{target,issues:[],support:{mapped_land_support:rectangle(support==='all'?.03:support==='mixed'?.001:-.001)}}]}),
    'physical-input.json':jsonBytes([{target,consumed:{geometry:rectangle(.03)},selected:{id:target,geometry:rectangle(.03)}}]),
    'physical.py':Buffer.from("raise RuntimeError('retained producer must not execute')\n"),
    'latitudes.f64le':latitudeBytes,'patch.json':jsonBytes({rows:[{y,runs:[[x,x+2,1]]}]}),
    'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json':jsonBytes({products:[{key:family,parts:[{path:'source.json',bytes:source.length,sha256:digest(source)}],feature_count:1,original_bytes:source.length,original_sha256:digest(source)}]}),
  };
  for(const [name,raw] of Object.entries(files))save(name,raw);
  git('add','.');git('commit','-qm','Original diagnostic inputs');
  const original=git('rev-parse','HEAD'),reader=pinReader(root),pin=name=>reader.pin(original,name);
  const owners=pin('owners.json'),physical=pin('physical.json'),latitudes=pin('latitudes.f64le');
  const evidence={version:1,kind:'source-target-native-evidence-v1',
    catalogue:pin('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'),
    owner_roster:owners,physical_evidence:physical,physical_input:pin('physical-input.json'),physical_reproduction:pin('physical.py'),
    native_latitudes:latitudes,native_contract:{size,native_latitudes:latitudes,original_assets:{bounds:{sha256:owners.sha256}}},
    base_reference:{id:'fixture-base'},families:[{source_id:family,parts:[pin('source.json')]}],
    targets:[{id:target,pixelIndex:1,source_family:family,base_geometry:rectangle(.03),coverage_classes:['mapped_land_support'],territorial_exclusions:[],source_receipt_sha256:physical.sha256}]};
  changeEvidence(evidence);save('source-evidence.json',jsonBytes(evidence));git('add','.');git('commit','-qm','Bound diagnostic evidence');
  const head=git('rev-parse','HEAD');
  const config={version:1,preparation_allowance:{phaseBytes:512*1024*1024,rssBytes:1024*1024*1024},
    source_evidence:{commit:head,path:'source-evidence.json'},native_patch:{commit:original,path:'patch.json'}};
  const run=(phase,destination,flags=[])=>{save('config.json',jsonBytes(config));return spawnSync(process.execPath,[script,phase,'config.json',destination,...flags],{
    cwd:root,encoding:'utf8',timeout:30000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',GIT_NO_LAZY_FETCH:'1'}});};
  return {root,save,git,head,original,config,run,reader};
}
const output='coordination/engineering/fixture/diagnostic';
const read=(f,name)=>JSON.parse(fs.readFileSync(path.join(f.root,output,name)));
for(const support of ['all','mixed','none'])test('native-diagnostic CLI publishes only an exact '+support+' supported/held partition',t=>{
  const f=fixture(t,{support}),run=f.run('native-diagnostic',output);assert.equal(run.status,0,run.stderr);
  assert.deepEqual(fs.readdirSync(path.join(f.root,output)).sort(),['native-diagnostic.json','preparation.json']);
  const result=read(f,'native-diagnostic.json'),supported=support==='all'?2:support==='mixed'?1:0;
  assert.equal(result.kind,'source-target-native-diagnostic-v1');assert.equal(result.requested_cells,2);
  assert.equal(result.supported_cells,supported);assert.equal(result.held_cells,2-supported);
  assert.deepEqual(result.supported_rows,supported?[{y,runs:[[x,x+supported,1]]}]:[]);
  assert.deepEqual(result.held_rows,supported===2?[]:[{y,runs:[[x+supported,x+2,1]]}]);
  assert.deepEqual(result.requested_rows,[{y,runs:[[x,x+2,1]]}]);
  assert.equal(result.first_failure?.predicate??null,supported===2?null:'unique-source-target-coverage');
  const spans=result.decision_rows.flatMap(row=>row.runs);
  assert.equal(spans.reduce((n,[a,b])=>n+b-a,0),2);
  assert.equal(spans.filter(r=>r[3]==='assigned_cells').reduce((n,[a,b])=>n+b-a,0),supported);
  assert.deepEqual(result.original_pins.source_evidence,f.reader.pin(f.head,'source-evidence.json'));
  assert.deepEqual(result.original_pins.native_patch,f.reader.pin(f.original,'patch.json'));
  assert.equal(result.rule_sha256,digest(jsonBytes({version:1,kind:'source-target-native-rule-v1',...result.original_pins})));
  assert(!('ledger_rows' in result));assert(!('native_proof' in result));
  const receipt=read(f,'preparation.json');assert.equal(receipt.binding.phase,'native-diagnostic');
  assert.deepEqual(Object.keys(receipt.outputs),['native-diagnostic.json']);
  const raw=fs.readFileSync(path.join(f.root,output,'native-diagnostic.json'));
  assert.deepEqual(receipt.outputs['native-diagnostic.json'],{bytes:raw.length,sha256:digest(raw)});
  assert.equal(receipt.binding.config_sha256,digest(jsonBytes(f.config)));
  const observation=JSON.parse(run.stdout).observation;assert.equal(observation.supported_cells,supported);
  assert(!('qualified_cells' in observation));assert(result.limitations.some(s=>s.includes('no authority')));
  const qualified=f.run('native-authority','coordination/engineering/fixture/authority');
  if(supported===2){assert.equal(qualified.status,0,qualified.stderr);assert.equal(JSON.parse(qualified.stdout).observation.qualified_cells,2);}
  else {assert.notEqual(qualified.status,0);assert.match(qualified.stderr,/unique source-target coverage/);assert(!fs.existsSync(path.join(f.root,'coordination/engineering/fixture/authority')));}
});
test('native diagnostic exact resume reauthenticates pins and refuses changed config, output or inventory',t=>{
  const f=fixture(t,{support:'mixed'}),first=f.run('native-diagnostic',output);assert.equal(first.status,0,first.stderr);
  const directory=path.join(f.root,output),names=fs.readdirSync(directory),before=new Map(names.map(n=>[n,fs.readFileSync(path.join(directory,n))]));
  f.save('patch.json','mutable checkout cannot retarget immutable input');
  const again=f.run('native-diagnostic',output,['--resume']);assert.equal(again.status,0,again.stderr);assert.equal(JSON.parse(again.stdout).resumed,true);
  for(const [name,raw] of before)assert.deepEqual(fs.readFileSync(path.join(directory,name)),raw);
  assert.notEqual(f.run('native-diagnostic',output).status,0);
  const patch=f.config.native_patch;f.config.native_patch={...patch,path:'absent.json'};
  assert.notEqual(f.run('native-diagnostic',output,['--resume']).status,0);f.config.native_patch=patch;
  for(const mutation of ['changed','missing-receipt','foreign','symlink']){
    if(mutation==='changed')fs.appendFileSync(path.join(directory,'native-diagnostic.json'),' ');
    if(mutation==='missing-receipt')fs.unlinkSync(path.join(directory,'preparation.json'));
    if(mutation==='foreign')fs.writeFileSync(path.join(directory,'foreign.json'),'{}');
    if(mutation==='symlink'){fs.unlinkSync(path.join(directory,'native-diagnostic.json'));fs.symlinkSync(path.join(f.root,'source.json'),path.join(directory,'native-diagnostic.json'));}
    const snapshot=()=>fs.readdirSync(directory).sort().map(name=>{const file=path.join(directory,name);return[name,fs.lstatSync(file).isSymbolicLink()?['symlink',fs.readlinkSync(file)]:['file',fs.readFileSync(file).toString('base64')]];});
    const altered=snapshot();
    assert.notEqual(f.run('native-diagnostic',output,['--resume']).status,0,mutation);
    assert.deepEqual(snapshot(),altered,'refused resume preserves the complete preexisting state');
    for(const name of fs.readdirSync(directory))fs.unlinkSync(path.join(directory,name));
    for(const [name,raw] of before)fs.writeFileSync(path.join(directory,name),raw);
  }
  f.config.preparation_allowance.phaseBytes--;
  assert.notEqual(f.run('native-diagnostic',output,['--resume']).status,0,'changed binding is not exact resume');
});
test('native diagnostic refuses malformed scientific custody, caller descriptors and insufficient admission before publication',t=>{
  const corrupt=fixture(t,{changeEvidence:e=>e.physical_input.sha256='0'.repeat(64)});
  assert.notEqual(corrupt.run('native-diagnostic',output).status,0);assert(!fs.existsSync(path.join(corrupt.root,output)));
  const f=fixture(t),original=structuredClone(f.config);
  for(const mutate of [c=>c.native_patch.path='absent.json',c=>c.native_patch.sha256='a'.repeat(64),c=>c.preparation_allowance.phaseBytes=1024,c=>c.accepted=true,c=>c.diagnostic=true]){
    Object.keys(f.config).forEach(k=>delete f.config[k]);Object.assign(f.config,structuredClone(original));mutate(f.config);
    assert.notEqual(f.run('native-diagnostic',output).status,0);assert(!fs.existsSync(path.join(f.root,output)));
  }
});
test('native diagnostic admission preserves occupied, dangling-symlink and linked-ancestor destinations',t=>{
  const f=fixture(t);f.save('coordination/engineering/fixture/file','sentinel');
  assert.notEqual(f.run('native-diagnostic','coordination/engineering/fixture/file').status,0);
  assert.equal(fs.readFileSync(path.join(f.root,'coordination/engineering/fixture/file'),'utf8'),'sentinel');
  fs.symlinkSync(path.join(f.root,'missing'),path.join(f.root,'coordination/engineering/fixture/dangling'));
  assert.notEqual(f.run('native-diagnostic','coordination/engineering/fixture/dangling').status,0);
  assert(fs.lstatSync(path.join(f.root,'coordination/engineering/fixture/dangling')).isSymbolicLink());
  fs.mkdirSync(path.join(f.root,'outside'));fs.symlinkSync(path.join(f.root,'outside'),path.join(f.root,'coordination/engineering/fixture/link'));
  assert.notEqual(f.run('native-diagnostic','coordination/engineering/fixture/link/output').status,0);
  assert.deepEqual(fs.readdirSync(path.join(f.root,'outside')),[]);
});
test('a completed diagnostic cannot substitute for source evidence in authority qualification',t=>{
  const f=fixture(t,{support:'mixed'});assert.equal(f.run('native-diagnostic',output).status,0);
  f.git('add',output);f.git('commit','-qm','Retained diagnostic is observation only');
  f.config.source_evidence={commit:f.git('rev-parse','HEAD'),path:output+'/native-diagnostic.json'};
  const destination='coordination/engineering/fixture/rejected-authority',run=f.run('native-authority',destination);
  assert.notEqual(run.status,0);assert.match(run.stderr,/Incomplete source-target evidence/);assert(!fs.existsSync(path.join(f.root,destination)));
});
