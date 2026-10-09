// Private execution authority for the actual model-reader checkout entry.
// This is not a package receipt or a historical scientific validation brand.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const ENTRY = 'scripts/run-integration-tests.mjs';
const CAP = 32 * 1024 * 1024;
const authenticated = new WeakMap();
const sha = raw => createHash('sha256').update(raw).digest('hex');
const same = (a,b) => ['dev','ino','mode','size','mtimeMs','ctimeMs'].forEach(k=>assert.equal(a[k],b[k]));
function ordinary(file, installed=false) {
  for(let p=file;;p=path.dirname(p)){assert(!fs.lstatSync(p).isSymbolicLink());if(p===path.dirname(p))break;}
  const stat=fs.lstatSync(file);assert(stat.isFile());
  assert(Number.isSafeInteger(stat.size)&&stat.size>0&&(installed||stat.size<=CAP));
  if(installed){assert.equal(fs.realpathSync(file),file);assert((stat.mode&73)!==0,'Installed executable requires execution permission');}
  else assert([420,493].includes(stat.mode&511));return stat;
}
function body(file,{installed=false,raw=false}={}) {
  const before=ordinary(file,installed),fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
  const hash=createHash('sha256'),chunk=Buffer.allocUnsafe(1024*1024);let total=0,contents;
  try{same(before,fs.fstatSync(fd));if(raw){contents=fs.readFileSync(fd);hash.update(contents);total=contents.length;}
    else{let n;while((n=fs.readSync(fd,chunk,0,chunk.length,null))){hash.update(chunk.subarray(0,n));total+=n;}}
    same(before,fs.fstatSync(fd));}finally{fs.closeSync(fd);}
  same(before,fs.lstatSync(file));assert.equal(total,before.size);
  return {mode:installed?(before.mode&4095):((before.mode&511)===493?'100755':'100644'),bytes:total,sha256:hash.digest('hex'),...(raw?{raw:contents}:{})};
}
export function authenticateInstalledCheckoutExecutable(file) {
  return body(file,{installed:true});
}
function actualEntry(root) {
  assert.equal(fs.realpathSync(root),root);
  assert.equal(path.resolve(process.argv[1]),path.join(root,ENTRY),'Actual model-reader runner required');
  assert.equal(process.env.INTEGRATION_PROFILE,'full');
  assert(['1','2'].includes(process.env.INTEGRATION_SHARD),'Only declared prepared/model-reader shards install checkout products');
  assert(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH&&process.execArgv.length===0,'Plain checkout execution required');
}
export function checkoutExecutionClosure(root) {
  const names=new Set(['package.json']);ordinary(path.join(root,'package.json'));
  function visit(relative){
    assert(!path.isAbsolute(relative)&&!relative.includes('\\')&&relative.split('/').every(p=>p&&p!=='.'&&p!=='..'));
    if(names.has(relative))return;names.add(relative);assert(names.size<=512);
    const {raw}=body(path.join(root,relative),{raw:true});
    for(const match of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))
      if(match[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(relative),match[1])));
  }
  visit(ENTRY);return [...names].sort();
}
export function issueCheckoutExecution({root,admission}) {
  actualEntry(root);
  assert.equal(admission?.kind,'qualified-artifact-normal-package-stat-admission');
  assert.equal(admission.numerical_aggregate_cap_applied,false);
  assert(['darwin','linux'].includes(process.platform),'Declared checkout Git implementation required');
  // macOS /usr/bin/git is a launcher. Execute and authenticate the full
  // installed implementation directly; no PATH or launcher dispatch is used.
  const tool=fs.realpathSync(process.platform==='darwin'
    ? '/Library/Developer/CommandLineTools/usr/bin/git' : '/usr/bin/git');
  const toolPin=authenticateInstalledCheckoutExecutable(tool);
  const git=args=>execFileSync(tool,['-C',root,...args],{encoding:'utf8',maxBuffer:CAP}).trim();
  const commit=git(['rev-parse','HEAD']),tree=git(['rev-parse','HEAD^{tree}']);
  assert(/^[a-f0-9]{40}$/.test(commit)&&/^[a-f0-9]{40}$/.test(tree));
  const files=checkoutExecutionClosure(root).map(relative=>{
    const pin=body(path.join(root,relative),{raw:true});
    const oid=createHash('sha1').update(Buffer.from(`blob ${pin.bytes}\0`)).update(pin.raw).digest('hex');
    assert.equal(git(['ls-tree',commit,'--',relative]),`${pin.mode} blob ${oid}\t${relative}`);
    return {path:relative,mode:pin.mode,bytes:pin.bytes,sha256:pin.sha256,git_blob:oid};
  });
  const executable=fs.realpathSync(process.execPath),runtime=authenticateInstalledCheckoutExecutable(executable);
  const record={version:1,issue:1520,kind:'model-reader-checkout-execution',entry_point:ENTRY,profile:process.env.INTEGRATION_PROFILE,shard:Number(process.env.INTEGRATION_SHARD),
    source_root:root,stage_root:root,source_commit:commit,source_tree:tree,
    runtime:{executable,...runtime},tool:{executable:tool,...toolPin},files,admission};
  assert.equal(git(['rev-parse','HEAD']),commit);assert.deepEqual(authenticateInstalledCheckoutExecutable(tool),toolPin);
  authenticated.set(record,{root,fingerprint:sha(JSON.stringify(record))});return record;
}
export function requireCheckoutExecution(record) {
  const saved=authenticated.get(record);assert(saved,'Actual private model-reader execution required');
  actualEntry(saved.root);assert.equal(record.profile,process.env.INTEGRATION_PROFILE);assert.equal(record.shard,Number(process.env.INTEGRATION_SHARD));assert.equal(sha(JSON.stringify(record)),saved.fingerprint);
  assert.deepEqual(authenticateInstalledCheckoutExecutable(record.runtime.executable),Object.fromEntries(Object.entries(record.runtime).filter(([k])=>k!=='executable')));
  assert.deepEqual(authenticateInstalledCheckoutExecutable(record.tool.executable),Object.fromEntries(Object.entries(record.tool).filter(([k])=>k!=='executable')));
  const commit=execFileSync(record.tool.executable,['-C',saved.root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();assert.equal(commit,record.source_commit);
  assert.deepEqual(checkoutExecutionClosure(saved.root),record.files.map(p=>p.path));
  for(const pin of record.files){const actual=body(path.join(saved.root,pin.path));for(const key of ['mode','bytes','sha256'])assert.equal(actual[key],pin[key]);}
  return record;
}
