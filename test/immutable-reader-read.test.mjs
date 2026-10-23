import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import {execFileSync,spawnSync} from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const {ImmutableReader} = await import(process.env.IMMUTABLE_READER_TEST_MODULE
  ? pathToFileURL(path.resolve(process.env.IMMUTABLE_READER_TEST_MODULE)).href
  : new URL('../scripts/check-effective-geographic-regression.mjs',import.meta.url).href);
const originalCreateHash=crypto.createHash;
const hash=body=>originalCreateHash('sha256').update(body).digest('hex');
const version='1'.repeat(40),name='tiny/body.json';

// Exercise the exported reader's real descriptor and complete read methods.
// Only Git's bounded metadata/body responses are synthetic; no Git history,
// production instrumentation or duplicated reader implementation is required.
function fixture() {
  class ControlledReader extends ImmutableReader {
    git(...args) {
      this.calls.push(args);
      if(args[0]==='ls-tree')return Buffer.from(`${this.mode??'100644'} blob ${this.blob}\t${args[4]}\0`);
      if(args[0]==='cat-file'&&args[1]==='-s')return Buffer.from(String(this.declaredBytes));
      if(args[0]==='cat-file'&&args[1]==='blob')return this.body;
      throw Error('Unexpected fixture Git call: '+args.join(' '));
    }
  }
  const reader=new ControlledReader('.',version);
  reader.calls=[];reader.body=Buffer.from('{"tiny":"body"}\n');
  reader.blob='a'.repeat(40);reader.declaredBytes=reader.body.length;
  return reader;
}
function observeHashes(t) {
  const algorithms=[];
  t.mock.method(crypto,'createHash',function(algorithm,...args){
    algorithms.push(algorithm);return originalCreateHash.call(this,algorithm,...args);
  });
  syncBuiltinESMExports();
  t.after(()=>{t.mock.restoreAll();syncBuiltinESMExports();});
  return algorithms;
}
const wholeReads=reader=>reader.calls.filter(args=>args[0]==='cat-file'&&args[1]==='blob').length;
const pin=reader=>reader.inventory.get(version+':'+name);

test('matching expected hash authenticates one whole read and records one computed digest',t=>{
  const reader=fixture(),expected=hash(reader.body);
  const algorithms=observeHashes(t),actual=reader.read(name,{expected});
  assert.equal(actual,reader.body);assert.deepEqual(algorithms,['sha256']);
  assert.equal(wholeReads(reader),1);
  assert.equal(pin(reader).sha256,expected);assert.equal(pin(reader).whole_body_consumed,true);
  assert.equal(pin(reader).git_blob_oid,reader.blob);
});

test('absent expected hash still computes and records the actual whole-body digest once',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  assert.equal(reader.read(name),reader.body);
  assert.deepEqual(algorithms,['sha256']);assert.equal(wholeReads(reader),1);
  assert.equal(pin(reader).sha256,expected);assert.equal(pin(reader).whole_body_consumed,true);
});

test('wrong expected hash refuses before marking the initially unconsumed inventory',t=>{
  const reader=fixture(),algorithms=observeHashes(t);
  assert.throws(()=>reader.read(name,{expected:'0'.repeat(64)}),/Whole immutable input differs: tiny\/body.json/);
  assert.deepEqual(algorithms,['sha256']);assert.equal(wholeReads(reader),1);
  assert.equal(Object.hasOwn(pin(reader),'sha256'),false);
  assert.equal(Object.hasOwn(pin(reader),'whole_body_consumed'),false);
});

for(const delta of [-1,1])test('body length '+(delta<0?'shortfall':'excess')+' refuses before hashing or inventory consumption',t=>{
  const reader=fixture(),algorithms=observeHashes(t);
  reader.body=Buffer.alloc(reader.declaredBytes+delta,120);
  assert.throws(()=>reader.read(name,{expected:'0'.repeat(64)}),/Whole immutable input differs/);
  assert.deepEqual(algorithms,[]);assert.equal(wholeReads(reader),1);
  assert.equal(Object.hasOwn(pin(reader),'sha256'),false);
  assert.equal(Object.hasOwn(pin(reader),'whole_body_consumed'),false);
});

test('each call rereads and reauthenticates; a later same-size body drift preserves prior inventory state',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  reader.read(name,{expected});const before={...pin(reader)};
  reader.body=Buffer.alloc(reader.declaredBytes,120);
  assert.throws(()=>reader.read(name,{expected}),/Whole immutable input differs/);
  assert.deepEqual(algorithms,['sha256','sha256']);assert.equal(wholeReads(reader),2);
  assert.deepEqual(pin(reader),before);
});

test('repeated immutable descriptors reuse their inventory entry while whole bodies are still read',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  const first=reader.descriptor(name);assert.equal(reader.descriptor(name),first);
  reader.read(name,{expected});reader.read(name,{expected});
  assert.equal(reader.calls.filter(args=>args[0]==='ls-tree').length,1);
  assert.equal(reader.calls.filter(args=>args[0]==='cat-file'&&args[1]==='-s').length,1);
  assert.equal(wholeReads(reader),2);assert.deepEqual(algorithms,['sha256','sha256']);
});

test('changed immutable commit or path gets fresh metadata and a separate descriptor',()=>{
  const reader=fixture(),first=reader.descriptor(name);
  reader.blob='b'.repeat(40);reader.mode='100755';
  const other=reader.descriptor(name,'2'.repeat(40));
  assert.notEqual(other,first);assert.equal(other.git_blob_oid,reader.blob);assert.equal(other.mode,'100755');
  const another=reader.descriptor('tiny/other.json');assert.equal(another.path,'tiny/other.json');
  assert.notEqual(another,first);assert.equal(reader.calls.filter(args=>args[0]==='ls-tree').length,3);
  assert.equal(reader.descriptor(name),first);assert.equal(first.mode,'100644');
});

test('fresh readers authenticate independently and unsafe mutable refs never hit the cache',()=>{
  const first=fixture();first.descriptor(name);
  const second=fixture();second.descriptor(name);
  assert.notEqual(first.inventory,second.inventory);assert.equal(second.calls.length,2);
  first.inventory.set('main:'+name,pin(first));
  assert.throws(()=>first.descriptor(name,'main'),/Unsafe immutable path\/commit/);
  assert.throws(()=>first.descriptor('../body.json'),/Unsafe immutable path\/commit/);
  assert.equal(first.calls.length,2);
});

for(const mode of ['120000','040000'])test(`fresh descriptor rejects non-ordinary mode ${mode}`,()=>{
  const reader=fixture();reader.mode=mode;
  assert.throws(()=>reader.descriptor(name),/Require whole ordinary Git input/);
  assert.equal(reader.inventory.size,0);assert.equal(wholeReads(reader),0);
});

function treeFixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'immutable-tree-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Tree fixture',
    '-c','user.email=tree@example.invalid','-C',root,...args],{stdio:['ignore','pipe','pipe']});
  git('init','-q');fs.mkdirSync(path.join(root,'dir'));
  fs.writeFileSync(path.join(root,'dir','ordinary'),'one');
  fs.writeFileSync(path.join(root,'executable'),'#!/bin/sh\n');fs.chmodSync(path.join(root,'executable'),0o755);
  fs.writeFileSync(path.join(root,'literal[1]'),'literal');fs.writeFileSync(path.join(root,'literal1'),'different');
  fs.symlinkSync('dir/ordinary',path.join(root,'link'));git('add','.');git('commit','-qm','Tree fixture');
  const head=git('rev-parse','HEAD').toString().trim();
  git('update-index','--add','--cacheinfo',`160000,${head},submodule`);git('commit','-qm','Gitlink fixture');
  const version=git('rev-parse','HEAD').toString().trim(),reader=new ImmutableReader(root,version);
  const calls=[],original=reader.git.bind(reader);reader.git=(...args)=>{calls.push(args);return original(...args);};
  return {root,git,version,reader,calls};
}

test('one complete Git tree serves literal files, modes, directories, gitlinks and absences',t=>{
  const f=treeFixture(t);
  for(const name of ['dir/ordinary','dir','executable','link','submodule','missing','dir/missing','literal[1]']) {
    const expected=f.git('--literal-pathspecs','ls-tree','-z',f.version,'--',name).toString();
    assert.equal(f.reader.treeRoute(name),expected);
    assert.equal(f.reader.treeRoute(name),expected);
  }
  assert.equal(f.calls.length,1);assert.deepEqual(f.calls[0],['ls-tree','-rtz','--full-tree',f.version]);
  assert.equal(f.reader.inventory.size,0,'Route metadata is not consumed-body custody');
});

test('fresh readers and changed exact commits obtain their own complete tree',t=>{
  const f=treeFixture(t),old=f.reader.treeRoute('dir/ordinary');
  fs.writeFileSync(path.join(f.root,'dir','ordinary'),'two');f.git('add','.');f.git('commit','-qm','Changed tree');
  const next=f.git('rev-parse','HEAD').toString().trim();
  assert.notEqual(f.reader.treeRoute('dir/ordinary',next),old);
  assert.equal(f.reader.treeRoute('dir/ordinary',f.version),old);assert.equal(f.calls.length,2);
  const fresh=new ImmutableReader(f.root,f.version);let calls=0;const git=fresh.git.bind(fresh);
  fresh.git=(...args)=>{calls++;return git(...args);};assert.equal(fresh.treeRoute('dir/ordinary'),old);assert.equal(calls,1);
  assert.throws(()=>f.reader.treeRoute('dir/ordinary','HEAD'),/Unsafe immutable/);
  assert.throws(()=>f.reader.treeRoute('../outside'),/Unsafe immutable/);
});

test('complete tree command failure and truncated or malformed output never establish absence',t=>{
  const f=treeFixture(t),failure=new ImmutableReader(f.root,'0'.repeat(40));
  assert.throws(()=>failure.treeRoute('missing'),/Command failed/);
  for(const output of ['100644 blob '+'a'.repeat(40)+'\tfile','bad\0',
    ('100644 blob '+'a'.repeat(40)+'\tfile\0').repeat(2)]) {
    const reader=new ImmutableReader(f.root,f.version);reader.git=()=>Buffer.from(output);
    assert.throws(()=>reader.treeRoute('missing'),/Incomplete immutable tree output|Invalid immutable tree entry/);
    reader.git=(...args)=>f.git(...args);assert.equal(reader.treeRoute('missing'),'');
  }
});

function batchFixture(t) {
  const f=treeFixture(t);
  const pin=(name,version=f.version)=>{
    const body=f.git('show',version+':'+name),row=f.git('--literal-pathspecs','ls-tree','-z',version,'--',name).toString();
    const [mode,,oid]=row.slice(0,row.indexOf('\t')).split(' ');
    return {commit:version,path:name,mode,git_blob_oid:oid,bytes:body.length,sha256:hash(body)};
  };
  const calls=[],batch=f.reader.gitBatch.bind(f.reader);
  f.reader.gitBatch=(args,input,maxBuffer)=>{calls.push({args,input,maxBuffer});return batch(args,input,maxBuffer);};
  return {...f,pin,batches:calls};
}

test('known immutable pins share commit, exact-path, size and complete-body processes',t=>{
  const f=batchFixture(t);
  const inputs=['literal[1]','dir/ordinary','executable'].map(name=>f.pin(name));
  const bodies=f.reader.readPinned(inputs);
  assert.deepEqual(bodies,inputs.map(p=>f.git('show',p.commit+':'+p.path)));
  assert.equal(f.calls.length,1);assert.deepEqual(f.calls[0],['--literal-pathspecs','ls-tree','-z',f.version,'--',...inputs.map(p=>p.path)]);
  assert.equal(f.batches.length,3);
  for(const p of inputs)assert.deepEqual(f.reader.inventory.get(p.commit+':'+p.path),{...p,whole_body_consumed:true});
});

test('only an already-loaded tree is reused and duplicate requests return independent mutable bodies',t=>{
  const f=batchFixture(t),p=f.pin('dir/ordinary');f.reader.treeRoute(p.path);
  const bodies=f.reader.readPinned([p,p]);assert.deepEqual(bodies,[Buffer.from('one'),Buffer.from('one')]);
  bodies[0][0]=0;assert.equal(bodies[1].toString(),'one');
  assert.equal(f.reader.readPinned([p])[0].toString(),'one');
  assert.equal(f.calls.length,1,'No new tree preload or path process');
  assert.equal(f.batches.filter(call=>call.args[1]==='--batch').length,2,'Every batch consumes fresh whole bytes');
  const fresh=new ImmutableReader(f.root,f.version);let reads=0;const batch=fresh.gitBatch.bind(fresh);
  fresh.gitBatch=(...args)=>{reads++;return batch(...args);};
  assert.equal(fresh.readPinned([p])[0].toString(),'one');assert.equal(reads,3);
});

test('missing original uses only an exact current alias and rechecks after a real fetch',t=>{
  const f=batchFixture(t),p=f.pin('dir/ordinary'),remote=path.join(f.root,'foreign');fs.mkdirSync(remote);
  const git=(...args)=>execFileSync('git',['-c','user.name=Foreign fixture','-c','user.email=foreign@example.invalid','-C',remote,...args],{stdio:['ignore','pipe','pipe']});
  git('init','-q');fs.mkdirSync(path.join(remote,'dir'));fs.writeFileSync(path.join(remote,p.path),'two');git('add','.');git('commit','-qm','Different original');
  const original=git('rev-parse','HEAD').toString().trim(),historical={...p,commit:original};
  assert.equal(f.reader.readPinned([historical])[0].toString(),'one');
  f.git('fetch','--no-tags',remote,original);
  assert.throws(()=>f.reader.readPinned([historical]),/mode\/OID\/size or historical alias changed/);
  const absent={...p,path:'absent',commit:'0'.repeat(40)};
  assert.throws(()=>f.reader.readPinned([absent]),/Missing whole ordinary/);
});

test('available original missing its path cannot fall back; changed versions authenticate independently',t=>{
  const f=batchFixture(t),old=f.version,p=f.pin('dir/ordinary');
  fs.writeFileSync(path.join(f.root,p.path),'two');fs.writeFileSync(path.join(f.root,'new-file'),'new');f.git('add','.');f.git('commit','-qm','New candidate');
  const newer=f.git('rev-parse','HEAD').toString().trim(),newPin=f.pin(p.path,newer),newFile=f.pin('new-file',newer);
  f.reader.version=newer;
  assert.deepEqual(f.reader.readPinned([p,newPin]).map(b=>b.toString()),['one','two']);
  assert.throws(()=>f.reader.readPinned([{...newFile,commit:old}]),/Missing whole ordinary/);
  assert.throws(()=>f.reader.readPinned([{...p,commit:newer}]),/mode\/OID\/size or historical alias changed/);
  assert.throws(()=>f.reader.readPinned([{...p,mode:'100755'}]),/mode\/OID\/size/);
  assert.throws(()=>f.reader.readPinned([{...p,bytes:p.bytes+1}]),/mode\/OID\/size/);
  assert.throws(()=>f.reader.readPinned([{...p,sha256:'0'.repeat(64)}]),/Whole immutable input differs/);
  assert.throws(()=>f.reader.readPinned([{...p,commit:'HEAD'}]),/Incomplete immutable read pin/);
  assert.throws(()=>f.reader.readPinned([{...p,path:'../outside'}]),/Incomplete immutable read pin/);
});

for(const name of ['dir','link','submodule'])test('batch refuses actual nonordinary tree entry '+name,t=>{
  const f=batchFixture(t),p={...f.pin('dir/ordinary'),path:name};
  assert.throws(()=>f.reader.readPinned([p]),/Require exact whole ordinary Git batch input/);
  assert.equal(f.reader.inventory.size,0);
});

for(const stage of ['commit','path','size','body'])test('batch rejects malformed, truncated, duplicate and unexpected '+stage+' responses',t=>{
  const f=batchFixture(t),pins=['dir/ordinary','executable'].map(name=>f.pin(name));
  const alterations=stage==='body'?[
    b=>Buffer.concat([Buffer.from('f'.repeat(40)),b.subarray(40)]),
    b=>Buffer.from(b.toString().replace(' blob ',' tree ')),
    b=>Buffer.from(b.toString().replace(' blob 3\n',' blob 4\n')),
    b=>b.subarray(0,b.length-2),
    b=>{const c=Buffer.from(b);c[c.indexOf(10)+1]^=1;return c;},
    b=>Buffer.concat([b,b]),
    b=>Buffer.concat([b,Buffer.from('unexpected\n')])
  ]:[
    b=>Buffer.from('malformed'+(stage==='path'?'\0':'\n')),
    b=>b.subarray(0,b.length-1),
    b=>Buffer.concat([b,b]),
    b=>Buffer.concat([b,Buffer.from('unexpected'+(stage==='path'?'\0':'\n'))]),
    b=>Buffer.from(b.toString().replace(/[a-f0-9]{40}/,'f'.repeat(40)))
  ];
  for(const alter of alterations){
    const reader=new ImmutableReader(f.root,f.version),git=reader.git.bind(reader),batch=reader.gitBatch.bind(reader);
    reader.git=(...args)=>{const result=git(...args);return stage==='path'?alter(result):result;};
    reader.gitBatch=(args,input,maxBuffer)=>{
      const result=batch(args,input,maxBuffer),current=args[1]==='--batch'?'body':input.includes('^{commit}')?'commit':'size';
      return stage===current?alter(result):result;
    };
    assert.throws(()=>reader.readPinned(pins),/immutable|whole ordinary|historical alias/i,stage);
    assert.ok([...reader.inventory.values()].every(p=>!p.whole_body_consumed),'No failed batch claims consumption');
  }
});

test('Git batch nonzero exit and malformed stdout refuse despite diagnostics',t=>{
  const f=batchFixture(t),script=path.join(f.root,'failed-git');
  fs.writeFileSync(script,'#!/bin/sh\ncat >/dev/null\nprintf "partial\\n"\nexit 1\n');fs.chmodSync(script,0o755);
  const reader=new ImmutableReader(f.root,f.version,{gitExecutable:script});
  assert.throws(()=>reader.readPinned([f.pin('dir/ordinary')]),/Incomplete immutable Git batch/);
  fs.writeFileSync(script,'#!/bin/sh\ncat >/dev/null\nprintf "partial\\n"\nprintf "diagnostic\\n" >&2\n');
  assert.throws(()=>reader.readPinned([f.pin('dir/ordinary')]),/Invalid immutable commit batch/);
  assert.equal(reader.inventory.size,0);
});

test('actual successful Git diagnostics do not consume the exact stdout budget or waive pins',t=>{
  const f=batchFixture(t),p=f.pin('dir/ordinary');
  f.git('repack','-ad');f.git('prune-packed');
  const absent=path.join(f.root,'unavailable-optional-alternate');
  fs.writeFileSync(path.join(f.root,'.git/objects/info/alternates'),absent+'\n');
  const probe=spawnSync('git',['--no-lazy-fetch','-C',f.root,'cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],
    {input:f.version+'^{commit}\n',encoding:'utf8'});
  assert.equal(probe.status,0);assert.match(probe.stdout,new RegExp('^'+f.version+' commit [0-9]+\\n$'));
  assert.ok(probe.stderr.includes(absent));assert.ok(Buffer.byteLength(probe.stderr)>128);
  assert.deepEqual(f.reader.readPinned([p]),[Buffer.from('one')]);
  assert.deepEqual(f.reader.inventory.get(f.version+':'+p.path),{...p,whole_body_consumed:true});
  const rejected=new ImmutableReader(f.root,f.version);
  assert.throws(()=>rejected.readPinned([{...p,sha256:'0'.repeat(64)}]),/Whole immutable input differs/);
  assert.ok([...rejected.inventory.values()].every(pin=>!pin.whole_body_consumed));
});

test('actual Git command and spawn failures still refuse before consumption',t=>{
  const f=batchFixture(t);
  assert.throws(()=>f.reader.gitBatch(['cat-file','--invalid-batch-mode'],'',128),/Incomplete immutable Git batch/);
  assert.equal(f.reader.inventory.size,0);
  const missing=new ImmutableReader(f.root,f.version,{gitExecutable:path.join(f.root,'absent-git')});
  assert.throws(()=>missing.readPinned([f.pin('dir/ordinary')]),{code:'ENOENT'});
  assert.equal(missing.inventory.size,0);
});

test('successful command with oversized stdout still fails the original response bound',t=>{
  const f=batchFixture(t),script=path.join(f.root,'oversized-git');
  fs.writeFileSync(script,'#!/bin/sh\ncat >/dev/null\nprintf "%0130d" 0\n');fs.chmodSync(script,0o755);
  const reader=new ImmutableReader(f.root,f.version,{gitExecutable:script});
  assert.throws(()=>reader.readPinned([f.pin('dir/ordinary')]),{code:'ENOBUFS'});
  assert.equal(reader.inventory.size,0);
});

test('transport chunking accepts a larger complete pin list without an aggregate count cap',t=>{
  const f=batchFixture(t),p=f.pin('dir/ordinary'),pins=Array.from({length:600},()=>p);
  const bodies=f.reader.readPinned(pins);assert.equal(bodies.length,600);assert.ok(bodies.every(b=>b.toString()==='one'));
  assert.equal(f.batches.filter(call=>call.args[1]==='--batch').length,3);
});

test('batch keeps literal tab/newline paths and authenticates an empty ordinary blob',t=>{
  const f=batchFixture(t),name='literal\tline\n[2]';fs.writeFileSync(path.join(f.root,name),'');
  f.git('add','.');f.git('commit','-qm','Empty literal path');const version=f.git('rev-parse','HEAD').toString().trim();
  const p=f.pin(name,version);assert.equal(p.bytes,0);
  const bodies=f.reader.readPinned([p]);assert.deepEqual(bodies,[Buffer.alloc(0)]);
  assert.equal(f.reader.inventory.get(version+':'+name).sha256,hash(Buffer.alloc(0)));
});

test('an actually missing blob fails whole size authentication without claiming consumption',t=>{
  const f=batchFixture(t),p=f.pin('dir/ordinary');
  fs.unlinkSync(path.join(f.root,'.git','objects',p.git_blob_oid.slice(0,2),p.git_blob_oid.slice(2)));
  assert.throws(()=>f.reader.readPinned([p]),/Invalid immutable blob size batch|Incomplete immutable Git batch/);
  assert.equal(f.reader.inventory.size,0);
});


// A real promisor remote is essential here: an ordinary repository reports a
// missing commit quietly and cannot reproduce the hosted availability failure.
function promisorFixture(t,{populated=false}={}) {
  const f=batchFixture(t),remote=path.join(f.root,'.git','promisor.git');
  const executable=execFileSync('which',['git'],{encoding:'utf8'}).trim();
  if(populated)execFileSync(executable,['clone','--bare','--quiet','--no-local',f.root,remote]);
  else execFileSync(executable,['init','--bare','--quiet',remote]);
  execFileSync(executable,['--git-dir',remote,'config','uploadpack.allowAnySHA1InWant','true']);
  execFileSync(executable,['--git-dir',remote,'config','uploadpack.allowFilter','true']);
  f.git('config','extensions.partialClone','origin');
  f.git('config','remote.origin.url',remote);f.git('config','remote.origin.promisor','true');
  f.git('config','remote.origin.partialclonefilter','blob:none');
  const trace=path.join(f.root,'.git','reader-git.trace'),wrapper=path.join(f.root,'.git','traced-git');
  fs.writeFileSync(wrapper,`#!/bin/sh\nGIT_NO_LAZY_FETCH=0 GIT_TRACE=${JSON.stringify(trace)} exec ${JSON.stringify(executable)} "$@"\n`,{mode:0o755});
  f.reader.gitExecutable=wrapper;
  const tracing=()=>fs.existsSync(trace)?fs.readFileSync(trace,'utf8'):'';
  return {...f,remote,executable,trace,wrapper,tracing};
}

test('real promisor missing original never invokes remote transport before exact current alias admission',t=>{
  const f=promisorFixture(t),p={...f.pin('dir/ordinary'),commit:'77be56dd849d1351b82f0e79d7d306c1080b2562'};
  const old=spawnSync(f.wrapper,['-C',f.root,'cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],
    {input:p.commit+'^{commit}\n',encoding:'utf8'});
  assert.equal(old.status,0);assert.equal(old.stdout,p.commit+'^{commit} missing\n');
  assert.match(old.stderr,/not our ref/);assert.match(f.tracing(),/fetch .*origin|upload-pack/);
  fs.writeFileSync(f.trace,'');
  assert.equal(f.reader.readPinned([p])[0].toString(),'one');
  assert.doesNotMatch(f.tracing(),/fetch .*origin|upload-pack/,'The real remote helper must not be invoked');
  assert.deepEqual(f.reader.inventory.get(f.version+':'+p.path),{...p,commit:f.version,whole_body_consumed:true});
  assert.equal(f.reader.inventory.has(p.commit+':'+p.path),false,'Do not fabricate historical consumption');
  for(const altered of [{...p,mode:'100755'},{...p,bytes:p.bytes+1},{...p,git_blob_oid:'f'.repeat(40)},
    {...p,sha256:'0'.repeat(64)},{...p,path:'missing'}]){
    const reader=new ImmutableReader(f.root,f.version,{gitExecutable:f.wrapper});
    assert.throws(()=>reader.readPinned([altered]),/historical alias changed|Whole immutable input differs|Missing whole ordinary/);
    assert.ok([...reader.inventory.values()].every(row=>!row.whole_body_consumed));
  }
  assert.doesNotMatch(f.tracing(),/fetch .*origin|upload-pack/);
});

test('promisor local original retains precedence over changed current bytes and a missing original path never falls back',t=>{
  const f=promisorFixture(t),original=f.version,p=f.pin('dir/ordinary');
  fs.writeFileSync(path.join(f.root,p.path),'two');fs.writeFileSync(path.join(f.root,'new-path'),'new');
  f.git('add','.');f.git('commit','-qm','Changed current alias');
  const current=f.git('rev-parse','HEAD').toString().trim();f.reader.version=current;
  assert.equal(f.reader.readPinned([p])[0].toString(),'one');
  assert.equal(f.reader.inventory.get(original+':'+p.path).commit,original);
  const currentPin=f.pin(p.path,current),newPin=f.pin('new-path',current);
  assert.throws(()=>f.reader.readPinned([{...currentPin,commit:original}]),/historical alias changed/);
  assert.throws(()=>f.reader.readPinned([{...newPin,commit:original}]),/Missing whole ordinary/);
  assert.doesNotMatch(f.tracing(),/fetch .*origin|upload-pack/);
});

test('nonfetching availability leaves actual missing-body promisor acquisition and authentication enabled',t=>{
  const f=promisorFixture(t,{populated:true}),p=f.pin('dir/ordinary');
  fs.unlinkSync(path.join(f.root,'.git','objects',p.git_blob_oid.slice(0,2),p.git_blob_oid.slice(2)));
  assert.equal(f.reader.readPinned([p])[0].toString(),'one');
  assert.match(f.tracing(),/fetch .*origin|upload-pack/,'The actual body still uses ordinary authenticated acquisition');
  assert.equal(f.reader.inventory.get(p.commit+':'+p.path).whole_body_consumed,true);
  assert.throws(()=>f.reader.readPinned([{...p,sha256:'0'.repeat(64)}]),/Whole immutable input differs/);
});

test('promisor missing-body failure is not reinterpreted as an unavailable original',t=>{
  const f=promisorFixture(t),p=f.pin('dir/ordinary');
  fs.unlinkSync(path.join(f.root,'.git','objects',p.git_blob_oid.slice(0,2),p.git_blob_oid.slice(2)));
  assert.throws(()=>f.reader.readPinned([p]),/Incomplete immutable Git batch|Invalid immutable blob size batch/);
  assert.match(f.tracing(),/fetch .*origin|upload-pack/);
  assert.ok([...f.reader.inventory.values()].every(row=>!row.whole_body_consumed));
});

test('remote-only original uses an exact alias, then rechecks the original after explicit acquisition',t=>{
  const f=promisorFixture(t,{populated:true});
  const remote=(args,input)=>execFileSync(f.executable,['--git-dir',f.remote,...args],{input,encoding:'utf8'}).trim();
  const blob=remote(['hash-object','-w','--stdin'],'different original');
  const dir=remote(['mktree'],`100644 blob ${blob}\tordinary\n`);
  const tree=remote(['mktree'],`040000 tree ${dir}\tdir\n`);
  const original=remote(['-c','user.name=Reader Test','-c','user.email=reader@example.invalid','commit-tree',tree], 'Remote original\n');
  const p={...f.pin('dir/ordinary'),commit:original};
  assert.equal(f.reader.readPinned([p])[0].toString(),'one');
  assert.doesNotMatch(f.tracing(),/fetch .*origin|upload-pack/);
  assert.equal(f.reader.inventory.has(original+':'+p.path),false);
  f.git('fetch','--quiet','--no-tags',f.remote,original);
  assert.throws(()=>f.reader.readPinned([p]),/historical alias changed/);
  assert.ok(!f.reader.inventory.get(original+':'+p.path).whole_body_consumed);
});
