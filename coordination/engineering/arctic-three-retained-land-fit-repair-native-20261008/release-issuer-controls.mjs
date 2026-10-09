import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {issueSuccessorRelease} from './release-issuer.mjs';
const plan=JSON.parse(fs.readFileSync(process.argv[2]));
const sha=body=>createHash('sha256').update(body).digest('hex');
const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/release-issuer-controls-'));
const originalOpen=fs.openSync;let opens=0;
fs.openSync=function(...args){opens++;return originalOpen.apply(this,args);};
let negative=0;
try{
 for(const [input,destination] of [
  [plan,root],
  [plan,path.join(process.cwd(),'.cache','..','..','escape')],
  [plan,path.join(root,'link','fresh')],
  [{...plan,kind:'foreign'},path.join(root,'foreign')],
  [{...plan,output_reserve:256*1024*1024},path.join(root,'over-budget')],
  [{...plan,inputs:Array(513).fill(plan.inputs[0])},path.join(root,'over-count')],
  [{...plan,members:plan.members.slice(1)},path.join(root,'missing')]
 ]){
  if(destination.includes('/link/'))fs.symlinkSync(root,path.join(root,'link'));
  process.env.WORLDATLAS_SELECTED_NATIVE_HEAD=input.source_head;
  process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256=sha(JSON.stringify(input));
  opens=0;await assert.rejects(issueSuccessorRelease(input,destination));assert.equal(opens,0);negative++;
 }
}finally{fs.openSync=originalOpen;fs.rmSync(root,{recursive:true,force:true});}
console.log(JSON.stringify({negative,zero_body_opens_before_admission:true,limits:'Boundary refusals only; complete release issuance remains unexecuted.'}));
