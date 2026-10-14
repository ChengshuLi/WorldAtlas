import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
test('physical metadata closure and single native buffer preserve exact boundaries',()=>{
 const result=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??process.env.PYTHON??'python3',['-I','-B','test/physical-source-retention.test.py'],{encoding:'utf8',timeout:60000});
 assert.ifError(result.error);assert.equal(result.status,0,result.stdout+'\n'+result.stderr);assert.doesNotMatch(result.stderr,/skipped=/);
});

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {resumeSource,jsonBytes} from '../scripts/prepare-delivery-handoff.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const json=value=>Buffer.from(JSON.stringify(value,null,2)+'\n');
test('physical resume authenticates complete original products and inputs without replay',t=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'physical-resume-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const destination='.cache/delivery-handoff/result',directory=path.join(root,destination);
 fs.mkdirSync(directory,{recursive:true});
 const pin={path:'input.json',bytes:2,sha256:hash('{}')};
 const config={physical:{version:1,inputs:[pin]}};
 const binding={phase:'physical',program_sha256:'a'.repeat(64),config_sha256:'b'.repeat(64)};
 const body=json({results:[{target:'one',issues:[]}],repaired_credit:0});
 const execution=json({complete:true,program:{sha256:binding.program_sha256},
  fresh_admission:{config_sha256:hash(jsonBytes(config.physical))},
  outputs:[{path:destination+'/whole-target-support.json',bytes:body.length,sha256:hash(body)}]});
 const products={'whole-target-support.json':body,'execution-receipt.json':execution};
 const receipt={version:1,binding,outputs:Object.fromEntries(Object.entries(products).map(([name,raw])=>[name,{bytes:raw.length,sha256:hash(raw)}]))};
 for(const [name,raw]of Object.entries(products))fs.writeFileSync(path.join(directory,name),raw);
 fs.writeFileSync(path.join(directory,'preparation.json'),jsonBytes(receipt));
 let reads=0;const reader={read:p=>{assert.deepEqual(p,{...pin,mode:'100644'});reads++;return Buffer.from('{}');},budget:{add(){}}};
 resumeSource(root,destination,config,binding,reader);assert.equal(reads,1);
 fs.writeFileSync(path.join(directory,'whole-target-support.json'),json({results:[]}));
 assert.throws(()=>resumeSource(root,destination,config,binding,reader),/product changed/);
 fs.writeFileSync(path.join(directory,'whole-target-support.json'),body);
 assert.throws(()=>resumeSource(root,destination,config,{...binding,program_sha256:'c'.repeat(64)},reader),/configuration\/code/);
});
