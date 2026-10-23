import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadPackageInputs, validatePackageInputs, containsPackagePath, safePackagePath, readPackageInputs, focusedCheckoutPatterns, preparedStartupPackageTransition, PREPARED_STARTUP_PREFIX, PREPARED_STARTUP_INDEX} from '../scripts/package-inputs.mjs';

test('declaration uses literal paths, precise directory membership and approved outputs', () => {
  const value = loadPackageInputs();
  assert.equal(validatePackageInputs(value), value);
  assert.equal(containsPackagePath(['src/'], 'src/main.js'), true);
  assert.equal(containsPackagePath(['src/'], 'src-other/main.js'), false);
  assert.equal(containsPackagePath(['research/public.json'], 'research/private.json'), false);
  for (const name of ['../escape', '/absolute', 'src//main', 'src/./main', 'src/*.js', 'src\\main', 'src/main\n']) {
    assert.equal(safePackagePath(name), false, name);
    assert.throws(() => validatePackageInputs({...value, inputs: [...value.inputs, name]}));
  }
  for (const name of ['.git/', 'node_modules/', '.cache/', 'dist/', 'data/atlas.sqlite']) {
    assert.throws(() => validatePackageInputs({...value, inputs: [...value.inputs, name]}), /Ambient/);
  }
  assert.throws(() => validatePackageInputs({...value, inputs: [...value.inputs, 'src/nested/']}), /Overlapping/);
  assert.throws(() => validatePackageInputs({...value, optional_inputs: ['not-declared']}), /Incomplete/);
  assert.doesNotThrow(() => validatePackageInputs({...value, generated_outputs: ['.cache/package-atlas.sqlite']}));
  for (const output of ['research/', '.cache/other.sqlite', 'data/atlas.sqlite.bak']) assert.throws(() => validatePackageInputs({...value, generated_outputs: [output]}), /Unsupported generated/);
});


test('complete package declarations retain exact whole immutable blob identity',async()=>{
  const value={version:1,inputs:['.github/package-inputs.json',...Array.from({length:4096},(_,i)=>`coordination/engineering/scaled-selected/role-${i}.json`)],optional_inputs:[],verification_paths:[],generated_outputs:['dist/', '.cache/package-atlas.sqlite']};
  const raw=Buffer.from(JSON.stringify(value));
  assert.ok(raw.length>128*1024);
  assert.equal(validatePackageInputs(value),value);
  assert.throws(()=>validatePackageInputs({...value,inputs:[...value.inputs,value.inputs[1]]}),/Invalid package inputs/);
  assert.throws(()=>validatePackageInputs({...value,inputs:[...value.inputs,'coordination/engineering/scaled-selected/']}),/Overlapping/);
  const {createHash}=await import('node:crypto');
  const blob={type:'file',encoding:'base64',path:'.github/package-inputs.json',size:raw.length,content:raw.toString('base64'),sha:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')};
  assert.deepEqual(await readPackageInputs({route:'/repo',base:'main',api:async()=>blob}),value);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',api:async()=>({...blob,size:Number.MAX_SAFE_INTEGER})}),/bytes changed/);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',api:async()=>({...blob,content:Buffer.from('changed complete body').toString('base64')})}),/bytes changed/);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',api:async()=>({...blob,sha:'0'.repeat(40)})}),/bytes changed/);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',api:async()=>({...blob,type:'dir'})}),/unavailable/);
});


test('original output capture and actual Python execution use the declared source boundary',()=>{
  const definition=loadPackageInputs();
  for(const name of ['scripts/package-output-artifact.mjs',
    'scripts/package-inputs.mjs','scripts/package-python-runtime.py'])
    assert(containsPackagePath(definition.inputs,name),name+' is a genuine capture dependency');
});


function selectedByGit(definition, names, inputs) {
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'focused-package-patterns-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of names){const file=path.join(temporary,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'fixture\n');}
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:focusedCheckoutPatterns(definition,inputs).join('\n')+'\n'});
    return names.filter(name=>fs.existsSync(path.join(temporary,name)));
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
}

test('focused checkout follows canonical verification operands and ordinary code without the package data tree',()=>{
  const definition={version:1,inputs:['.github/package-inputs.json','research/geography/package-only/'],
    optional_inputs:[],verification_paths:['research/geography/fixture/required.json','coordination/engineering/fixture/results/'],generated_outputs:[]};
  const required=['scripts/consumer.mjs','test/consumer.test.mjs','coordination/engineering/fixture/consumer.py',
    'research/geography/fixture/required.json','coordination/engineering/fixture/results/part.json'];
  const excluded=['research/geography/fixture/unrelated.json','research/geography/package-only/source.bin',
    'coordination/engineering/fixture/unrelated.json','data/unrelated.json'];
  assert.deepEqual(selectedByGit(definition,[...required,...excluded]),required);
  assert.throws(()=>focusedCheckoutPatterns({...definition,verification_paths:['../outside']}),/Invalid package verification_paths/);
  const changed={...definition,verification_paths:[...definition.verification_paths,excluded[0]]};
  assert.deepEqual(selectedByGit(changed,excluded),[excluded[0]],'one declaration changes the actual Git checkout');
  assert.deepEqual(selectedByGit(definition,[...required,...excluded],[excluded[0]]),
    [...required.slice(0,3),excluded[0]],'an exact reviewed fixture list omits unrelated verification operands');
});

test('focused checkout retains every original body exposed by the cold delivery controls',()=>{
  const definition=loadPackageInputs();
  const required=[
    'data/ownership-selection.json',
    'research/geography/ukraine-original-singleton-source-fit-20261010/vintages/physical-restoration-001/sources-000.jsonl.gz',
    'research/geography/gap-source-angola-drc-shared-seams-20261006/vintages/congo-physical-custody-002/components-021.jsonl.gz'
  ];
  for(const name of required)assert(containsPackagePath(definition.verification_paths,name),name);
  assert.deepEqual(selectedByGit(definition,required),required);
});


test('prepared transition derives exact additions and retirements from two whole selector-bound indexes',()=>{
  const sha=raw=>createHash('sha256').update(raw).digest('hex'),oid=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  const raw=value=>Buffer.from(JSON.stringify(value));
  const fixture=()=>{
    const sources=[],buffers=[],indexes=[];
    const pin=(name,text)=>({path:name,bytes:Buffer.byteLength(text),sha256:sha(Buffer.from(text))});
    const fixed=[pin('native/rows.bin','rows'),pin('native/runs.bin','runs'),pin('native/latitudes.bin','latitudes'),pin('old-promised/url.bin','old URL')];
    const base={id:'geography:base',footprints_sha256:'b'.repeat(64),hierarchy_sha256:'c'.repeat(64)};
    for(const label of ['before','after']){
      const selection={version:1,method:'native-linear-evenodd-first-owner-v1',sha256:'a'.repeat(64),release_id:base.id,additive_release:{path:label+'.json'}};
      const active=[pin(label+'/runs.bin',label+' runs'),pin(label+'/context.json.gz',label+' context')];
      const effective={...base,id:'geography:'+label,footprints_sha256:sha(raw(label))};
      const index={version:2,native_manifest_sha256:selection.sha256,release_id:effective.id,footprints_sha256:effective.footprints_sha256,hierarchy_sha256:effective.hierarchy_sha256,
        compatibility_files:fixed,files:[...fixed,...active],pixelMap:{parts:[fixed[0],active[0]]},additiveRelease:{base_reference:base,effective_reference:effective},
        preparedOwnership:{version:2,selection_sha256:sha(raw(selection)),native_manifest_sha256:selection.sha256,
          native_pixel_map:{canonical_grid_sha256:selection.sha256,parts:fixed.slice(0,2),native_latitudes:{transport_path:fixed[2].path,sha256:fixed[2].sha256}},
          context_parts:[active[1]],base_reference:base,effective_reference:effective}};
      const source={selection,files:index.files.map(pin=>({path:PREPARED_STARTUP_PREFIX+pin.path,mode:'100644',oid:sha(raw(pin)).slice(0,40),bytes:pin.bytes}))};
      sources.push(source);indexes.push(index);buffers.push({index:raw(index),selection:raw(selection)});
    }
    const seal=()=>{for(let i=0;i<2;i++){
      buffers[i].index=raw(indexes[i]);buffers[i].selection=raw(sources[i].selection);
      for(const [path,body] of [[PREPARED_STARTUP_INDEX,buffers[i].index],['data/ownership-selection.json',buffers[i].selection]]){
        sources[i].files=sources[i].files.filter(row=>row.path!==path);sources[i].files.push({path,mode:'100644',oid:oid(body),bytes:body.length});
      }
    }};
    const check=()=>preparedStartupPackageTransition(sources[0],sources[1],{beforeIndex:buffers[0].index,afterIndex:buffers[1].index,beforeSelection:buffers[0].selection,afterSelection:buffers[1].selection});
    seal();return {sources,buffers,indexes,seal,check};
  };
  const f=fixture(),result=f.check();
  assert.deepEqual([...result.added].sort(),['after/context.json.gz','after/runs.bin'].map(p=>PREPARED_STARTUP_PREFIX+p));
  assert.deepEqual([...result.removed].sort(),['before/context.json.gz','before/runs.bin'].map(p=>PREPARED_STARTUP_PREFIX+p));
  for(const [name,change] of [
    ['stale selector',g=>{g.indexes[1].preparedOwnership.selection_sha256='f'.repeat(64);}],
    ['changed original native',g=>{g.indexes[1].preparedOwnership.native_pixel_map.runWords=99;}],
    ['changed content reference',g=>{const changed={...g.indexes[1].preparedOwnership.base_reference,id:'other'};g.indexes[1].preparedOwnership.base_reference=changed;g.indexes[1].additiveRelease.base_reference=changed;}],
    ['same URL different body',g=>{g.sources[1].files[0].oid='f'.repeat(40);}],
    ['dropped promised URL',g=>{const name='old-promised/url.bin';g.indexes[1].files=g.indexes[1].files.filter(p=>p.path!==name);g.indexes[1].compatibility_files=g.indexes[1].compatibility_files.filter(p=>p.path!==name);g.sources[1].files=g.sources[1].files.filter(p=>p.path!==PREPARED_STARTUP_PREFIX+name);}],
    ['extra tree member',g=>{g.sources[1].files.push({path:PREPARED_STARTUP_PREFIX+'unbound',mode:'100644',oid:'f'.repeat(40),bytes:1});}],
    ['missing pinned member',g=>{g.sources[1].files.splice(4,1);}],
    ['nonordinary member',g=>{g.sources[1].files[4].mode='120000';}],
    ['inactive member retained',g=>{const p={path:'inactive',bytes:1,sha256:'f'.repeat(64)};g.indexes[1].files.push(p);g.sources[1].files.push({path:PREPARED_STARTUP_PREFIX+p.path,mode:'100644',oid:'f'.repeat(40),bytes:1});}]
  ]){const g=fixture();change(g);g.seal();assert.throws(g.check,undefined,name);}
  const g=fixture();g.buffers[1].index=Buffer.concat([g.buffers[1].index,Buffer.from(' ')]);
  assert.throws(g.check,/whole metadata differs/,'A public declaration is not proof of the committed bytes');
});
