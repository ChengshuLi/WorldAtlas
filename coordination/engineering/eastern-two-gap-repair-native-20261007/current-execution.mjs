// Package-issued current code custody, separate from immutable scientific lineage.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const CAP=32*1024*1024, TOTAL=256*1024*1024;
const ENTRY='scripts/native-ownership/validate-build-context-stage.mjs';
const SELF='coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs';
const brands=new WeakMap();
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const oid=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const safe=p=>typeof p==='string'&&!path.isAbsolute(p)&&!p.includes('\\')&&p.split('/').every(x=>x&&x!=='.'&&x!=='..');
function body(root,p){
 assert(safe(p)&&path.isAbsolute(root)&&fs.realpathSync(root)===root);
 const file=path.join(root,p),stat=fs.lstatSync(file);
 assert(stat.isFile()&&fs.realpathSync(file)===file&&stat.size<=CAP,'Current execution source must be ordinary and bounded');
 const fd=fs.openSync(file,'r');let raw;
 try{assert.equal(fs.fstatSync(fd).size,stat.size);const buffer=Buffer.alloc(stat.size+1);let offset=0;
  while(offset<buffer.length){const n=fs.readSync(fd,buffer,offset,buffer.length-offset,null);if(!n)break;offset+=n;}
  assert.equal(offset,stat.size,'Actual current source EOF changed');assert.equal(fs.readSync(fd,Buffer.alloc(1),0,1,null),0);raw=buffer.subarray(0,offset);
 }finally{fs.closeSync(fd);}
 return {raw,mode:(stat.mode&0o111)?'100755':'100644'};
}
const allowedEntries=new Set(['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs','scripts/build-cloudflare-inner.mjs','coordination/engineering/eastern-two-gap-repair-native-20261007/integration-producer.mjs']);
export function currentExecutionClosure(root,entry='scripts/build-static-inner.mjs'){
 assert(allowedEntries.has(entry),'Unsupported actual execution entry');
 const entries=[ENTRY,SELF,'scripts/package-build.mjs',entry];
 const names=new Set(['package.json','.github/package-inputs.json']);
 let admitted=0;
 const admit=p=>{assert(safe(p));const file=path.join(root,p),stat=fs.lstatSync(file);assert(stat.isFile()&&fs.realpathSync(file)===file&&stat.size<=CAP);admitted+=stat.size;assert(admitted<=TOTAL,'Current import closure exceeds aggregate before read');};
 for(const p of names)admit(p);
 function visit(p){
  assert(safe(p));if(names.has(p))return;names.add(p);assert(names.size<=512);admit(p);
  const {raw}=body(root,p);
  for(const m of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))
   if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));
 }
 for(const entry of entries)visit(entry);
 assert(names.size<=512);return [...names].sort();
}
function runtime(){
 const executable=fs.realpathSync(process.execPath),stat=fs.statSync(executable),hash=createHash('sha256'),fd=fs.openSync(executable,'r');
 try{const chunk=Buffer.alloc(1024*1024);let n,total=0;while((n=fs.readSync(fd,chunk,0,chunk.length,null))){hash.update(chunk.subarray(0,n));total+=n;}assert.equal(total,stat.size);}finally{fs.closeSync(fd);}
 return {executable,mode:stat.mode&0o777,bytes:stat.size,sha256:hash.digest('hex'),version:process.version,versions:process.versions,platform:process.platform,arch:process.arch,exec_argv:process.execArgv};
}
function plain(){assert.equal(process.execArgv.length,0);assert(!process.env.NODE_OPTIONS?.trim()&&!process.env.NODE_PATH?.trim(),'Current package execution must use plain Node');}
function fingerprint(value){return sha(Buffer.from(JSON.stringify(value)));}
function verifySource(record){
 assert.equal(fs.realpathSync(record.source_root),record.source_root,'Wrong actual source root');
 const git=args=>execFileSync('git',['-C',record.source_root,...args],{maxBuffer:CAP,encoding:'utf8'}).trim();
 assert.equal(git(['rev-parse','HEAD']),record.source_commit,'Actual source HEAD changed');
 assert.equal(git(['rev-parse','HEAD^{tree}']),record.source_tree,'Actual source tree changed');
 for(const pin of record.files)assert.equal(git(['ls-tree',record.source_commit,'--',pin.path]),`${pin.mode} blob ${pin.git_blob}\t${pin.path}`,'Source Git object binding changed');
 verifyFiles(record.source_root,record.files,record.entry_point);
}
function verifyFiles(root,files,entry){
 assert(Array.isArray(files)&&files.length>0&&files.length<=512);let total=0;const names=new Set();
 for(const pin of files){assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&pin.bytes<=CAP);total+=pin.bytes;assert(total<=TOTAL,'Current execution aggregate exceeds cap before reads');}total=0;
 for(const pin of files){
  assert(safe(pin.path)&&!names.has(pin.path));names.add(pin.path);
  assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&pin.bytes<=CAP&&['100644','100755'].includes(pin.mode));
  assert(/^[a-f0-9]{40}$/.test(pin.git_blob)&&/^[a-f0-9]{64}$/.test(pin.sha256));
  const {raw,mode}=body(root,pin.path);assert.equal(raw.length,pin.bytes);assert.equal(mode,pin.mode);assert.equal(sha(raw),pin.sha256);assert.equal(oid(raw),pin.git_blob);
  total+=raw.length;assert(total<=TOTAL);
 }
 assert.deepEqual(files.map(p=>p.path),currentExecutionClosure(root,entry));return total;
}
export function issueCurrentExecution({source,stage,entry='scripts/build-static-inner.mjs'}){
 plain();source=fs.realpathSync(source);stage=fs.realpathSync(stage);
 const git=args=>execFileSync('git',['-C',source,...args],{maxBuffer:CAP,encoding:'utf8'}).trim();
 const commit=git(['rev-parse','HEAD']),tree=git(['rev-parse','HEAD^{tree}']);
 assert(/^[a-f0-9]{40}$/.test(commit)&&/^[a-f0-9]{40}$/.test(tree));
 const files=currentExecutionClosure(source,entry).map(p=>{
  const {raw,mode}=body(source,p),row=git(['ls-tree',commit,'--',p]);
  assert.equal(row,`${mode} blob ${oid(raw)}\t${p}`,'Current executing body differs from immutable actual checkout');
  const copied=body(stage,p);assert.equal(copied.mode,mode);assert(copied.raw.equals(raw),'Materialized execution body differs from source');
  return {path:p,mode,bytes:raw.length,sha256:sha(raw),git_blob:oid(raw)};
 });
 const record={version:1,issue:1295,kind:'package-issued-current-execution',entry_point:entry,source_root:source,source_commit:commit,source_tree:tree,stage_root:stage,runtime:runtime(),files};
 assert.equal(git(['rev-parse','HEAD']),commit,'Checkout changed while issuing execution binding');
 verifyFiles(stage,files,entry);return record;
}
export function authenticateCurrentExecution(record,{root,executingRoot=root,sourceRoot}){
 root=fs.realpathSync(root);executingRoot=fs.realpathSync(executingRoot);
 assert.equal(record.source_root,fs.realpathSync(sourceRoot),'Wrong independently supplied source root');
 plain();assert.equal(record?.version,1);assert.equal(record.issue,1295);assert.equal(record.kind,'package-issued-current-execution');
 assert(/^[a-f0-9]{40}$/.test(record.source_commit)&&/^[a-f0-9]{40}$/.test(record.source_tree));
 assert.equal(record.stage_root,fs.realpathSync(root));assert.deepEqual(record.runtime,runtime());
 verifySource(record);
 verifyFiles(root,record.files,record.entry_point);verifyFiles(executingRoot,record.files,record.entry_point);
 brands.set(record,{root:fs.realpathSync(root),executingRoot:fs.realpathSync(executingRoot),fingerprint:fingerprint(record)});return record;
}
export function requireCurrentExecution(record){
 const retained=brands.get(record);assert(retained,'Current execution must have an authenticated package-boundary binding');
 assert.equal(fingerprint(record),retained.fingerprint,'Current execution receipt changed');
 plain();assert.deepEqual(record.runtime,runtime());verifySource(record);verifyFiles(retained.root,record.files,record.entry_point);verifyFiles(retained.executingRoot,record.files,record.entry_point);
 return record;
}
export function readPackageCurrentExecution(root){
 const name=process.env.WORLDATLAS_CURRENT_EXECUTION_PATH,expected=process.env.WORLDATLAS_CURRENT_EXECUTION_SHA256;
 assert.equal(name,'.cache/current-context-execution.json','Missing actual package-issued current execution');
 assert(/^[a-f0-9]{64}$/.test(expected??''));const {raw}=body(fs.realpathSync(root),name);assert.equal(sha(raw),expected);
 return authenticateCurrentExecution(JSON.parse(raw),{root,sourceRoot:process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT,executingRoot:path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..')});
}
