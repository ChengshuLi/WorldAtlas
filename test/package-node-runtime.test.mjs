import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {installedNodeIdentity,effectiveNodeDependencyInventory,validateNodeIdentity} from '../scripts/package-node-runtime.mjs';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
const generator=path.resolve(path.dirname(fs.realpathSync(process.execPath)),
  '../lib/node_modules/npm/node_modules/node-gyp/gyp/gyp_main.py');
const packageName='atlas-native-path-control',packagePath='node_modules/'+packageName;
const makePath=packagePath+'/build/Makefile';
const compatibility=identity=>({node:identity.node,dependencies:{files:identity.dependencies.files,
  bytes:identity.dependencies.bytes,sha256:identity.dependencies.sha256}});
function write(root,name,value){const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,value);return file;}
function fixture(t){
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-node-runtime-'));t.after(()=>fs.rmSync(temp,{recursive:true,force:true}));
  const roots=['original','candidate+longer'].map(name=>path.join(temp,name));
  const pkg=JSON.stringify({name:packageName,version:'1.0.0',main:'index.js',
    scripts:{install:`python3 ${generator} binding.gyp -f make --depth=. -Dmodule_root_dir=$PWD --generator-output=build`}});
  const binding=JSON.stringify({targets:[{target_name:'control',type:'none',sources:['control.cc']}]});
  const lock=JSON.stringify({lockfileVersion:3,packages:{[packagePath]:{version:'1.0.0',hasInstallScript:true,
    resolved:'file:native.tgz',integrity:'sha512-test-fixture-identical-in-both-roots'}}});
  for(const root of roots){
    write(root,'package-lock.json',lock);write(root,packagePath+'/package.json',pkg);
    write(root,packagePath+'/binding.gyp',binding);write(root,packagePath+'/index.js','module.exports=42;\n');
    write(root,packagePath+'/control.cc','int unchanged_runtime_source=42;\n');
    // Only the actual installed make generator runs, with inert type:none.
    // No npm install, native compile, package build, network or emitted JS runs.
    execFileSync('python3',[generator,'binding.gyp','-f','make','--depth=.',
      '-Dmodule_root_dir='+path.join(root,packagePath),'-Dlibrary=shared_library','-Dvisibility=default',
      '-Dnode_lib_file=/opt/node/include/<(target_arch)/node.lib','--generator-output=build','--no-parallel','-Goutput_dir=.'],
      {cwd:path.join(root,packagePath),stdio:'pipe',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
  }
  return {roots,temp};
}
function identities(roots){return roots.map(root=>installedNodeIdentity(root));}
function assertDifferent(roots){const [a,b]=identities(roots);assert.notDeepEqual(compatibility(a),compatibility(b));return [a,b];}
function edit(root,relative,change){const file=path.join(root,relative);fs.writeFileSync(file,change(fs.readFileSync(file)));}

test('actual gyp regeneration in two physical package roots has exact raw evidence and equal effective identity',t=>{
  const {roots}=fixture(t),[a,b]=identities(roots);
  if(!a.dependencies.inventory.some(row=>row.normalization)){
    assert.notDeepEqual(compatibility(a),compatibility(b));
    assert.equal(a.dependencies.sha256,a.dependencies.raw_sha256);
    assert.equal(b.dependencies.sha256,b.dependencies.raw_sha256);
    t.diagnostic('Installed generator is outside reviewed normalization; exact-byte fallback is valid.');return;
  }
  assert.deepEqual(compatibility(a),compatibility(b));
  assert.deepEqual(effectiveNodeDependencyInventory(a),effectiveNodeDependencyInventory(b));
  assert.notEqual(a.dependencies.raw_sha256,b.dependencies.raw_sha256);
  assert.notEqual(a.dependencies.raw_bytes,b.dependencies.raw_bytes);
  const normalized=a.dependencies.inventory.filter(row=>row.normalization);
  assert.deepEqual(normalized.map(row=>row.path),[makePath]);
  assert.equal(normalized[0].normalization.field,'cmd_regen_makefile/-Dmodule_root_dir');
  assert.equal(normalized[0].normalization.physical_root,path.join(roots[0],packagePath));
  assert.equal(normalized[0].normalization.generator.files.length,4);
  for(const [index,identity]of [a,b].entries())for(const row of identity.dependencies.inventory){
    if(row.link!==undefined)continue;
    const raw=fs.readFileSync(path.join(roots[index],row.path));assert.equal(row.bytes,raw.length);assert.equal(row.sha256,sha(raw));
  }
  assert.equal(a.dependencies.sha256,sha(JSON.stringify(effectiveNodeDependencyInventory(a))));
});

test('JavaScript containing each installation root remains strict executable evidence',t=>{
  const {roots}=fixture(t);
  for(const root of roots)write(root,packagePath+'/index.js',`module.exports=${JSON.stringify(root)};\n`);
  const [a,b]=assertDifferent(roots);
  assert.equal(a.dependencies.inventory.find(row=>row.path===packagePath+'/index.js').effective,undefined);
});

test('path-like bytes inside a native binary and build directory remain exact',t=>{
  const {roots}=fixture(t);
  for(const root of roots)write(root,packagePath+'/build/Release/addon.node',Buffer.concat([Buffer.from([0x7f,0x45,0x4c,0x46,0]),Buffer.from(root)]));
  const [a]=assertDifferent(roots);
  assert.equal(a.dependencies.inventory.find(row=>row.path.endsWith('/addon.node')).effective,undefined);
});

test('an executable-mode Makefile is never normalized even with generated provenance',t=>{
  const {roots}=fixture(t);for(const root of roots)fs.chmodSync(path.join(root,makePath),0o755);
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).normalization,undefined);
});

test('changed generated nonpath compiler settings cannot become equivalent',t=>{
  const {roots}=fixture(t);edit(roots[1],makePath,raw=>raw.toString().replace('CFLAGS.target ?= $(CPPFLAGS) $(CFLAGS)','CFLAGS.target ?= -DALTERED_BEHAVIOR'));
  assertDifferent(roots);
});

test('changed generated nonpath regeneration flags cannot become equivalent',t=>{
  const {roots}=fixture(t);edit(roots[1],makePath,raw=>raw.toString().replace(' "--depth=."',' "-Dchanged_feature=1" "--depth=."'));
  assertDifferent(roots);
});

test('unknown Makefile format and copied marker text fail closed to raw identity',t=>{
  const {roots}=fixture(t);
  for(const root of roots)edit(root,makePath,raw=>'# Unknown generator wrapper\n'+raw.toString());
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).effective,undefined);
});

test('path-like executable command tails are not accepted as regeneration fields',t=>{
  const {roots}=fixture(t);
  for(const root of roots)edit(root,makePath,raw=>raw.toString().replace(' binding.gyp\n',` binding.gyp; node ${root}/payload.js\n`));
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).normalization,undefined);
});

test('a second root occurrence in arbitrary executable Makefile content stays exact',t=>{
  const {roots}=fixture(t);
  for(const root of roots)edit(root,makePath,raw=>raw.toString().replace('MAKEFLAGS=-r\n',`MAKEFLAGS=-r\nEXECUTABLE_PAYLOAD=${root}/run\n`));
  assertDifferent(roots);
});

test('a module-root value referring to any different package is not normalized',t=>{
  const {roots}=fixture(t);
  for(const root of roots)edit(root,makePath,raw=>raw.toString().replace('-Dmodule_root_dir='+path.join(root,packagePath),'-Dmodule_root_dir='+path.join(root,'other-package')));
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).normalization,undefined);
});

test('same-named file outside actual package root cannot receive gyp normalization',t=>{
  const {roots}=fixture(t);
  for(const root of roots)write(root,packagePath+'/arbitrary/build/Makefile',fs.readFileSync(path.join(root,makePath)));
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path.includes('/arbitrary/')).effective,undefined);
});

test('absent install provenance or altered generator command stays exact',t=>{
  const {roots}=fixture(t);
  for(const root of roots){const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json')));delete lock.packages[packagePath].hasInstallScript;write(root,'package-lock.json',JSON.stringify(lock));}
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).normalization,undefined);
});

test('unknown generator path must not borrow the recognized generator identity',t=>{
  const {roots}=fixture(t);
  for(const root of roots)edit(root,makePath,raw=>raw.toString().replace(generator,path.join(root,'other-gyp.py')));
  const [a]=assertDifferent(roots);assert.equal(a.dependencies.inventory.find(row=>row.path===makePath).effective,undefined);
});

test('altering ordinary source or generated target instructions remains incompatible',t=>{
  const {roots}=fixture(t);edit(roots[1],packagePath+'/build/control.target.mk',raw=>raw.toString()+'\n# changed generated target semantics\n');assertDifferent(roots);
});

test('large runtime files are streamed exactly rather than excluded by metadata recognition budget',t=>{
  const {roots}=fixture(t),raw=Buffer.alloc(2*1024*1024,0x53);
  for(const root of roots)write(root,packagePath+'/large.node',raw);
  const [a,b]=identities(roots);assert.deepEqual(compatibility(a),compatibility(b));
  const row=a.dependencies.inventory.find(row=>row.path.endsWith('/large.node'));assert.equal(row.bytes,raw.length);assert.equal(row.sha256,sha(raw));
  const fd=fs.openSync(path.join(roots[1],packagePath+'/large.node'),'r+');fs.writeSync(fd,Buffer.from([0]),0,1,raw.length-1);fs.closeSync(fd);assertDifferent(roots);
});

test('internal symlinks are inventoried exactly and links escaping installation reject',t=>{
  const {roots}=fixture(t);
  for(const root of roots)fs.symlinkSync('index.js',path.join(root,packagePath+'/linked.js'));
  const [a,b]=identities(roots);assert.deepEqual(compatibility(a),compatibility(b));
  assert.deepEqual(a.dependencies.inventory.find(row=>row.path.endsWith('/linked.js')),{path:packagePath+'/linked.js',link:'index.js'});
  const link=path.join(roots[1],packagePath+'/linked.js');fs.unlinkSync(link);fs.symlinkSync(path.join(roots[0],packagePath+'/index.js'),link);
  assert.throws(()=>installedNodeIdentity(roots[1]),/link escapes installation/);
});


test('retained v2 evidence validates full rows and summaries, never aggregate-only compatibility',t=>{
  const identity=schemaIdentity();
  assert.equal(validateNodeIdentity(identity),identity);
  const mutations=[
    ['aggregate-only',value=>delete value.dependencies.inventory],
    ['wrong count',value=>value.dependencies.files++],
    ['wrong effective total',value=>value.dependencies.bytes++],
    ['wrong raw total',value=>value.dependencies.raw_bytes++],
    ['wrong raw hash',value=>value.dependencies.raw_sha256='0'.repeat(64)],
    ['wrong effective hash',value=>value.dependencies.sha256='0'.repeat(64)],
    ['missing member',value=>value.dependencies.inventory.pop()],
    ['duplicate member',value=>value.dependencies.inventory.push(value.dependencies.inventory[0])],
    ['unsorted members',value=>value.dependencies.inventory.reverse()],
    ['unsafe path',value=>value.dependencies.inventory[0].path='node_modules/../outside'],
    ['invalid raw digest',value=>value.dependencies.inventory[0].sha256='invalid'],
    ['unexplained effective descriptor',value=>value.dependencies.inventory.find(row=>row.path.endsWith('/index.js')).effective={bytes:1,sha256:'0'.repeat(64)}],
    ['unknown normalization method',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.kind='ignore-all-build-files'],
    ['wrong normalized field',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.field='CFLAGS.target'],
    ['wrong normalized byte delta',value=>value.dependencies.inventory.find(row=>row.normalization).effective.bytes++],
    ['unknown generator',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.generator.version='unknown'],
    ['altered generator source',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.generator.files[0].sha256='0'.repeat(64)],
    ['incomplete generator source',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.generator.files.pop()],
    ['unbound package provenance',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.package_manifest.sha256='0'.repeat(64)],
    ['unbound generator wrapper',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.generated_wrapper.bytes++],
    ['wrong physical root',value=>value.dependencies.inventory.find(row=>row.normalization).normalization.physical_root='/different/package'],
  ];
  for(const [label,mutate]of mutations){const value=structuredClone(identity);mutate(value);assert.throws(()=>validateNodeIdentity(value),undefined,label);}
});

test('recomputed summaries cannot authorize normalization on executable or native bytes',t=>{
  const identity=schemaIdentity(),value=structuredClone(identity);
  const row=value.dependencies.inventory.find(row=>row.normalization);row.mode='100755';
  const effective=effectiveNodeDependencyInventory(value),raw=value.dependencies.inventory.map(({effective,normalization,...item})=>item);
  value.dependencies.sha256=sha(JSON.stringify(effective));value.dependencies.raw_sha256=sha(JSON.stringify(raw));
  assert.throws(()=>validateNodeIdentity(value),/Ordinary generated metadata/);
});


test('atomic path replacement during a read cannot certify removed executable bytes',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-node-runtime-race-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const file=write(root,'node_modules/example/index.js','original executable bytes');
  const inode=fs.statSync(file).ino,originalRead=fs.readSync;let replaced=false;
  fs.readSync=function(fd,...args){
    const count=originalRead.call(fs,fd,...args);
    if(!replaced&&count&&fs.fstatSync(fd).ino===inode){
      replaced=true;fs.writeFileSync(file+'.replacement','modified executable bytes');fs.renameSync(file+'.replacement',file);
    }
    return count;
  };
  try{assert.throws(()=>installedNodeIdentity(root),/changed during observation/);}
  finally{fs.readSync=originalRead;}
  assert.equal(replaced,true);assert.equal(fs.readFileSync(file,'utf8'),'modified executable bytes');
});

// Retained synthetic-boundary evidence from the real reviewed gyp12.2 generator.
// Validator adverse controls remain deterministic if the host upgrades gyp;
// this fixture is never accepted as package producer authority.
function schemaIdentity(){return {
  "node": {
    "bytes": 125989464,
    "sha256": "bc17c508ffeed0ec622934f9b7fa72f8e78da65350e63c3eceb56fa688aa5e12"
  },
  "dependencies": {
    "files": 7,
    "bytes": 15291,
    "sha256": "84d2b6711bca0622084da00007eb000fe4e05d02e413f0010b83900183d25019",
    "raw_bytes": 15344,
    "raw_sha256": "db0219052fb6ccad01fa8a68d974ebce10ce0b623823821bb43fd80ab14144d8",
    "inventory": [
      {
        "path": "node_modules/atlas-native-path-control/binding.gyp",
        "bytes": 78,
        "sha256": "ea8b99023c021195106896a68c2ca025452101dfa79ad5ef5521207ed0528dc3",
        "mode": "100644"
      },
      {
        "path": "node_modules/atlas-native-path-control/build/Makefile",
        "bytes": 13304,
        "sha256": "ab16dfc53513b46d66514cb7157facccf54932895243499425e49f7e09e95946",
        "mode": "100644",
        "effective": {
          "bytes": 13251,
          "sha256": "39baed285f9460aaebec7c48c9284d3fef2911e0c2b0ee96e26b478baffcaaa6"
        },
        "normalization": {
          "kind": "node-gyp-make-regeneration-module-root-v1",
          "field": "cmd_regen_makefile/-Dmodule_root_dir",
          "physical_root": "/tmp/atlas-node-runtime-AX4Q1u/original/node_modules/atlas-native-path-control",
          "package_path": "node_modules/atlas-native-path-control",
          "generator": {
            "version": "12.2.0",
            "files": [
              {
                "path": "gyp/gyp_main.py",
                "bytes": 1250,
                "sha256": "80eb0a1948230c832f17bf99f31a8729d54044d80469cfe0fecace69e7ab66a6"
              },
              {
                "path": "gyp/pylib/gyp/generator/make.py",
                "bytes": 111764,
                "sha256": "0ce6c09023c2cf4fa48f2c5d17d0f6c96ff6debc44df5d8477bbee6eb33dc0ca"
              },
              {
                "path": "gyp/pylib/gyp/common.py",
                "bytes": 25313,
                "sha256": "cbbc59947402ff878a121a6d95034e8b04016486154502beb9f9b84c4b2d8db8"
              },
              {
                "path": "gyp/pylib/gyp/__init__.py",
                "bytes": 24653,
                "sha256": "a7333a360f53319d1992bc3d71a010ef5a02effb23b93ecfd8be75edf5716065"
              }
            ]
          },
          "package_manifest": {
            "path": "node_modules/atlas-native-path-control/package.json",
            "bytes": 301,
            "sha256": "ddd17917ab61b69855055829aefb8f9c56f9a489c98a9b77519beef5a80ce484"
          },
          "binding": {
            "path": "node_modules/atlas-native-path-control/binding.gyp",
            "bytes": 78,
            "sha256": "ea8b99023c021195106896a68c2ca025452101dfa79ad5ef5521207ed0528dc3"
          },
          "generated_wrapper": {
            "path": "node_modules/atlas-native-path-control/build/binding.Makefile",
            "bytes": 115,
            "sha256": "080a0672717a84a72a9c52ca45181c8ff4e88ff56f27ca941e03088850c81b00"
          }
        }
      },
      {
        "path": "node_modules/atlas-native-path-control/build/binding.Makefile",
        "bytes": 115,
        "sha256": "080a0672717a84a72a9c52ca45181c8ff4e88ff56f27ca941e03088850c81b00",
        "mode": "100644"
      },
      {
        "path": "node_modules/atlas-native-path-control/build/control.target.mk",
        "bytes": 1494,
        "sha256": "9854202dd2ef66f34c9326acc072d0324186e9374785aa6c3cadfc79fa7640a6",
        "mode": "100644"
      },
      {
        "path": "node_modules/atlas-native-path-control/control.cc",
        "bytes": 33,
        "sha256": "ada4d36d47e912cb79cec4af1240a782efacfe1634fe1a653ca8a8743343f19b",
        "mode": "100644"
      },
      {
        "path": "node_modules/atlas-native-path-control/index.js",
        "bytes": 19,
        "sha256": "d8ba574f0d3f0f0f6efee8cb42cd4f197a83fc6e4bc8a76a1bc69f409cdf4a57",
        "mode": "100644"
      },
      {
        "path": "node_modules/atlas-native-path-control/package.json",
        "bytes": 301,
        "sha256": "ddd17917ab61b69855055829aefb8f9c56f9a489c98a9b77519beef5a80ce484",
        "mode": "100644"
      }
    ]
  }
};}
