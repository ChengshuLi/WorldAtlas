import test from 'node:test';
import assert from 'node:assert/strict';
import {laneForBranch,validateLanePaths,validateIssuePRBody,validateIssueMetadata} from '../scripts/check-handoff-scope.mjs';

test('lane IDs must be explicit and safe',()=>{assert.deepEqual(laneForBranch('research/japan-names'),{lane:'research',id:'japan-names'});for(const branch of ['work','research/../code','engineering/a/b','research/Japan','research/a;echo'])assert.throws(()=>laneForBranch(branch));});
test('research owns only campaign files, excluding shared handovers and other campaigns',()=>{validateLanePaths('research/japan',['research/campaigns/japan/input.json']);for(const file of ['docs/HISTORY_HANDOFF.md','src/main.js','AGENTS.md','.github/workflows/run.yml','docs/HANDOFF_STATUS.md','research/campaigns/italy/input.json','research/campaigns/japan/../italy/notes.md'])assert.throws(()=>validateLanePaths('research/japan',[file]));});
test('engineering preserves research and other engineering progress',()=>{validateLanePaths('engineering/grid',['src/pixel-layer.js','coordination/engineering/grid.json']);for(const file of ['research/campaigns/japan/input.json','coordination/engineering/other.json'])assert.throws(()=>validateLanePaths('engineering/grid',[file]));});
test('special contracts: partial and final PRs link one issue without needing a document tracker ID',()=>{
 assert.deepEqual(validateIssuePRBody('Refs #12\n\nImplement the first part.'),{github_issue:12,issue_action:'reference'});
 assert.deepEqual(validateIssuePRBody('Closes #12\n\nAll acceptance criteria verified.'),{github_issue:12,issue_action:'close'});
 for(const legacy of ['TODO: ENG-08','TODO: obsolete/id','TODO: ENG-01\nTODO: CAM:other:2'])assert.deepEqual(validateIssuePRBody(legacy+'\nCloses #12'),{github_issue:12,issue_action:'close'});
});
test('special contracts: a unique binding accepts punctuation and explanatory prose, including the PR2342 incident',()=>{
 const incident="Refs #2335. Draft combined delivery; actual selected/emitted acceptance and the serialized queue remain root-owned. Original #2302 and #2313 remain incomplete, and #2329 awaits accepted delivery.";
 assert.deepEqual(validateIssuePRBody(incident),{github_issue:2335,issue_action:'reference'});
 for(const action of ['Refs','Closes'])for(const suffix of ['.', '; completed checks', ': verified', ' for this focused change', '. Context from #13 remains separate.']){
  assert.deepEqual(validateIssuePRBody(`${action} #12${suffix}`),{github_issue:12,issue_action:action==='Closes'?'close':'reference'});
 }
});
test('special contracts: PR policy rejects ambiguous issue links and accidental additional closures',()=>{
 for(const body of ['No issue','Refs #0','Refs #12\nCloses #13','Closes #12 and #13','Closes #12\nFixes #13','Fixes #12','Refs #12\nRefs #13','Refs #12\nThis fixes #13 too.','Closes #12\nThis also resolves #13.','Refs #12 and #13','Refs #12, #13','Refs #12. Refs #13','Refs #12. Closes #13','Closes #12. Fixes #13','Refs #12abc','Refs #12#13','Refs #12\nRefs #12'])assert.throws(()=>validateIssuePRBody(body));
});
test('GitHub issue type agrees with its lane and references an open issue',()=>{
 validateIssueMetadata('engineering/grid',{state:'open',labels:[{name:'type:engineering'},{name:'kind:umbrella'}]});
 validateIssueMetadata('research/japan',{state:'open',labels:['type:history-research']});
 for(const issue of [{state:'closed',labels:['type:engineering']},{state:'open',pull_request:{},labels:['type:engineering']},{state:'open',labels:[]},{state:'open',labels:['type:history-research']},{state:'open',labels:['type:engineering','type:future']}])assert.throws(()=>validateIssueMetadata('engineering/grid',issue));
});



test('geography may own narrower subdirectories without acquiring sibling or parent files',()=>{
 const ownedPaths=['data/regional-review/packet/nukunonu/','research/geography/campaign/evidence/'];
 validateLanePaths('geography/repair',['data/regional-review/packet/nukunonu/findings.json','research/geography/campaign/evidence/receipt.json'],{ownedPaths});
 for(const file of ['data/regional-review/packet/README.md','data/regional-review/packet/bounty/findings.json','research/geography/campaign/other/receipt.json'])assert.throws(()=>validateLanePaths('geography/repair',[file],{ownedPaths}),/declared owned_paths/);
 for(const prefix of ['data/regional-review/packet/../other/','data/regional-review/packet//nested/','data/regional-review/packet/./nested/','data/regional-review/packet/nested','data/regional-review/packet/nested.json/','data/geography/packet/nested/'])assert.throws(()=>validateLanePaths('geography/repair',[],{ownedPaths:[prefix]}));
});
