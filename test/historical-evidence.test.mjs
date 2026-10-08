import test from 'node:test';
import assert from 'node:assert/strict';
import {validateEvidence, baselineFiles, baselineFile, sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import {checkPremergeEvidence, validateRecordChecks} from '../scripts/premerge-evidence.mjs';
const old='a'.repeat(40), later='b'.repeat(40), evaluation='c'.repeat(40), head='d'.repeat(40);
const manifestPath='coordination/engineering/vintage-fixture/evidence-quality.json';
const outputPath='coordination/engineering/vintage-fixture/results.json';
const desc=(path,raw,commit)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes',...(commit?{commit}:{})});
function fixture() {
 const input=Buffer.from('[{"id":"A","parent":"old-parent"}]'), comparison=Buffer.from('later retained evidence'), output=Buffer.from('{"value":1}');
 const manifest={version:1,issue:100,lane:'engineering',worker_id:'author',subject_ids:[],subject_ids_sha256:subjectsHash([]),
 baseline:{version:2,commit:evaluation,files:[desc('reference.json',input,old),desc('later.txt',comparison,later)],
 pins:{original:sha256(input),retained:sha256(comparison)},pin_files:{original:{path:'reference.json',commit:old},retained:{path:'later.txt',commit:later}}},
 sources:[],outputs:[desc(outputPath,output)],methods:[{id:'test',kind:'code',description:'test',software:'Node 24',units:'count'}],
 metrics:[{id:'count',value:1,unit:'count',vintage:'current',evaluation_commit:evaluation,input_sha256:sha256(input),input_file:{path:'reference.json',commit:old}}],
 summaries:[],conclusions:[],stages:{research:'complete',implementation:'implemented',geographic_approval:'not-requested'},commands:['node --test test/historical-evidence.test.mjs'],
 change_receipts:[{path:outputPath,status:'added'},{path:manifestPath,status:'added'}],metric_bindings:[{metric_id:'count',path:outputPath,json_pointer:'/value'}]};
 const spec={mode:'engineering',scope:'test',max_prs:1,depends_on:[],evidence_quality:{version:1,manifest_path:manifestPath,subject_ids:[],pins:manifest.baseline.pins,review_kind:'code'}};
 const issue={number:100,created_at:'2026-10-07T00:00:00Z',body:`<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
 const store=new Map([[`${old}:reference.json`,input],[`${later}:later.txt`,comparison],[`candidate:${outputPath}`,output]]);
 const readFile=(path,commit)=>{assert.ok(store.has(`${commit}:${path}`),'Missing exact immutable input');return store.get(`${commit}:${path}`);};
 readFile.assertAncestor=commit=>assert.ok([old,later,evaluation].includes(commit),'Not an ancestor');
 return {manifest,input,comparison,output,store,readFile,issue,spec,manifestPath,branch:'engineering/vintage-fixture',reservation:{worker_id:'author'},
 files:[{filename:outputPath,status:'added'},{filename:manifestPath,status:'added'}],pr:{number:101,head:{sha:head,ref:'engineering/vintage-fixture'},base:{sha:evaluation},changed_files:2},
 policy:{version:1,mode:'enforce-new',activation_time:'2026-10-03T00:00:00Z',legacy_follow_up:624}};
}
const validate=f=>validateEvidence(f.manifest,{readFile:f.readFile,expectedPins:f.spec.evidence_quality.pins});
test('historical bytes and metric evaluation use distinct authenticated vintages',()=>{
 const f=fixture();assert.equal(validate(f).status,'bytes-verified');assert.deepEqual(baselineFiles(f.manifest).map(x=>x.commit),[old,later]);
});
test('wrong hashes/commits, missing versions, candidate historical bytes and unsupported version declarations fail',()=>{
 for(const mutate of [f=>delete f.manifest.baseline.files[0].commit,f=>f.manifest.baseline.files[0].commit=head,
 f=>f.manifest.baseline.files[0].commit='candidate',f=>f.manifest.baseline.files[0].sha256='f'.repeat(64),
 f=>delete f.manifest.baseline.version,f=>f.manifest.baseline.version=3,
 f=>f.manifest.baseline.pin_files.original.commit=later,f=>f.manifest.metrics[0].input_file.commit=later,
 f=>f.manifest.metrics[0].evaluation_commit=old,f=>f.manifest.outputs[0].commit=old,
 f=>delete f.readFile.assertAncestor]){const f=fixture();mutate(f);assert.throws(()=>validate(f));}
});
test('duplicate paths at different vintages require explicit pin and metric identities',()=>{
 const f=fixture();f.manifest.baseline.files.push(desc('reference.json',f.input,later));f.store.set(`${later}:reference.json`,f.input);
 assert.equal(validate(f).status,'bytes-verified');
 f.manifest.baseline.pin_files.original='reference.json';assert.throws(()=>validate(f),/Ambiguous/);
 f.manifest.baseline.pin_files.original={path:'reference.json',commit:old};delete f.manifest.metrics[0].input_file;assert.throws(()=>validate(f),/Ambiguous/);
 f.manifest.metrics[0].input_file={path:'reference.json',commit:old};f.manifest.baseline.files.push(desc('reference.json',f.input,old));assert.throws(()=>validate(f),/Duplicate/);
});
test('historical inventories retain bounded file/phase/commit admission',()=>{
 const f=fixture();assert.throws(()=>validateEvidence(f.manifest,{readFile:f.readFile,maxTotalBytes:1}),/budget/);
 assert.throws(()=>validateEvidence(f.manifest,{readFile:f.readFile,maxFileBytes:1}),/budget/);
 for(let i=0;i<16;i++)f.manifest.baseline.files.push(desc(`extra-${i}`,Buffer.from('x'),i.toString(16).padStart(40,'0')));
 assert.throws(()=>baselineFiles(f.manifest),/commit inventory/);
});
test('subject lookup selects the declared historical file rather than snapshot bytes',()=>{
 const f=fixture();const raw=Buffer.from(JSON.stringify({features:[{id:'A'}]}));
 f.manifest.lane='geography';f.manifest.stages.implementation='not-proposed';f.manifest.subject_ids=['A'];f.manifest.subject_ids_sha256=subjectsHash(['A']);
 f.manifest.baseline.files=[desc('subjects.json',raw,old),desc('subjects.json',Buffer.from('{"features":[]}'),later)];
 f.manifest.baseline.pins={};f.spec.evidence_quality.pins={};f.manifest.metrics=[];
 f.store.set(`${old}:subjects.json`,raw);f.store.set(`${later}:subjects.json`,Buffer.from('{"features":[]}'));
 f.manifest.baseline.subject_files={A:{path:'subjects.json',commit:old}};assert.equal(validate(f).status,'bytes-verified');
 f.manifest.baseline.subject_files.A='subjects.json';assert.throws(()=>validate(f),/Ambiguous/);
 f.manifest.baseline.subject_files.A={path:'subjects.json',commit:later};assert.throws(()=>validate(f),/Subject missing/);
});
test('structured references cannot silently use another historical version',()=>{
 const f=fixture();const output=Buffer.from('[{"id":"A","parent":"old-parent"}]');
 f.manifest.outputs=[desc(outputPath,output)];f.store.set(`candidate:${outputPath}`,output);
 f.manifest.record_checks=[{version:1,path:outputPath,json_pointer:'',id_key:'id',reference_path:'reference.json',reference_commit:old,reference_json_pointer:'',reference_id_key:'id',fields:{parent:'parent'}}];
 assert.equal(validateRecordChecks(f.manifest,f.readFile),1);
 f.manifest.baseline.files.push(desc('reference.json',Buffer.from('[{"id":"A","parent":"wrong"}]'),later));f.store.set(`${later}:reference.json`,Buffer.from('[{"id":"A","parent":"wrong"}]'));
 delete f.manifest.record_checks[0].reference_commit;assert.throws(()=>validateRecordChecks(f.manifest,f.readFile),/Ambiguous/);
 f.manifest.record_checks[0].reference_commit=later;assert.throws(()=>validateRecordChecks(f.manifest,f.readFile),/join mismatch/);
});
function remoteFixture(f,{badAncestor,missingCommit}={}) {
 const stores=new Map([[old,new Map([['reference.json',f.input]])],[later,new Map([['later.txt',f.comparison]])],
 [evaluation,new Map()],[head,new Map([[manifestPath,Buffer.from(JSON.stringify(f.manifest))],[outputPath,f.output]])]]);
 const blobs=new Map(),trees=new Map();let id=0;const calls=[];
 for(const [commit,files] of stores){const rows=[];for(const [path,bytes]of files){const sha=`blob-${id++}`;blobs.set(sha,bytes);rows.push({path,sha,size:bytes.length,type:'blob',mode:'100644'});}trees.set(commit,rows);}
 const api=async route=>{
 calls.push(route);
 if(route.includes('/compare/'))return {status:route.includes(badAncestor??'not-a-commit')?'diverged':'ahead'};
 if(route.includes('/git/commits/')){const c=route.split('/').pop();if(c===missingCommit)throw Error('Commit missing');assert.ok(stores.has(c));return {sha:c,tree:{sha:c}};}
 if(route.includes('/git/trees/'))return {truncated:false,tree:trees.get(route.split('/').pop().split('?')[0])};
 if(route.includes('/git/blobs/')){const b=blobs.get(route.split('/').pop());assert.ok(b);return {encoding:'base64',content:b.toString('base64')};}
 throw Error('Unexpected route '+route);
 };return {api,calls};
}
test('trusted hosted gate authenticates each vintage before loading and preserves independent evaluation',async()=>{
 const f=fixture(),r=remoteFixture(f);const checked=await checkPremergeEvidence({...f,api:r.api,repo:'test/repo'});
 assert.equal(checked.status,'bytes-verified');for(const c of [old,later,evaluation])assert.ok(r.calls.some(p=>p.includes(`/compare/${c}...${evaluation}`)));
 assert.ok(checked.checked.includes(`${old}:reference.json`));assert.ok(checked.checked.includes(`${later}:later.txt`));
});
test('trusted hosted gate refuses nonancestor/missing commits and absent immutable files despite candidate copies',async()=>{
 for(const badAncestor of [old,later]){const f=fixture(),r=remoteFixture(f,{badAncestor});await assert.rejects(()=>checkPremergeEvidence({...f,api:r.api,repo:'test/repo'}),/ancestor/);assert.ok(!r.calls.some(x=>x.includes('/git/commits/'+old)));}
 const f=fixture(),r=remoteFixture(f,{missingCommit:old});await assert.rejects(()=>checkPremergeEvidence({...f,api:r.api,repo:'test/repo'}),/missing/);
 const g=fixture();g.manifest.baseline.files[0].path=outputPath;g.manifest.baseline.pin_files.original={path:outputPath,commit:old};const s=remoteFixture(g);
 await assert.rejects(()=>checkPremergeEvidence({...g,api:s.api,repo:'test/repo'}),/Missing/);
});

test('prior-evidence subject rosters use their selected commit and preserve source limitations',()=>{
 const f=fixture(), roster=Buffer.from('{"subjects":["A"]}');
 const registry=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',id:'native:A',geometry:null,properties:{id:'native:A',source_value:'A',source_property:'native_id'}}]}));
 f.manifest.lane='geography';f.manifest.stages.implementation='not-proposed';
 f.manifest.subject_ids=['native:A'];f.manifest.subject_ids_sha256=subjectsHash(f.manifest.subject_ids);
 f.manifest.baseline.files=[desc('roster.json',roster,old),desc('roster.json',Buffer.from('{"subjects":["B"]}'),later)];
 f.manifest.baseline.pins={};f.spec.evidence_quality.pins={};f.manifest.metrics=[];
 f.manifest.baseline.subject_inventory={version:1,basis:'prior-evidence',path:'roster.json',commit:old,json_pointer:'/subjects',id_prefix:'native:',source_property:'native_id',source_id:'source',registry_path:outputPath};
 f.manifest.sources=[{id:'source',url:'https://example.org/source',role:'reference',vintage:'historical',retrieved_at:'2026-10-07',license:{status:'unknown',terms:'Unknown'},retention:'restoration-only',verification:'unverified',temporal_status:'reference',restoration:'Restore original',limit:'Source not independently checked'}];
 f.manifest.outputs=[desc(outputPath,registry)];f.store.set(`candidate:${outputPath}`,registry);f.store.set(`${old}:roster.json`,roster);f.store.set(`${later}:roster.json`,Buffer.from('{"subjects":["B"]}'));
 const result=validate(f);assert.equal(result.status,'limited');assert.match(result.limits.join(' '),/original source membership/);
 delete f.manifest.baseline.subject_inventory.commit;assert.throws(()=>validate(f),/Ambiguous/);
 f.manifest.baseline.subject_inventory.commit=later;assert.throws(()=>validate(f),/roster differs/);
});
test('historical versions do not widen remote descriptors or tree reads',async()=>{
 const f=fixture(),r=remoteFixture(f);await checkPremergeEvidence({...f,api:r.api,repo:'test/repo'});
 // Initial manifest loading has its own candidate/base reader; the evidence reader adds four distinct commits.
 assert.equal(r.calls.filter(x=>x.includes('/git/commits/')).length,6);
 assert.equal(r.calls.filter(x=>x.endsWith('/git/commits/'+evaluation)).length,2);
 assert.equal(r.calls.filter(x=>x.includes('/git/trees/')).length,6);
 const g=fixture();for(let i=0;i<511;i++)g.manifest.baseline.files.push(desc(`extra-${i}`,Buffer.from('x'),old));
 const oversized=remoteFixture(g);await assert.rejects(()=>checkPremergeEvidence({...g,api:oversized.api,repo:'test/repo'}),/oversized evidence inventory/);
 assert.equal(oversized.calls.filter(x=>x.includes('/compare/')).length,0);
});

test('altering consumed historical bytes fails while hashes and summaries remain unchanged',()=>{
 const f=fixture();f.store.set(`${old}:reference.json`,Buffer.from('[{"id":"B","parent":"old-parent"}]'));
 assert.throws(()=>validate(f),/Input bytes mismatch/);
});

test('composed geography identities select historical bytes while retaining existing binding rules',()=>{
 const f=fixture(),raw=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',properties:{native:'A'}}]}));
 f.manifest.lane='geography';f.manifest.stages.implementation='not-proposed';f.manifest.subject_ids=['source:A'];f.manifest.subject_ids_sha256=subjectsHash(f.manifest.subject_ids);
 f.manifest.baseline.files=[desc('subjects.json',raw,old),desc('subjects.json',Buffer.from('{"type":"FeatureCollection","features":[]}'),later)];
 f.manifest.baseline.pins={};f.spec.evidence_quality.pins={};f.manifest.metrics=[];
 f.store.set(`${old}:subjects.json`,raw);f.store.set(`${later}:subjects.json`,Buffer.from('{"type":"FeatureCollection","features":[]}'));
 const binding={version:1,path:'subjects.json',commit:old,properties:['native'],id_template:'source:{native}'};
 f.manifest.baseline.subject_files={'source:A':binding};assert.equal(validate(f).status,'bytes-verified');
 delete binding.commit;assert.throws(()=>validate(f),/Ambiguous/);
 binding.commit=later;assert.throws(()=>validate(f),/Composed subject missing/);
 binding.commit=old;binding.unrecognized=true;assert.throws(()=>validate(f),/Invalid versioned/);
});

test('local validation rejects excess descriptors and ignored source commit declarations before reading',()=>{
 const f=fixture();for(let i=0;i<511;i++)f.manifest.baseline.files.push(desc(`extra-${i}`,Buffer.from('x'),old));
 let reads=0;const reader=()=>{reads++;throw Error('Must not read');};reader.assertAncestor=()=>{reads++;};
 assert.throws(()=>validateEvidence(f.manifest,{readFile:reader}),/inventory exceeds/);assert.equal(reads,0);
 const g=fixture();g.manifest.sources=[{files:[desc('unretained.txt',Buffer.from('x'),old)],retention:'restoration-only'}];
 assert.throws(()=>validate(g),/source file cannot declare historical commit/);
});
