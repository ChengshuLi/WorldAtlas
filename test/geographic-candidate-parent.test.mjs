import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const root = path.resolve(import.meta.dirname, '..');
const workflow = fs.readFileSync(path.join(root,'.github/workflows/merge-integration-checks.yml'),'utf8');
const body = workflow.match(/python3 -I -S -B - <<'PYTHON'\n([\s\S]*?)          PYTHON/)[1].split('\n').map(line=>line.slice(10)).join('\n');
const candidate='c'.repeat(40),head='d'.repeat(40),baseline='b'.repeat(40),main='a'.repeat(40);
function resolve({advanced=false,wrongHead=false,unaccepted=false,extraParent=false,wrongCandidate=false,identicalParents=false,malformedParent=false,wrongMergeBase=false}={}) {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-actual-parent-'));
  try {
    const output=path.join(dir,'out');
    const routes={['git/commits/'+candidate]:{sha:wrongCandidate?main:candidate,parents:[{sha:malformedParent?'invalid':identicalParents?head:baseline},{sha:wrongHead?main:head},...(extraParent?[{sha:main}]:[])]},
      'git/ref/heads/main':{object:{sha:advanced?main:baseline}},
      ['compare/'+baseline+'...'+main+'?per_page=1']:{status:unaccepted?'diverged':'ahead',base_commit:{sha:baseline},merge_base_commit:{sha:unaccepted||wrongMergeBase?head:baseline}}};
    const wrapper=`import io,json,os,urllib.request\nroutes=json.loads(${JSON.stringify(JSON.stringify(routes))})\nclass Response:\n def __init__(self,raw): self.raw=io.BytesIO(raw)\n def __enter__(self): return self\n def __exit__(self,*args): pass\n def read(self,limit): return self.raw.read(limit)\nclass Opener:\n def open(self,request,timeout):\n  assert request.full_url.startswith('https://api.github.com/repos/ChengshuLi/WorldAtlas/')\n  assert timeout==20\n  assert request.get_header('Authorization')=='Bearer fixture'\n  return Response(json.dumps(routes[request.full_url.split('/WorldAtlas/')[1]]).encode())\nurllib.request.build_opener=lambda *args: Opener()\nexec(${JSON.stringify(body)})`;
    const result=spawnSync('python3',['-I','-S','-B','-c',wrapper],{encoding:'utf8',env:{PATH:process.env.PATH,GH_TOKEN:'fixture',CANDIDATE:candidate,REVIEWED_HEAD:head,GITHUB_OUTPUT:output}});
    return {...result,output:fs.existsSync(output)?fs.readFileSync(output,'utf8'):''};
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
}
for(const [name,options] of [['unchanged accepted parent',{}],['advanced accepted main',{advanced:true}]])test('geographic actual-parent resolver accepts '+name,()=>{
 const result=resolve(options);assert.equal(result.status,0,result.stderr);assert.equal(result.output,'baseline='+baseline+'\n');
});
for(const [name,options] of [['wrong reviewed head',{wrongHead:true}],['unaccepted parent',{advanced:true,unaccepted:true}],['extra parent',{extraParent:true}],['wrong candidate',{wrongCandidate:true}],['identical parents',{identicalParents:true}],['malformed parent',{malformedParent:true}],['wrong merge base',{advanced:true,wrongMergeBase:true}]])test('geographic actual-parent resolver rejects '+name+' before output',()=>{
 const result=resolve(options);assert.notEqual(result.status,0);assert.equal(result.output,'');
});
test('profile and geography share one authenticated accepted-parent resolution',()=>{
 const profile=workflow.slice(workflow.indexOf('  profile:'),workflow.indexOf('  evidence:'));
 const geography=workflow.slice(workflow.indexOf('  geography:'),workflow.indexOf('  regression:'));
 assert.equal((workflow.match(/name: Resolve accepted geographic candidate parent/g)||[]).length,1);
 assert.match(profile,/ref: \$\{\{ steps\.geographic_parent\.outputs\.baseline \}\}/);
 assert.match(profile,/geography_baseline: \$\{\{ steps\.geographic_parent\.outputs\.baseline \}\}/);
 assert.match(profile,/PR_GATE_CODE_COMMIT: \$\{\{ steps\.geographic_parent\.outputs\.baseline \}\}/);
 assert.ok(profile.indexOf('Resolve accepted geographic candidate parent')<profile.indexOf('uses: actions/checkout'));
 assert.match(geography,/GEOGRAPHY_BASELINE: \$\{\{ needs\.profile\.outputs\.geography_baseline \}\}/);
 assert.match(geography,/needs\.profile\.outputs\.geography_baseline == github\.event\.pull_request\.base\.sha/);
 assert.match(geography,/geography_software == 'true'\) && github\.sha \|\| needs\.profile\.outputs\.geography_baseline/);
});
