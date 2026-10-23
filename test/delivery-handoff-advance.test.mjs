import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {valueBytes} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {constructOriginalAuthority, constructAuthorityRegistry} from '../scripts/delivery-handoff-advance.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {locate} from '../scripts/delivery-handoff-advance.mjs';
const digest = raw => createHash('sha256').update(raw).digest('hex');
const commit = 'a'.repeat(40);
function fixture() {
  const files = new Map(), pins = new Map();
  function add(version, name, value) {
    const raw = Buffer.from(JSON.stringify(value) + '\n');
    const pin = {commit: version, path: name, mode: '100644', git_blob_oid: digest(raw).slice(0, 40), bytes: raw.length, sha256: digest(raw)};
    files.set(version + ':' + name, raw); pins.set(version + ':' + name, pin); return pin;
  }
  const reader = {pin: (version, name) => {const pin = pins.get(version + ':' + name); assert.ok(pin, name); return pin;},
    read: pin => files.get(pin.commit + ':' + pin.path), json: pin => JSON.parse(files.get(pin.commit + ':' + pin.path))};
  return {reader, add};
}
test('locators derive descriptors and refuse handwritten hashes', () => {
  const f = fixture(); const pin = f.add(commit, 'one.json', {real: true});
  assert.deepEqual(locate(f.reader, {commit, path: 'one.json'}), pin);
  assert.throws(() => locate(f.reader, {commit, path: 'one.json', sha256: pin.sha256}), /handwritten/);
  assert.throws(() => locate(f.reader, {commit, path: '../one.json'}), /locator/);
});
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
for (const phase of ['advance', 'status']) test('removed '+phase+' CLI refuses before config reads or destination creation', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-removed-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const script = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  const env = {...process.env}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
  assert.throws(() => execFileSync(process.execPath, [script, phase, 'missing.json', '.cache/delivery-handoff/one'],
    {cwd: root, env, stdio: ['ignore', 'pipe', 'pipe']}), error =>
    error.stderr.toString().includes('Use prepare-delivery-handoff.mjs requests|native-requests|retain|'));
  assert.deepEqual(fs.readdirSync(root), []);
});

// authority constructor controls
{

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HEAD = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: REPO, encoding: 'utf8'}).trim();
const RETAINED = '5735ce1e6d91fba7d8b3b8e1efcf09a0f7ef4dc4';
const ACCEPTED = '9e7b93f43f8a2dccffc23cb1c9e6cd60613f3b9c';
const PREFIX = 'coordination/engineering/nor-grc-congo-delivery-20261011/';
const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
  GIT_AUTHOR_NAME: 'Authority test', GIT_AUTHOR_EMAIL: 'test@example.invalid', GIT_COMMITTER_NAME: 'Authority test', GIT_COMMITTER_EMAIL: 'test@example.invalid'};
const git = (root, args, input) => {
  const command = ['-c', 'core.hooksPath=/dev/null', '-C', root];
  const output = args[0] === 'show' ? {maxBuffer: Number(execFileSync('git', [...command, 'cat-file', '-s', args[1]], {env})) + 1} : {};
  return execFileSync('git', [...command, ...args], {env, input, ...output, stdio: ['pipe', 'pipe', 'pipe']});
};
class OfflineReader extends ImmutableReader {
  git(...args) { return git(this.repo, args); }
}
const reader = (repo = REPO) => new OfflineReader(repo, HEAD);
const realFixture = process.env.WORLDATLAS_DELIVERY_FIXTURE === '1';
function deriveCurrent13Fixture(repo = REPO) {
  const read = p => JSON.parse(git(repo, ['show', p.commit + ':' + p.path]));
  const locate = p => ({commit: p.commit, path: p.path});
  const config = read({commit: HEAD, path: 'coordination/engineering/delivery-handoff-20261011/current13-compose.json'});
  if (config.registries.length !== 1) throw Error('Expected the single accepted current13 registry');
  const registry = locate(config.registries[0]), accepted = read(registry);
  const prefix = 'coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/authorities/';
  const entries = accepted.entries.filter(e => e.source_authority.path.startsWith(prefix));
  if (entries.length !== 5) throw Error('Expected all five historical current13 authority groups');
  const authorities = entries.map(entry => {
    const binding = read(entry.source_authority), request = read(binding.original_pins.native_request), spec = request.additive;
    const matches = spec.inputs.filter(p => p.path === spec.publication_path);
    if (matches.length !== 1) throw Error('Ambiguous original SOURCE publication');
    const aliases = (binding.source_output_aliases ?? []).filter(a => a.original.path === matches[0].path);
    if (aliases.length > 1) throw Error('Ambiguous retained SOURCE publication alias');
    const source = aliases.length ? aliases[0].published : matches[0];
    return {observations: {source_publication: locate(source), native_publication: locate(binding.native_proof.publication),
      native_operating: locate(binding.native_proof.operating)},
    committed: {rule_preimage: locate(entry.rule_preimage), source_authority: locate(entry.source_authority)}};
  });
  return {registry, authorities};
}
const current13 = realFixture ? deriveCurrent13Fixture() : null;
// Retained offline metadata is an explicit suite, not skipped default-CI work.
const fixtureTest = (name, fn) => { if (realFixture) test(name, fn); };
const byGroup = group => {
  const item = current13.authorities.find(a => a.committed.source_authority.path.includes('/' + group.toUpperCase() + '/'));
  assert.ok(item); return structuredClone(item);
};
const locators = group => byGroup(group).observations;
const read = (name, commit = ACCEPTED) => git(REPO, ['show', commit + ':' + name]);
const registryLocators = group => byGroup(group).committed;

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'authority-fixture-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  git(root, ['init', '-q']);
  const objects = git(REPO, ['rev-parse', '--path-format=absolute', '--git-path', 'objects']).toString().trim();
  fs.mkdirSync(path.join(root, '.git/objects/info'), {recursive: true});
  fs.writeFileSync(path.join(root, '.git/objects/info/alternates'), objects + '\n');
  return {root, commit(files) {
    const rows = Object.entries(files).map(([name, raw]) => {
      assert.ok(!name.includes('/'));
      const oid = git(root, ['hash-object', '-w', '--stdin'], Buffer.isBuffer(raw) ? raw : valueBytes(raw)).toString().trim();
      return '100644 blob ' + oid + '\t' + name + '\n';
    });
    const tree = git(root, ['mktree'], rows.sort().join('')).toString().trim();
    return git(root, ['commit-tree', tree], 'Bounded adverse fixture\n').toString().trim();
  }};
}

fixtureTest('real GRC-001 authority bytes replay exactly from three locators using unchanged custody qualifiers', () => {
  const r = reader(), result = constructOriginalAuthority(r, locators('grc-001'));
  for (const [name, raw] of Object.entries(result.products))
    assert.deepEqual(raw, read(PREFIX + 'combined-selected/authorities/GRC-001/' + name));
  const ledger = JSON.parse(read(result.ledger.path, result.ledger.commit));
  assert.deepEqual(result.component_ids, ledger.scope_ids);
  assert.equal(result.rule_sha256, ledger.rule_sha256);
  assert.ok(result.limitations.every(s => !s.includes('approved')));
  const readPaths = [...r.inventory.values()].map(p => p.path);
  assert.ok(!readPaths.some(p => p.includes('/payloads/') || p.includes('/assets-bank/') || p.startsWith('data/geography/')),
    'Constructor must not hydrate original GIS/scientific operands');
});

fixtureTest('same immutable inputs replay deterministic authority output on a fresh reader', () => {
  const a = constructOriginalAuthority(reader(), locators('grc-001'));
  const b = constructOriginalAuthority(reader(), locators('grc-001'));
  assert.deepEqual(a, b);
});

fixtureTest('registry derives exact accepted entry after the generated authority bodies are committed', () => {
  const pair = registryLocators('GRC-001');
  const result = JSON.parse(constructAuthorityRegistry(reader(), [pair])['authority-registry.json']);
  const expected = JSON.parse(read(PREFIX + 'combined-selected/authority-registry.json')).entries
    .find(e => e.source_authority.path === pair.source_authority.path);
  assert.deepEqual(result.entries, [expected]);
});

fixtureTest('wrong real SOURCE/NATIVE joins and wrong qualified operating proof fail', () => {
  const wrongSource = locators('grc-001'); wrongSource.source_publication = locators('grc-002').source_publication;
  assert.throws(() => constructOriginalAuthority(reader(), wrongSource), /alias.*differ|predecessor|source receipt/i);
  const wrongNative = locators('grc-001'); wrongNative.native_publication = locators('grc-002').native_publication;
  assert.throws(() => constructOriginalAuthority(reader(), wrongNative), /alias.*differ|predecessor|source receipt/i);
  const wrongTerminal = locators('grc-001'); wrongTerminal.native_operating = locators('grc-002').native_operating;
  assert.throws(() => constructOriginalAuthority(reader(), wrongTerminal), /Unqualified original native operating/);
});

fixtureTest('missing inputs, handwritten derived fields and uncommitted or partial bodies fail', t => {
  for (const mutate of [x => delete x.native_operating, x => x.extra = x.native_publication,
    x => x.native_publication.sha256 = '0'.repeat(64), x => x.native_publication.component_ids = ['fabricated'],
    x => x.native_publication.path = '../publication.json', x => x.native_publication.commit = '0'.repeat(40)]) {
    const inputs = locators('grc-001'); mutate(inputs);
    assert.throws(() => constructOriginalAuthority(reader(), inputs));
  }
  const f = fixture(t), publication = JSON.parse(read(locators('grc-001').source_publication.path, RETAINED));
  const commit = f.commit({'publication.json': publication});
  const inputs = locators('grc-001'); inputs.source_publication = {commit, path: 'publication.json'};
  assert.throws(() => constructOriginalAuthority(reader(f.root), inputs), /whole ordinary Git input/);
});

fixtureTest('coherently committed failed terminal cannot produce an authority', t => {
  const f = fixture(t), inputs = locators('grc-001');
  const terminal = JSON.parse(read(inputs.native_operating.path, RETAINED));
  terminal.exit.code = 1;
  const commit = f.commit({'terminal.json': terminal}); inputs.native_operating = {commit, path: 'terminal.json'};
  assert.throws(() => constructOriginalAuthority(reader(f.root), inputs), /Unqualified original native operating/);
});

fixtureTest('registry rejects duplicate, cross-rule and coherently drifted source-authority joins', t => {
  const pair = registryLocators('GRC-001');
  assert.throws(() => constructAuthorityRegistry(reader(), [pair, pair]), /Duplicate committed/);
  assert.throws(() => constructAuthorityRegistry(reader(), [{...pair, source_authority: registryLocators('GRC-002').source_authority}]), /relabelled original/);
  const f = fixture(t), binding = JSON.parse(read(pair.source_authority.path, pair.source_authority.commit));
  const other = JSON.parse(read(registryLocators('GRC-002').source_authority.path, pair.source_authority.commit));
  binding.original_pins.source_facts = other.original_pins.source_facts;
  const commit = f.commit({'binding.json': binding});
  assert.throws(() => constructAuthorityRegistry(reader(f.root), [{...pair, source_authority: {commit, path: 'binding.json'}}]), /facts rebound|predecessor|source receipt/i);
});

fixtureTest('all five current13 authorities replay exact bodies and registry from discovered accepted locators', () => {
  assert.deepEqual(deriveCurrent13Fixture(), current13);
  let total = 0;
  for (const item of current13.authorities) {
    const result = constructOriginalAuthority(reader(), item.observations);
    assert.deepEqual(result.products['original-rule-preimage.json'], read(item.committed.rule_preimage.path, item.committed.rule_preimage.commit));
    assert.deepEqual(result.products['authority-binding.json'], read(item.committed.source_authority.path, item.committed.source_authority.commit));
    total += result.component_ids.length;
  }
  assert.equal(total, 13);
  const pairs = current13.authorities.map(a => a.committed).reverse();
  const actual = JSON.parse(constructAuthorityRegistry(reader(), pairs)['authority-registry.json']);
  const paths = new Set(pairs.map(a => a.source_authority.path));
  const expected = JSON.parse(read(current13.registry.path, current13.registry.commit)).entries.filter(e => paths.has(e.source_authority.path));
  assert.deepEqual(actual.entries, expected);
});

}

import {admitPublication} from '../scripts/prepare-delivery-handoff.mjs';
test('materialization report preflight refuses late collisions and changed postimages', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-report-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const j = {root}, destination = '.cache/delivery-handoff/report';
  const products = {'materialized-inputs.json': Buffer.from('{}\n')};
  const commit = admitPublication(j.root, destination, products, {phase: 'materialize'}, false);
  assert.equal(fs.existsSync(path.join(j.root, destination)), false);
  fs.mkdirSync(path.join(j.root, destination), {recursive: true}); fs.writeFileSync(path.join(j.root, destination, 'sentinel'), 'preserve');
  assert.throws(commit, /Occupied destination/);
  assert.equal(fs.readFileSync(path.join(j.root, destination, 'sentinel'), 'utf8'), 'preserve');
  const second = admitPublication(j.root, destination + '-second', products, {phase: 'materialize'}, false);
  products['materialized-inputs.json'][0] = 65;
  assert.throws(second, /changed before publication/);
  assert.equal(fs.existsSync(path.join(j.root, destination + '-second')), false);
});

import {gzipSync} from 'node:zlib';
import {acquireDeliveryInputs, deliveryAcquisitionExecute} from '../scripts/delivery-handoff-advance.mjs';
{
const sha=b=>createHash('sha256').update(b).digest('hex');
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const json=v=>Buffer.from(JSON.stringify(canonical(v))+'\n');
function fixture(){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'delivery-input-materializer-')),origin=path.join(directory,'origin'),destination=path.join(directory,'destination');
 const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',GIT_AUTHOR_NAME:'fixture',GIT_AUTHOR_EMAIL:'fixture@example.invalid',GIT_COMMITTER_NAME:'fixture',GIT_COMMITTER_EMAIL:'fixture@example.invalid'};
 const git=(cwd,args,input)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',cwd,...args],{env,input,stdio:['pipe','pipe','pipe']});
 for(const repo of [origin,destination]){fs.mkdirSync(repo);git(repo,['init','--bare','--template=']);}
 const decoded=Buffer.from('one complete immutable fixture row\n'),rawA=gzipSync(decoded,{mtime:0}),rawB=Buffer.from('second immutable body\n');
 const oidA=git(origin,['hash-object','-w','--stdin'],rawA).toString().trim(),oidB=git(origin,['hash-object','-w','--stdin'],rawB).toString().trim();
 const tree=git(origin,['mktree'],`100644 blob ${oidA}\talias-a.gz\n100644 blob ${oidA}\tsource-a.gz\n100644 blob ${oidB}\tsource-b.txt\n`).toString().trim();
 const commit=git(origin,['commit-tree',tree],'fixture\n').toString().trim();git(origin,['update-ref','refs/heads/main',commit]);
 // The destination has actual immutable tree/commit metadata and no file bodies.
 for(const [type,id]of [['tree',tree],['commit',commit]])git(destination,['hash-object','-w','-t',type,'--stdin'],git(origin,['cat-file',type,id]));
 const pin=(name,body,oid,extra={})=>({commit,path:name,mode:'100644',blob:oid,bytes:body.length,sha256:sha(body),...extra});
 const a=pin('source-a.gz',rawA,oidA,{uncompressed_bytes:decoded.length,uncompressed_sha256:sha(decoded)}),alias={...a,path:'alias-a.gz'},b=pin('source-b.txt',rawB,oidB);
 const destA='.cache/additive-native-gap-repair/delivery/'+a.sha256+'/sources-000.jsonl.gz',destB='.cache/additive-native-gap-repair/delivery/'+b.sha256+'/components-001.jsonl.gz';
 const product=(p,destination)=>({identity:sha(json({mode:p.mode,bytes:p.bytes,sha256:p.sha256,uncompressed_bytes:p.uncompressed_bytes??null,uncompressed_sha256:p.uncompressed_sha256??null})),source:p,destinations:[p.path,destination],uses:['source-input','native-input','physical-product']});
 const plan={version:1,kind:'transport-only-deduplicated-input-plan',products:[product(a,destA),product(alias,destA),product(b,destB)],unique_encoded_bytes:a.bytes+alias.bytes+b.bytes};
 const gitExecPath=fs.realpathSync(git(origin,['--exec-path']).toString().trim()),gitExecutable=fs.realpathSync(path.resolve(gitExecPath,'../../bin/git'));
 const fetchCalls=[],importedOids=[],writes=[],bodyReads=[],control={interruptFetch:false,interruptFile:false,corruptRead:false};
 const execute=(command,args,options)=>{
  assert.ok(command==='git'||command===gitExecutable);assert.equal(options.env.GIT_NO_LAZY_FETCH,'1');
  if(args.includes('fetch')){
   const requested=options.input.trim().split('\n');fetchCalls.push(requested);assert.equal(new Set(requested).size,requested.length);
   args=args.map(a=>a==='https://github.com/ChengshuLi/WorldAtlas.git'?origin:a);
   if(control.interruptFetch){control.interruptFetch=false;const first=requested[0];execFileSync(command,args,{...options,input:first+'\n'});importedOids.push(first);throw Error('fixture interruption after real first-object import');}
   const out=execFileSync(command,args,options);importedOids.push(...requested);return out;
  }
  if(args.includes('cat-file')&&args.includes('blob'))bodyReads.push(args.at(-1));
  const raw=execFileSync(command,args,options);
  if((control.corruptRead||control.corruptOid===args.at(-1))&&args.includes('cat-file')&&args.includes('blob'))return Buffer.from('wrong bytes');return raw;
 };
 const options={execute,token:'',onMaterialized(event){writes.push(event.path);if(control.interruptFile){control.interruptFile=false;throw Error('fixture interruption after completed alias');}}};
 return {directory,origin,destination,plan,options,execute,control,fetchCalls,importedOids,writes,bodyReads,git,gitExecutable,gitExecPath,rawA,rawB,a,b,destA,destB,oidA,oidB,close(){fs.rmSync(directory,{recursive:true,force:true});}};
}

test('actual missing Git objects and repeated identities acquire once; complete aliases are materialized once',async()=>{
 const f=fixture();try{
  const sourceSentinel=Buffer.from('Existing ordinary source-tree path is not a materialization target.\n');
  fs.writeFileSync(path.join(f.destination,f.a.path),sourceSentinel);
  const result=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(result.status,'complete');assert.equal(result.unique_objects,2);assert.equal(result.declarations,3);assert.equal(result.fetched_objects,2);assert.equal(result.materialized_files,2);assert.equal(result.materialization_body_reads,2);assert.equal(f.bodyReads.length,2);
  assert.equal(f.fetchCalls.length,1);assert.deepEqual(new Set(f.importedOids),new Set([f.oidA,f.oidB]));assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
  assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destA)),f.rawA);assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destB)),f.rawB);
  for(let i=0;i<2;i++){const warm=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(warm.fetched_objects,0);assert.equal(warm.materialized_files,0);assert.equal(warm.resumed_files,2);assert.equal(warm.materialization_body_reads,2);}
  assert.equal(f.bodyReads.length,6); // Complete per-invocation reauthentication is retained.
  assert.equal(f.fetchCalls.length,1);assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
  assert.deepEqual(fs.readFileSync(path.join(f.destination,f.a.path)),sourceSentinel);assert.equal(fs.existsSync(path.join(f.destination,f.b.path)),false);
 }finally{f.close();}
});

test('interrupted real import resumes from actual object state without fetching the completed identity again',async()=>{
 const f=fixture();try{
  f.control.interruptFetch=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/acquisition failed/);assert.equal(f.importedOids.length,1);assert.equal(f.writes.length,0);
  const before=f.git(f.destination,['cat-file','--batch-check'],f.oidA+'\n'+f.oidB+'\n').toString();assert.equal(before.split('\n').filter(line=>line.endsWith(' missing')).length,1);
  const resumed=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(resumed.status,'complete');assert.equal(f.fetchCalls.length,2);assert.equal(f.fetchCalls[1].length,1);assert.notEqual(f.fetchCalls[1][0],f.importedOids[0]);assert.equal(new Set(f.importedOids).size,2);assert.equal(f.importedOids.length,2);assert.equal(f.writes.length,2);
 }finally{f.close();}
});

test('interruption after a complete file resumes without another fetch or overwriting the completed alias',async()=>{
 const f=fixture();try{
  f.control.interruptFile=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/completed alias/);assert.equal(f.fetchCalls.length,1);assert.equal(f.writes.length,1);const first=path.join(f.destination,f.writes[0]),before=fs.statSync(first);
  const resumed=await acquireDeliveryInputs(f.plan,f.destination,f.options);assert.equal(resumed.materialized_files,1);assert.equal(resumed.resumed_files,1);assert.equal(f.fetchCalls.length,1);assert.equal(f.writes.length,2);const after=fs.statSync(first);assert.equal(after.ino,before.ino);assert.equal(after.mtimeMs,before.mtimeMs);
 }finally{f.close();}
});

test('partial, corrupted and symlinked aliases are preserved and refused before any fetch',async()=>{
 for(const mode of ['partial','corrupt','symlink']){const f=fixture();try{const destination=path.join(f.destination,f.destA);fs.mkdirSync(path.dirname(destination),{recursive:true});let sentinel;
  if(mode==='symlink'){sentinel=path.join(f.directory,'sentinel');fs.writeFileSync(sentinel,f.rawA);fs.symlinkSync(sentinel,destination);}else fs.writeFileSync(destination,mode==='partial'?f.rawA.subarray(0,3):Buffer.alloc(f.rawA.length,1));
  const before=mode==='symlink'?fs.readFileSync(sentinel):fs.readFileSync(destination);
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/Nonordinary|differs/);assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);assert.deepEqual(mode==='symlink'?fs.readFileSync(sentinel):fs.readFileSync(destination),before);
 }finally{f.close();}}
});

test('wrong whole bytes or decoded gzip identities cannot produce a materialized receipt',async()=>{
 let f=fixture();try{f.control.corruptRead=true;await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/Acquired body changed before materialization/);assert.equal(f.writes.length,0);}finally{f.close();}
 f=fixture();try{const changed=structuredClone(f.plan);for(const p of changed.products.filter(p=>p.source.blob===f.oidA)){p.source.uncompressed_sha256='0'.repeat(64);p.identity=sha(json({mode:p.source.mode,bytes:p.source.bytes,sha256:p.source.sha256,uncompressed_bytes:p.source.uncompressed_bytes,uncompressed_sha256:p.source.uncompressed_sha256}));}
 await assert.rejects(acquireDeliveryInputs(changed,f.destination,f.options),/decoded identity/);assert.equal(f.writes.length,0);
 }finally{f.close();}
});

test('identity, destination and aggregate inventory failures occur before object fetches',async()=>{
 for(const edit of [p=>p.products[0].identity='0'.repeat(64),p=>p.products[0].destinations.push('../escape'),p=>p.products[0].destinations.push('data/unowned.json'),p=>p.unique_encoded_bytes++]){const f=fixture();try{const bad=structuredClone(f.plan);edit(bad);await assert.rejects(acquireDeliveryInputs(bad,f.destination,f.options));assert.equal(f.fetchCalls.length,0);assert.equal(f.writes.length,0);}finally{f.close();}}
});

test('later corrupt input cannot complete materialization; an earlier exact alias is safely resumed',async()=>{
 const f=fixture();try{
  f.control.corruptOid=f.oidB;
  await assert.rejects(acquireDeliveryInputs(f.plan,f.destination,f.options),/Acquired body changed before materialization/);
  assert.deepEqual(f.writes,[f.destA]);assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destA)),f.rawA);
  assert.equal(fs.existsSync(path.join(f.destination,f.destB)),false);
  const before=fs.statSync(path.join(f.destination,f.destA));f.control.corruptOid=null;
  const result=await acquireDeliveryInputs(f.plan,f.destination,f.options);
  assert.equal(result.status,'complete');assert.equal(result.resumed_files,1);assert.equal(result.materialized_files,1);
  assert.equal(fs.statSync(path.join(f.destination,f.destA)).ino,before.ino);
  assert.deepEqual(fs.readFileSync(path.join(f.destination,f.destB)),f.rawB);assert.equal(f.fetchCalls.length,1);
 }finally{f.close();}
});

test('plain materialize CLI authenticates a saved recipe index and resumes with identical receipt and zero writes', () => {
  const f = fixture();
  try {
    const index = json({version: 1, acquisition_plan: f.plan});
    const blob = f.git(f.origin, ['hash-object', '-w', '--stdin'], index).toString().trim();
    const tree = f.git(f.origin, ['mktree'], `100644 blob ${blob}\trecipe-index.json\n`).toString().trim();
    const commit = f.git(f.origin, ['commit-tree', tree], 'saved recipe index\n').toString().trim();
    fs.writeFileSync(path.join(f.origin, 'config.json'), JSON.stringify({version: 1,
      recipe_index: {commit, path: 'recipe-index.json'}}));
    const script = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../scripts/prepare-delivery-handoff.mjs');
    const env = {...process.env}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
    const run = (...flags) => JSON.parse(execFileSync(process.execPath, [script, 'materialize', 'config.json',
      '.cache/delivery-handoff/materialized', ...flags], {cwd: f.origin, env, stdio: ['ignore', 'pipe', 'pipe']}));
    const first = run(); assert.equal(first.acquisition.materialized_files, 2); assert.equal(first.acquisition.fetch_batches, 0);
    const receiptPath = path.join(f.origin, '.cache/delivery-handoff/materialized/preparation.json');
    const original = fs.readFileSync(receiptPath), before = fs.statSync(path.join(f.origin, f.destA));
    const second = run('--resume'); assert.equal(second.resumed, true); assert.equal(second.acquisition.materialized_files, 0);
    assert.equal(second.acquisition.resumed_files, 2); assert.equal(second.acquisition.fetch_batches, 0);
    assert.deepEqual(fs.readFileSync(receiptPath), original); assert.equal(fs.statSync(path.join(f.origin, f.destA)).ino, before.ino);
    assert.throws(() => run(), error => error.stderr.toString().includes('Occupied destination'));
  } finally { f.close(); }
});

test('cold acquisition reuses selected Git/helpers and gh login; warm reads never reselect or request credentials', async () => {
  const f = fixture(); let tokenReads = 0, authenticatedFetches = 0;
  const keys = ['PATH','GIT_EXEC_PATH','GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_CONFIG_GLOBAL'];
  const saved = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  try {
    for (const key of ['GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_CONFIG_GLOBAL']) process.env[key] = path.join(f.directory, 'unrelated-' + key);
    const execute = deliveryAcquisitionExecute({readToken: () => { tokenReads++; return 'local-fixture-token'; },
      execute: (command, args, options) => {
        assert.equal(command, f.gitExecutable);
        assert.equal(options.env.GIT_EXEC_PATH, f.gitExecPath);
        for (const key of ['GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE']) assert.equal(options.env[key], undefined);
        assert.equal(options.env.GIT_CONFIG_GLOBAL, '/dev/null');
        assert.equal(options.env.GIT_NO_REPLACE_OBJECTS, '1');
        if (args.includes('fetch')) {
          authenticatedFetches++; assert.equal(options.env.GIT_CONFIG_COUNT, '3');
          assert.equal(options.env.GIT_CONFIG_KEY_2, 'http.https://github.com/.extraheader');
          assert.equal(options.env.GIT_CONFIG_VALUE_2, 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:local-fixture-token').toString('base64'));
        } else assert.notEqual(options.env?.GIT_CONFIG_COUNT, '3');
        return f.execute(command, args, options);
      }});
    await acquireDeliveryInputs(f.plan, f.destination, {...f.options, execute});
    assert.equal(tokenReads, 1); assert.equal(authenticatedFetches, 1);
    process.env.PATH = ''; process.env.GIT_EXEC_PATH = path.join(f.directory, 'wrong-helpers');
    await acquireDeliveryInputs(f.plan, f.destination, {...f.options, execute});
    assert.equal(tokenReads, 1); assert.equal(authenticatedFetches, 1);
    assert.throws(() => execute('git', ['fetch', 'https://example.invalid/repository'], {env: {}}), /Unexpected acquisition/);
    assert.equal(tokenReads, 1);
  } finally {
    for (const [key, value] of Object.entries(saved)) { if (value === undefined) delete process.env[key]; else process.env[key] = value; }
    f.close();
  }
});

}
