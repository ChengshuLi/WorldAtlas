// Transport only for the explicit locator bodies requested by the applicability
// collector. Historical producer graphs and scientific leaves are never acquired.
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {createAcquisition, githubTree} from './geography-prefetch.mjs';

const FILE = 32 * 1024 * 1024, TOTAL = 64 * 1024 * 1024;
const demand = (value, message) => { if (!value) throw Error(message); };
const oid = value => /^[a-f0-9]{40}$/.test(value ?? '');
export function createRoutingMetadataAcquisition({repo, baseline, execute = execFileSync,
  loadTree = githubTree, token = process.env.GH_TOKEN,
  limits = {member: FILE, metadata: TOTAL, entries: 4096}}) {
  const env = {...Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_'))),
    GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0'};
  const git = args => {
    try { return execute('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', repo, ...args],
      {env, maxBuffer: FILE, timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']}).toString().trim(); }
    catch { throw Error('routing-metadata-tree-unavailable'); }
  };
  const trees = new Map(), planned = new Map(); let index;
  const stats = {tree_metadata_bytes: 0, tree_metadata_requests: 0, discovery_batches: 0};
  function tree(root, recursive) {
    demand(oid(root), 'routing-metadata-invalid-tree');
    const key = root + ':' + recursive;
    if (!trees.has(key)) {
      demand(trees.size < 128, 'routing-metadata-tree-count-limit');
      trees.set(key, (async () => {
        const value = await loadTree(root, recursive);
        const size = Buffer.byteLength(JSON.stringify(value));
        demand(size <= FILE && stats.tree_metadata_bytes + size <= TOTAL, 'routing-metadata-tree-byte-limit');
        stats.tree_metadata_bytes += size; stats.tree_metadata_requests++;
        demand(value && !value.truncated && value.sha === root && Array.isArray(value.tree)
          && new Set(value.tree.map(row => row.path)).size === value.tree.length, 'routing-metadata-invalid-tree-response');
        return value.tree;
      })());
    }
    return trees.get(key);
  }
  async function descriptor(version, name) {
    const line = git(['ls-tree', '-z', version, '--', name]);
    const match = line.match(/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/);
    demand(match && match[3] === name, 'routing-metadata-invalid-locator');
    // Immutable identity is still bound to the exact original (commit,path).
    // The baseline inventory is only an authenticated OID-to-size index, shared
    // by retained historical aliases; it never chooses a different body.
    index ??= tree(git(['rev-parse', baseline + '^{tree}']), true).then(rows => {
      const result = new Map();
      for (const row of rows.filter(row => row.type === 'blob')) {
        demand(!result.has(row.sha) || result.get(row.sha) === row.size, 'routing-metadata-conflicting-size');
        result.set(row.sha, row.size);
      }
      return result;
    });
    let size = (await index).get(match[2]);
    if (size === undefined) {
      const directory = path.posix.dirname(name);
      const root = git(['rev-parse', directory === '.' ? version + '^{tree}' : version + ':' + directory]);
      const rows = await tree(root, false), row = rows.find(row => row.path === path.posix.basename(name));
      demand(row && row.type === 'blob' && row.mode === match[1] && row.sha === match[2], 'routing-metadata-remote-identity');
      size = row.size;
    }
    // Admit the finite typed routing plan before any body fetch. The reader's
    // metadata limit bounds live raw retention, not cumulative legitimate I/O.
    demand(Number.isSafeInteger(size) && size > 0 && size <= limits.member && size <= limits.metadata,
      'metadata-byte-limit');
    demand(!planned.has(match[2]) || planned.get(match[2]) === size, 'routing-metadata-conflicting-size');
    demand(planned.has(match[2]) || planned.size < limits.entries, 'identity-entry-limit');
    planned.set(match[2], size);
    return {path: name, type: 'blob', mode: match[1], sha: match[2], size};
  }
  const acquisition = createAcquisition({repo, loadDescriptor: descriptor, execute, token,
    limits: {member: limits.member, total: limits.metadata, entries: limits.entries}});
  let pending = [], scheduled = false;
  async function flush() {
    const batch = pending; pending = []; scheduled = false;
    try {
      // Independent reader branches enqueue in one discovery round. Admit ALL
      // declared sizes before any exact-OID fetch from that round.
      const rows = await Promise.all(batch.map(item => acquisition.descriptor(item.pin.commit, item.pin.path,
        {mode: item.pin.mode, git_blob_oid: item.pin.git_blob_oid, ...item.expected})));
      acquisition.acquire(rows); stats.discovery_batches++;
      for (const item of batch) item.resolve();
    } catch (error) { for (const item of batch) item.reject(error); }
  }
  return {
    acquire(pin, expected) { return new Promise((resolve, reject) => {
      pending.push({pin, expected, resolve, reject});
      if (!scheduled) { scheduled = true; setImmediate(flush); }
    }); },
    summary() { return {...acquisition.stats, ...stats, scope: 'explicit-routing-metadata-only', scientific_leaf_imports: 0}; }
  };
}
