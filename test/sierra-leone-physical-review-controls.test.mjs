import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const retainedCodePrefix='coordination/engineering/sierra-leone-physical-review-20261018-worker4/';
const fixturePrefix='test/fixtures/sle-physical-review/';
const fixtureFiles=[
  'input-pins.json',
  'intervals/block-030.json.gz',
  'intervals/package.json',
  'results-001/interval-assessments.json',
  'results-001/cell-observations.json',
  'results-001/questions.json'
];
const retainedScripts=['interpret.py','test_interpret.py','observe-selected-state.mjs'];
const loader=path.resolve('test/fixtures/sle-observation-loader.mjs');
const digest=body=>createHash('sha256').update(body).digest('hex');

function copyRetainedPacket(directory) {
  const packet=path.join(directory,'packet');
  fs.mkdirSync(packet);
  for(const name of retainedScripts) {
    fs.copyFileSync(path.join(process.cwd(),retainedCodePrefix,name),path.join(packet,name));
  }
  for(const name of fixtureFiles) {
    const source=path.join(process.cwd(),fixturePrefix,name);
    const destination=path.join(packet,name);
    fs.mkdirSync(path.dirname(destination),{recursive:true});
    fs.copyFileSync(source,destination);
  }
  return packet;
}

function runObserver(observer,output) {
  return spawnSync(process.execPath,['--import',loader,observer,output],{
    cwd:process.cwd(),encoding:'utf8',maxBuffer:8*1024*1024
  });
}

test('bounded retained Python interpretation controls run in the ordinary Node test inventory',t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'sle-python-controls-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const packet=copyRetainedPacket(directory);
  const result=spawnSync(process.env.PYTHON??'python3',['-I','-B',path.join(packet,'test_interpret.py')],{
    cwd:process.cwd(),encoding:'utf8',maxBuffer:8*1024*1024
  });
  assert.equal(result.error,undefined,result.error?.message);
  assert.equal(result.status,0,result.stderr);
  const report=JSON.parse(result.stdout);
  assert.equal(report.passed,15);
  assert(report.checks.includes('actual complete original scope/source metadata'));
  assert(report.checks.includes('actual retained mapped-land positive contact'));
  assert(report.checks.includes('actual retained Pujehun issue positive contact'));
  assert(report.checks.includes('literal interval/cell/question conservation without predicate replay'));
  assert(report.checks.includes('actual CLI existing-output refusal before input/query'));
  assert(report.checks.includes('actual CLI dangling-symlink refusal before input/query'));
  assert.match(report.limit,/No full centre computation/);
});

test('existing selected-state observer emits a complete conflict-aware key/accounting receipt',t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'sle-observer-controls-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const packet=copyRetainedPacket(directory);
  const observer=path.join(packet,'observe-selected-state.mjs');
  const output=path.join(directory,'fresh');
  const result=runObserver(observer,output);
  assert.equal(result.error,undefined,result.error?.message);
  assert.equal(result.status,0,result.stderr);
  const events=result.stdout.trim().split('\n').map(line=>JSON.parse(line));
  assert.deepEqual(events.map(event=>event.event),['actual-start','actual-exit']);
  const state=JSON.parse(fs.readFileSync(path.join(output,'selected-state.json'),'utf8'));
  const publication=JSON.parse(fs.readFileSync(path.join(output,'publication.json'),'utf8'));
  const intervals=JSON.parse(gunzipSync(fs.readFileSync(path.join(packet,'intervals/block-030.json.gz'))));
  const expected=new Map();
  for(const [y,start,end,owners] of intervals)for(let x=start;x<end;x++){
    const key=y+':'+x;
    assert(!expected.has(key),'retained original interval keys are disjoint');
    expected.set(key,[y,x,owners[0]]);
  }
  assert.equal(state.original_cells,1213);
  assert.equal(state.original_intervals,613);
  assert.equal(state.original_owners,7);
  assert.equal(state.keys.length,1213);
  assert.equal(new Set(state.keys.map(key=>key.y)).size,events[1].rows);
  assert.deepEqual(new Set(state.keys.map(key=>key.y+':'+key.x)),new Set(expected.keys()));
  assert(state.keys.every(key=>expected.get(key.y+':'+key.x)?.[2]===key.original_owner));
  assert.equal(state.selected_targets.length,14);
  assert.equal(state.keys.filter(key=>key.base_owner!==0).length,1213);
  assert.equal(state.keys.filter(key=>key.accepted_additive_owner!==0).length,1);
  assert.equal(state.keys.filter(key=>key.existing_product_overlap).length,1);
  assert.equal(state.keys.filter(key=>key.effective_selected_owner===null).length,1);
  const conflict=state.keys.find(key=>key.existing_product_overlap);
  assert(conflict.base_owner!==0&&conflict.accepted_additive_owner!==0);
  assert.equal(conflict.effective_selected_owner,null);
  const body=fs.readFileSync(path.join(output,'selected-state.json'));
  assert.equal(publication.complete,true);
  assert.equal(publication.files.length,1);
  assert.equal(publication.files[0].path,'selected-state.json');
  assert.equal(publication.files[0].bytes,body.length);
  assert.equal(publication.files[0].sha256,digest(body));
  assert.equal(events[1].cells,state.keys.length);
  assert.equal(events[1].base_occupied,state.keys.length);
  assert.equal(events[1].additive_occupied,1);
  assert.equal(events[1].conflicts,1);
});

test('selected-state observer refuses existing and symlink output paths before writing',t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'sle-observer-refusal-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const packet=copyRetainedPacket(directory);
  const observer=path.join(packet,'observe-selected-state.mjs');
  const existing=path.join(directory,'existing');
  fs.mkdirSync(existing);
  fs.writeFileSync(path.join(existing,'sentinel'),'unchanged');
  const refused=runObserver(observer,existing);
  assert.notEqual(refused.status,0);
  assert.equal(refused.stdout,'');
  assert.match(refused.stderr,/Fresh output required/);
  assert.equal(fs.readFileSync(path.join(existing,'sentinel'),'utf8'),'unchanged');

  const target=path.join(directory,'target');
  fs.mkdirSync(target);
  const link=path.join(directory,'linked-parent');
  fs.symlinkSync(target,link);
  const symlinkRefused=runObserver(observer,path.join(link,'new-output'));
  assert.notEqual(symlinkRefused.status,0);
  assert.equal(symlinkRefused.stdout,'');
  assert.match(symlinkRefused.stderr,/Symlink output refused/);
  assert.deepEqual(fs.readdirSync(target),[]);
});
