import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const root=path.resolve(import.meta.dirname,'..');
const yaml=fs.readFileSync(path.join(root,'.github/workflows/merge-integration-checks.yml'),'utf8');
const match=yaml.match(/node --input-type=module <<'NODE'\n([\s\S]+?)\n          NODE/);
assert.ok(match,'bounded bootstrap script missing');
// Execute the actual workflow body with its trusted helper at the real source
// path; only read-only GitHub transport is mocked. No live mutation or checkout.
const body=match[1].split('\n').map(line=>line.slice(10)).join('\n')
 .replace("'./scripts/issue-claim-contract.mjs'",JSON.stringify(pathToFileURL(path.join(root,'scripts/issue-claim-contract.mjs')).href));
const head='a'.repeat(40), branch='engineering/geographic-gate-920-20261005-local04';
function probe({delta={},files=[{filename:'scripts/run-geographic-check.py'}],count=files.length}={}) {
 const scratch=path.join(root,'.cache/bootstrap-controls');fs.mkdirSync(scratch,{recursive:true});
 const dir=fs.mkdtempSync(path.join(scratch,'case-'));
 const pr={head:{sha:head,ref:branch,repo:{full_name:'owner/repo'}},base:{ref:'main'},changed_files:count,...delta};
 fs.writeFileSync(path.join(dir,'event.json'),JSON.stringify({pull_request:{number:1}}));
 const fake=`globalThis.fetch=async url=>new Response(JSON.stringify(String(url).includes('/files')?${JSON.stringify(files)}:${JSON.stringify(pr)}),{status:200,headers:{'Content-Type':'application/json'}});\n`;
 try {
  const result=spawnSync(process.execPath,['--input-type=module','-e',fake+body],{cwd:dir,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-read-only-token',GITHUB_EVENT_PATH:path.join(dir,'event.json'),GITHUB_REPOSITORY:'owner/repo',GEOGRAPHY_CANDIDATE:head}});
  const out=path.join(dir,'geography-check.json');
  return {result,report:fs.existsSync(out)?JSON.parse(fs.readFileSync(out)):null};
 } finally {fs.rmSync(dir,{recursive:true,force:true});}
}
test('only named no-data activation branch can report bootstrap absence',()=>{
 const {result,report}=probe();assert.equal(result.status,0,result.stderr);
 assert.equal(report.status,'bootstrap-unavailable');assert.equal(report.geometry_validated,false);assert.equal(report.live_data_changed,false);
});
for(const [name,args] of [
 ['another branch',{delta:{head:{sha:head,ref:'engineering/other',repo:{full_name:'owner/repo'}}}}],
 ['stale head',{delta:{head:{sha:'b'.repeat(40),ref:branch,repo:{full_name:'owner/repo'}}}}],
 ['fork head',{delta:{head:{sha:head,ref:branch,repo:{full_name:'other/repo'}}}}],
 ['live data change',{files:[{filename:'data/geography/part-0.json'}]}],
 ['renamed live data',{files:[{filename:'research/geography/proposal.json',previous_filename:'data/hierarchy.json'}]}],
 ['incomplete inventory',{count:2}],
 ['duplicate inventory',{files:[{filename:'scripts/a.py'},{filename:'scripts/a.py'}]}],
 ['oversized inventory',{count:3001}],
]) test(`bootstrap rejects ${name}`,()=>{
 const {result,report}=probe(args);assert.notEqual(result.status,0);assert.equal(report,null);
});

test('bootstrap job explicitly grants only the read permissions its API calls require',()=>{
 function allowed(text) {
  const job=text.match(/\n  geography:\n([\s\S]*?)(?=\n  [a-z][a-z-]*:|$)/)?.[1];
  const permissions=job?.match(/    permissions:\n([\s\S]*?)    steps:/)?.[1];
  return permissions?.trim()==='contents: read\n      pull-requests: read';
 }
 assert.equal(allowed(yaml),true);
 assert.equal(allowed(yaml.replace('      pull-requests: read\n','')),false);
 assert.equal(allowed(yaml.replace('      pull-requests: read','      pull-requests: write')),false);
});
