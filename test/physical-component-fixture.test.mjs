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
test('actual ephemeral component cache invalidates every input family and a fresh method',t=>{
  const run=runPython(t,['-B','-c',String.raw`
import copy, importlib.util, pathlib
spec=importlib.util.spec_from_file_location('actual_controls','test/physical-component-evidence-controls.py')
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
original=helper.validator.components
features=[{'id':'a','properties':{'kind':'land'},'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,0]]]}}]
blocked=[{'id':'tile-a','bounds':[0,0,1,1]}]
bounds=[-180,-90,180,90]
calls=[]
def kernel(*args):
    calls.append(copy.deepcopy(args))
    return {'method':'first','call':len(calls)}
helper.validator.components=kernel
try:
    helper.Controls.setUpClass()
    try:
        cached=helper.validator.components
        first=cached(features,blocked,bounds)
        assert cached(copy.deepcopy(features),copy.deepcopy(blocked),copy.deepcopy(bounds))==first
        assert len(calls)==1
        mutations=[]
        for field in ['properties','geometry','id']:
            changed=copy.deepcopy(features)
            if field=='properties': changed[0]['properties']['kind']='water'
            elif field=='geometry': changed[0]['geometry']['coordinates'][0][1][0]=2
            else: changed[0]['id']='different-subject'
            mutations.append((changed,blocked,bounds))
        mutations.extend([(features+[{'id':'new-subject','properties':{},'geometry':None}],blocked,bounds),
                          (features,[{'id':'tile-b','bounds':[0,0,1,1]}],bounds),
                          (features,[{'id':'tile-a','bounds':[0,0,2,1]}],bounds),
                          (features,blocked,[-179,-90,180,90])])
        for expected,args in enumerate(mutations,start=2):
            assert cached(*args)['call']==expected
            assert len(calls)==expected
        retained=pathlib.Path(helper.Controls.cache_directory.name)
    finally: helper.Controls.tearDownClass()
    assert not retained.exists()
    second_calls=[]
    def second_kernel(*args):
        second_calls.append(args)
        return {'method':'second'}
    helper.validator.components=second_kernel
    helper.Controls.setUpClass()
    try:
        assert helper.validator.components(features,blocked,bounds)=={'method':'second'}
        assert len(second_calls)==1
    finally: helper.Controls.tearDownClass()
finally: helper.validator.components=original
print('cache input and method reload controls passed')
`]);
  assert.match(run.stdout,/cache input and method reload controls passed/);
});
