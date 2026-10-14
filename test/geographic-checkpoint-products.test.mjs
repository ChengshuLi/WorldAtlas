import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {reportHash} from '../scripts/geographic-report-artifact.mjs';
const modulePath=path.resolve('scripts/geographic_checkpoint_products.py');
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const bytes=value=>Buffer.from(JSON.stringify(canonical(value))+'\n');
function fixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'checkpoint-retention-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const source=path.join(root,'source'),out=path.join(root,'out');fs.mkdirSync(source);fs.mkdirSync(out);
  const put=(name,raw)=>{fs.writeFileSync(path.join(source,name),raw,{mode:0o644});return {path:name,bytes:raw.length,sha256:reportHash(raw)};};
  const gzip=(name,value)=>{const raw=bytes(value);return {...put(name,gzipSync(raw)),decoded_bytes:raw.length,decoded_sha256:reportHash(raw)};};
  const publication={version:1,complete:true,kind:'trusted-selected-continuous-comparison-v1',
    operands:gzip('operands.json.gz',{baseline:{},candidate:{}}),facts:put('facts.json',bytes({candidate_code_executed:false}))};
  const native={status:'no-new-native-loss',candidate_code_executed:false,intervals:[],lost_or_reassigned_cells:0};
  const routes=put('checkpoint-routes.json',bytes([]));
  const facts={continuous_publication:publication,native_result_sha256:reportHash(bytes(native)),checkpoint_routes:routes};
  const derived={version:1,complete:true,kind:'derived-selected-checkpoint-candidate-v1',accepted_checkpoint:false,
    validation_stage:'native-passed-continuous-pending',certificate:gzip('derived-certificate.json.gz',{version:1,entries:[]}),
    facts:put('derived-facts.json',bytes(facts)),routes};
  put('publication.json',bytes(publication));put('derived-publication.json',bytes(derived));
  const issued={native:{...native,runtime:{notPartOfInnerHash:true}},continuous:{publication,derived_checkpoint:derived},
    continuous_result:{candidate_code_executed:false,issued_publication:publication,
      original_strict_polygon_result:{status:'no-new-regression',regressions:0}}};
  return {root,source,out,issued,put};
}
function run(f,action='retain',extra='') {
  const input=JSON.stringify(f.issued);
  const code=`import json,runpy,sys\nm=runpy.run_path(sys.argv[1])\nissued=json.loads(sys.argv[4])\n${extra}\nresult=m['${action==='retain'?'retain_checkpoint_products':'admit_checkpoint_destination'}'](${action==='retain'?'sys.argv[2],sys.argv[3],issued':'sys.argv[3]'})\nprint(json.dumps(result) if isinstance(result,dict) else str(result))`;
  const env={...process.env};delete env.GH_TOKEN;delete env.GITHUB_TOKEN;
  return spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code,modulePath,f.source,f.out,input],{encoding:'utf8',env});
}
test('actual Python retention binds whole provisional copies and preserves native/strict outcomes', t=>{
  const f=fixture(t),result=run(f);assert.equal(result.status,0,result.stderr);
  const descriptor=JSON.parse(result.stdout);assert.equal(descriptor.members.length,7);
  for(const row of descriptor.members) assert(fs.readFileSync(path.join(f.out,row.name)).equals(fs.readFileSync(path.join(f.source,row.name))));
  assert.equal(JSON.parse(fs.readFileSync(path.join(f.out,'derived-publication.json'))).accepted_checkpoint,false);
});
test('ordinary and dangling-symlink collisions refuse before writing and preserve original sentinels',t=>{
  for(const symbolic of [false,true]) {
    const f=fixture(t),target=path.join(f.out,'facts.json');
    if(symbolic)fs.symlinkSync(path.join(f.root,'missing'),target);else fs.writeFileSync(target,'original sentinel');
    const result=run(f);assert.notEqual(result.status,0);assert.match(result.stderr,/already exists/);
    assert.equal(fs.readdirSync(f.out).length,1);
    if(symbolic)assert(fs.lstatSync(target).isSymbolicLink());else assert.equal(fs.readFileSync(target,'utf8'),'original sentinel');
  }
});
test('failed/missing strict result, forged native result, incomplete publication and extra files refuse',t=>{
  for(const alter of [f=>f.issued.continuous_result.original_strict_polygon_result.regressions=1,
    f=>delete f.issued.continuous_result.original_strict_polygon_result,f=>f.issued.native.lost_or_reassigned_cells=1,
    f=>f.issued.continuous.derived_checkpoint.accepted_checkpoint=true,f=>f.put('extra.json',bytes({})),
    f=>fs.unlinkSync(path.join(f.source,'checkpoint-routes.json'))]) {
    const f=fixture(t);alter(f);const result=run(f);assert.notEqual(result.status,0);assert.deepEqual(fs.readdirSync(f.out),[]);
  }
});
test('bounded gzip reader rejects trailer size lies before trusting inflated bodies',t=>{
  const f=fixture(t),file=path.join(f.source,'operands.json.gz'),body=fs.readFileSync(file);body.writeUInt32LE(1,body.length-4);fs.writeFileSync(file,body);
  const result=run(f);assert.notEqual(result.status,0);assert.deepEqual(fs.readdirSync(f.out),[]);
});
test('complete union admission precedes product reads and output creation',t=>{
  const f=fixture(t),result=run(f,'retain',"original=m['retain_checkpoint_products']\nm['retain_checkpoint_products']=lambda *args: original(*args,allowance=1)");
  assert.notEqual(result.status,0);assert.match(result.stderr,/current allowance/);assert.deepEqual(fs.readdirSync(f.out),[]);
});
test('partial write failure yields no completion descriptor and preserves failed output evidence',t=>{
  const f=fixture(t);const code=`import pathlib\noriginal=pathlib.Path.open\ndef fail(self,*args,**kwargs):\n    if self.parent==pathlib.Path(sys.argv[3]) and self.name=='facts.json': raise OSError('injected write failure')\n    return original(self,*args,**kwargs)\npathlib.Path.open=fail`;
  const result=run(f,'retain',code);assert.notEqual(result.status,0);assert.match(result.stderr,/injected write failure/);
  assert.equal(result.stdout,'');assert(fs.readdirSync(f.out).length>0);assert(!fs.existsSync(path.join(f.out,'geography-check.json')));
});
test('actual joint Python parent retains products before its temporary directory closes',t=>{
  for(const regressions of [0,1]) {
    const f=fixture(t),runner=path.resolve('scripts/run-geographic-check.py');
    f.issued.kind='trusted-selected-joint-comparison-v1';f.issued.mode='authenticated-checkpoint-append-v1';f.issued.candidate_code_executed=false;
    f.issued.continuous_result.original_strict_polygon_result.regressions=regressions;
    if(regressions)f.issued.continuous_result.original_strict_polygon_result.status='regressions-found';
    const code=`import importlib.util,json,pathlib,shutil,sys\nspec=importlib.util.spec_from_file_location('joint_parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nissued=json.loads(sys.argv[5]);destinations=[]\ndef child(command,**kwargs):\n    destination=pathlib.Path(command[-2]);shutil.copytree(sys.argv[3],destination);destinations.append(destination);return json.dumps(issued).encode()\nm.subprocess.check_output=child\nm.consume_selected_continuous=lambda *args,**kwargs: issued['continuous_result']\nm.selected_consumer_allowance=lambda repo: 256*1024*1024\nresult=m.selected_joint(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,None,checkpoint_destination=pathlib.Path(sys.argv[4]))\nassert all(not p.exists() for p in destinations)\nprint(json.dumps(result))`;
    const result=spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code,runner,process.cwd(),f.source,f.out,JSON.stringify(f.issued)],{encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);const actual=JSON.parse(result.stdout);
    if(regressions){assert.equal(actual.checkpoint,undefined);assert.deepEqual(fs.readdirSync(f.out),[]);}
    else {assert.equal(actual.checkpoint.members.length,7);assert(fs.existsSync(path.join(f.out,'derived-certificate.json.gz')));}
  }
});
test('joint parent collision admission runs before launching its scientific child',t=>{
  for(const symbolic of [false,true]) {
    const f=fixture(t),target=path.join(f.out,'facts.json');
    if(symbolic)fs.symlinkSync(path.join(f.root,'missing'),target);else fs.writeFileSync(target,'original sentinel');
    const runner=path.resolve('scripts/run-geographic-check.py');
    const code=`import importlib.util,pathlib,sys\nspec=importlib.util.spec_from_file_location('joint_parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\ndef child(*args,**kwargs): raise AssertionError('scientific child started before collision admission')\nm.subprocess.check_output=child\nm.selected_joint(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,None,checkpoint_destination=pathlib.Path(sys.argv[3]))`;
    const result=spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code,runner,process.cwd(),f.out],{encoding:'utf8'});
    assert.notEqual(result.status,0);assert.match(result.stderr,/Checkpoint output already exists/);assert.doesNotMatch(result.stderr,/scientific child started/);
    if(symbolic)assert(fs.lstatSync(target).isSymbolicLink());else assert.equal(fs.readFileSync(target,'utf8'),'original sentinel');
  }
});
test('runner reserves optional full-bank prefetch for the explicit legacy cold route',t=>{
  for(const cold of [false,true]) {
    const f=fixture(t),runner=path.resolve('scripts/run-geographic-check.py');
    fs.mkdirSync(path.join(f.root,'scripts'));
    fs.writeFileSync(path.join(f.root,'scripts/check-geographic-regression.py'),"def inspect(*args): return {'status':'no-new-regression','regressions':0}\n");
    const code=`import importlib.util,json,pathlib,sys\nspec=importlib.util.spec_from_file_location('joint_parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nissued=json.loads(sys.argv[3]);cold=sys.argv[4]=='true';calls=[]\nm.verify_trusted_checkout=lambda *args:'verified-fixture'\nm.inventory=lambda repo,version: {'fixture':version}\nm.git=lambda *args:b'present'\ndef joint(*args,**kwargs):\n    calls.append('joint');return {'mode':'legacy-cold-required'} if cold else {'mode':'authenticated-checkpoint-append-v1','native':issued['native'],'continuous_result':issued['continuous_result']}\nm.selected_joint=joint\nm.prefetch_declared_inputs=lambda *args:calls.append('prefetch')\ndef native(*args,**kwargs):\n    calls.append('native');return json.dumps(issued['native']).encode()\nm.subprocess.check_output=native\ndef continuous(*args,**kwargs):\n    calls.append('continuous');return issued['continuous_result']\nm.selected_continuous=continuous\nm.inspect(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,prefetch=True)\nprint(json.dumps(calls))`;
    const result=spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code,runner,f.root,JSON.stringify(f.issued),String(cold)],{encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);
    assert.deepEqual(JSON.parse(result.stdout),cold?['joint','prefetch','native','continuous']:['joint']);
  }
});

function pixelFixture(t) {
  const f=fixture(t);
  for(const name of ['facts.json','operands.json.gz','publication.json'])fs.unlinkSync(path.join(f.source,name));
  const native={status:'no-new-native-loss',method:'selected-native-owner-conservation-v1',candidate_code_executed:false,
    intervals:[],lost_or_reassigned_cells:0,affected_rows:1,
    native_row_scope:{proof:'shared-qualified-complete-base-and-cumulative-patch',changed_rows:[3]},
    repair_visibility:{new_components:1,witnesses:[{component_id:'new',geometry_sha256:'a'.repeat(64),x:2,y:3,previous_owner:0,candidate_owner:1}]}};
  const derived=JSON.parse(fs.readFileSync(path.join(f.source,'derived-publication.json')));
  const facts=JSON.parse(fs.readFileSync(path.join(f.source,'derived-facts.json')));
  derived.validation_stage='native-passed-continuous-not-applicable';
  Object.assign(facts,{validation_stage:derived.validation_stage,continuous_publication:null,native_result_sha256:reportHash(bytes(native))});
  derived.facts=f.put('derived-facts.json',bytes(facts));f.put('derived-publication.json',bytes(derived));
  const result={version:1,kind:'trusted-selected-continuous-comparison-v1',status:'not-applicable',
    scope:'visible-native-pixel-repair-v1',regressions:null,issued_publication:null,complete_owners:3,
    changed_ids:['A'],candidate_code_executed:false};
  f.issued={native,continuous:{...result,derived_checkpoint:derived},continuous_result:result};
  return f;
}
test('pixel-only retention keeps exactly four derived members and never invents polygon success',t=>{
  const f=pixelFixture(t),result=run(f);assert.equal(result.status,0,result.stderr);
  const descriptor=JSON.parse(result.stdout);assert.equal(descriptor.members.length,4);
  assert.deepEqual(descriptor.members.map(row=>row.name),['checkpoint-routes.json','derived-certificate.json.gz','derived-facts.json','derived-publication.json']);
  for(const row of descriptor.members)assert(fs.readFileSync(path.join(f.out,row.name)).equals(fs.readFileSync(path.join(f.source,row.name))));
  assert.equal(f.issued.continuous_result.original_strict_polygon_result,undefined);
});
test('pixel-only retention rejects missing native evidence, mixed rosters and fabricated polygon claims',t=>{
  for(const mutate of [f=>f.issued.native.repair_visibility.new_components=0,
    f=>f.issued.native.repair_visibility.witnesses=[],f=>f.issued.native.repair_visibility.witnesses[0].previous_owner=1,
    f=>f.issued.native.native_row_scope.changed_rows=[],f=>f.issued.native.lost_or_reassigned_cells=1,
    f=>f.issued.continuous.original_strict_polygon_result={status:'no-new-regression',regressions:0},
    f=>f.issued.continuous.regressions=0,f=>delete f.issued.continuous.scope,
    f=>f.put('publication.json',bytes({})),f=>fs.unlinkSync(path.join(f.source,'checkpoint-routes.json'))]) {
    const f=pixelFixture(t);mutate(f);const result=run(f);assert.notEqual(result.status,0);assert.deepEqual(fs.readdirSync(f.out),[]);
  }
});
test('actual Python joint wrapper skips polygon consumer only for live explicit pixel scope',t=>{
  const f=pixelFixture(t),runner=path.resolve('scripts/run-geographic-check.py');
  Object.assign(f.issued,{kind:'trusted-selected-joint-comparison-v1',mode:'authenticated-checkpoint-append-v1',candidate_code_executed:false});
  const code=`import importlib.util,json,pathlib,shutil,sys\nspec=importlib.util.spec_from_file_location('parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nissued=json.loads(sys.argv[5])\ndef child(command,**kwargs):\n    shutil.copytree(sys.argv[3],pathlib.Path(command[-2]));return json.dumps(issued).encode()\nm.subprocess.check_output=child\ndef polygons(*args,**kwargs): raise AssertionError('continuous polygons must not execute')\nm.consume_selected_continuous=polygons\nm.selected_consumer_allowance=lambda repo:256*1024*1024\nresult=m.selected_joint(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,None,checkpoint_destination=pathlib.Path(sys.argv[4]))\nprint(json.dumps(result))`;
  const result=spawnSync(process.env.PYTHON??'python3',['-I','-B','-c',code,runner,process.cwd(),f.source,f.out,JSON.stringify(f.issued)],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);const actual=JSON.parse(result.stdout);
  assert.equal(actual.continuous_result.status,'not-applicable');assert.equal(actual.continuous_result.original_strict_polygon_result,undefined);
  assert.equal(actual.checkpoint.members.length,4);
});
