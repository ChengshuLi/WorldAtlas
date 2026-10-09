import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

test('science consumes the authenticated report even if its payload changes after custody', t => {
  const temporary = fs.mkdtempSync(path.join(process.cwd(), '.cache/component-report-binding-'));
  t.after(() => fs.rmSync(temporary, {recursive: true, force: true}));
  const env = {...process.env, TMPDIR: temporary, PYTHONDONTWRITEBYTECODE: '1'};
  for (const key of Object.keys(env)) {
    if (/TOKEN|SECRET|PASSWORD|CREDENTIAL|GH_|GITHUB_|AWS_|CLOUDFLARE|NEON|DATABASE_URL/i.test(key)) delete env[key];
  }
  const run = spawnSync(process.env.PYTHON || 'python3', ['-B', '-c', String.raw`
import importlib.util, json, pathlib, tempfile
from unittest import mock
spec = importlib.util.spec_from_file_location('fixture', 'test/physical-component-evidence-controls.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
v = helper.validator
custody = v.validate
with tempfile.TemporaryDirectory(prefix='report-drift-') as directory:
    fixture = helper.Fixture(pathlib.Path(directory))
    fixture.finalize()
    logical = fixture.complete[0]['prefix'] + '/report.json'
    target = fixture.root / fixture.aliases[logical]['payload']
    original_path = helper.ROOT / fixture.aliases[logical]['payload']
    preserved = original_path.read_bytes()
    passed = []
    def change_after_custody(root, index):
        result = custody(root, index)
        passed.append(True)
        altered = json.loads(target.read_bytes())
        altered['new_components'] = 0
        target.unlink()  # detach the fixture's hard link before replacing it
        target.write_bytes(helper.canonical_json(altered))
        return result
    with mock.patch.object(v, 'ROOT', fixture.root), mock.patch.object(v, 'validate', change_after_custody):
        try:
            v.validate_science()
        except ValueError as error:
            assert str(error) == 'Whole original scientific report changed', str(error)
        else:
            raise AssertionError('Changed consumed report passed')
    assert passed == [True], 'The real complete custody phase was not exercised'
    assert original_path.read_bytes() == preserved, 'Original evidence was changed'
print('actual report drift rejected after complete custody; original preserved')
`], {encoding: 'utf8', timeout: 120000, maxBuffer: 4 * 1024 * 1024, env});
  assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);
  assert.match(run.stdout, /actual report drift rejected after complete custody; original preserved/);
});
