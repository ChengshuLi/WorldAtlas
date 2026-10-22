import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createAcquisition, prefetchSelectedGeography, githubTree} from '../scripts/geography-prefetch.mjs';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {createRoutingMetadataAcquisition} from '../scripts/geography-routing-metadata.mjs';

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
  function importMetadata() {
    for (const {type, body} of objects.values()) git(destination, ['hash-object', '-w', '-t', type, '--stdin'], body);
  }
  importMetadata();
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
  const acquisition = options => createAcquisition({repo: destination, loadTree: async root => [...maps.values()].find(value => value.sha === root), execute, token: 'fixture-secret', ...options});
  return {directory, origin, destination, baseline, candidate, maps, bodies, batches, git, acquisition, bankFiles, commit, importMetadata, execute,
    close() { fs.rmSync(directory, {recursive: true, force: true}); }};
}

test('GitHub commit-valued envelopes require requesting the exact local root tree', async () => {
  const f = fixture(); try {
    const requested = [], root = f.git(f.destination, ['rev-parse', f.baseline + '^{tree}']).toString().trim();
    const metadata = f.maps.get(f.baseline);
    assert.notEqual(root, f.baseline);
    const acquisition = f.acquisition({loadTree: async requestedOid => {
      requested.push(requestedOid);
      // Production API returns the requested commit or tree as envelope SHA.
      return {...metadata, sha: requestedOid};
    }});
    await acquisition.descriptor(f.baseline, 'data/ownership-selection.json');
    assert.deepEqual(requested, [root]);
    await assert.rejects(f.acquisition({loadTree: async () => ({...metadata, sha: f.baseline})}).tree(f.baseline), /wrong immutable tree/);
  } finally { f.close(); }
});

test('real missing-object fetches are batched, shared OIDs deduplicate, and candidate-only bytes arrive', async () => {
  const f = fixture(); try {
    const before = f.git(f.destination, ['cat-file', '--batch-check'], [...f.bodies.keys()].join('\n') + '\n').toString();
    assert(before.split('\n').filter(Boolean).every(line => line.endsWith(' missing')));
    const result = await prefetchSelectedGeography(f.acquisition(), f.baseline, f.candidate);
    assert.equal(result.status, 'scoped-prefetch-completed'); assert.equal(result.complete_scientific_closure, false);
    assert(f.batches.some(batch => batch.length >= 4));
    assert.equal(new Set(f.batches.flat()).size, f.batches.flat().length);
    assert.equal(result.fetched_objects, f.bodies.size);
    // The same unchanged reader of actual Git bytes sees the exact expected
    // differing source semantics; prefetch does not supply a replacement result.
    const consume = (repo, commit) => JSON.parse(f.git(repo, ['show', commit + ':data/source.json'])).features[0].points;
    for (const commit of [f.baseline, f.candidate]) assert.deepEqual(consume(f.destination, commit), consume(f.origin, commit));
    assert.notDeepEqual(consume(f.destination, f.baseline), consume(f.destination, f.candidate));
    const count = f.batches.length;
    const warm = await prefetchSelectedGeography(f.acquisition(), f.baseline, f.candidate);
    assert.equal(warm.fetched_objects, 0); assert.equal(f.batches.length, count);
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
    await assert.rejects(a.json(f.baseline, name, {sha256: '0'.repeat(64)}), /declared hash/);
  } finally { f.close(); }
});

for (const transport of [false, true]) test(`complete ${transport ? 'fragment-transport' : 'direct-native'} and source rosters authenticate every declared path`, async () => {
  const f = fixture(); try {
    const files = f.bankFiles(), native = {rows: [[0, 2, 1]]}, nativePin = {bytes: bytes(native).length, sha256: digest(bytes(native))};
    const source = {features: [{id: 'target', points: [1, 2]}]}, sourcePin = {bytes: bytes(source).length, sha256: digest(bytes(source))};
    const parts = [], sources = [];
    for (let i = 0; i < 2; i++) {
      const nativePath = `native/${transport ? 'fragment' : 'run'}-${i}.json`, sourcePath = `data/source-${i}.json`;
      files[nativePath] = native; files[sourcePath] = source;
      parts.push({path: path.posix.basename(nativePath), ...nativePin});
      sources.push({path: sourcePath, ...sourcePin});
    }
    if (transport) {
      const index = {parts}; files['native/index.json'] = index;
      files['native/manifest.json'] = {parts: [{path: 'absent-run.bin', bytes: 1, sha256: '0'.repeat(64)}],
        native_asset_transport: {kind: 'ordered-exact-original-byte-fragments',
          index: {path: 'native/index.json', bytes: bytes(index).length, sha256: digest(bytes(index))}}};
    } else files['native/manifest.json'] = {parts};
    files['source-bank.json'].unchanged_files = sources;
    files['data/ownership-selection.json'].sha256 = digest(bytes(files['native/manifest.json']));
    files['data/ownership-selection.json'].selected_geography = {
      ...files['data/ownership-selection.json'].selected_geography,
      bytes: bytes(files['source-bank.json']).length, sha256: digest(bytes(files['source-bank.json']))};
    const head = f.commit(files); f.importMetadata();
    const paths = [], bodyReads = [];
    const a = f.acquisition({execute(command, args, options) {
      if (args.includes('ls-tree')) paths.push(args.at(-1));
      if (args.includes('blob')) bodyReads.push(args.at(-1));
      return f.execute(command, args, options);
    }});
    const result = await prefetchSelectedGeography(a, head, head);
    assert.equal(result.status, 'scoped-prefetch-completed');
    const expectedPaths = ['data/ownership-selection.json', 'native/manifest.json', 'source-bank.json', 'data/world-index.json',
      ...parts.map(p => 'native/' + p.path), ...sources.map(p => p.path), ...(transport ? ['native/index.json'] : [])];
    assert.deepEqual(paths.sort(), expectedPaths.sort());
    assert.equal(bodyReads.length, transport ? 4 : 3); // Only actual JSON consumers read bodies.
    assert(bodyReads.length < result.unique_objects);
    assert.equal(new Set(bodyReads).size, bodyReads.length);
    assert.equal(new Set(f.batches.flat()).size, f.batches.flat().length);
    for (const name of [`native/${transport ? 'fragment' : 'run'}-0.json`, `native/${transport ? 'fragment' : 'run'}-1.json`, 'data/source-0.json', 'data/source-1.json']) {
      const expected = name.startsWith('native/') ? native : source;
      assert.deepEqual(JSON.parse(f.git(f.destination, ['show', head + ':' + name])), expected);
    }
  } finally { f.close(); }
});

test('all immutable tree identities are loaded and duplicate metadata paths still fail', async () => {
  const f = fixture(); try {
    const commits = Array.from({length: 2}, (_, i) => f.commit({'input.json': {i}})); f.importMetadata();
    const a = f.acquisition();
    for (let i = 0; i < commits.length; i++) {
      const value = await a.json(commits[i], 'input.json'); assert.deepEqual(value, {i});
    }
    const original = f.maps.get(f.baseline);
    await assert.rejects(f.acquisition({loadTree: async () => ({...original, tree: [...original.tree, original.tree[0]]})}).tree(f.baseline), /Duplicate tree metadata paths/);
  } finally { f.close(); }
});

test('GitHub metadata preserves a complete response and propagates malformed responses', async () => {
  const originalFetch = globalThis.fetch;
  try {
    const value = {sha: 'a'.repeat(40), truncated: false, tree: [], note: 'complete response metadata'};
    globalThis.fetch = async () => new Response(JSON.stringify(value));
    assert.deepEqual(await githubTree(value.sha), value);
    globalThis.fetch = async () => new Response('{');
    await assert.rejects(githubTree(value.sha), SyntaxError);
    globalThis.fetch = async () => new Response('unavailable', {status: 503});
    await assert.rejects(githubTree(value.sha), /metadata unavailable/);
  } finally { globalThis.fetch = originalFetch; }
});

test('GitHub metadata retries only one interrupted immutable GET, including body transport', async () => {
  const originalFetch = globalThis.fetch, originalToken = process.env.GH_TOKEN;
  process.env.GH_TOKEN = 'fixture-metadata-secret';
  const id = 'a'.repeat(40), value = {sha: id, tree: {sha: 'b'.repeat(40)}};
  const interrupted = () => new TypeError('fixture-metadata-secret', {cause: {code: 'UND_ERR_SOCKET'}});
  try {
    for (const [read, locator] of [[() => githubTree(id, false), `trees/${id}`], [() => githubTree(id), `trees/${id}?recursive=1`]]) {
      for (const bodyFailure of [false, true]) {
        const requests = [];
        globalThis.fetch = async (url, options) => {
          requests.push({url, headers: {...options.headers}});
          assert(options.signal instanceof AbortSignal);
          if (requests.length === 1) {
            if (bodyFailure) return {ok: true, json: async () => { throw interrupted(); }};
            throw interrupted();
          }
          return new Response(JSON.stringify(value));
        };
        assert.deepEqual(await read(), value);
        assert.equal(requests.length, 2);
        assert.deepEqual(requests[1], requests[0], 'Retry must preserve the exact immutable GET and headers');
        assert.equal(requests[0].url, `https://api.github.com/repos/ChengshuLi/WorldAtlas/git/${locator}`);
        assert.equal(requests[0].headers.Authorization, 'Bearer fixture-metadata-secret');
      }
    }
  } finally {
    globalThis.fetch = originalFetch;
    if (originalToken === undefined) delete process.env.GH_TOKEN; else process.env.GH_TOKEN = originalToken;
  }
});

test('repeated metadata socket closure stops after two GETs with a safe exact locator', async () => {
  const originalFetch = globalThis.fetch, id = 'a'.repeat(40);
  try {
    for (const [read, locator] of [[() => githubTree(id, false), `trees/${id}`], [() => githubTree(id), `trees/${id}?recursive=1`]]) {
      let requests = 0;
      globalThis.fetch = async () => { requests++; throw new TypeError('private header fixture-secret', {cause: {code: 'UND_ERR_SOCKET'}}); };
      await assert.rejects(read(), error => error.message === `Geography metadata transport unavailable (${locator}; UND_ERR_SOCKET)`
        && !String(error.stack).includes('fixture-secret') && error.cause === undefined);
      assert.equal(requests, 2, 'A second socket failure must remain terminal');
    }
  } finally { globalThis.fetch = originalFetch; }
});

test('metadata HTTP refusals, parsing, timeout, abort and other errors never retry', async () => {
  const originalFetch = globalThis.fetch, id = 'a'.repeat(40);
  try {
    for (const status of [401, 403, 404, 429, 500, 503]) {
      let requests = 0;
      globalThis.fetch = async () => { requests++; return new Response('fixture-secret response', {status}); };
      await assert.rejects(githubTree(id, false), error => error.message === `Geography tree metadata unavailable (trees/${id}; HTTP ${status})`);
      assert.equal(requests, 1, 'An HTTP refusal is not a socket interruption');
    }
    for (const error of [new SyntaxError('malformed metadata'), new DOMException('timeout', 'TimeoutError'),
      new DOMException('abort', 'AbortError'), new TypeError('other network failure', {cause: {code: 'ECONNRESET'}})]) {
      let requests = 0;
      globalThis.fetch = async () => { requests++; return {ok: true, json: async () => { throw error; }}; };
      await assert.rejects(githubTree(id), actual => actual === error);
      assert.equal(requests, 1);
    }
    let requests = 0;
    globalThis.fetch = async () => {
      if (++requests === 1) throw new TypeError('socket closed', {cause: {code: 'UND_ERR_SOCKET'}});
      return new Response('denied', {status: 403});
    };
    await assert.rejects(githubTree(id, false), /HTTP 403/);
    assert.equal(requests, 2, 'A refusal after the one retry cannot become success or another attempt');
  } finally { globalThis.fetch = originalFetch; }
});

test('a successful metadata retry does not admit a wrong immutable tree', async () => {
  const originalFetch = globalThis.fetch, f = fixture();
  try {
    let requests = 0;
    globalThis.fetch = async () => {
      if (++requests === 1) throw new TypeError('socket closed', {cause: {code: 'UND_ERR_SOCKET'}});
      return new Response(JSON.stringify({...f.maps.get(f.baseline), sha: 'f'.repeat(40)}));
    };
    const a = f.acquisition({loadTree: githubTree});
    await assert.rejects(a.tree(f.baseline), /wrong immutable tree metadata/);
    assert.equal(requests, 2); assert.equal(a.stats.complete_scientific_closure, false);
    assert.deepEqual(f.batches, []);
  } finally { globalThis.fetch = originalFetch; f.close(); }
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
    assert.equal(damaged.stats.fetched_objects, 1); // Fetch success does not claim body authentication.
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


test('cold routing acquisition supplies exact objects and authenticates tree metadata', async () => {
  const f = fixture(); try {
    const raw = 'complete routing body', head = f.commit({'routing.json': raw}); f.importMetadata();
    const metadata = f.maps.get(head), row = metadata.tree[0];
    const pin = {commit: head, path: row.path, mode: row.mode, git_blob_oid: row.sha};
    const options = {repo: f.destination, baseline: head, execute: f.execute, token: 'fixture-secret'};
    const a = createRoutingMetadataAcquisition({...options, loadTree: async root => {
      assert.equal(root, metadata.sha); return {...metadata, note: 'complete tree metadata'};
    }});
    await a.acquire(pin, {bytes: row.size, sha256: digest(raw)});
    assert.equal(a.summary().fetched_bytes, row.size); assert.equal(a.summary().fetch_batches, 1);
    await a.acquire(pin, {bytes: row.size, sha256: '0'.repeat(64)}); // The collector checks the consumed hash.
    assert.equal(a.summary().complete_scientific_closure, false);
    for (const alter of [m => ({...m, truncated: true}), m => ({...m, sha: head}),
      m => ({...m, tree: [...m.tree, m.tree[0]]}),
      m => ({...m, tree: m.tree.map(r => ({...r, size: r.size + 1}))})]) {
      const bad = createRoutingMetadataAcquisition({...options, loadTree: async () => alter(metadata)});
      await assert.rejects(bad.acquire(pin, {bytes: row.size, sha256: digest(raw)}), /tree-response|differs from tree/);
    }
  } finally { f.close(); }
});

// No alternates or historical checkout: start with an empty object store, then
// exercise the same private native commit transport and authenticated tree cache as CI.
function originFixture() {
  const f = fixture(), remote = path.join(f.directory, 'cold-origin');
  fs.mkdirSync(remote); f.git(remote, ['init', '--bare']);
  f.git(f.origin, ['config', 'uploadpack.allowFilter', 'true']);
  f.git(f.origin, ['config', 'uploadpack.allowAnySHA1InWant', 'true']);
  const calls = {commits: [], trees: [], fetches: [], stores: []};
  const loaders = {
    loadTree() { assert.fail('Historical metadata must use the native Git transport'); },
    execute(command, args, options) {
      if (args.includes('init')) calls.stores.push(args[args.indexOf('-C') + 1]);
      if (args.includes('fetch')) {
        assert(args.includes('--filter=tree:0'));
        (args.includes('--depth=1') ? calls.commits : calls.trees).push(options.input.trim());
        calls.fetches.push(options.input.trim());
        args = args.map(arg => arg === 'https://github.com/ChengshuLi/WorldAtlas.git' ? 'file://' + f.origin : arg);
      }
      return execFileSync(command, args, options);
    }
  };
  const acquisition = extra => createAcquisition({repo: remote, ...loaders, token: '', ...extra});
  const inventory = () => f.git(remote, ['cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)']).toString().trim().split('\n').filter(Boolean).map(line => line.split(' '));
  return {...f, remote, loaders, calls, acquisition, inventory, assertIsolated() {
    assert.deepEqual(inventory(), []); assert(!fs.existsSync(path.join(remote, 'shallow')));
    for (const store of calls.stores) assert(!fs.existsSync(store), 'owned origin store was not removed');
  }};
}

test('cold origin metadata resolves and caches exact path trees without blobs or parent history', async () => {
  const f = originFixture(); try {
    const id = f.commit({'first/a.json': 'first scientific leaf', 'second/b.json': 'second scientific leaf'});
    const parent = f.baseline, root = f.git(f.origin, ['rev-parse', id + '^{tree}']).toString().trim();
    const withParent = f.git(f.origin, ['commit-tree', root, '-p', parent], 'historical origin\n').toString().trim();
    const a = f.acquisition();
    const first = await a.resolvePath(withParent, 'first/a.json');
    assert(Object.isFrozen(first)); f.assertIsolated();
    const before = {...a.stats}; await a.resolvePath(withParent, 'first/a.json');
    assert.deepEqual(a.stats, before); assert.equal(f.calls.fetches.length, 3);
    // A present commit/root must not conceal a missing second path's tree.
    await a.resolvePath(withParent, 'second/b.json');
    assert.equal(a.stats.origin_metadata_objects, 4); assert.equal(a.stats.origin_metadata_imports, 0);
    assert.equal(f.calls.trees.length, 3); assert.equal(f.calls.commits.length, 1);
    f.assertIsolated();
    for (const name of ['first/a.json', 'second/b.json']) {
      const row = await a.resolvePath(withParent, name);
      assert.equal(`${row.mode} blob ${row.git_blob_oid}\t${row.path}\0`,
        f.git(f.origin, ['ls-tree', '-z', withParent, '--', name]).toString());
      assert.equal(row.commit, withParent);
    }
  } finally { f.close(); }
});

for (const mode of ['denied commit', 'denied tree', 'wrong inventory type', 'extra private object',
  'wrong object oid', 'wrong type', 'wrong length', 'wrong commit bytes', 'wrong tree bytes', 'changed child'])
test('cold origin metadata refuses unavailable or unauthenticated native objects: ' + mode, async () => {
  const f = originFixture(); try {
    const id = f.commit({'nested/input.json': 'scientific leaf'}), a = f.acquisition({
      execute(command, args, options) {
        const isCommit=args.includes('--depth=1');
        if(args.includes('fetch')&&(mode==='denied commit'&&isCommit||mode==='denied tree'&&!isCommit))throw Error('denied native transport');
        const result=f.loaders.execute(command,args,options);
        if(args.includes('--batch-all-objects')){
          if(mode==='wrong inventory type')return Buffer.from(result.toString().replace(/ (commit|tree)\n/,' blob\n'));
          if(mode==='extra private object')return Buffer.concat([result,Buffer.from('f'.repeat(40)+' blob\n')]);
          if(mode==='wrong object oid')return Buffer.from(result.toString().replace(/^[a-f0-9]{40}/,'f'.repeat(40)));
        }
        if(mode==='wrong type'&&args.includes('--batch-check=%(objectname) %(objecttype) %(objectsize)'))
          return Buffer.from(result.toString().replace(/ (commit|tree) /,' blob '));
        const i=args.indexOf('cat-file'),kind=args[i+1];
        if(i>=0&&['commit','tree'].includes(kind)){
          if(mode==='wrong length')return result.subarray(0,result.length-1);
          if(mode==='wrong commit bytes'&&kind==='commit'||['wrong tree bytes','changed child'].includes(mode)&&kind==='tree'){
            const changed=Buffer.from(result);changed[mode==='changed child'?changed.length-1:0]^=1;return changed;
          }
        }
        return result;
      }
    });
    await assert.rejects(a.resolvePath(id,'nested/input.json'),/fetch failed|Unexpected private origin|Wrong immutable/);
    f.assertIsolated();
  } finally { f.close(); }
});

test('cold origin metadata rejects blob-valued origins, nonordinary members and unsafe paths', async () => {
  const f = originFixture(); try {
    const id = f.commit({'input.json': 'scientific leaf'}), blob = f.git(f.origin, ['rev-parse', id + ':input.json']).toString().trim();
    const a = f.acquisition();
    await assert.rejects(a.resolvePath(blob, 'input.json')); assert.equal(f.calls.fetches.length, 1);
    for (const name of ['../input.json', '/input.json', 'a//b', 'a\\b']) await assert.rejects(a.resolvePath(id, name), /Unsafe/);
    await assert.rejects(a.resolvePath(id, 'missing.json'), /Missing or nonordinary/);
    const tree = f.git(f.origin, ['mktree'], `120000 blob ${blob}\tlink\n`).toString().trim();
    const link = f.git(f.origin, ['commit-tree', tree], 'symlink\n').toString().trim();
    await assert.rejects(a.resolvePath(link, 'link'), /Missing or nonordinary/);
    f.assertIsolated();
  } finally { f.close(); }
});

test('cold origin metadata authenticates already present native object type and bytes before reuse', async () => {
  for (const variant of ['wrong type', 'wrong hash']) {
    const f = originFixture(); try {
      const id = f.commit({'input.json': 'scientific leaf'}), raw = variant === 'wrong type' ? Buffer.from('blob 1\0x')
        : (() => { const bytes = Buffer.concat([f.git(f.origin, ['cat-file', 'commit', id]), Buffer.from('changed')]);
          return Buffer.concat([Buffer.from(`commit ${bytes.length}\0`), bytes]); })();
      const file = path.join(f.remote, 'objects', id.slice(0, 2), id.slice(2));
      fs.mkdirSync(path.dirname(file), {recursive: true});
      fs.writeFileSync(file, (await import('node:zlib')).deflateSync(raw));
      await assert.rejects(f.acquisition().resolvePath(id, 'input.json'), /Wrong immutable origin metadata/);
      assert.equal(f.calls.fetches.length, 0);
    } finally { f.close(); }
  }
});


test('cold routing body acquisition uses the private original descriptor without exposing its origin', async () => {
  const f = fixture(); try {
    f.git(f.origin, ['config', 'uploadpack.allowFilter', 'true']);
    f.git(f.origin, ['config', 'uploadpack.allowAnySHA1InWant', 'true']);
    const raw = 'historical routing body absent from the current tree', id = f.commit({'nested/routing.json': raw});
    const row = f.maps.get(id).tree[0], pin = {commit: id, path: row.path, mode: row.mode, git_blob_oid: row.sha};
    const before = f.git(f.destination, ['cat-file', '--batch-all-objects', '--batch-check=%(objectname)']).toString().trim().split('\n');
    const a = createRoutingMetadataAcquisition({repo: f.destination, baseline: f.baseline, token: '',
      loadTree: async (root, recursive) => ({sha: root, truncated: false,
        tree: f.git(f.origin, ['ls-tree', '-l', '-z', ...(recursive ? ['-r'] : []), root]).toString().split('\0').filter(Boolean).map(line => {
          const [, mode, type, sha, size, name] = line.match(/^(\d+) (\w+) ([a-f0-9]+)\s+(\d+|-)\t(.+)$/s);
          return {mode, type, sha, size: Number(size), path: name};
        })}),
      execute: (command, args, options) => execFileSync(command,
        args.map(arg => arg === 'https://github.com/ChengshuLi/WorldAtlas.git' ? 'file://' + f.origin : arg), options)
    });
    await a.resolvePath(id, pin.path);
    await a.acquire(pin, {bytes: row.size, sha256: digest(raw)});
    assert.equal(f.git(f.destination, ['cat-file', 'blob', row.sha]).toString(), raw);
    assert.throws(() => f.git(f.destination, ['cat-file', '-e', id]));
    assert(!fs.existsSync(path.join(f.destination, 'shallow')));
    const after = f.git(f.destination, ['cat-file', '--batch-all-objects', '--batch-check=%(objectname)']).toString().trim().split('\n');
    assert.deepEqual(after.filter(id => !before.includes(id)), [row.sha]);
    assert.equal(a.summary().origin_metadata_imports, 0); assert.equal(a.summary().fetched_objects, 1);
    await assert.rejects(a.acquire({...pin, git_blob_oid: 'f'.repeat(40)}, {bytes: row.size}), /differs from tree/);
    assert.equal(a.summary().fetched_objects, 1);
  } finally { f.close(); }
});


// The full cold reader consumes the original pin, not the newer same-path
// alias. Only the existing native metadata transport may issue its private proof.
test('cold immutable reader authenticates absent original paths without importing producer history',async()=>{
 const lazy=process.env.GIT_NO_LAZY_FETCH;process.env.GIT_NO_LAZY_FETCH='0';
 const f=originFixture();try{
  const name='scripts/physical.py',raw=Buffer.from('# original physical programme\n');
  const original=f.commit({[name]:raw.toString()}),current=f.commit({[name]:'# newer unrelated programme\n'});
  const row=f.maps.get(original).tree.find(p=>p.path===name);
  const pin={commit:original,path:name,mode:row.mode,git_blob_oid:row.sha,bytes:row.size,sha256:digest(raw)};
  const importObject=(id,type)=>f.git(f.remote,['hash-object','-w','-t',type,'--stdin'],f.git(f.origin,['cat-file',type,id]));
  const importTrees=id=>{const root=f.git(f.origin,['rev-parse',id+'^{tree}']).toString().trim();
   importObject(root,'tree');for(const line of f.git(f.origin,['ls-tree','-rt',id]).toString().trim().split('\n')){
    const [mode,type,oid]=line.split(/[ \t]/);if(type==='tree')importObject(oid,'tree');}
  };
  importObject(current,'commit');importTrees(current);
  const options={...f.loaders,execute:(command,args,options)=>{
    assert.equal(options.env.GIT_NO_LAZY_FETCH,'1');assert.equal(options.env.GIT_NO_REPLACE_OBJECTS,'1');
    if(args.includes('init'))f.calls.stores.push(args[args.indexOf('-C')+1]);
    if(args.includes('fetch'))args=args.map(arg=>arg==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+f.origin:arg);
    return execFileSync(command,args,options);
  }};
  const reader=new ImmutableReader(f.remote,current);
  assert.equal(reader.pinnedVersion(pin),current);
  assert.throws(()=>reader.descriptor(name,reader.pinnedVersion(pin)));
  await reader.acquirePinned(pin,options);
  assert.equal(reader.pinnedVersion(pin),original);
  assert.deepEqual(reader.read(name,{version:reader.pinnedVersion(pin),expected:pin.sha256}),raw);
  assert.equal(reader.inventory.get(original+':'+name).whole_body_consumed,true);
  assert.deepEqual(f.inventory().filter(([,type])=>type==='blob'),[[pin.git_blob_oid,'blob']]);
  assert.throws(()=>f.git(f.remote,['cat-file','-e',original+'^{commit}']));
  assert(!fs.existsSync(path.join(f.remote,'shallow')));
  for(const directory of f.calls.stores)assert(!fs.existsSync(directory));
  // Public inventory is observation, never authority for an absent origin.
  const forged=new ImmutableReader(f.remote,current);forged.inventory.set(original+':'+name,{...pin});
  assert.equal(forged.pinnedVersion(pin),current);
  await assert.rejects(forged.acquirePinned(pin,{...options,execute:()=>{throw Error('metadata unavailable');}}),/acquisition failed/);
  assert.equal(forged.pinnedVersion(pin),current);
  for(const changed of [{mode:'100755'},{git_blob_oid:'f'.repeat(40)},{bytes:pin.bytes+1},{sha256:'f'.repeat(64)}]){
   const bad=new ImmutableReader(f.remote,current);
   await assert.rejects(bad.acquirePinned({...pin,...changed},options),/differs|acquisition failed/);
   assert.equal(bad.pinnedVersion(pin),current);
  }
  await assert.rejects(new ImmutableReader(f.remote,current).acquirePinned(pin,{...options,execute:()=>{throw Error('transport unavailable');}}),/acquisition failed/);
  // Once original commit metadata becomes local, its own missing tree must
  // refuse instead of continuing to use the previously authenticated fallback.
  importObject(original,'commit');
  assert.equal(reader.pinnedVersion(pin),original);
  const beforeMissingTree=f.inventory();
  assert.throws(()=>reader.read(name,{version:reader.pinnedVersion(pin),expected:pin.sha256}));
  assert.throws(()=>reader.readPinned([pin]));
  assert.throws(()=>reader.treeRoute(name,original));
  await assert.rejects(reader.acquirePinned(pin,options));
  assert.deepEqual(f.inventory(),beforeMissingTree,'Known-origin tree probes cannot hydrate producer history');
  importTrees(original);
  assert.deepEqual(reader.read(name,{version:reader.pinnedVersion(pin),expected:pin.sha256}),raw);
  // A known original with a different path identity cannot use an exact alias.
  await assert.rejects(reader.acquirePinned({...pin,commit:current},options));
 }finally{f.close();if(lazy===undefined)delete process.env.GIT_NO_LAZY_FETCH;else process.env.GIT_NO_LAZY_FETCH=lazy;}
});

test('immutable sync, batch and stream reads ignore replacements without ambient guards',async()=>{
 const replace=process.env.GIT_NO_REPLACE_OBJECTS;delete process.env.GIT_NO_REPLACE_OBJECTS;
 const f=fixture();try{
  const name='data/source.json',row=f.maps.get(f.baseline).tree.find(p=>p.path===name),raw=f.bodies.get(row.sha);
  f.git(f.destination,['hash-object','-w','--stdin'],raw);
  const reader=new ImmutableReader(f.destination,f.baseline);reader.descriptor(name);
  const replacement=f.git(f.destination,['hash-object','-w','--stdin'],Buffer.alloc(raw.length,120)).toString().trim();
  f.git(f.destination,['update-ref','refs/replace/'+row.sha,replacement]);
  assert.deepEqual(reader.read(name,{expected:digest(raw)}),raw);
  assert.deepEqual(reader.gitBatch(['cat-file','--batch'],row.sha+'\n',raw.length+100),Buffer.concat([Buffer.from(`${row.sha} blob ${raw.length}\n`),raw,Buffer.from('\n')]));
  const chunks=[];for await(const chunk of reader.stream(name,{expected:digest(raw)}))chunks.push(chunk);
  assert.deepEqual(Buffer.concat(chunks),raw);
 }finally{f.close();if(replace===undefined)delete process.env.GIT_NO_REPLACE_OBJECTS;else process.env.GIT_NO_REPLACE_OBJECTS=replace;}
});

test('warm exact current aliases need no original metadata or transport',async()=>{
 const f=fixture();try{
  const name='data/source.json',row=f.maps.get(f.baseline).tree.find(p=>p.path===name),raw=f.bodies.get(row.sha);
  f.git(f.destination,['hash-object','-w','--stdin'],raw);
  const reader=new ImmutableReader(f.destination,f.baseline),pin={commit:'f'.repeat(40),path:name,mode:row.mode,git_blob_oid:row.sha,bytes:row.size,sha256:digest(raw)};
  const unavailable=()=>{throw Error('Warm aliases must remain offline');};
  await reader.acquirePinned(pin,{execute:unavailable});
  assert.equal(reader.pinnedVersion(pin),f.baseline);
  assert.deepEqual(reader.read(name,{version:reader.pinnedVersion(pin),expected:pin.sha256}),raw);
 }finally{f.close();}
});

test('historical code path groups authenticate one private origin session, never current aliases',async()=>{
 const lazy=process.env.GIT_NO_LAZY_FETCH;process.env.GIT_NO_LAZY_FETCH='0';
 const f=originFixture();try{
  const bodies={'code/a.js':'original first code\n','code/b.js':'original second code\n'};
  const original=f.commit(bodies),current=f.commit({...bodies,'code/b.js':'different current code\n'});
  const pins=Object.entries(bodies).map(([path,raw])=>({commit:original,path,bytes:Buffer.byteLength(raw),sha256:digest(raw)}));
  const importObject=(id,type)=>f.git(f.remote,['hash-object','-w','-t',type,'--stdin'],f.git(f.origin,['cat-file',type,id]));
  const importTrees=id=>{importObject(f.git(f.origin,['rev-parse',id+'^{tree}']).toString().trim(),'tree');
   for(const line of f.git(f.origin,['ls-tree','-rt',id]).toString().trim().split('\n')){const [,type,oid]=line.split(/[ \t]/);if(type==='tree')importObject(oid,'tree');}};
  importObject(current,'commit');importTrees(current);
  let blobBatches=0;
  const options={...f.loaders,execute:(command,args,options)=>{
   assert.equal(options.env.GIT_NO_LAZY_FETCH,'1');assert.equal(options.env.GIT_NO_REPLACE_OBJECTS,'1');
   if(args.includes('init'))f.calls.stores.push(args[args.indexOf('-C')+1]);
   if(args.includes('fetch')){if(!args.includes('--filter=tree:0'))blobBatches++;else(args.includes('--depth=1')?f.calls.commits:f.calls.trees).push(options.input.trim());args=args.map(x=>x==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+f.origin:x);}
   return execFileSync(command,args,options);
  }};
  const reader=new ImmutableReader(f.remote,current);
  await reader.acquireOriginalPaths(pins,options);
  assert.equal(f.calls.commits.length,1,'One native origin authentication for the known complete group');
  assert.equal(f.calls.trees.length,2,'One complete root and one complete code tree');assert.equal(blobBatches,1);
  for(const p of pins){assert.equal(reader.pinnedVersion(p),original);assert.deepEqual(reader.read(p.path,{version:original,expected:p.sha256}),Buffer.from(bodies[p.path]));}
  assert.throws(()=>f.git(f.remote,['--no-lazy-fetch','cat-file','-e',original+'^{commit}']));
  assert(!fs.existsSync(path.join(f.remote,'shallow')));for(const dir of f.calls.stores)assert(!fs.existsSync(dir));
  const before=f.calls.commits.length;await reader.acquireOriginalPaths(pins,{...options,execute:()=>{throw Error('warm original must not fetch');}});assert.equal(f.calls.commits.length,before);
  // Even an exact current a.js is not proof that the original commit had it.
  const forged=new ImmutableReader(f.remote,current);forged.inventory.set(original+':'+pins[0].path,{...pins[0],mode:'100644',git_blob_oid:'a'.repeat(40)});
  await assert.rejects(forged.acquireOriginalPaths([pins[0]],{...options,execute:()=>{throw Error('origin unavailable');}}),/acquisition failed/);
  for(const change of [{bytes:pins[0].bytes+1},{sha256:'f'.repeat(64)},{path:'code/absent.js'}]){
   const bad=new ImmutableReader(f.remote,current);await assert.rejects(bad.acquireOriginalPaths([{...pins[0],...change}],options));
   assert.equal(bad.pinnedVersion(pins[0]),current,'Failed acquisition must not install private origin proof');
  }
  await assert.rejects(new ImmutableReader(f.remote,current).acquireOriginalPaths([pins[0],pins[0]],options),/unique original path group/);
  await assert.rejects(new ImmutableReader(f.remote,current).acquireOriginalPaths(pins,{...options,execute:()=>{throw Error('transport unavailable');}}),/acquisition failed/);
  importObject(original,'commit');const inventory=f.inventory();
  await assert.rejects(reader.acquireOriginalPaths(pins,options));
  assert.throws(()=>reader.read(pins[0].path,{version:original,expected:pins[0].sha256}));
  assert.deepEqual(f.inventory(),inventory,'A now-known missing original tree cannot hydrate or use cached/current metadata');
  importTrees(original);await reader.acquireOriginalPaths(pins,{...options,execute:()=>{throw Error('known origin must not fetch');}});
  for(const p of pins)assert.deepEqual(reader.read(p.path,{version:original,expected:p.sha256}),Buffer.from(bodies[p.path]));
  await assert.rejects(reader.acquireOriginalPaths([{...pins[0],commit:current,path:'code/absent.js'}],options));
  assert.throws(()=>reader.read(pins[1].path,{version:current,expected:pins[1].sha256}),'Known wrong original bytes never fall back');
 }finally{f.close();if(lazy===undefined)delete process.env.GIT_NO_LAZY_FETCH;else process.env.GIT_NO_LAZY_FETCH=lazy;}
});


test('cold reader reuses native metadata across actual invocation readers, not bodies or transports',async()=>{
 const f=originFixture();try{
  const names=['a','b','c','d','e'],bodies=Object.fromEntries(names.map(n=>['code/'+n+'.js','original '+n+'\n']));
  const original=f.commit(bodies),current=f.commit(Object.fromEntries(names.map(n=>['code/'+n+'.js','current '+n+'\n'])));
  const pins=f.maps.get(original).tree.map(row=>({commit:original,path:row.path,mode:row.mode,git_blob_oid:row.sha,bytes:row.size,sha256:digest(bodies[row.path])}));
  for(const id of [current,f.git(f.origin,['rev-parse',current+'^{tree}']).toString().trim(),f.git(f.origin,['rev-parse',current+':code']).toString().trim()]){
   const type=f.git(f.origin,['cat-file','-t',id]).toString().trim();f.git(f.remote,['hash-object','-w','-t',type,'--stdin'],f.git(f.origin,['cat-file',type,id]));
  }
  const metadata=[],blobs=[],invocation=Object.freeze({});
  const execute=(command,args,options)=>{
   assert.equal(options.env.GIT_NO_LAZY_FETCH,'1');assert.equal(options.env.GIT_NO_REPLACE_OBJECTS,'1');
   if(args.includes('fetch')){(args.includes('--filter=tree:0')?metadata:blobs).push(options.input.trim());
    args=args.map(x=>x==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+f.origin:x);}
   return execFileSync(command,args,options);
  };
  const a=new ImmutableReader(f.remote,current,{invocation}),b=new ImmutableReader(f.remote,current,{invocation});
  await a.acquirePinned(pins[0],{execute});await a.acquirePinned(pins[1],{execute});await b.acquirePinned(pins[2],{execute});
  await b.acquireOriginalPaths([{commit:original,path:pins[3].path,bytes:pins[3].bytes,sha256:pins[3].sha256}],{execute});
  assert.equal(metadata.length,3,'One genuine commit, root tree and shared code tree for the entire invocation');
  assert.equal(new Set(metadata).size,3);assert.equal(blobs.length,4,'Each newly consumed exact body is still acquired');
  for(const [reader,group]of [[a,pins.slice(0,2)],[b,pins.slice(2,4)]])for(const p of group){
   assert.deepEqual(reader.read(p.path,{version:reader.pinnedVersion(p),expected:p.sha256}),Buffer.from(bodies[p.path]));
   assert.equal(reader.inventory.get(original+':'+p.path).whole_body_consumed,true);
  }
  const foreign=new ImmutableReader(f.remote,current,{invocation});
  await assert.rejects(foreign.acquirePinned(pins[4],{execute:(...args)=>{if(args[1].includes('fetch'))throw Error('distinct transport unavailable');return execute(...args);}}),/Immutable origin object fetch failed/);
  assert.equal(foreign.pinnedVersion(pins[4]),current,'A different transport cannot inherit private origin admission');
  const separate=new ImmutableReader(f.remote,current);await separate.acquirePinned(pins[4],{execute});
  assert.equal(metadata.length,6,'A separate invocation authenticates its own three origin objects');
  assert.throws(()=>f.git(f.remote,['--no-lazy-fetch','cat-file','-e',original+'^{commit}']));
  for(const changed of [{mode:'100755'},{git_blob_oid:'f'.repeat(40)},{bytes:pins[4].bytes+1},{sha256:'f'.repeat(64)}])
   await assert.rejects(new ImmutableReader(f.remote,current,{invocation}).acquirePinned({...pins[4],...changed},{execute}));
  f.git(f.remote,['hash-object','-w','-t','commit','--stdin'],f.git(f.origin,['cat-file','commit',original]));
  const before=f.inventory();await assert.rejects(b.acquirePinned(pins[4],{execute}));assert.deepEqual(f.inventory(),before);
  assert.throws(()=>a.read(pins[0].path,{version:a.pinnedVersion(pins[0]),expected:pins[0].sha256}),'Newly local incomplete origin overrides shared private proof');
 }finally{f.close();}
});
