import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync, spawnSync} from 'node:child_process';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {pinReader,nativeAuthority} from '../scripts/prepare-delivery-handoff.mjs';
const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const version='a'.repeat(40),family='gb:TST:ADM2',a=family+':A',b=family+':B',c=family+':C';
const size=262166,latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const collection=features=>({type:'FeatureCollection',features});
const rawFeature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
function constructorBodies(change=()=>{}){
  const first=rectangle(-.03,.006,-.02,.02),second=rectangle(.004,.03,-.02,.02);
  const cityGeometry={type:'MultiPolygon',coordinates:[first.coordinates,second.coordinates]};
  const direct=rectangle(.015,.06,-.02,.02);
  const state={originals:[rawFeature('A',first),rawFeature('B',second),rawFeature('C',direct)],
    roster:[{id:'city',index:1},{id:c,index:2},{id:'other-city',index:3}],
    lineage:{changes:[{id:'city',replaces:[a,b]},{id:'irrelevant-split-1',replaces:['unrelated']},{id:'irrelevant-split-2',replaces:['unrelated']}]},
    index:{parts:['geography/part-0.json']},
    accepted:collection([{type:'Feature',id:'city',geometry:cityGeometry,properties:{metadata:{source_member_ids:[a,b]}}}]),
    targets:[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']},
      {id:b,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']}],
    physical:{results:[{target:a,issues:[],support:{mapped_land_support:first}},{target:b,issues:[],support:{mapped_land_support:second}}]},
    measured:[{target:a,consumed:{geometry:first},selected:{id:'city',geometry:cityGeometry}},
      {target:b,consumed:{geometry:second},selected:{id:'city',geometry:cityGeometry}}],
    proposed:{rows:[{y:size/2,runs:[[Math.floor(size/2-.02/360*size),Math.floor(size/2-.02/360*size)+1,1]]}]},
    membership:true};
  change(state);
  const files=new Map(),byBlob=new Map();
  const put=(name,value)=>{
    const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    const pin={commit:version,path:name,mode:'100644',git_blob_oid:blob(raw),bytes:raw.length,sha256:digest(raw)};
    files.set(name,{raw,pin});byBlob.set(pin.git_blob_oid,raw);return pin;
  };
  const source=put('original-source.json',collection(state.originals)),roster=put('owners.json',state.roster);
  const physical=put('physical.json',state.physical),measured=put('measured.json',state.measured);
  const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
    products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
      feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256}]});
  const nativeLatitudes=put('latitudes.f64le',latitudeBytes);
  const membership={index:put('data/world-index.json',state.index),lineage:put('data/semantic-report.json',state.lineage),
    parts:[put('data/geography/part-0.json',state.accepted)]};
  const evidence=put('source-evidence.json',{version:1,kind:'source-target-native-evidence-v1',catalogue,
    owner_roster:roster,physical_evidence:physical,physical_input:measured,physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
    native_latitudes:nativeLatitudes,native_contract:{size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}},
    base_reference:{id:'fixture-base'},families:[{source_id:family,parts:[source]}],
    targets:state.targets.map(target=>({...target,source_receipt_sha256:physical.sha256})),
    ...(state.membership?{source_membership:membership}:{})});
  const patch=put('patch.json',state.proposed);
  return {files};
}

function gitFixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'native-authority-entry-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',args,{cwd:root,stdio:['ignore','pipe','pipe']}).toString().trim();
  const save=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),raw);};
  git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  const {files}=constructorBodies();
  for(const [name,{raw}] of files)if(name!=='source-evidence.json')save(name,raw);
  git('add','.');git('commit','-m','Whole original scientific inputs');
  const original=git('rev-parse','HEAD');
  const evidence=JSON.parse(files.get('source-evidence.json').raw);
  const rewrite=value=>{if(Array.isArray(value))value.forEach(rewrite);else if(value&&typeof value==='object'){
    if(value.commit===version)value.commit=original;Object.values(value).forEach(rewrite);
  }};rewrite(evidence);
  save('source-evidence.json',JSON.stringify(evidence));git('add','.');git('commit','-m','Bound modern evidence');
  const head=git('rev-parse','HEAD'),reader=pinReader(root);
  const config={version:1,preparation_allowance:{phaseBytes:512*1024*1024,rssBytes:512*1024*1024},
    source_evidence:{commit:head,path:'source-evidence.json'},native_patch:{commit:original,path:'patch.json'}};
  const script=new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url).pathname;
  const run=(destination,flags=[])=>{save('config.json',JSON.stringify(config));return spawnSync(process.execPath,[script,'native-authority','config.json',destination,...flags],{cwd:root,encoding:'utf8',env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',GIT_NO_LAZY_FETCH:'1'}});};
  return {root,save,git,config,run,reader};
}
test('plain Node native-authority entry publishes genuine complete constructor products and exact resume',t=>{
  const f=gitFixture(t),destination='coordination/engineering/fixture/authority';
  const first=f.run(destination);assert.equal(first.status,0,first.stderr);
  const output=path.join(f.root,destination),names=fs.readdirSync(output).sort();
  assert.deepEqual(names,['authority-binding.json','constructor-result.json','original-rule-preimage.json','preparation.json']);
  const result=JSON.parse(fs.readFileSync(path.join(output,'constructor-result.json')));
  assert.equal(result.kind,'existing-source-target-native-constructor-result');
  assert.equal(result.ledger_rows.length,1);assert.equal(result.ledger_rows[0].native_cells,1);
  assert.equal(result.ledger_rows[0].target_id,'city');assert.deepEqual(result.inputs,{native_patch:f.config.native_patch,source_evidence:f.config.source_evidence});
  const before=names.map(name=>fs.readFileSync(path.join(output,name)));
  const second=f.run(destination,['--resume']);assert.equal(second.status,0,second.stderr);
  names.forEach((name,i)=>assert.deepEqual(fs.readFileSync(path.join(output,name)),before[i]));
  assert.equal(JSON.parse(second.stdout).resumed,true);
  assert.notEqual(f.run(destination).status,0,'occupied output requires explicit resume');
  fs.appendFileSync(path.join(output,'constructor-result.json'),' ');
  assert.notEqual(f.run(destination,['--resume']).status,0,'changed result cannot be adopted');
});
test('native-authority leaves whole input discovery to the unchanged constructor and preserves CLI products',async t=>{
  const f=gitFixture(t),destination='coordination/engineering/fixture/direct-constructor';
  let outerReads=0;
  for(const name of ['pin','read']){
    const original=f.reader[name];
    f.reader[name]=(...args)=>{outerReads++;return original(...args);};
  }
  const direct=await nativeAuthority(f.config,f.reader,f.root);
  assert.equal(outerReads,0,'authority must not retain a second outer copy of constructor inputs');
  const cli=f.run(destination);assert.equal(cli.status,0,cli.stderr);
  const output=path.join(f.root,destination);
  for(const [name,raw]of Object.entries(direct.products))
    assert.deepEqual(fs.readFileSync(path.join(output,name)),raw,name+' must preserve the genuine constructor product');
  const result=JSON.parse(direct.products['constructor-result.json']);
  assert.equal(result.ledger_rows.length,1);
  assert.equal(result.ledger_rows[0].target_id,'city');
  assert.equal(result.ledger_rows[0].native_cells,1);
});
test('native-authority constructor refuses malformed or mutated committed scientific inputs before publication',t=>{
  for(const mutation of ['malformed-evidence','changed-physical-hash','changed-patch-owner','executable-evidence','executable-patch','unsafe-source-path']){
    const f=gitFixture(t),destination='coordination/engineering/fixture/'+mutation;
    const executable=mutation==='executable-evidence'?'source-evidence.json':mutation==='executable-patch'?'patch.json':null;
    if(executable){
      fs.chmodSync(path.join(f.root,executable),0o755);
    }else if(mutation==='unsafe-source-path'){
      f.save('source evidence.json',fs.readFileSync(path.join(f.root,'source-evidence.json')));
      f.config.source_evidence.path='source evidence.json';
    }else if(mutation==='changed-patch-owner'){
      const patch=JSON.parse(fs.readFileSync(path.join(f.root,'patch.json')));
      patch.rows[0].runs[0][2]=3;f.save('patch.json',JSON.stringify(patch));
    }else{
      const evidence=JSON.parse(fs.readFileSync(path.join(f.root,'source-evidence.json')));
      if(mutation==='changed-physical-hash')evidence.physical_evidence.sha256='0'.repeat(64);
      f.save('source-evidence.json',mutation==='malformed-evidence'?'{':JSON.stringify(evidence));
    }
    f.git('add','.');
    if(executable)f.git('update-index','--chmod=+x',executable);
    f.git('commit','-m','Alter one actually consumed scientific input');
    const head=f.git('rev-parse','HEAD');
    if(executable)assert.match(f.git('ls-tree',head,'--',executable),/^100755 blob /);
    f.config[mutation==='changed-patch-owner'||mutation==='executable-patch'?'native_patch':'source_evidence'].commit=head;
    const run=f.run(destination);assert.notEqual(run.status,0,mutation);
    const expected={
      'malformed-evidence':/JSON/,
      'changed-physical-hash':/Whole immutable input differs: physical\.json/,
      'changed-patch-owner':/Foreign or conflicting proposed source-target interval/,
      'executable-evidence':/Missing ordinary exact Git body: source-evidence\.json/,
      'executable-patch':/Missing ordinary exact Git body: patch\.json/,
      'unsafe-source-path':/Exact commit and safe whole-file path required/
    }[mutation];
    assert.doesNotMatch(run.stderr,/Requested preparation allowance|Insufficient current preparation memory|ERR_MODULE_NOT_FOUND|Cannot find (?:module|package)/,mutation+' must reach its intended input boundary');
    assert.match(run.stderr,expected,mutation);
    assert.equal(fs.existsSync(path.join(f.root,destination)),false,mutation+' must not publish authority');
  }
});
test('native-authority entry refuses missing pins, handwritten descriptors, symlink destination and undersized admission before publishing',t=>{
  for(const mutation of ['missing','handwritten','resources','unknown']){
    const f=gitFixture(t),destination='coordination/engineering/fixture/'+mutation;
    if(mutation==='missing')f.config.native_patch.path='missing.json';
    if(mutation==='handwritten')f.config.native_patch.sha256='1'.repeat(64);
    if(mutation==='resources')f.config.preparation_allowance.phaseBytes=1024;
    if(mutation==='unknown')f.config.accepted=true;
    const run=f.run(destination);assert.notEqual(run.status,0,mutation);
    const expected={missing:/Missing ordinary exact Git body: missing\.json/,
      handwritten:/Supply exact commit\/path locators only/,
      resources:/Installed runtime\/metadata exceeds complete phase/,
      unknown:/Explicit native-authority inputs and allowance required/}[mutation];
    assert.doesNotMatch(run.stderr,/Requested preparation allowance|Insufficient current preparation memory|ERR_MODULE_NOT_FOUND|Cannot find (?:module|package)/,mutation+' must reach its intended boundary');
    assert.match(run.stderr,expected,mutation);
    assert.equal(fs.existsSync(path.join(f.root,destination)),false);
  }
  const f=gitFixture(t);fs.mkdirSync(path.join(f.root,'coordination/engineering'),{recursive:true});fs.symlinkSync(os.tmpdir(),path.join(f.root,'coordination/engineering/link'));
  assert.notEqual(f.run('coordination/engineering/link/authority').status,0);
});
