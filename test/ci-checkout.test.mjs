import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {selectedDataCheckoutPatterns} from '../scripts/package-inputs.mjs';

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

function checkout(patterns) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-stock-selection-'));
  const env = {...process.env, GIT_CONFIG_NOSYSTEM:'1', GIT_CONFIG_GLOBAL:os.devNull,
    GIT_NO_LAZY_FETCH:'1', GIT_TERMINAL_PROMPT:'0'};
  const git = (args, input) => execFileSync('git', ['-c','core.hooksPath='+os.devNull,
    '-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-C',directory,...args],
  {env, input, encoding:'utf8', stdio:['pipe','pipe','pipe']}).trim();
  try {
    git(['init','-q']);
    for (const name of names) {
      const target = path.join(directory,name); fs.mkdirSync(path.dirname(target),{recursive:true});
      fs.writeFileSync(target, name==='coordination/engineering/unconsumed/package.json' ? '{"type":"module"}\n' : name+'\n');
      if (entries().get(name).mode==='100755') fs.chmodSync(target,0o755);
    }
    git(['add','.']); git(['commit','-qm','Tiny existing-role selection']);
    const head=git(['rev-parse','HEAD']), tree=git(['rev-parse','HEAD^{tree}']);
    git(['sparse-checkout','set','--no-cone','--stdin'], patterns.join('\n')+'\n');
    git(['checkout','--detach','-q',head]);
    assert.equal(git(['rev-parse','HEAD']),head); assert.equal(git(['rev-parse','HEAD^{tree}']),tree);
    return names.filter(name=>fs.existsSync(path.join(directory,name)));
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

test('complete stock checkout keeps the existing two source-only exclusions',()=>{
  const retained=checkout(['/*','!/data/regional-review/','!/research/campaigns/']);
  assert.deepEqual(retained.sort(), names.filter(name=>!name.startsWith('data/regional-review/')&&
    !name.startsWith('research/campaigns/')).sort());
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
