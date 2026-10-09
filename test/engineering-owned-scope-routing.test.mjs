import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateLanePaths} from '../scripts/check-handoff-scope.mjs';

test('engineering literal grants retain branch fallback, exact-file and directory boundaries',()=>{
 const ownedPaths=['coordination/engineering/batch/composition/','coordination/engineering/prevention/helper.mjs','.github/workflows/fixture.yml'];
 validateLanePaths('engineering/repair',['coordination/engineering/repair.json','coordination/engineering/repair/proof.json','coordination/engineering/batch/composition/README.md','coordination/engineering/prevention/helper.mjs','.github/workflows/fixture.yml'],{ownedPaths});
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
