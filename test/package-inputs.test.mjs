import test from 'node:test';
import assert from 'node:assert/strict';
import {loadPackageInputs, validatePackageInputs, containsPackagePath, safePackagePath, readPackageInputs} from '../scripts/package-inputs.mjs';

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


test('package declarations use actual metadata memory rather than historical batch count',async()=>{
  const value={version:1,inputs:['.github/package-inputs.json',...Array.from({length:4096},(_,i)=>`coordination/engineering/scaled-selected/role-${i}.json`)],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
  const raw=Buffer.from(JSON.stringify(value)),budget=raw.length;
  assert.ok(raw.length>128*1024);
  assert.equal(validatePackageInputs(value,{maximumBytes:budget}),value);
  assert.throws(()=>validatePackageInputs(value,{maximumBytes:budget-1}),/memory admission/);
  assert.throws(()=>validatePackageInputs({...value,inputs:[...value.inputs,value.inputs[1]]}),/Invalid package inputs/);
  assert.throws(()=>validatePackageInputs({...value,inputs:[...value.inputs,'coordination/engineering/scaled-selected/']}),/Overlapping/);
  const {createHash}=await import('node:crypto');
  const blob={type:'file',encoding:'base64',path:'.github/package-inputs.json',size:raw.length,content:raw.toString('base64'),sha:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')};
  assert.deepEqual(await readPackageInputs({route:'/repo',base:'main',api:async()=>blob}),value);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',api:async()=>({...blob,size:Number.MAX_SAFE_INTEGER})}),/unavailable/);
  await assert.rejects(readPackageInputs({route:'/repo',base:'main',maximumBytes:128,api:async()=>({...blob,size:1,content:'A'.repeat(1024)})}),/Encoded package metadata/);
});


test('original output capture and runtime evidence use the declared source boundary',()=>{
  const definition=loadPackageInputs();
  for(const name of ['scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs',
    'scripts/package-inputs.mjs','scripts/package-python-runtime.py'])
    assert(containsPackagePath(definition.inputs,name),name+' is a genuine capture dependency');
});
