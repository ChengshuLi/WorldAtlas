import test from 'node:test';
import assert from 'node:assert/strict';
import {sha256} from '../scripts/evidence-quality.mjs';
import {selectAggregateReview,boundPartitionReview,checkPartitionReviewInventory} from '../scripts/validate-evidence-partition-review.mjs';
const head='a'.repeat(40),reviewer='independent-worker';
const marker=(name,value)=>'<!-- '+name+':v1\n'+JSON.stringify(value)+'\n-->';
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
