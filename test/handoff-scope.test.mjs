import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {laneForBranch,validateLanePaths,checkGitScope,validateIssuePRBody,validateIssueMetadata} from '../scripts/check-handoff-scope.mjs';

test('lane IDs must be explicit and safe',()=>{assert.deepEqual(laneForBranch('research/japan-names'),{lane:'research',id:'japan-names'});for(const branch of ['work','research/../code','engineering/a/b','research/Japan','research/a;echo'])assert.throws(()=>laneForBranch(branch));});
test('research owns only campaign files, excluding shared handovers and other campaigns',()=>{validateLanePaths('research/japan',['research/campaigns/japan/input.json']);for(const file of ['docs/HISTORY_HANDOFF.md','src/main.js','AGENTS.md','.github/workflows/run.yml','docs/HANDOFF_STATUS.md','research/campaigns/italy/input.json','research/campaigns/japan/../italy/notes.md'])assert.throws(()=>validateLanePaths('research/japan',[file]));});
test('engineering preserves research and other engineering progress',()=>{validateLanePaths('engineering/grid',['src/pixel-layer.js','coordination/engineering/grid.json']);for(const file of ['research/campaigns/japan/input.json','coordination/engineering/other.json'])assert.throws(()=>validateLanePaths('engineering/grid',[file]));});
test('partial and final PRs link one issue without needing a document tracker ID',()=>{
 assert.deepEqual(validateIssuePRBody('Refs #12\n\nImplement the first part.'),{github_issue:12,issue_action:'reference'});
 assert.deepEqual(validateIssuePRBody('Closes #12\n\nAll acceptance criteria verified.'),{github_issue:12,issue_action:'close'});
 assert.deepEqual(validateIssuePRBody('TODO: ENG-08\nCloses #12'),{todo_id:'ENG-08',github_issue:12,issue_action:'close'});
});
test('PR policy rejects ambiguous issue links and accidental additional closures',()=>{
 for(const body of ['No issue','Refs #0','Refs #12\nCloses #13','Closes #12 and #13','Closes #12\nFixes #13','Fixes #12','Refs #12\nRefs #13','Refs #12\nThis fixes #13 too.','Closes #12\nThis also resolves #13.','TODO: ENG-01\nTODO: ENG-02\nCloses #12'])assert.throws(()=>validateIssuePRBody(body));
});
test('GitHub issue type agrees with its lane and references an open issue',()=>{
 validateIssueMetadata('engineering/grid',{state:'open',labels:[{name:'type:engineering'},{name:'kind:umbrella'}]});
 validateIssueMetadata('research/japan',{state:'open',labels:['type:history-research']});
 for(const issue of [{state:'closed',labels:['type:engineering']},{state:'open',pull_request:{},labels:['type:engineering']},{state:'open',labels:[]},{state:'open',labels:['type:history-research']},{state:'open',labels:['type:engineering','type:future']}])assert.throws(()=>validateIssueMetadata('engineering/grid',issue));
});
test('real git diff checks rename source paths, not only allowed destinations',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-lanes-'));
 const git=args=>execFileSync('git',args,{cwd:directory,encoding:'utf8'});
 try{
  git(['init','-q']);git(['config','user.email','test@example.com']);git(['config','user.name','Scope test']);fs.mkdirSync(path.join(directory,'src'));fs.writeFileSync(path.join(directory,'src/main.js'),'Original source\n');git(['add','.']);git(['commit','-qm','base']);const base=git(['rev-parse','HEAD']).trim();
  fs.mkdirSync(path.join(directory,'research/campaigns/japan'),{recursive:true});git(['mv','src/main.js','research/campaigns/japan/notes.md']);git(['commit','-qm','rename source into campaign']);
  assert.throws(()=>checkGitScope({branch:'research/japan',base,run:(command,args,options)=>execFileSync(command,args,{...options,cwd:directory})}),/Research changes/);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
test('another lane advancing work is not mistaken for this branch changing its files',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-lanes-base-'));
 const git=args=>execFileSync('git',args,{cwd:directory,encoding:'utf8'});
 try{
  git(['init','-q']);git(['config','user.email','test@example.com']);git(['config','user.name','Scope test']);fs.mkdirSync(path.join(directory,'src'));fs.writeFileSync(path.join(directory,'src/main.js'),'Original source\n');git(['add','.']);git(['commit','-qm','base']);const original=git(['rev-parse','HEAD']).trim();
  git(['checkout','-qb','research/japan']);fs.mkdirSync(path.join(directory,'research/campaigns/japan'),{recursive:true});fs.writeFileSync(path.join(directory,'research/campaigns/japan/notes.md'),'Research\n');git(['add','.']);git(['commit','-qm','research']);const head=git(['rev-parse','HEAD']).trim();
  git(['checkout','-q','--detach',original]);fs.writeFileSync(path.join(directory,'src/main.js'),'Unrelated engineering advance\n');git(['add','.']);git(['commit','-qm','engineering integration']);const base=git(['rev-parse','HEAD']).trim();
  const result=checkGitScope({branch:'research/japan',base,head,run:(command,args,options)=>execFileSync(command,args,{...options,cwd:directory})});assert.equal(result.changed_files,1);assert.equal(result.merge_base,original);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('remote issue validation reads only the event repository and requires successful labeled issue metadata',async()=>{
 const {checkLinkedIssue}=await import('../scripts/check-linked-github-issue.mjs');
 const event={repository:{full_name:'ChengshuLi/WorldAtlas'},pull_request:{body:'Refs #12'}};
 let requests=0;
 const fetchIssue=async(url,options)=>{requests++;assert.equal(url,'https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/12');assert.equal(options.headers.Authorization,'Bearer test-only');return {ok:true,json:async()=>({state:'open',body:'<!-- worldatlas-work:v1\n{"max_prs":1,"depends_on":[],"mode":"source-only","scope":"Synthetic source-only fixture"}\n-->',labels:[{name:'type:history-research'}]})};};
 assert.deepEqual(await checkLinkedIssue({branch:'research/japan',event,token:'test-only',fetchIssue,evidencePolicy:{version:1,mode:'report-only'}}),{github_issue:12,issue_action:'reference',issue_type:'type:history-research',evidence_policy:{required:false,legacy:false,decision:'Reporting rollout: no declared evidence contract'}});
 await assert.rejects(checkLinkedIssue({branch:'engineering/grid',event,token:'test-only',fetchIssue,evidencePolicy:{version:1,mode:'report-only'}}),/type:engineering/);
 await assert.rejects(checkLinkedIssue({branch:'research/japan',event,fetchIssue}),/token/);
 assert.equal(requests,2);
 await assert.rejects(checkLinkedIssue({branch:'research/japan',event,token:'test-only',fetchIssue:async()=>({ok:false,status:404})}),/HTTP 404/);
});
