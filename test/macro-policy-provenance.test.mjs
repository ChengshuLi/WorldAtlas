import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const decision='data/macro-foundation/europe-asia-boundary-decisions.json';
const policy='data/macro-foundation/membership-decisions.json';
const correction='data/macro-foundation/europe-asia-policy-provenance-correction-v1.json';
function run(root){return spawnSync('python3',['scripts/macro_policy_provenance.py',root],{encoding:'utf8'});}
test('retained original mismatch is resolved additively, with no semantic approval',()=>{
 const result=run('.');assert.equal(result.status,0,result.stderr);
 const receipt=JSON.parse(result.stdout);assert.equal(receipt.status,'corrected-binding-verified');
 assert.equal(receipt.earlier_vintage_origin,'unknown');assert.equal(receipt.geographic_approval,'not-assessed');
 assert.notEqual(JSON.parse(fs.readFileSync(decision)).referenced_membership_policy.sha256,receipt.policy_sha256);
});
test('missing correction, wrong citation/hash/commit and either changed original fail closed',()=>{
 const mutations=[
  root=>fs.unlinkSync(path.join(root,correction)),
  ...['sha256','path','commit'].map(key=>root=>{const file=path.join(root,correction);let value=JSON.parse(fs.readFileSync(file));value.corrected_reference[key]='wrong';fs.writeFileSync(file,JSON.stringify(value));}),
  root=>fs.appendFileSync(path.join(root,policy),' '),
  root=>fs.appendFileSync(path.join(root,decision),' '),
  root=>{const file=path.join(root,correction);let value=JSON.parse(fs.readFileSync(file));value.original.recorded_reference.sha256='0'.repeat(64);fs.writeFileSync(file,JSON.stringify(value));}
 ];
 for(const mutate of mutations){const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-policy-'));try{
  for(const file of [decision,policy,correction]){fs.mkdirSync(path.dirname(path.join(root,file)),{recursive:true});fs.copyFileSync(file,path.join(root,file));}
  mutate(root);const result=run(root);assert.notEqual(result.status,0,'invalid provenance accepted');
 }finally{fs.rmSync(root,{recursive:true,force:true});}}
});
test('actual preparation consumer rejects a missing correction before geography reads',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-policy-consumer-'));
 try{
  for(const file of [decision,policy]){fs.mkdirSync(path.dirname(path.join(root,file)),{recursive:true});fs.copyFileSync(file,path.join(root,file));}
  const result=spawnSync('python3',['scripts/prepare-global-macro-geography.py','--data',path.join(root,'data'),'--policy',path.join(root,policy),'--output',path.join(root,'candidate'),'--receipts',path.join(root,'receipts')],{encoding:'utf8'});
  assert.notEqual(result.status,0);assert.match(result.stderr,/europe-asia-policy-provenance-correction-v1.json/);
  assert.equal(fs.existsSync(path.join(root,'candidate')),false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
