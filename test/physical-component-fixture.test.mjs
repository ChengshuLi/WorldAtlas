import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function runPython(t,args) {
  const temporary=fs.mkdtempSync(path.join(process.cwd(),'.cache/component-fixture-'));
  t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
  const run=spawnSync(process.env.PYTHON||'python3',args,
    {encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024,env:{...process.env,TMPDIR:temporary}});
  assert.equal(run.status,0,`${run.stdout}\n${run.stderr}`);
  return run;
}
test('control fixture retains actual shared-output custody and refuses unchanged bad descriptors',t=>{
  const run=runPython(t,['-B','test/physical-component-evidence-controls.py','FixtureBindingControls']);
  assert.match(run.stderr,/Ran 2 tests/);
});
test('compact controls consume the current reconstruction method on every validation',t=>{
  const run=runPython(t,['-B','-c',String.raw`
import importlib.util
spec=importlib.util.spec_from_file_location('actual_controls','test/physical-component-evidence-controls.py')
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
fixture=helper.CompactFixture()
original=helper.validator.components
calls=[]
def observed(*args):
    calls.append(True)
    return original(*args)
try:
    helper.validator.components=observed
    fixture.validate()
    fixture.validate()
    assert len(calls)==2, 'Every reconstruction must execute the current method'
    def missing_contacts(*args):
        rebuilt, contacts=original(*args)
        assert contacts
        return rebuilt, []
    helper.validator.components=missing_contacts
    try:
        fixture.validate()
    except ValueError as error:
        assert 'Complete original edge/point/dateline contact roster changed' in str(error), str(error)
    else:
        raise AssertionError('A changed reconstruction method reused a prior success')
finally:
    helper.validator.components=original
print('current reconstruction method controls passed')
`]);
  assert.match(run.stdout,/current reconstruction method controls passed/);
});
