import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const focused=['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
  'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration',
  'merge-integration-client','merge-integration-entrypoint','integration-proof'];
const helper='coordination/engineering/eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';

function fixture(t,{full=false,helperBody,skip=false}={}) {
  // This is a tiny actual runner boundary fixture, not a scientific restoration.
  const sources=['scripts/run-integration-tests.mjs','scripts/compile-hosted-migrations.mjs'];
  const bodies=sources.map(name=>{
    const p=path.join(repo,name),s=fs.lstatSync(p);
    assert.ok(s.isFile()&&!s.isSymbolicLink()&&s.size<64*1024);
    return fs.readFileSync(p);
  });
  const cache=path.join(repo,'.cache');fs.mkdirSync(cache,{recursive:true});
  const root=fs.mkdtempSync(path.join(cache,'integration-profile-boundary-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  function write(name,body) {const p=path.join(root,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,body,{flag:'wx'});}
  write('package.json','{"type":"module"}\n');
  sources.forEach((name,i)=>write(name,bodies[i]));
  const names=full?['probe']:focused;
  for(const name of names)write(`test/${name}.test.mjs`,
    `import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
test('actual selected test',${skip?'{skip:true},':''}()=>{
  assert.equal(fs.existsSync('restored-fixture.json'),${full});
  fs.writeFileSync('tests-reached-'+${JSON.stringify(name)},'reached',{flag:'wx'});
});\n`);
  if(helperBody!==undefined)write(helper,helperBody);
  return {root,run(profile=full?'full':'evidence',shard='0') {
    const env={...process.env,INTEGRATION_PROFILE:profile,INTEGRATION_SHARD:shard};
    // Match a plain CLI launch, rather than inheriting node:test's recursion tag.
    delete env.NODE_TEST_CONTEXT;
    return spawnSync(process.execPath,['scripts/run-integration-tests.mjs'],{
      cwd:root,encoding:'utf8',timeout:30000,maxBuffer:1024*1024,
      env
    });
  }};
}

test('real evidence entry runs every selected test with no canonical namespace',t=>{
  const f=fixture(t),r=f.run();assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/# skipped 0/);
  assert.ok(!fs.existsSync(path.join(f.root,'coordination')));
  assert.equal(fs.readdirSync(f.root).filter(n=>n.startsWith('tests-reached-')).length,focused.length);
  assert.ok(!r.stdout.includes('canonical_checkout'));
});
test('real full entry calls canonical preparation before selected readers',t=>{
  const f=fixture(t,{full:true,helperBody:`import fs from 'node:fs';
export function prepareCanonicalCheckout(){fs.writeFileSync('restored-fixture.json','{"complete":true}',{flag:'wx'});return {fixture_only:true};}\n`});
  const r=f.run();assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/canonical_checkout/);
  assert.match(r.stdout,/# skipped 0/);assert.ok(fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real full entry rejects an absent canonical helper before tests',t=>{
  const f=fixture(t,{full:true}),r=f.run();assert.notEqual(r.status,0);
  assert.match(r.stderr,/ERR_MODULE_NOT_FOUND/);assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real full entry propagates canonical input rejection before tests',t=>{
  const f=fixture(t,{full:true,helperBody:"export function prepareCanonicalCheckout(){throw Error('missing authenticated canonical input');}\n"});
  const r=f.run();assert.notEqual(r.status,0);assert.match(r.stderr,/missing authenticated canonical input/);
  assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real evidence entry preserves the zero-skips safeguard',t=>{
  const f=fixture(t,{skip:true}),r=f.run();assert.notEqual(r.status,0);
  assert.match(r.stderr,/Regression did not establish zero skipped tests/);
});
test('invalid profile rejects before either restoration or tests',t=>{
  const f=fixture(t),r=f.run('invalid');assert.notEqual(r.status,0);
  assert.match(r.stderr,/Invalid trusted integration test profile/);
  assert.ok(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
});
