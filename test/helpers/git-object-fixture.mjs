// Test-only exact omission. Object identity, not Git's current loose/packed
// storage choice, defines a missing-input fixture. Preserve the complete store
// outside the repository until this test's ordinary temporary cleanup.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
export function omitFixtureObjects(t,repo,ids,{packed=false}={}) {
  const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'};
  const git=(...args)=>execFileSync('git',['--no-lazy-fetch','--no-replace-objects','-C',repo,...args],{env,encoding:'utf8'}).trim();
  const objects=path.resolve(repo,git('rev-parse','--git-path','objects'));
  assert.equal(objects,path.join(repo,'.git','objects'),'Fixture owns its ordinary object directory');
  assert(fs.lstatSync(objects).isDirectory()&&!fs.lstatSync(objects).isSymbolicLink());
  assert(!fs.existsSync(path.join(objects,'info','alternates')));
  assert(ids.length>0&&ids.every(id=>/^[a-f0-9]{40}$/.test(id)));
  assert.equal(new Set(ids).size,ids.length,'Omission targets must be unique exact objects');
  if(packed){
    git('repack','-ad');
    assert(fs.readdirSync(path.join(objects,'pack')).some(name=>name.endsWith('.pack')));
    assert(ids.every(id=>!fs.existsSync(path.join(objects,id.slice(0,2),id.slice(2)))));
  }
  const inventory=()=>git('cat-file','--batch-all-objects','--batch-check=%(objectname)').split('\n').filter(Boolean).sort();
  const all=inventory();assert(ids.every(id=>all.includes(id)),'Every omission target must exist first');
  const retained=all.filter(id=>!ids.includes(id));
  const pack=execFileSync('git',['--no-lazy-fetch','--no-replace-objects','-C',repo,'pack-objects','--stdout'],
    {env,input:retained.join('\n')+'\n',maxBuffer:64*1024*1024});
  const custody=fs.mkdtempSync(path.join(path.dirname(repo),'.fixture-object-custody-'));
  t.after(()=>fs.rmSync(custody,{recursive:true,force:true}));
  fs.renameSync(objects,path.join(custody,'objects'));
  fs.mkdirSync(path.join(objects,'pack'),{recursive:true});fs.mkdirSync(path.join(objects,'info'));
  execFileSync('git',['--no-lazy-fetch','--no-replace-objects','-C',repo,'index-pack','--stdin'],{env,input:pack,stdio:['pipe','pipe','pipe']});
  assert.deepEqual(inventory(),retained,'All and only declared fixture objects are omitted');
  for(const id of ids)assert.throws(()=>git('cat-file','-e',id));
}
