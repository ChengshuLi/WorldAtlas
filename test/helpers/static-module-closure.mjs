// Test-fixture discovery only. Parse eager ESM imports without linking/evaluating
// source. Static JSON modules are validated leaves; dynamic imports and other
// non-module operands remain explicit fixture roles.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const self=fileURLToPath(import.meta.url);
export function staticModuleClosure(root,entries) {
  const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  return JSON.parse(execFileSync(process.execPath,
    ['--experimental-vm-modules',self,root,JSON.stringify(entries)],
    {encoding:'utf8',env,timeout:20000,maxBuffer:4*1024*1024,stdio:['ignore','pipe','pipe']}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===self) {
  const root=fs.realpathSync(process.argv[2]),pending=JSON.parse(process.argv[3]),seen=new Set();
  assert(Array.isArray(pending)&&pending.length>0,'Nonempty static module entries required');
  while(pending.length) {
    const name=pending.pop();
    assert(typeof name==='string'&&/^[A-Za-z0-9_./-]+$/.test(name)&&
      !path.posix.isAbsolute(name)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'),
      'Static module path must stay inside the fixture root');
    if(seen.has(name))continue;
    const file=path.join(root,name);
    assert(fs.lstatSync(file).isFile()&&fs.realpathSync(file)===file,'Static fixture source must be ordinary');
    seen.add(name);
    const source=fs.readFileSync(file,'utf8');
    if(name.endsWith('.json')){JSON.parse(source);continue;}
    const module=new vm.SourceTextModule(source);
    for(const specifier of module.dependencySpecifiers) {
      if(specifier.startsWith('./')||specifier.startsWith('../'))pending.push(path.posix.normalize(path.posix.join(path.posix.dirname(name),specifier)));
      else assert(specifier.startsWith('node:'),'Unsupported external static fixture import: '+specifier);
    }
  }
  process.stdout.write(JSON.stringify([...seen].sort()));
}
