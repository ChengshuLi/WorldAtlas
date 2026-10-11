// Acquisition only. No candidate module is imported and no validation is skipped.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const FILE = 32 * 1024 * 1024, TOTAL = 512 * 1024 * 1024, ENTRIES = 512;
const repository = 'ChengshuLi/WorldAtlas';
const oid = value => /^[a-f0-9]{40}$/.test(value ?? '');
const sha256 = body => createHash('sha256').update(body).digest('hex');
const safe = value => typeof value === 'string' && value && !value.includes('\\') && !value.includes('\0') && !path.posix.isAbsolute(value) && value.split('/').every(p => p && p !== '.' && p !== '..');
const requireValue = (value, message) => { if (!value) throw Error(message); };

export function createAcquisition({repo, loadTree, execute = execFileSync, token = process.env.GH_TOKEN, limits = {member: FILE, total: TOTAL, entries: ENTRIES}}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
  Object.assign(env, {GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
    GIT_CONFIG_COUNT: token ? '3' : '2', GIT_CONFIG_KEY_0: 'core.hooksPath', GIT_CONFIG_VALUE_0: '/dev/null',
    GIT_CONFIG_KEY_1: 'credential.helper', GIT_CONFIG_VALUE_1: ''});
  if (token) Object.assign(env, {GIT_CONFIG_KEY_2: 'http.https://github.com/.extraheader',
    GIT_CONFIG_VALUE_2: 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:' + token).toString('base64')});
  const git = (args, input, maxBuffer = FILE + 1024) => {
    try { return execute('git', ['-C', repo, ...args], {env, input, maxBuffer, timeout: 60000, stdio: ['pipe', 'pipe', 'pipe']}); }
    catch { throw Error('Bounded geography object acquisition failed'); }
  };
  const trees = new Map(), inventory = new Map(), verified = new Set();
  const stats = {scope: 'declared-selected-bank-and-direct-additive-assets', complete_scientific_closure: false,
    unique_objects: 0, declared_bytes: 0, verified_import_objects: 0, verified_import_bytes: 0, fetch_batches: 0,
    tree_metadata_ms: 0, fetch_ms: 0, verification_ms: 0, declarations: 0};
  async function tree(version) {
    requireValue(oid(version), 'Invalid immutable geography commit');
    if (!trees.has(version)) {
      requireValue(trees.size < 8, 'Geography prefetch tree limit');
      const started = performance.now();
      const root = git(['rev-parse', version + '^{tree}']).toString().trim();
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
    requireValue(stats.declarations < limits.entries, 'Geography prefetch declaration limit');
    stats.declarations++;
    const row = (await tree(version)).get(name);
    requireValue(row?.type === 'blob' && ['100644', '100755'].includes(row.mode) && oid(row.sha)
      && Number.isSafeInteger(row.size) && row.size >= 0 && row.size <= limits.member, 'Missing, nonordinary or oversized declared geography input');
    requireValue(git(['ls-tree', '-z', version, '--', name]).toString() === `${row.mode} blob ${row.sha}\t${name}\0`,
      'Remote descriptor differs from actual immutable Git tree');
    requireValue((expected.mode === undefined || expected.mode === row.mode)
      && (expected.git_blob_oid === undefined || expected.git_blob_oid === row.sha)
      && (expected.bytes === undefined || expected.bytes === row.size), 'Declared geography identity differs from tree');
    if (expected.sha256 !== undefined) requireValue(/^[a-f0-9]{64}$/.test(expected.sha256), 'Invalid declared geography hash');
    const previous = inventory.get(row.sha);
    requireValue(!previous || previous.bytes === row.size, 'Conflicting declared object lengths');
    if (!previous) {
      requireValue(inventory.size < limits.entries && stats.declared_bytes + row.size <= limits.total, 'Geography prefetch aggregate limit');
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
    const raw = git(['cat-file', 'blob', row.oid]);
    requireValue(raw.length === row.bytes && createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === row.oid,
      'Acquired geography object does not match tree');
    requireValue(!row.sha256 || sha256(raw) === row.sha256, 'Acquired geography body differs from declared hash');
    return raw;
  }
  function acquire(rows) {
    const unique = [...new Map(rows.map(row => [row.oid, row])).values()];
    if (!unique.length) return;
    const status = git(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], unique.map(r => r.oid).join('\n') + '\n').toString().trim().split('\n');
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
      // or lazy graph hydration, one bounded batch rather than per-body fetches.
      const started = performance.now();
      git(['-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules', '--no-auto-maintenance',
        '--filter=blob:none', '--stdin', 'https://github.com/' + repository + '.git'], missing.map(r => r.oid).join('\n') + '\n', 1024 * 1024);
      stats.fetch_ms += Math.round(performance.now() - started);
      stats.fetch_batches++;
    }
    const started = performance.now();
    for (const row of rows) {
      // Verify once per actual OID/hash binding, including multiple aliases.
      const key = row.oid + ':' + (row.sha256 ?? '');
      if (!verified.has(key)) { body(row); verified.add(key); }
    }
    stats.verification_ms += Math.round(performance.now() - started);
    stats.verified_import_objects += missing.length; stats.verified_import_bytes += missing.reduce((n, r) => n + r.bytes, 0);
  }
  async function json(version, name, expected) {
    const row = await descriptor(version, name, expected); acquire([row]); return JSON.parse(body(row));
  }
  return {tree, descriptor, pin, acquire, json, stats};
}

export async function prefetchSelectedGeography(acquisition, baseline, candidate) {
  const a = acquisition, banks = [], leaves = [];
  for (const version of new Set([baseline, candidate])) {
    const tree = await a.tree(version);
    if (!tree.has('data/ownership-selection.json')) continue;
    const selection = await a.json(version, 'data/ownership-selection.json');
    requireValue(selection.version === 1 && safe(selection.manifest_path), 'Unsupported selected geography');
    const manifest = await a.json(version, selection.manifest_path, {sha256: selection.sha256});
    requireValue(Array.isArray(manifest.parts) && manifest.parts.length <= ENTRIES, 'Unsupported native part roster');
    requireValue(manifest.parts.every(p => safe(p.path)), 'Unsafe native part path');
    const root = path.posix.dirname(selection.manifest_path);
    const missingParts = manifest.parts.filter(p => !tree.has(path.posix.join(root, p.path)));
    for (const p of manifest.parts.filter(p => tree.has(path.posix.join(root, p.path))))
      leaves.push(await a.descriptor(version, path.posix.join(root, p.path), p));
    if (missingParts.length) {
      const transport = manifest.native_asset_transport;
      requireValue(transport?.kind === 'ordered-exact-original-byte-fragments' && transport.index, 'Unrecognized native transport; retain ordinary checker acquisition');
      const index = await a.json(version, transport.index.path, transport.index);
      requireValue(Array.isArray(index.parts) && index.parts.length <= ENTRIES, 'Unsupported native transport roster');
      const directory = path.posix.dirname(transport.index.path);
      for (const p of index.parts) { requireValue(safe(p.path), 'Unsafe transport part'); leaves.push(await a.descriptor(version, path.posix.join(directory, p.path), p)); }
    }
    const declared = selection.selected_geography;
    requireValue(declared?.kind === 'complete-world-index-with-exact-encoded-overrides', 'Unrecognized source bank; retain ordinary checker acquisition');
    const bank = await a.json(version, declared.path, declared);
    requireValue(Array.isArray(bank.unchanged_files) && Array.isArray(bank.overrides)
      && bank.unchanged_files.length + bank.overrides.length + 1 <= ENTRIES, 'Unsupported selected source roster');
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

async function githubTree(version) {
  const headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};
  if (process.env.GH_TOKEN) headers.Authorization = 'Bearer ' + process.env.GH_TOKEN;
  const response = await fetch(`https://api.github.com/repos/${repository}/git/trees/${version}?recursive=1`, {headers, signal: AbortSignal.timeout(60000)});
  requireValue(response.ok, 'Geography tree metadata unavailable');
  const chunks = []; let bytes = 0;
  for await (const chunk of response.body) { bytes += chunk.length; requireValue(bytes <= FILE, 'Geography tree metadata exceeds bound'); chunks.push(chunk); }
  return JSON.parse(Buffer.concat(chunks).toString());
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
