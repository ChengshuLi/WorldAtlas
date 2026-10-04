import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {readGitPRFiles} from '../scripts/validate-evidence-partitions.mjs';
import {sha256,subjectsHash} from '../scripts/evidence-quality.mjs';
import {validatePremergeManifest} from '../scripts/premerge-evidence.mjs';
import {selectAggregateReview,boundPartitionReview,checkPartitionReviewInventory} from '../scripts/validate-evidence-partition-review.mjs';
const head='a'.repeat(40),reviewer='independent-worker';
const marker=(name,value)=>'<!-- '+name+':v1\n'+JSON.stringify(value)+'\n-->';
test('PR evidence inventory preserves author renames and excludes a disjoint main advance',()=>{
 const cwd=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-pr-diff-'));
 const git=(...args)=>execFileSync('git',['-c','user.name=Evidence fixture','-c','user.email=fixture@example.invalid',...args],{cwd,encoding:'utf8'}).trim();
 try{
  git('init','--initial-branch=main');fs.writeFileSync(path.join(cwd,'original.txt'),'retained original\n');fs.writeFileSync(path.join(cwd,'shared.json'),'before\n');git('add','.');git('commit','-m','baseline');const initial=git('rev-parse','HEAD');
  git('checkout','-b','author');git('mv','original.txt','renamed.txt');fs.writeFileSync(path.join(cwd,'shared.json'),'candidate\n');git('commit','-am','author changes');const head=git('rev-parse','HEAD');
  git('checkout','main');fs.writeFileSync(path.join(cwd,'main-only.json'),'other worker evidence\n');git('add','.');git('commit','-m','disjoint main advance');let base=git('rev-parse','HEAD');
  assert.deepEqual(readGitPRFiles(base,head,{cwd}),[{filename:'renamed.txt',previous_filename:'original.txt',status:'renamed'},{filename:'shared.json',status:'modified'}]);
  assert.match(git('diff','--name-status',base,head),/D\s+main-only.json/);
  assert.equal(git('show',base+':shared.json'),'before');assert.equal(git('show',head+':shared.json'),'candidate');
  const blob=(name,commit)=>execFileSync('git',['show',commit+':'+name],{cwd});
  const desc=(name,commit)=>{const raw=blob(name,commit);return {path:name,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'};};
  const manifestPath='coordination/engineering/pr-diff/evidence-quality.json',files=[...readGitPRFiles(base,head,{cwd}),{filename:manifestPath,status:'added'}];
  const manifest={version:1,issue:6,lane:'engineering',worker_id:'pr-diff-worker',subject_ids:[],subject_ids_sha256:subjectsHash([]),baseline:{commit:initial,files:[desc('shared.json',initial)],pins:{},pin_files:{}},sources:[],outputs:[desc('renamed.txt',head),desc('shared.json',head)],methods:[{id:'byte-check',kind:'code',description:'Real divergent Git fixture with actual-base original receipts',software:'Git and Node24',units:'bytes'}],metrics:[],metric_bindings:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'proposed',geographic_approval:'not-requested'},commands:['synthetic divergent Git control'],change_receipts:files.map(row=>({path:row.filename,status:row.status,...(row.previous_filename?{previous_path:row.previous_filename}:{}),...(row.status!=='added'?{original_sha256:sha256(blob(row.previous_filename??row.filename,initial))}:{})}))};
  const validate=()=>validatePremergeManifest(manifest,{files,manifestPath,branch:'engineering/pr-diff',issue:{number:6},spec:{mode:'engineering',evidence_quality:{subject_ids:[],pins:{}}},reservation:{worker_id:'pr-diff-worker'},readFile:(name,vintage)=>blob(name,vintage==='candidate'?head:vintage==='base'?base:vintage)});
  assert.doesNotThrow(validate);
  fs.writeFileSync(path.join(cwd,'shared.json'),'changed relevant main input\n');git('commit','-am','overlapping main advance');base=git('rev-parse','HEAD');
  assert.equal(readGitPRFiles(base,head,{cwd}).length,2);
  assert.throws(validate,/Original|original/);
 }finally{fs.rmSync(cwd,{recursive:true,force:true});}
});
function root(id=1,extra={}){
 return {id,author_association:'OWNER',body:marker('worldatlas-review',{head_sha:head,reviewer_worker_id:reviewer,outcome:'accepted'})+'\n'+marker('worldatlas-review-aggregate',{head_sha:head,reviewer_worker_id:reviewer}),...extra};
}
test('aggregate selection requires actual qualified latest current-head reviewer comment',()=>{
 const accepted=root();assert.equal(selectAggregateReview([accepted],head),accepted);
 for(const author_association of ['NONE','CONTRIBUTOR','FIRST_TIMER'])assert.throws(()=>selectAggregateReview([root(1,{author_association})],head),/qualified/);
 assert.throws(()=>selectAggregateReview([accepted],'b'.repeat(40)),/exact-head/);
 const superseding={id:2,author_association:'MEMBER',body:marker('worldatlas-review',{head_sha:head,reviewer_worker_id:reviewer,outcome:'accepted'})};
 assert.throws(()=>selectAggregateReview([accepted,superseding],head),/latest/);
});
test('unresolved current-head changes-requested review blocks, superseded and outsider comments do not',()=>{
 const blocked={id:2,author_association:'COLLABORATOR',body:marker('worldatlas-review',{head_sha:head,reviewer_worker_id:'another-worker',outcome:'changes-requested'})};
 assert.throws(()=>selectAggregateReview([root(),blocked],head),/unresolved/);
 assert.equal(selectAggregateReview([root(),{...blocked,author_association:'NONE'}],head).id,1);
 const newer={...blocked,id:3,body:marker('worldatlas-review',{head_sha:head,reviewer_worker_id:'another-worker',outcome:'accepted'})};
 assert.equal(selectAggregateReview([root(),blocked,newer],head).id,1);
});
test('subordinate review binds actual body, URL, author, exact head and same worker',()=>{
 const content={head_sha:head,reviewer_worker_id:reviewer,manifest_sha256:'c'.repeat(64),outcome:'accepted'};
 const comment={id:7,html_url:'https://github.com/ChengshuLi/WorldAtlas/pull/1#issuecomment-7',author_association:'MEMBER',body:marker('worldatlas-review-partition',content)};
 const binding={comment_id:7,comment_url:comment.html_url,body_sha256:sha256(Buffer.from(comment.body))};
 assert.equal(boundPartitionReview(binding,[comment],{head,reviewer}).comment,comment);
 for(const change of [{body:comment.body+'edited'},{html_url:comment.html_url+'wrong'},{author_association:'NONE'}])assert.throws(()=>boundPartitionReview(binding,[{...comment,...change}],{head,reviewer}));
 assert.throws(()=>boundPartitionReview(binding,[],{head,reviewer}),/qualified/);
 assert.throws(()=>boundPartitionReview(binding,[comment],{head:'b'.repeat(40),reviewer}),/head/);
 assert.throws(()=>boundPartitionReview(binding,[comment],{head,reviewer:'other'}),/reviewer/);
 const later={...comment,id:8,body:marker('worldatlas-review-partition',{...content,outcome:'changes-requested'})};
 assert.throws(()=>boundPartitionReview(binding,[comment,later],{head,reviewer}),/Unresolved/);
 assert.equal(boundPartitionReview(binding,[comment,{...later,author_association:'NONE'}],{head,reviewer}).comment.id,7);
});
test('every subordinate manifest must have exactly one actual review binding',()=>{
 const index={partitions:[{path:'one.json'},{path:'two.json'}]},complete={partitions:[{manifest_path:'one.json'},{manifest_path:'two.json'}]};
 assert.doesNotThrow(()=>checkPartitionReviewInventory(complete,index));
 for(const partitions of [[],[complete.partitions[0]],[complete.partitions[0],complete.partitions[0]],[complete.partitions[0],{manifest_path:'absent.json'}]])assert.throws(()=>checkPartitionReviewInventory({partitions},index),/Incomplete/);
});
