import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {laneForBranch,validateLanePaths,validateTrackerChange,checkGitScope,validateIssuePRBody} from '../scripts/check-handoff-scope.mjs';

const header='| ID | Scope | Status | Raised | Recorded | Completed | Evidence |\n| --- | --- | --- | --- | --- | --- | --- |';
const doc=rows=>`Instructions\n<!-- RESEARCH-CAMPAIGNS:START -->\n${header}\n${rows.join('\n')}\n<!-- RESEARCH-CAMPAIGNS:END -->\nEnd instructions\n`;
const row=(id,status='active',date='—',evidence='—')=>`| CAM:${id}:1 | Dated names | ${status} | unknown | 2026-10-02 | ${date} | ${evidence} |`;

test('lane IDs must be explicit and safe',()=>{assert.deepEqual(laneForBranch('research/japan-names'),{lane:'research',id:'japan-names'});for(const branch of ['work','research/../code','engineering/a/b','research/Japan','research/a;echo'])assert.throws(()=>laneForBranch(branch));});
test('research owns its campaign files and tracker, excluding code and other campaigns',()=>{validateLanePaths('research/japan',['research/campaigns/japan/input.json','docs/HISTORY_HANDOFF.md']);for(const file of ['src/main.js','AGENTS.md','.github/workflows/run.yml','docs/HANDOFF_STATUS.md','research/campaigns/italy/input.json','research/campaigns/japan/../italy/notes.md'])assert.throws(()=>validateLanePaths('research/japan',[file]));});
test('engineering preserves research and other engineering progress',()=>{validateLanePaths('engineering/grid',['src/pixel-layer.js','coordination/engineering/grid.json']);for(const file of ['research/campaigns/japan/input.json','coordination/engineering/other.json'])assert.throws(()=>validateLanePaths('engineering/grid',[file]));});
test('research can add owned rows and mark them done with a date and evidence',()=>{const first=doc([row('japan')]);validateTrackerChange('research/japan',doc([]),first);validateTrackerChange('research/japan',first,doc([row('japan','done','2026-10-02','bundle/import-receipts.json')]));});
test('research cannot change instructions, other campaign rows, global rows or delete records',()=>{const original=doc([row('japan'),row('italy')]);for(const changed of [original.replace('Instructions','Changed instructions'),doc([row('japan')]),doc([row('japan'),row('italy','blocked')]),doc([row('japan'),row('italy'),row('france')])])assert.throws(()=>validateTrackerChange('research/japan',original,changed));});
test('completion requires a real date and an evidence path',()=>{for(const changed of [row('japan','done','—','receipt.json'),row('japan','done','2026-02-31','receipt.json'),row('japan','done','2026-10-02','—'),row('japan','active','2026-10-02','receipt.json')])assert.throws(()=>validateTrackerChange('research/japan',doc([]),doc([changed])));});
test('original tracker dates and completed milestones remain retained',()=>{const original=doc([row('japan')]),done=doc([row('japan','done','2026-10-02','receipt.json')]);assert.throws(()=>validateTrackerChange('research/japan',original,original.replace('| unknown |','| 2026-10-01 |')));assert.throws(()=>validateTrackerChange('research/japan',done,done.replace('Dated names','New scope')));assert.throws(()=>validateTrackerChange('research/japan',done,original));});
test('a research PR cannot combine two separate TODO items',()=>{assert.throws(()=>validateTrackerChange('research/japan',doc([]),doc([row('japan'),row('japan').replace(':1 |',':2 |')])),/One research TODO/);});
test('PR policy requires exactly one TODO issue and one linked GitHub issue',()=>{assert.deepEqual(validateIssuePRBody('TODO: ENG-01-01\nCloses #12\n\nValidation passed.'),{todo_id:'ENG-01-01',github_issue:12});for(const body of ['No issue','TODO: ENG-01\nCloses #12\nCloses #13','TODO: ENG-01\nTODO: ENG-02\nCloses #12','TODO: ENG-01\nCloses #12 and #13','TODO: ENG-01\nCloses #12\nFixes #13'])assert.throws(()=>validateIssuePRBody(body));});
test('engineering may update handover instructions but not campaign-owned rows',()=>{validateTrackerChange('engineering/grid',doc([row('japan')]),doc([row('japan')]).replace('Instructions','Updated instructions'));assert.throws(()=>validateTrackerChange('engineering/grid',doc([row('japan')]),doc([row('japan','done','2026-10-02','receipt.json')])));});
test('tracker markers and unique row identities are mandatory',()=>{for(const changed of [doc([]).replace('RESEARCH-CAMPAIGNS:END','REMOVED'),doc([row('japan'),row('japan')]),doc([])+'<!-- RESEARCH-CAMPAIGNS:START -->'])assert.throws(()=>validateTrackerChange('research/japan',doc([]),changed));});
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
