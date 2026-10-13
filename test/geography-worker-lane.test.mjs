import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {laneForBranch,validateLanePaths,validateIssueMetadata,checkGitScope,validateGeographyOwnedPaths} from '../scripts/check-handoff-scope.mjs';
import {workSpec,transitionClaim,readClaim,renderClaim,verifyIssueScope} from '../scripts/issue-claim-contract.mjs';
import {checkLinkedIssue} from '../scripts/check-linked-github-issue.mjs';

const owned=['data/regional-review/regional-review-packet-a/'],now=Date.parse('2026-10-02T22:00:00Z');
const spec={max_prs:2,depends_on:[],mode:'geography',scope:'Review the exact published packet, retaining source evidence and recommendations only',owned_paths:owned};
const issue=(scope=spec)=>({number:507,created_at:'2020-01-01T00:00:00Z',state:'open',labels:['type:geography','kind:work-item','status:ready'],body:`<!-- worldatlas-work:v1\n${JSON.stringify(scope)}\n-->`});
const request=(extra={})=>({action:'claim',worker_id:'geo-worker',branch:'geography/packet-a',claim_id:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',request_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',...extra});
const comment=claim=>({id:88,user:{login:'github-actions[bot]'},body:renderClaim(claim)});

test('geography has its own branch and exactly one matching type',()=>{
 assert.deepEqual(laneForBranch('geography/packet-a'),{lane:'geography',id:'packet-a'});
 validateIssueMetadata('geography/packet-a',issue());
 for(const branch of ['engineering/packet-a','research/packet-a'])assert.throws(()=>validateIssueMetadata(branch,issue()),/type:/);
 assert.throws(()=>validateIssueMetadata('geography/packet-a',{...issue(),labels:['type:geography','type:engineering']}),/exactly one/);
});
test('declared geography ownership is finite, safe and limited to source evidence namespaces',()=>{
 validateGeographyOwnedPaths(owned);
 validateGeographyOwnedPaths(['research/geography/iberya-source-a/']);
 validateGeographyOwnedPaths(['data/regional-review/a/nested/']);
 for(const paths of [undefined,[],['data/'],['src/a/'],['research/campaigns/a/'],['data/regional-review/'],['data/regional-review/a/../b/'],['/data/regional-review/a/'],['data/regional-review/a\\b/'],['data/regional-review/a//'],['data/regional-review/a'],[...owned,...owned],Array.from({length:9},(_,i)=>`research/geography/a${i}/`)])assert.throws(()=>validateGeographyOwnedPaths(paths));
});
test('geography cannot edit core, history, another packet or an undeclared proposal directory',()=>{
 validateLanePaths('geography/packet-a',[owned[0]+'sources.json',owned[0]+'reproduce/check.py'],{ownedPaths:owned});
 for(const file of ['data/hierarchy.json','data/world-index.json','data/canonical-grid/a.bin','src/main.js','hosted/server.js','drizzle/a.sql','research/campaigns/history-a/input.json','data/regional-review/other/a.json','research/geography/other/a.json','docs/GEOGRAPHY_HANDOFF.md',owned[0]+'../other/a.json'])assert.throws(()=>validateLanePaths('geography/packet-a',[file],{ownedPaths:owned}));
 assert.throws(()=>validateLanePaths('geography/packet-a',[owned[0]+'source.json']),/owned_paths/);
});
test('engineering consumes but preserves geography evidence while existing lanes still work',()=>{
 validateLanePaths('engineering/integrate',['data/hierarchy.json','scripts/integrate-geography.mjs']);
 for(const file of [owned[0]+'sources.json','research/geography/source-a/proposal.json','research/campaigns/history-a/input.json'])assert.throws(()=>validateLanePaths('engineering/integrate',[file]),/preserve/);
 validateLanePaths('research/history-a',['research/campaigns/history-a/input.json']);
});
test('geography scope comes from the issue without entering live-operation reservations',()=>{
 assert.deepEqual(verifyIssueScope({branch:'geography/packet-a',issue:issue()}).owned_paths,owned);
 assert.throws(()=>transitionClaim({issue:issue(),comments:[],request:request(),now}),/only for engineering live/);
 for(const mode of ['engineering','source-only','content'])assert.throws(()=>verifyIssueScope({branch:'geography/packet-a',issue:issue({...spec,mode,geographic_release:'r',scope_manifest:'s',territory_match_review:'t'})}),/mode.*lane/);
 assert.throws(()=>workSpec(issue({...spec,owned_paths:['data/hierarchy.json']}).body),/owned_paths/);
 // Historical canonical comments remain parseable but confer no ordinary scope.
 const legacy={version:1,active:true,worker_id:'legacy',claim_id:'legacy',branch:'geography/packet-a',expires_at:'2020-01-01',mode:'geography',owned_paths:owned};
 assert.deepEqual(readClaim([comment(legacy)]).owned_paths,owned);
 assert.throws(()=>readClaim([comment({...legacy,owned_paths:['data/']})]),/owned_paths/);
});
test('actual linked GitHub issue supplies geography ownership, not a PR-controlled declaration',async()=>{
 const event={repository:{full_name:'ChengshuLi/WorldAtlas'},pull_request:{body:'Refs #507\nUntrusted owned_paths: data/hierarchy.json'}};
 const result=await checkLinkedIssue({branch:'geography/packet-a',event,token:'test-only',fetchIssue:async()=>({ok:true,json:async()=>issue()})});
 assert.deepEqual(result.owned_paths,owned);assert.equal(result.issue_type,'type:geography');
 await assert.rejects(checkLinkedIssue({branch:'geography/packet-a',event,token:'test-only',fetchIssue:async()=>({ok:true,json:async()=>issue({...spec,owned_paths:['data/']})})}),/owned_paths/);
});
test('real geography Git scope checks renamed source paths, symlinks and issue-backed CLI ownership',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-geography-lane-')),git=args=>execFileSync('git',args,{cwd:directory,encoding:'utf8'}),run=(command,args,options)=>execFileSync(command,args,{...options,cwd:directory});
 try{
  git(['init','-q']);git(['config','user.email','scope@example.com']);git(['config','user.name','Scope test']);fs.mkdirSync(path.join(directory,'src'));fs.writeFileSync(path.join(directory,'src/core.js'),'original\n');git(['add','.']);git(['commit','-qm','base']);const base=git(['rev-parse','HEAD']).trim();
  fs.mkdirSync(path.join(directory,owned[0]),{recursive:true});git(['mv','src/core.js',owned[0]+'notes.js']);git(['commit','-qm','rename protected core']);
  assert.throws(()=>checkGitScope({branch:'geography/packet-a',base,run,ownedPaths:owned}),/declared owned_paths/);
  git(['reset','--hard',base]);fs.mkdirSync(path.join(directory,owned[0]),{recursive:true});fs.symlinkSync('../../../src/core.js',path.join(directory,owned[0]+'source.js'));git(['add','.']);git(['commit','-qm','unsafe link']);
  assert.throws(()=>checkGitScope({branch:'geography/packet-a',base,run,ownedPaths:owned}),/not symlinks/);
  git(['reset','--hard',base]);fs.mkdirSync(path.join(directory,owned[0]),{recursive:true});fs.writeFileSync(path.join(directory,owned[0]+'source.json'),'{}\n');git(['add','.']);git(['commit','-qm','scoped evidence']);
  assert.equal(checkGitScope({branch:'geography/packet-a',base,run,ownedPaths:owned}).changed_files,1);
  const actualIssue=path.join(directory,'actual-issue.json');fs.writeFileSync(actualIssue,JSON.stringify(issue()));
  const checker=new URL('../scripts/check-handoff-scope.mjs',import.meta.url);
  const cli=execFileSync(process.execPath,[checker.pathname,'--branch','geography/packet-a','--base',base,'--issue-file',actualIssue],{cwd:directory,encoding:'utf8'});
  assert.equal(JSON.parse(cli).scope_check,'passed');
  const remote=await checkLinkedIssue({branch:'geography/packet-a',base,run,event:{repository:{full_name:'ChengshuLi/WorldAtlas'},pull_request:{body:'Refs #507'}},token:'test-only',fetchIssue:async()=>({ok:true,json:async()=>issue()})});
  assert.equal(remote.git_scope.changed_files,1);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
