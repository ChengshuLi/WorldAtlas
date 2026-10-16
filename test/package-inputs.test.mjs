import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {loadPackageInputs, validatePackageInputs, containsPackagePath, safePackagePath, readPackageInputs, focusedCheckoutPatterns} from '../scripts/package-inputs.mjs';

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
  assert.throws(() => validatePackageInputs({...value, generated_outputs: ['research/']}), /Unsupported generated/);
});


test('complete package declarations retain exact whole immutable blob identity',async()=>{
  const value={version:1,inputs:['.github/package-inputs.json',...Array.from({length:4096},(_,i)=>`coordination/engineering/scaled-selected/role-${i}.json`)],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
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


function selectedByGit(definition, names) {
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'focused-package-patterns-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of names){const file=path.join(temporary,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'fixture\n');}
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:focusedCheckoutPatterns(definition).join('\n')+'\n'});
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
