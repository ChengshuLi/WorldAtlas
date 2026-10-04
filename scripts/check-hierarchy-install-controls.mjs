// Run meaningful controls and bind their actual log bytes into typed receipts.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';
const owned='data/engineering/hierarchy-install-20261003-a9c2';
const files=['test/install-macro-reference.test.mjs','test/evidence-revalidation-chain.test.mjs','test/evidence-partitions.test.mjs','test/macro-review-projection.test.mjs','test/source-policy-corrections.test.mjs','test/reference-macro-binding.test.mjs','test/evidence-partition-review.test.mjs'];
const result=spawnSync(process.execPath,['--test',...files],{encoding:'utf8',maxBuffer:8*1024*1024,env:process.env});
const log=Buffer.from(result.stdout+result.stderr),name=`${owned}/final-controls.log`;
fs.writeFileSync(name,log);
if(result.error||result.status!==0)throw Error('Scoped controls failed; retain the actual log');
const scenarios=result.stdout.split('\n').filter(row=>row.startsWith('✔ ')).map(row=>row.slice(2).replace(/ \([\d.]+ms\)$/,''));
const negative=scenarios.filter(row=>/reject|refuse|cannot|must|wrong|tamper|unsafe|alter|unrelated|incomplete|partial|duplicate|budget|order|cycle|retired|archive|preserv|exact|retain/i.test(row));
if(scenarios.length<30||negative.length<10)throw Error('Incomplete meaningful positive/negative controls');
for(const [kind,selected]of [['positive-control',scenarios],['negative-control',negative]]){
 const receipt={version:1,method_id:'hierarchy-install-generator',kind,outcome:'passed',actual_test_files:files,passed_tests:scenarios.length,scenarios:selected,log_path:name,log_sha256:createHash('sha256').update(log).digest('hex'),scope:kind==='positive-control'?'Actual successful source/membership/archive/release and preservation fixtures':'Actual failing-case assertions reject altered byte pins, incomplete histories, changed identities/owners, dropped assessments, approval transfer, incomplete inventories and unsafe paths',published:false};
 fs.writeFileSync(`${owned}/${kind}.json`,encodeEvidenceJSON(receipt));
}
console.log(JSON.stringify({passed_tests:scenarios.length,negative_scenarios:negative.length,log:name}));
