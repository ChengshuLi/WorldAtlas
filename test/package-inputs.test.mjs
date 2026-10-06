import test from 'node:test';
import assert from 'node:assert/strict';
import {loadPackageInputs, validatePackageInputs, containsPackagePath, safePackagePath} from '../scripts/package-inputs.mjs';

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
