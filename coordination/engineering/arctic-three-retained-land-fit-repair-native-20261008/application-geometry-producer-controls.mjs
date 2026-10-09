// Actual issuer admission controls. The argument is the complete reviewed plan.
import fs from 'node:fs';import assert from 'node:assert/strict';import path from 'node:path';
import {issueApplicationGeometry} from './application-geometry-producer.mjs';
const plan=JSON.parse(fs.readFileSync(process.argv[2]));process.env.WORLDATLAS_SELECTED_NATIVE_HEAD=plan.head;const root=fs.mkdtempSync(new URL('../../../.cache/application-serialization-adverse-', import.meta.url).pathname);const originalOpen=fs.openSync;let opens=0;fs.openSync=()=>{opens++;throw Error('BODY_OPEN_FORBIDDEN');};let negatives=0;
try{for(const change of [p=>p.head='foreign',p=>p.runtime.path='/foreign',p=>p.sources.pop(),p=>p.sources[0].bytes++,p=>p.sources[0].mode=0o600,p=>p.outputReserve=256*1024*1024,p=>p.sources[0].path+='.missing',p=>p.code.pop()]){const bad=structuredClone(plan);change(bad);assert.throws(()=>issueApplicationGeometry(bad,root+'/unused'));assert.equal(opens,0);negatives++;}
for(const dest of [root,root+'/../escaped','/foreign-output']){assert.throws(()=>issueApplicationGeometry(plan,dest));assert.equal(opens,0);negatives++;}
fs.symlinkSync(root+'/absent',root+'/dangling');assert.throws(()=>issueApplicationGeometry(plan,root+'/dangling'));assert.equal(opens,0);negatives++;
}finally{fs.openSync=originalOpen;fs.rmSync(root,{recursive:true});}console.log(JSON.stringify({negatives,source_runtime_body_opens:opens,production_issuer: true,scientific_execution:false}));
