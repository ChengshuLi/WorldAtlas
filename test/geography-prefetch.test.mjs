import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createAcquisition, prefetchSelectedGeography} from '../scripts/geography-prefetch.mjs';

const digest = b => createHash('sha256').update(b).digest('hex');
const bytes = value => Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
function fixture() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'geography-prefetch-'));
  const origin = path.join(directory, 'origin'), destination = path.join(directory, 'destination');
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
    GIT_AUTHOR_NAME: 'fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid', GIT_COMMITTER_NAME: 'fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid'};
  const git = (repo, args, input) => execFileSync('git', ['-C', repo, ...args], {env, input, stdio: ['pipe', 'pipe', 'pipe']});
  for (const repo of [origin, destination]) { fs.mkdirSync(repo); git(repo, ['init', '--bare']); }
  const maps = new Map(), bodies = new Map(), objects = new Map();
  function commit(files) {
    const rows = Object.entries(files).map(([name, value]) => {
      const body = bytes(value), sha = git(origin, ['hash-object', '-w', '--stdin'], body).toString().trim();
      bodies.set(sha, body); return {path: name, mode: '100644', type: 'blob', sha, size: body.length};
    });
    function tree(prefix) {
      const groups = new Map(), lines = [];
      for (const row of rows.filter(r => r.path.startsWith(prefix))) {
        const rest = row.path.slice(prefix.length), slash = rest.indexOf('/');
        if (slash < 0) lines.push(`${row.mode} blob ${row.sha}\t${rest}`);
        else groups.set(rest.slice(0, slash), true);
      }
      for (const name of groups.keys()) lines.push(`040000 tree ${tree(prefix + name + '/')}\t${name}`);
      const sha = git(origin, ['mktree'], lines.sort().join('\n') + '\n').toString().trim();
      const body = git(origin, ['cat-file', 'tree', sha]); objects.set(sha, {type: 'tree', body}); return sha;
    }
    const root = tree(''), sha = git(origin, ['commit-tree', root], 'fixture\n').toString().trim();
    objects.set(sha, {type: 'commit', body: git(origin, ['cat-file', 'commit', sha])});
    maps.set(sha, {sha: root, truncated: false, tree: rows});
    git(origin, ['update-ref', 'refs/heads/' + sha, sha]); return sha;
  }
  function pin(name, value, extra = {}) { const body = bytes(value); return {path: name, bytes: body.length, sha256: digest(body), ...extra}; }
  function bankFiles(extra = false) {
    const source = {features: [{id: 'target', points: extra ? [1, 2, 3] : [1, 2]}]};
    const sourcePin = pin('data/source.json', source, {mode: '100644', commit: 'f'.repeat(40)});
    const sourceBody = bytes(source); sourcePin.git_blob_oid = createHash('sha1').update(`blob ${sourceBody.length}\0`).update(sourceBody).digest('hex');
    const world = {parts: ['source.json']}, fragment = 'native whole fragment';
    const index = {parts: [pin('fragment.bin', fragment)]};
    const manifest = {parts: [{path: 'absent-run.bin', bytes: 1, sha256: '0'.repeat(64)}], native_asset_transport: {kind: 'ordered-exact-original-byte-fragments', index: pin('native/bank/index.json', index)}};
    const bank = {unchanged_files: [sourcePin], overrides: [], world_index: pin('data/world-index.json', world)};
    const selection = {version: 1, manifest_path: 'native/manifest.json', sha256: digest(bytes(manifest)),
      selected_geography: {...pin('source-bank.json', bank), kind: 'complete-world-index-with-exact-encoded-overrides'}};
    return {'data/ownership-selection.json': selection, 'native/manifest.json': manifest, 'native/bank/index.json': index,
      'native/bank/fragment.bin': fragment, 'source-bank.json': bank, 'data/source.json': source, 'data/world-index.json': world};
  }
  const baseline = commit(bankFiles()), candidate = commit(bankFiles(true));
  // Commit/tree metadata is present; all file objects are genuinely missing.
  for (const {type, body} of objects.values()) git(destination, ['hash-object', '-w', '-t', type, '--stdin'], body);
  const batches = [];
  const execute = (command, args, options) => {
    assert.equal(options.env.GIT_NO_LAZY_FETCH, '1');
    if (args.includes('fetch')) {
      assert(args.includes('fetch.negotiationAlgorithm=noop')); assert(args.includes('--stdin'));
      assert(args.includes('--no-auto-maintenance'));
      assert(!args.some(a => a.includes('fixture-secret')));
      batches.push(options.input.trim().split('\n'));
      args = args.map(a => a === 'https://github.com/ChengshuLi/WorldAtlas.git' ? origin : a);
    }
    return execFileSync(command, args, options);
  };
  const acquisition = options => createAcquisition({repo: destination, loadTree: async version => maps.get(version), execute, token: 'fixture-secret', ...options});
  return {directory, origin, destination, baseline, candidate, maps, bodies, batches, git, acquisition, bankFiles, commit,
    close() { fs.rmSync(directory, {recursive: true, force: true}); }};
}

test('real missing-object fetches are batched, shared OIDs deduplicate, and candidate-only bytes arrive', async () => {
  const f = fixture(); try {
    const before = f.git(f.destination, ['cat-file', '--batch-check'], [...f.bodies.keys()].join('\n') + '\n').toString();
    assert(before.split('\n').filter(Boolean).every(line => line.endsWith(' missing')));
    const result = await prefetchSelectedGeography(f.acquisition(), f.baseline, f.candidate);
    assert.equal(result.status, 'scoped-prefetch-completed'); assert.equal(result.complete_scientific_closure, false);
    assert(f.batches.some(batch => batch.length >= 4));
    assert.equal(new Set(f.batches.flat()).size, f.batches.flat().length);
    assert.equal(result.verified_import_objects, f.bodies.size);
    // The same unchanged reader of actual Git bytes sees the exact expected
    // differing source semantics; prefetch does not supply a replacement result.
    const consume = (repo, commit) => JSON.parse(f.git(repo, ['show', commit + ':data/source.json'])).features[0].points;
    for (const commit of [f.baseline, f.candidate]) assert.deepEqual(consume(f.destination, commit), consume(f.origin, commit));
    assert.notDeepEqual(consume(f.destination, f.baseline), consume(f.destination, f.candidate));
    const count = f.batches.length;
    const warm = await prefetchSelectedGeography(f.acquisition(), f.baseline, f.candidate);
    assert.equal(warm.verified_import_objects, 0); assert.equal(f.batches.length, count);
  } finally { f.close(); }
});

test('wrong tree, mode, size, OID and hash are not accepted as scoped completion', async () => {
  const f = fixture(); try {
    const original = f.maps.get(f.baseline), name = 'data/ownership-selection.json';
    await assert.rejects(f.acquisition({loadTree: async () => ({...original, truncated: true})}).tree(f.baseline), /Incomplete/);
    await assert.rejects(f.acquisition({loadTree: async () => ({...original, sha: '0'.repeat(40)})}).tree(f.baseline), /wrong/);
    const replacement = f.maps.get(f.candidate).tree.find(r => r.path === name);
    await assert.rejects(f.acquisition({loadTree: async () => ({...original,
      tree: original.tree.map(row => row.path === name ? replacement : row)})}).json(f.baseline, name), /actual immutable Git tree/);
    const a = f.acquisition();
    await assert.rejects(a.descriptor(f.baseline, name, {bytes: 1}), /identity/);
    await assert.rejects(a.descriptor(f.baseline, name, {mode: '120000'}), /identity/);
    await assert.rejects(a.descriptor(f.baseline, name, {git_blob_oid: '0'.repeat(40)}), /identity/);
    await assert.rejects(a.descriptor(f.baseline, '../outside'), /Unsafe/);
    const p = await a.descriptor(f.baseline, name, {sha256: '0'.repeat(64)});
    assert.throws(() => a.acquire([p]), /declared hash/);
  } finally { f.close(); }
});

test('duplicate OIDs cannot bypass the independent declaration-count limit', async () => {
  const f = fixture(); try {
    const a = f.acquisition({limits: {member: 100000, total: 100000, entries: 2}});
    await a.descriptor(f.baseline, 'data/ownership-selection.json');
    await a.descriptor(f.baseline, 'data/ownership-selection.json');
    await assert.rejects(a.descriptor(f.baseline, 'data/ownership-selection.json'), /declaration limit/);
    assert.equal(a.stats.unique_objects, 1); assert.equal(f.batches.length, 0);
  } finally { f.close(); }
});

test('member, entry and aggregate admission precede any object fetch', async () => {
  const f = fixture(); try {
    for (const limits of [{member: 1, total: 100000, entries: 512}, {member: 100000, total: 1, entries: 512}, {member: 100000, total: 100000, entries: 0}]) {
      await assert.rejects(prefetchSelectedGeography(f.acquisition({limits}), f.baseline, f.candidate), /oversized|limit/);
      assert.equal(f.batches.length, 0);
    }
  } finally { f.close(); }
});

test('failed transport remains unavailable and redacts subprocess errors', async () => {
  const f = fixture(); try {
    const a = f.acquisition({execute(command, args, options) {
      if (args.includes('fetch')) throw Error('fixture-secret transport interruption');
      return execFileSync(command, args, options);
    }});
    await assert.rejects(prefetchSelectedGeography(a, f.baseline, f.candidate), error => /acquisition failed/.test(error.message) && !error.message.includes('fixture-secret'));
    assert.equal(a.stats.complete_scientific_closure, false);
  } finally { f.close(); }
});

test('wrong local object type and corrupted acquired bytes refuse completion', async () => {
  const f = fixture(); try {
    const original = f.maps.get(f.baseline), row = original.tree.find(r => r.path === 'data/ownership-selection.json');
    const bad = f.acquisition({loadTree: async () => ({...original, tree: original.tree.map(r => r === row ? {...r, sha: original.sha} : r)})});
    await assert.rejects(bad.json(f.baseline, row.path), /actual immutable Git tree/);
    const damaged = f.acquisition({execute(command, args, options) {
      if (args.includes('fetch')) args = args.map(a => a === 'https://github.com/ChengshuLi/WorldAtlas.git' ? f.origin : a);
      const raw = execFileSync(command, args, options);
      return args.includes('blob') ? Buffer.from('truncated') : raw;
    }});
    await assert.rejects(damaged.json(f.baseline, row.path), /does not match tree/);
    assert.equal(damaged.stats.verified_import_objects, 0);
  } finally { f.close(); }
});

test('direct native and additive historical aliases are scoped acquisitions', async () => {
  const f = fixture(); try {
    const files = f.bankFiles(), native = {rows: [[0, 2, 1]]};
    const pin = (name, body) => {
      const raw = bytes(body);
      return {path: name, bytes: raw.length, sha256: digest(raw), mode: '100644', commit: 'e'.repeat(40),
        git_blob_oid: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')};
    };
    files['native/run.json'] = native;
    files['native/manifest.json'] = {parts: [{...pin('run.json', native), commit: undefined}]};
    delete files['native/manifest.json'].parts[0].commit;
    const roles = ['base_manifest', 'ledger', 'owner_roster', 'patch', 'runtime_envelope', 'authority_registry'];
    const pins = {};
    for (const role of roles) { const name = 'additive/' + role + '.json', body = {role}; files[name] = body; pins[role] = pin(name, body); }
    const sidecar = {kind: 'retained-native-additive-selection-v2', runtime_envelope: pins.runtime_envelope,
      authority_registry: pins.authority_registry, logical_asset_map: Object.fromEntries(roles.slice(0, 4).map(role => [role, pins[role]]))};
    files['sidecar.json'] = sidecar;
    files['data/ownership-selection.json'].sha256 = digest(bytes(files['native/manifest.json']));
    files['data/ownership-selection.json'].additive_release = pin('sidecar.json', sidecar);
    const head = f.commit(files);
    // Copy only fresh metadata, exactly as a blob:none checkout would.
    const tree = f.git(f.origin, ['rev-parse', head + '^{tree}']).toString().trim();
    const queue = [tree];
    while (queue.length) { const current = queue.pop(), raw = f.git(f.origin, ['cat-file', 'tree', current]); f.git(f.destination, ['hash-object', '-w', '-t', 'tree', '--stdin'], raw);
      for (const line of f.git(f.origin, ['ls-tree', current]).toString().trim().split('\n')) if (line.includes(' tree ')) queue.push(line.split(' ')[2].split('\t')[0]); }
    f.git(f.destination, ['hash-object', '-w', '-t', 'commit', '--stdin'], f.git(f.origin, ['cat-file', 'commit', head]));
    const result = await prefetchSelectedGeography(f.acquisition(), head, head);
    assert.equal(result.status, 'scoped-prefetch-completed');
    for (const role of roles) assert.deepEqual(JSON.parse(f.git(f.destination, ['show', head + ':additive/' + role + '.json'])), {role});
    assert.deepEqual(JSON.parse(f.git(f.destination, ['show', head + ':native/run.json'])), native);
    assert.equal(new Set(f.batches.flat()).size, f.batches.flat().length);
  } finally { f.close(); }
});

test('an unsupported source bank cannot return a completed acquisition', async () => {
  const a = {stats: {complete_scientific_closure: false}, tree: async () => new Map([['data/ownership-selection.json', {}]]),
    json: async (_version, name) => name === 'data/ownership-selection.json' ? {version: 1, manifest_path: 'manifest.json'} : {parts: []}};
  await assert.rejects(prefetchSelectedGeography(a, 'a'.repeat(40), 'a'.repeat(40)), /Unrecognized source bank/);
});

test('real timeout and failed launcher stop descendants before fallback, with honest summaries', () => {
  const code = `import importlib.util,pathlib,subprocess,contextlib,io,json,tempfile,sys,os,time
spec=importlib.util.spec_from_file_location('checker','scripts/run-geographic-check.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.environ['NODE']=sys.executable
with tempfile.TemporaryDirectory() as directory:
    root=pathlib.Path(directory);(root/'scripts').mkdir()
    marker=root/'heartbeat'
    descendant="import pathlib,time; p=pathlib.Path("+repr(str(marker))+");\\nwhile True: p.write_text(str(time.monotonic())); time.sleep(0.03)"
    for fail in [False,True]:
        launcher="import subprocess,sys,time,json\\nsubprocess.Popen([sys.executable,'-c',"+repr(descendant)+"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\\ntime.sleep(0.15)\\n"
        if fail: launcher+="print(json.dumps({'status':'scoped-prefetch-completed','complete_scientific_closure':False}),flush=True)\\nsys.exit(1)\\n"
        else: launcher+="time.sleep(60)\\n"
        (root/'scripts/geography-prefetch.mjs').write_text(launcher)
        output=io.StringIO()
        with contextlib.redirect_stderr(output):
            with m.stage_timing('fixture'):
                m.prefetch_declared_inputs(root,'a'*40,'b'*40,timeout=0.5)
        rows=[json.loads(s) for s in output.getvalue().splitlines()]
        assert rows[0]['geography_prefetch']['status']=='scoped-prefetch-unavailable'
        assert rows[0]['geography_prefetch']['complete_scientific_closure'] is False
        assert rows[1]['geography_stage']=='fixture' and rows[1]['elapsed_ms']>=0
        before=marker.read_text();time.sleep(0.15);assert marker.read_text()==before,'descendant still running after fallback'
`;
  execFileSync('python', ['-B', '-c', code], {stdio: ['ignore', 'pipe', 'pipe'], timeout: 10000});
});

test('unconfirmed process-group cleanup blocks checker continuation', () => {
  const code = `import importlib.util,pathlib
spec=importlib.util.spec_from_file_location('checker','scripts/run-geographic-check.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Child:
    pid=123
    returncode=0
    def communicate(self,timeout): return (b'{}',b'')
m.subprocess.Popen=lambda *a,**k: Child()
def denied(*a): raise PermissionError('fixture cleanup denial')
m.os.killpg=denied
try: m.prefetch_declared_inputs(pathlib.Path('.'),'a'*40,'b'*40)
except RuntimeError as error: assert 'Cannot terminate owned' in str(error)
else: raise AssertionError('checker resumed after unconfirmed cleanup')
`;
  execFileSync('python', ['-B', '-c', code], {stdio: ['ignore', 'pipe', 'pipe']});
});
