import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
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


test('geography may own narrower subdirectories without acquiring sibling or parent files',()=>{
 const ownedPaths=['data/regional-review/packet/nukunonu/','research/geography/campaign/evidence/'];
 validateLanePaths('geography/repair',['data/regional-review/packet/nukunonu/findings.json','research/geography/campaign/evidence/receipt.json'],{ownedPaths});
 for(const file of ['data/regional-review/packet/README.md','data/regional-review/packet/bounty/findings.json','research/geography/campaign/other/receipt.json'])assert.throws(()=>validateLanePaths('geography/repair',[file],{ownedPaths}),/declared owned_paths/);
 for(const prefix of ['data/regional-review/packet/../other/','data/regional-review/packet//nested/','data/regional-review/packet/./nested/','data/regional-review/packet/nested','data/regional-review/packet/nested.json/','data/geography/packet/nested/'])assert.throws(()=>validateLanePaths('geography/repair',[],{ownedPaths:[prefix]}));
});


test('engineering literal grants retain branch fallback, exact-file and directory boundaries',()=>{
 const ownedPaths=['coordination/engineering/batch/composition/','coordination/engineering/prevention/helper.mjs'];
 validateLanePaths('engineering/repair',['coordination/engineering/repair.json','coordination/engineering/repair/proof.json','coordination/engineering/batch/composition/README.md','coordination/engineering/prevention/helper.mjs'],{ownedPaths});
 for(const file of ['coordination/engineering/batch/README.md','coordination/engineering/batch/composition-sibling/README.md','coordination/engineering/prevention/helper.mjs.bak','coordination/engineering/prevention/helper.mjs/nested','coordination/engineering/unrelated/README.md'])assert.throws(()=>validateLanePaths('engineering/repair',[file],{ownedPaths}));
 for(const grant of ['coordination/engineering/','coordination/engineering','coordination/','scripts/','coordination/engineering/batch/../other/','coordination/engineering/batch//nested/','coordination/engineering/batch/./nested/','coordination/engineering/batch/*','/coordination/engineering/batch/','coordination\\engineering\\batch','research/campaigns/a/','research/geography/a/','data/regional-review/a/'])assert.throws(()=>validateLanePaths('engineering/repair',[],{ownedPaths:[grant]}));
 assert.throws(()=>validateLanePaths('engineering/repair',[],{ownedPaths:[ownedPaths[0],ownedPaths[0]]}));
 for(const file of ['research/campaigns/a/input.json','research/geography/a/input.json','data/regional-review/a/input.json'])assert.throws(()=>validateLanePaths('engineering/repair',[file],{ownedPaths}));
});

test('actual CLI consumes only valid matched engineering issue grants',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-engineering-cli-'));
 const git=args=>execFileSync('git',args,{cwd:directory,encoding:'utf8'});
 const script=fileURLToPath(new URL('../scripts/check-handoff-scope.mjs',import.meta.url));
 const grants=['coordination/engineering/batch/composition/','coordination/engineering/prevention/helper.mjs'];
 const spec={max_prs:1,depends_on:[],mode:'engineering',scope:'Fixture extra coordination routing',owned_paths:grants};
 const block=value=>`<!-- worldatlas-work:v1\n${JSON.stringify(value)}\n-->`;
 const issue={number:42,state:'open',labels:['type:engineering'],body:block(spec)};
 try{
  git(['init','-q']);git(['config','user.email','test@example.com']);git(['config','user.name','Scope test']);
  fs.writeFileSync(path.join(directory,'README.md'),'Fixture baseline\n');git(['add','.']);git(['commit','-qm','base']);const base=git(['rev-parse','HEAD']).trim();
  fs.mkdirSync(path.join(directory,'coordination/engineering/batch/composition'),{recursive:true});fs.mkdirSync(path.join(directory,'coordination/engineering/prevention'),{recursive:true});
  fs.writeFileSync(path.join(directory,'coordination/engineering/batch/composition/README.md'),'Reviewed namespace\n');fs.writeFileSync(path.join(directory,'coordination/engineering/prevention/helper.mjs'),'// Reviewed exact helper\n');git(['add','.']);git(['commit','-qm','declared coordination changes']);
  const run=(actual=issue,body='Refs #42',withIssue=true)=>{
   fs.writeFileSync(path.join(directory,'issue.json'),JSON.stringify(actual));fs.writeFileSync(path.join(directory,'body.md'),body);
   return execFileSync(process.execPath,[script,'--branch','engineering/repair','--base',base,'--pr-body-file','body.md',...(withIssue?['--issue-file','issue.json']:[])],{cwd:directory,encoding:'utf8',stdio:'pipe'});
  };
  assert.equal(JSON.parse(run()).changed_files,2);
  assert.throws(()=>run(issue,'Refs #42',false));
  const failures=[{...issue,body:''},{...issue,body:'<!-- worldatlas-work:v1\n{bad json\n-->'},{...issue,body:block(spec)+'\n'+block(spec)},{...issue,body:block({...spec,mode:'source-only'})},{...issue,body:block({...spec,max_prs:0})},{...issue,body:block({...spec,owned_paths:undefined})},{...issue,body:block({...spec,owned_paths:[grants[0],grants[0]]})},{...issue,body:block({...spec,owned_paths:['coordination/engineering/']})},{...issue,number:43},{...issue,state:'closed'},{...issue,labels:['type:history-research']}];
  for(const actual of failures)assert.throws(()=>run(actual));
  for(const file of ['coordination/engineering/unrelated/README.md','coordination/engineering/batch/composition-sibling/README.md','coordination/engineering/prevention/helper.mjs.bak','research/campaigns/a/input.json','research/geography/a/input.json','data/regional-review/a/input.json']){
   git(['reset','--hard','-q','HEAD']);const target=path.join(directory,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,'Forbidden addition\n');git(['add','.']);git(['commit','-qm','outside reviewed routing']);assert.throws(()=>run());git(['reset','--hard','-q','HEAD~1']);
  }
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('actual linked-issue reader passes engineering grants to git scope and rejects foreign declarations',async()=>{
 const {checkLinkedIssue}=await import('../scripts/check-linked-github-issue.mjs');
 const ownedPaths=['coordination/engineering/batch/','coordination/engineering/prevention/helper.mjs'];
 const issue={number:42,state:'open',labels:['type:engineering'],body:`<!-- worldatlas-work:v1\n${JSON.stringify({max_prs:1,depends_on:[],mode:'engineering',scope:'Fixture routing',owned_paths:ownedPaths})}\n-->`};
 const options={branch:'engineering/repair',event:{repository:{full_name:'ChengshuLi/WorldAtlas'},pull_request:{body:'Refs #42'}},token:'test-only',evidencePolicy:{version:1,mode:'report-only'},fetchIssue:async()=>({ok:true,json:async()=>issue}),base:'base',run:(_command,args)=>args[0]==='diff'?'coordination/engineering/batch/proof.json\0coordination/engineering/prevention/helper.mjs\0':'a'.repeat(40)+'\n'};
 await assert.rejects(checkLinkedIssue({...options,fetchIssue:async()=>({ok:true,json:async()=>({...issue,body:issue.body.replace('\"mode\":\"engineering\"','\"mode\":\"source-only\"')})})}),/engineering mode/);
 const result=await checkLinkedIssue(options);assert.deepEqual(result.owned_paths,ownedPaths);assert.equal(result.git_scope.changed_files,2);
 await assert.rejects(checkLinkedIssue({...options,fetchIssue:async()=>({ok:true,json:async()=>({...issue,body:issue.body.replace('coordination/engineering/batch/','coordination/engineering/unrelated/')})})}));
 await assert.rejects(checkLinkedIssue({...options,fetchIssue:async()=>({ok:true,json:async()=>({...issue,body:issue.body.replace('coordination/engineering/batch/','coordination/engineering/')})})}));
});
