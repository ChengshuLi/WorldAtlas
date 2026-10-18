// Acquisition only. No candidate module is imported; actual readers authenticate their inputs.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const repository = 'ChengshuLi/WorldAtlas';
const oid = value => /^[a-f0-9]{40}$/.test(value ?? '');
const sha256 = body => createHash('sha256').update(body).digest('hex');
const safe = value => typeof value === 'string' && value && !value.includes('\\') && !value.includes('\0') && !path.posix.isAbsolute(value) && value.split('/').every(p => p && p !== '.' && p !== '..');
const requireValue = (value, message) => { if (!value) throw Error(message); };

export function createAcquisition({repo, loadTree, loadDescriptor, loadCommit, execute = execFileSync, token = process.env.GH_TOKEN}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
  Object.assign(env, {GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
    GIT_CONFIG_COUNT: token ? '3' : '2', GIT_CONFIG_KEY_0: 'core.hooksPath', GIT_CONFIG_VALUE_0: '/dev/null',
    GIT_CONFIG_KEY_1: 'credential.helper', GIT_CONFIG_VALUE_1: ''});
  if (token) Object.assign(env, {GIT_CONFIG_KEY_2: 'http.https://github.com/.extraheader',
    GIT_CONFIG_VALUE_2: 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:' + token).toString('base64')});
  const git = (args, input, expectedBytes) => {
    // Captured output has an exact immutable/protocol length. Commands whose
    // output is not consumed need no buffered stdout or stderr at all.
    const output = expectedBytes === undefined ? {} : {maxBuffer: expectedBytes + 1};
    try { return execute('git', ['-C', repo, ...args], {env, input, ...output, timeout: 60000,
      stdio: ['pipe', expectedBytes === undefined ? 'ignore' : 'pipe', 'ignore']}); }
    catch { throw Error('Geography object acquisition failed'); }
  };
  const trees = new Map(), inventory = new Map();
  const stats = {scope: 'declared-selected-bank-and-direct-additive-assets', complete_scientific_closure: false,
    unique_objects: 0, declared_bytes: 0, fetched_objects: 0, fetched_bytes: 0, fetch_batches: 0,
    tree_metadata_ms: 0, fetch_ms: 0, declarations: 0,
    origin_metadata_objects: 0, origin_metadata_bytes: 0, origin_metadata_fetches: 0, origin_metadata_imports: 0};
  const originObjects = new Map(), originPaths = new Set();
  async function originObject(id, type) {
    requireValue(oid(id) && ['commit', 'tree'].includes(type), 'Invalid immutable origin metadata');
    if (!originObjects.has(id)) {
      let declaredRoot;
      // --missing prevents implicit lazy acquisition even on older Git versions.
      // No ancestry traversal: the only requested root is this exact object.
      const present = git(['-c', 'core.commitGraph=false', 'rev-list', '--objects', '--filter=tree:0',
        '--missing=print', '--ignore-missing', '--no-walk=unsorted', '--no-object-names', '--stdin'], id + '\n', 42).toString().trim();
      if (present !== id) {
        requireValue(present === '' || present === '?' + id, 'Invalid local origin metadata inventory');
        if (type === 'commit') {
          // An explicitly wanted blob bypasses Git's filter. Admit the exact
          // origin through the commit endpoint before any native fetch, then
          // verify the imported native object's type, hash and root below.
          const declared = await loadCommit(id);
          requireValue(declared?.sha === id && oid(declared.tree?.sha), 'Wrong immutable origin commit metadata');
          declaredRoot = declared.tree.sha;
          git(['-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '--no-tags', '--no-write-fetch-head',
            '--no-recurse-submodules', '--no-auto-maintenance', '--filter=tree:0', '--depth=1',
            '--stdin', 'https://github.com/' + repository + '.git'], id + '\n');
          stats.origin_metadata_fetches++;
        } else {
          // Reconstruct only one nonrecursive Git tree, authenticating its
          // complete native bytes before import. No child object is requested.
          const value = await loadTree(id, false);
          requireValue(value?.sha === id && !value.truncated && Array.isArray(value.tree)
            && new Set(value.tree.map(row => row.path)).size === value.tree.length, 'Wrong immutable origin tree metadata');
          const modes = {'040000': 'tree', '100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'};
          const chunks = value.tree.map(row => {
            requireValue(Object.hasOwn(modes, row.mode) && modes[row.mode] === row.type && oid(row.sha)
              && typeof row.path === 'string' && row.path && !['.', '..'].includes(row.path)
              && !row.path.includes('\0') && !row.path.includes('/'), 'Malformed immutable origin tree entry');
            return Buffer.concat([Buffer.from(`${row.mode === '040000' ? '40000' : row.mode} ${row.path}\0`), Buffer.from(row.sha, 'hex')]);
          });
          const raw = Buffer.concat(chunks);
          requireValue(createHash('sha1').update(`tree ${raw.length}\0`).update(raw).digest('hex') === id,
            'Wrong immutable origin tree identity');
          requireValue(git(['hash-object', '-w', '-t', 'tree', '--stdin'], raw, 41).toString().trim() === id,
            'Wrong imported origin tree identity');
        }
        stats.origin_metadata_imports++;
      }
      const status = git(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], id + '\n', 80).toString().trim().split(' ');
      const size = Number(status[2]);
      requireValue(status.length === 3 && status[0] === id && status[1] === type
        && Number.isSafeInteger(size) && size >= 0, 'Wrong immutable origin metadata type/size');
      const raw = git(['cat-file', type, id], undefined, size);
      requireValue(raw.length === size && createHash('sha1').update(`${type} ${size}\0`).update(raw).digest('hex') === id,
        'Wrong immutable origin metadata identity');
      const root = type === 'commit' ? raw.toString().match(/^tree ([a-f0-9]{40})\n/)?.[1] : undefined;
      requireValue(type !== 'commit' || oid(root), 'Invalid immutable origin root tree');
      requireValue(declaredRoot === undefined || root === declaredRoot, 'Wrong immutable origin root tree');
      originObjects.set(id, {type, size, root});
      stats.origin_metadata_objects++; stats.origin_metadata_bytes += size;
    }
    const value = originObjects.get(id);
    requireValue(value.type === type, 'Wrong immutable origin metadata type/size');
    return value;
  }
  async function resolvePath(version, name) {
    requireValue(oid(version) && safe(name), 'Unsafe immutable origin locator');
    const key = version + ':' + name;
    if (originPaths.has(key)) return;
    let root = (await originObject(version, 'commit')).root;
    const parts = name.split('/');
    for (let i = 0; i < parts.length; i++) {
      const tree = await originObject(root, 'tree');
      // Resolve one component at a time. Having the commit (or another path's
      // trees) does not imply that this path's intermediate trees are present.
      const row = git(['--literal-pathspecs', 'ls-tree', '-z', root, '--', parts[i]], undefined, tree.size + 64).toString();
      const match = row.match(/^(040000 tree|100644 blob|100755 blob) ([a-f0-9]{40})\t([^\0]+)\0$/);
      requireValue(match && match[3] === parts[i]
        && (i === parts.length - 1 ? match[1].endsWith(' blob') : match[1] === '040000 tree'), 'Missing or nonordinary immutable origin path');
      root = match[2];
    }
    // The final blob is only an identity operand. Never acquire its body here.
    originPaths.add(key);
  }
  async function tree(version) {
    requireValue(oid(version), 'Invalid immutable geography commit');
    if (!trees.has(version)) {
      const started = performance.now();
      const root = git(['rev-parse', version + '^{tree}'], undefined, 41).toString().trim();
      requireValue(oid(root), 'Invalid immutable geography root tree');
      // GitHub echoes a supplied commit in the envelope SHA. Request the actual
      // locally bound tree OID so the envelope and every row remain exact-bound.
      const value = await loadTree(root);
      stats.tree_metadata_ms += Math.round(performance.now() - started);
      requireValue(value && !value.truncated && value.sha === root && Array.isArray(value.tree), 'Incomplete or wrong immutable tree metadata');
      const rows = new Map(value.tree.map(row => [row.path, row]));
      requireValue(rows.size === value.tree.length, 'Duplicate tree metadata paths');
      trees.set(version, rows);
    }
    return trees.get(version);
  }
  async function descriptor(version, name, expected = {}) {
    requireValue(safe(name), 'Unsafe declared geography path');
    stats.declarations++;
    const row = loadDescriptor ? await loadDescriptor(version, name) : (await tree(version)).get(name);
    requireValue(row?.type === 'blob' && ['100644', '100755'].includes(row.mode) && oid(row.sha)
      && Number.isSafeInteger(row.size) && row.size >= 0, 'Missing or nonordinary declared geography input');
    const expectedTreeRow = `${row.mode} blob ${row.sha}\t${name}\0`;
    requireValue(git(['ls-tree', '-z', version, '--', name], undefined, Buffer.byteLength(expectedTreeRow)).toString() === expectedTreeRow,
      'Remote descriptor differs from actual immutable Git tree');
    requireValue((expected.mode === undefined || expected.mode === row.mode)
      && (expected.git_blob_oid === undefined || expected.git_blob_oid === row.sha)
      && (expected.bytes === undefined || expected.bytes === row.size), 'Declared geography identity differs from tree');
    if (expected.sha256 !== undefined) requireValue(/^[a-f0-9]{64}$/.test(expected.sha256), 'Invalid declared geography hash');
    const previous = inventory.get(row.sha);
    requireValue(!previous || previous.bytes === row.size, 'Conflicting declared object lengths');
    if (!previous) {
      inventory.set(row.sha, {oid: row.sha, bytes: row.size}); stats.declared_bytes += row.size;
    }
    stats.unique_objects = inventory.size;
    return {version, path: name, oid: row.sha, bytes: row.size, ...(expected.sha256 ? {sha256: expected.sha256} : {})};
  }
  async function pin(version, value) {
    requireValue(value && safe(value.path), 'Missing declared geography pin');
    let selected = version;
    if (value.commit !== undefined) {
      requireValue(oid(value.commit), 'Invalid historical geography commit');
      // Match the existing reader's same-path historical alias when the original
      // producer commit is absent. Never fetch a historical graph implicitly.
      try { git(['cat-file', '-e', value.commit + '^{commit}']); selected = value.commit; } catch {}
    }
    return descriptor(selected, value.path, value);
  }
  function body(row) {
    const raw = git(['cat-file', 'blob', row.oid], undefined, row.bytes);
    requireValue(raw.length === row.bytes && createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === row.oid,
      'Acquired geography object does not match tree');
    requireValue(!row.sha256 || sha256(raw) === row.sha256, 'Acquired geography body differs from declared hash');
    return raw;
  }
  function acquire(rows) {
    const unique = [...new Map(rows.map(row => [row.oid, row])).values()];
    if (!unique.length) return;
    const statusBytes = unique.reduce((n, row) => n + Math.max(
      Buffer.byteLength(`${row.oid} missing\n`), Buffer.byteLength(`${row.oid} blob ${row.bytes}\n`)), 0);
    const status = git(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
      unique.map(r => r.oid).join('\n') + '\n', statusBytes).toString().trim().split('\n');
    requireValue(status.length === unique.length, 'Incomplete local object inventory');
    const missing = [];
    for (let i = 0; i < unique.length; i++) {
      const row = unique[i], fields = status[i].split(' ');
      requireValue(fields[0] === row.oid, 'Wrong local object inventory');
      if (fields.length === 2 && fields[1] === 'missing') missing.push(row);
      else requireValue(fields.length === 3 && fields[1] === 'blob' && Number(fields[2]) === row.bytes, 'Local geography object type/size differs');
    }
    if (missing.length) {
      // Existing cloud bootstrap import mechanism: exact OIDs, no negotiation
      // or lazy graph hydration, one shared batch rather than per-body fetches.
      const started = performance.now();
      git(['-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules', '--no-auto-maintenance',
        '--filter=blob:none', '--stdin', 'https://github.com/' + repository + '.git'], missing.map(r => r.oid).join('\n') + '\n');
      stats.fetch_ms += Math.round(performance.now() - started);
      stats.fetch_batches++;
      stats.fetched_objects += missing.length; stats.fetched_bytes += missing.reduce((n, r) => n + r.bytes, 0);
    }
    // Acquisition supplies objects, not verified scientific inputs. Each actual
    // reader authenticates its consumed bytes, including the JSON reader below.
  }
  async function json(version, name, expected) {
    const row = await descriptor(version, name, expected);
    acquire([row]);
    return JSON.parse(body(row));
  }
  return {tree, descriptor, pin, acquire, json, resolvePath, stats};
}

export async function prefetchSelectedGeography(acquisition, baseline, candidate) {
  const a = acquisition, banks = [], leaves = [];
  for (const version of new Set([baseline, candidate])) {
    const tree = await a.tree(version);
    if (!tree.has('data/ownership-selection.json')) continue;
    const selection = await a.json(version, 'data/ownership-selection.json');
    requireValue(selection.version === 1 && safe(selection.manifest_path), 'Unsupported selected geography');
    const manifest = await a.json(version, selection.manifest_path, {sha256: selection.sha256});
    requireValue(Array.isArray(manifest.parts), 'Unsupported native part roster');
    requireValue(manifest.parts.every(p => safe(p.path)), 'Unsafe native part path');
    const root = path.posix.dirname(selection.manifest_path);
    const missingParts = manifest.parts.filter(p => !tree.has(path.posix.join(root, p.path)));
    for (const p of manifest.parts.filter(p => tree.has(path.posix.join(root, p.path))))
      leaves.push(await a.descriptor(version, path.posix.join(root, p.path), p));
    if (missingParts.length) {
      const transport = manifest.native_asset_transport;
      requireValue(transport?.kind === 'ordered-exact-original-byte-fragments' && transport.index, 'Unrecognized native transport; retain ordinary checker acquisition');
      const index = await a.json(version, transport.index.path, transport.index);
      requireValue(Array.isArray(index.parts), 'Unsupported native transport roster');
      const directory = path.posix.dirname(transport.index.path);
      for (const p of index.parts) { requireValue(safe(p.path), 'Unsafe transport part'); leaves.push(await a.descriptor(version, path.posix.join(directory, p.path), p)); }
    }
    const declared = selection.selected_geography;
    requireValue(declared?.kind === 'complete-world-index-with-exact-encoded-overrides', 'Unrecognized source bank; retain ordinary checker acquisition');
    const bank = await a.json(version, declared.path, declared);
    requireValue(Array.isArray(bank.unchanged_files) && Array.isArray(bank.overrides), 'Unsupported selected source roster');
    for (const p of [bank.world_index, ...bank.unchanged_files, ...bank.overrides]) leaves.push(await a.pin(version, p));
    if (selection.additive_release) {
      const p = selection.additive_release, sidecar = await a.json(version, p.path, p);
      requireValue(sidecar.kind === 'retained-native-additive-selection-v2' && sidecar.logical_asset_map
        && Object.keys(sidecar.logical_asset_map).sort().join(',') === 'base_manifest,ledger,owner_roster,patch', 'Unsupported additive acquisition scope');
      for (const pin of [sidecar.runtime_envelope, sidecar.authority_registry, ...Object.values(sidecar.logical_asset_map)]) leaves.push(await a.pin(version, pin));
    }
    if (selection.artifact_consumption) {
      const {certificate: p, review} = selection.artifact_consumption;
      const certificate = await a.json(version, p.path, p);
      for (const pin of [review, certificate.application_consumer_code, certificate.qualification_inventory,
        certificate.release_product_catalogue, certificate.selected_artifact_bindings?.registry].filter(Boolean)) leaves.push(await a.pin(version, pin));
    }
    banks.push(version);
  }
  a.acquire(leaves);
  return {...a.stats, selected_commits: banks, status: 'scoped-prefetch-completed',
    limits: ['No scientific or full dependency-closure claim. Deeper historical authority/rebind inputs and unknown formats retain the unchanged checker acquisition.']};
}

export async function githubCommit(version) {
  return githubMetadata(`commits/${version}`);
}

export async function githubTree(version, recursive = true) {
  return githubMetadata(`trees/${version}${recursive ? '?recursive=1' : ''}`);
}

async function githubMetadata(locator) {
  const headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};
  if (process.env.GH_TOKEN) headers.Authorization = 'Bearer ' + process.env.GH_TOKEN;
  const response = await fetch(`https://api.github.com/repos/${repository}/git/${locator}`, {headers, signal: AbortSignal.timeout(60000)});
  requireValue(response.ok, 'Geography tree metadata unavailable');
  return response.json();
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo, baseline, candidate] = process.argv.slice(2), start = performance.now();
  const acquisition = createAcquisition({repo, loadTree: githubTree});
  try {
    const result = await prefetchSelectedGeography(acquisition, baseline, candidate);
    process.stdout.write(JSON.stringify({...result, elapsed_ms: Math.round(performance.now() - start)}) + '\n');
  } catch (error) {
    // Acquisition is optional. Never conceal a partial attempt or convert it to
    // science success; the original trusted checker still runs in full.
    process.stdout.write(JSON.stringify({...acquisition.stats, status: 'scoped-prefetch-unavailable', partial_import_possible: true,
      reason: error instanceof SyntaxError ? 'Invalid declared JSON metadata' : error.message,
      elapsed_ms: Math.round(performance.now() - start)}) + '\n');
    process.exitCode = 1;
  }
}
