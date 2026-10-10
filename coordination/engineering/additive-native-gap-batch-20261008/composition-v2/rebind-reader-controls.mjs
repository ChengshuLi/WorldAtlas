import {fixtureIssuedPlan,executionFixture} from './execution-custody-fixture.mjs';
// Actual ImmutableReader and production rebind custody API in a tiny ordinary
// Git fixture. Its certificates/operating receipts are synthetic, not authority.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';
import {all} from './current-rebind-controls.mjs';
import {CURRENT_REBIND_CODE} from './current-rebind.mjs';
import {ImmutableReader} from '../../../../scripts/check-effective-geographic-regression.mjs';
import {readCurrentRebindCustody,selectedAdditiveRows,valueBytes,valueSha} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const Q='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/',git='/Library/Developer/CommandLineTools/usr/bin/git',sha=b=>createHash('sha256').update(b).digest('hex');
const fixture=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-rebind-reader-'));
const g=(...args)=>execFileSync(git,['-c','core.hooksPath=/dev/null','-C',fixture,...args],{encoding:'utf8',maxBuffer:33554433});
const write=(name,body)=>{const p=path.join(fixture,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,Buffer.isBuffer(body)?body:valueBytes(body));};
const commit=()=>{g('add','.');g('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Bounded custody fixture');return g('rev-parse','HEAD').trim();};
const pin=(name,head)=>{const row=g('ls-tree','-l',head,'--',name).trim().split(/\s+/),body=fs.readFileSync(path.join(fixture,name));return {commit:head,path:name,mode:row[0],git_blob_oid:row[2],bytes:body.length,sha256:sha(body)};};
let head,positive,negative=0;
try{
 g('init','-q');for(const name of CURRENT_REBIND_CODE)write(name,fs.readFileSync(name));const codeHead=commit();
 const request=structuredClone(all.request);request.execution_commit=codeHead;const issuedPlanBytes=valueBytes(fixtureIssuedPlan(request));request.execution.pre_use.plan.bytes=issuedPlanBytes.length;request.execution.pre_use.plan.sha256=sha(issuedPlanBytes);write('request.json',request);const requestHead=commit(),requestPin=pin('request.json',requestHead);
 write('result.json',all.result);const resultHead=commit(),resultPin=pin('result.json',resultHead);
 const facts={...all.facts,execution_commit:codeHead,request_sha256:requestPin.sha256,result_sha256:resultPin.sha256};write('facts.json',facts);const factsHead=commit(),factsPin=pin('facts.json',factsHead);
 const publication={...all.publication,execution_commit:codeHead,request_sha256:requestPin.sha256,outputs:{facts:{path:'facts.json',bytes:factsPin.bytes,sha256:factsPin.sha256},result:{path:'result.json',bytes:resultPin.bytes,sha256:resultPin.sha256}}};write('publication.json',publication);const pubHead=commit(),pubPin=pin('publication.json',pubHead);
 const fixturePin=(name,body)=>({commit:codeHead,path:name+'.json',mode:'100644',git_blob_oid:'2'.repeat(40),bytes:body.length,sha256:sha(body)});
 const execution=executionFixture(request,{requestPin,publicationPin:pubPin,resultPin,pin:fixturePin});for(const [name,b]of Object.entries(execution.bodies))write('execution-'+name+'.json',b);const executionHead=commit(),executionPins=Object.fromEntries(Object.keys(execution.bodies).map(name=>[name,pin('execution-'+name+'.json',executionHead)]));
 const operating={...all.operating,execution_custody:executionPins,execution_commit:codeHead,request_sha256:requestPin.sha256,publication_sha256:pubPin.sha256};write('operating.json',operating);const opHead=commit(),opPin=pin('operating.json',opHead);
 const certificate={...all.certificate,execution_commit:codeHead,request:requestPin,facts:factsPin,publication:pubPin,operating:opPin,result:resultPin};write('certificate.json',certificate);head=commit();const certPin=pin('certificate.json',head);
 const options={baseSelection:all.baseSelection,registry:all.registry,originalRows:all.originalRows,originalPatches:all.originalPatches,size:all.size};
 const reader=()=>new ImmutableReader(fixture,head,{runtimeBytes:fs.statSync(process.execPath).size+fs.statSync(git).size,executionBytes:CURRENT_REBIND_CODE.reduce((n,p)=>n+fs.statSync(p).size,0),outputBytes:4*1048576});
 const r=reader();assert.throws(()=>readCurrentRebindCustody(r,certPin,options),/actual privately authenticated selected snapshot/);negative++;
 assert.throws(()=>readCurrentRebindCustody(r,certPin,{...options,snapshot:{reader:r}}),/Require authenticated selected snapshot/);negative++;
 assert(r.used<=268435456&&r.charged.size<=512);positive=all.result;
 const reject=(p=certPin,o=options)=>{const actual=reader();assert.throws(()=>readCurrentRebindCustody(actual,p,{...o,snapshot:{reader:actual}}));negative++;};
 reject({...certPin,git_blob_oid:'f'.repeat(40)});reject({...certPin,sha256:'f'.repeat(64)});reject({...certPin,bytes:certPin.bytes+1});
 reject(certPin,{...options,baseSelection:{...options.baseSelection,sha256:'f'.repeat(64)}});
 const bad={...certificate,result:{...resultPin,path:'missing.json'}};write('bad-certificate.json',bad);const badHead=commit();reject(pin('bad-certificate.json',badHead));
 const foreign={...certificate,result:requestPin};write('foreign-certificate.json',foreign);const foreignHead=commit();reject(pin('foreign-certificate.json',foreignHead));
 // Private selection identity is not issued by reading a product or cloning it.
 assert.throws(()=>selectedAdditiveRows(positive,all.result.native.rows[0].y,all.result.native.current_rows[0].runs));negative++;
 const report={version:1,kind:'actual-current-rebind-immutable-reader-private-snapshot-refusal-controls',fixture_head:head,complete_phase_bytes:r.used,descriptors:r.charged.size,components:positive.original_rows.length,current_targets:positive.current_targets.length,original_cells:positive.native.assigned_cells,negative_controls:negative,certificate_pin:certPin,input_pins:[...r.inventory.values()],limits:['Actual immutable reader authenticates the synthetic product roster, then production acquisition refuses the forged snapshot. There is no successful selected acquisition in this fixture.','No selected-bank activation, full v9 qualification or original source/native scientific replay.']};
 fs.writeFileSync(Q+'rebind-reader-controls.json',valueBytes(report));console.log(JSON.stringify({components:12,cells:141,negatives:negative,phase:r.used}));
}finally{fs.rmSync(fixture,{recursive:true,force:true});}
