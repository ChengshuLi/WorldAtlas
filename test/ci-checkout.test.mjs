import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {integrationTestFiles} from '../scripts/run-integration-tests.mjs';
import {selectedDataCheckoutPatterns, fullCheckoutPatterns} from '../scripts/package-inputs.mjs';

const expectations = 'coordination/engineering/current/selected-delivery-expectations.json';
const definition = {version:1, inputs:['.github/package-inputs.json', 'research/geography/required/body.json',
  'coordination/engineering/required/body.bin', 'data/required/body.json'], optional_inputs:[],
  verification_paths:['research/geography/verified/body.json'], generated_outputs:[]};
const names = ['README.md', '.github/package-inputs.json', expectations,
  ...definition.inputs.slice(1), ...definition.verification_paths,
  'research/geography/required/body.json-sibling', 'research/geography/unconsumed/body.json',
  'coordination/engineering/unconsumed/body.bin', 'coordination/engineering/unconsumed/helper.py',
  'coordination/engineering/unconsumed/package.json', 'coordination/engineering/unconsumed/executable.bin',
  'data/unconsumed/body.json', 'data/regional-review/source/body.json', 'research/campaigns/source/body.json'];
const entries = () => new Map(names.map(name => [name, {path:name, type:'blob',
  mode:name.endsWith('/executable.bin') ? '100755' : '100644', sha:'a'.repeat(40)}]));

function checkout(patterns, files = names) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-stock-selection-'));
  const env = {...process.env, GIT_CONFIG_NOSYSTEM:'1', GIT_CONFIG_GLOBAL:os.devNull,
    GIT_NO_LAZY_FETCH:'1', GIT_TERMINAL_PROMPT:'0'};
  const git = (args, input) => execFileSync('git', ['-c','core.hooksPath='+os.devNull,
    '-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-C',directory,...args],
  {env, input, encoding:'utf8', stdio:['pipe','pipe','pipe']}).trim();
  try {
    git(['init','-q']);
    for (const name of files) {
      const target = path.join(directory,name); fs.mkdirSync(path.dirname(target),{recursive:true});
      fs.writeFileSync(target, name==='coordination/engineering/unconsumed/package.json' ? '{"type":"module"}\n' : name+'\n');
      if (entries().get(name)?.mode==='100755') fs.chmodSync(target,0o755);
    }
    git(['add','.']); git(['commit','-qm','Tiny existing-role selection']);
    const head=git(['rev-parse','HEAD']), tree=git(['rev-parse','HEAD^{tree}']);
    git(['sparse-checkout','set','--no-cone','--stdin'], patterns.join('\n')+'\n');
    git(['checkout','--detach','-q',head]);
    assert.equal(git(['rev-parse','HEAD']),head); assert.equal(git(['rev-parse','HEAD^{tree}']),tree);
    assert.equal(git(['status','--porcelain']), '');
    assert.throws(()=>git(['symbolic-ref','-q','HEAD']));
    return files.filter(name=>fs.existsSync(path.join(directory,name)));
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
}

test('stock non-cone checkout retains exact selected roles and executable helpers without opaque siblings',()=>{
  const retained=checkout(selectedDataCheckoutPatterns(definition,entries(),expectations));
  assert.deepEqual(retained.sort(), ['README.md','.github/package-inputs.json',expectations,
    ...definition.inputs.slice(1),...definition.verification_paths,
    'coordination/engineering/unconsumed/helper.py','coordination/engineering/unconsumed/package.json',
    'coordination/engineering/unconsumed/executable.bin'].sort());
});

for (const namespace of ['research/geography/','coordination/engineering/','data/']) {
  for (const role of ['inputs','verification_paths']) test(`stock selection preserves declared ${namespace} ancestor in ${role}`,()=>{
    const prefix=namespace.split('/')[0]+'/';
    const policy={...definition,[role]:[...definition[role].filter(name=>!name.startsWith(prefix)),prefix]};
    if(role==='inputs')policy.inputs=policy.inputs.filter(name=>!name.startsWith(prefix)||name===prefix);
    const retained=checkout(selectedDataCheckoutPatterns(policy,entries(),expectations));
    for(const name of names.filter(name=>name.startsWith(namespace)))assert(retained.includes(name),name);
  });
}

const archives = [
  'coordination/engineering/global-source-comparisons-b-package3-20261006/',
  'coordination/engineering/global-source-comparisons-a-20261006/',
  'coordination/engineering/global-source-comparisons-a-001-20261006/',
  'coordination/engineering/global-source-comparisons-b-20261006/',
  'coordination/engineering/reference-source-custody-20261007/',
  'coordination/engineering/complete-numeric-closure-diagnosis-20261007/',
  'research/geography/lithuania-latvia-gap-source-fitness-20261007/',
  'research/geography/shared-seam-prt-esp-20261006/'
];
const archiveFiles = archives.flatMap(prefix => [prefix+'body.json', prefix+'nested/body.bin',
  prefix+'historical-helper.py', prefix.slice(0,-1)+'-retained/body.json']);
const sourceOnly = ['data/regional-review/','research/campaigns/'];

test('complete stock checkout omits only eight whole archives and existing source-only roots',()=>{
  const files=[...names,...archiveFiles], patterns=fullCheckoutPatterns(definition);
  assert.deepEqual(patterns,['/*',...sourceOnly.map(prefix=>'!/'+prefix),...archives.map(prefix=>'!/'+prefix)]);
  const retained=checkout(patterns,files);
  assert.deepEqual(retained.sort(),files.filter(name=>![...sourceOnly,...archives].some(prefix=>name.startsWith(prefix))).sort());
});

for(const role of ['inputs','verification_paths']) {
  test(`complete stock checkout preserves explicitly declared archive members and ancestors in ${role}`,()=>{
    for(const kind of ['file','directory','ancestor']){
      const declared=archives.map(prefix=>kind==='file'?prefix+'nested/body.bin':kind==='directory'?prefix:prefix.split('/').slice(0,-2).join('/')+'/');
      const policy={...definition,[role]:[...definition[role],...new Set(declared)]};
      if(kind==='ancestor')policy[role]=[...new Set(policy[role].filter(name=>!declared.some(parent=>name!==parent&&name.startsWith(parent))))];
      const files=[...names,...archiveFiles], retained=checkout(fullCheckoutPatterns(policy),files);
      assert.deepEqual(retained.sort(),files.filter(name=>!sourceOnly.some(prefix=>name.startsWith(prefix))).sort());
    }
  });
}

test('complete stock checkout keeps the complete actual three-shard inventory and package controls',()=>{
  const shards=[0,1,2].map(shard=>integrationTestFiles('full',shard));
  const discovered=fs.readdirSync(new URL('../test/',import.meta.url)).filter(name=>name.endsWith('.test.mjs')).map(name=>'test/'+name).sort();
  assert.deepEqual(shards.flat().sort(),discovered);
  assert.equal(new Set(shards.flat()).size,discovered.length);
  const files=[...names,...archiveFiles,...discovered];
  const retained=new Set(checkout(fullCheckoutPatterns(definition),files));
  for(const shard of shards)for(const file of shard)assert(retained.has(file),file);
  for(const file of ['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'])assert(retained.has(file));
  assert.throws(()=>fullCheckoutPatterns({...definition,verification_paths:['../escape']}),/Invalid package/);
});

test('selected patterns reject nonordinary execution and untrusted expectations before checkout',()=>{
  for(const mode of ['120000','160000']){
    const tree=entries(); tree.set('coordination/engineering/unconsumed/helper.py',{type:'blob',mode});
    assert.throws(()=>selectedDataCheckoutPatterns(definition,tree,expectations),/Nonordinary/);
  }
  for(const name of ['../selected-delivery-expectations.json','/selected-delivery-expectations.json',
    'data/wrong.json','coordination/*/selected-delivery-expectations.json'])
    assert.throws(()=>selectedDataCheckoutPatterns(definition,entries(),name),/expectations/);
  for(const mode of ['120000','100755']){
    const tree=entries();tree.set(expectations,{type:'blob',mode});
    assert.throws(()=>selectedDataCheckoutPatterns(definition,tree,expectations),/expectations/);
  }
  assert.throws(()=>selectedDataCheckoutPatterns({...definition,inputs:['../escape']},entries(),expectations));
});
