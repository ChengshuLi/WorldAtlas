// Read historical Git blobs only. Never execute or edit the geography packet.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {validateEvidence, sha256} from '../../../scripts/evidence-quality.mjs';
const root=process.cwd();
const fixture=JSON.parse(fs.readFileSync('test/fixtures/historical-evidence-1381.json','utf8'));
const git=(...args)=>execFileSync('git',['-C',root,...args],{maxBuffer:33*1024*1024,stdio:['ignore','pipe','pipe']});
const original=JSON.parse(git('show',`${fixture.head}:${fixture.manifest_path}`));
const manifest=structuredClone(original);
manifest.baseline.version=2;
// Preserve every issue pin's original commit, including identical files at different commits.
const files=new Map();
for(const pin of fixture.pins) {
 // Old manifests sometimes bind two identical pin hashes to one path. Restore each
 // original issue path explicitly; the reader below authenticates the actual bytes.
 const descriptor=original.baseline.files.find(file=>file.sha256===pin.sha256 && file.bytes===pin.bytes) ?? {hash_kind:'file-bytes'};
 files.set(`${pin.commit}:${pin.path}`,{...descriptor,path:pin.path,bytes:pin.bytes,sha256:pin.sha256,commit:pin.commit});
 if(original.baseline.pins[pin.key]!==pin.sha256)throw Error('Original named pin changed '+pin.key);
 manifest.baseline.pin_files[pin.key]={path:pin.path,commit:pin.commit};
}
const helperBytes=git('show',`${fixture.executed_helper.commit}:${fixture.executed_helper.path}`);
if(sha256(helperBytes)!==fixture.executed_helper.sha256)throw Error('Executed helper hash mismatch');
files.set(`${fixture.executed_helper.commit}:${fixture.executed_helper.path}`,{...fixture.executed_helper,bytes:helperBytes.length,hash_kind:'file-bytes'});
manifest.baseline.files=[...files.values()];
for(const metric of manifest.metrics) {
 const input=manifest.baseline.files.find(file=>file.sha256===metric.input_sha256);
 if(!input)throw Error('No retained metric input');
 metric.input_file={path:input.path,commit:input.commit};
}
const cache=new Map();
const reader=(name,vintage)=>{
 const commit=vintage==='candidate'?fixture.head:vintage,key=`${commit}:${name}`;
 if(!cache.has(key))cache.set(key,git('show',key));
 return cache.get(key);
};
reader.assertAncestor=commit=>git('merge-base','--is-ancestor',commit,fixture.pr_base);
const result=validateEvidence(manifest,{readFile:reader,expectedPins:Object.fromEntries(fixture.pins.map(pin=>[pin.key,pin.sha256]))});
const report={version:1,issue:fixture.issue,head:fixture.head,pr_base:fixture.pr_base,
 pins_checked:fixture.pins.length,historical_descriptors:manifest.baseline.files.length,
 historical_commits:[...new Set([manifest.baseline.commit,...manifest.baseline.files.map(file=>file.commit)])],
 metrics_checked:manifest.metrics.length,status:result.status,limits:result.limits,
 executed_helper:fixture.executed_helper,
 scope:'Local read-only representation conformance; original pins and packet bytes unchanged. Not a hosted gate, scientific review, execution reproduction or geography approval.'};
console.log(JSON.stringify(report,null,2));
