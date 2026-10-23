// Transport only for the explicit locator bodies requested by the applicability
// collector, plus exact origin commit/path trees when descriptors are cold.
// Historical parent graphs and scientific leaves are never acquired.
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {createAcquisition, githubTree} from './geography-prefetch.mjs';

const demand = (value, message) => { if (!value) throw Error(message); };
const oid = value => /^[a-f0-9]{40}$/.test(value ?? '');
export function createRoutingMetadataAcquisition({repo, baseline, execute = execFileSync,
  loadTree = githubTree, token = process.env.GH_TOKEN}) {
  const env = {...Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_'))),
    GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0'};
  const git = args => {
    try { return execute('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', repo, ...args],
      {env, maxBuffer: Infinity, timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']}).toString().trim(); }
    catch { throw Error('routing-metadata-tree-unavailable'); }
  };
  const trees = new Map(), planned = new Map(); let index;
  const stats = {tree_metadata_bytes: 0, tree_metadata_requests: 0, discovery_batches: 0};
  function validEntry(row, recursive) {
    const parts = typeof row?.path === 'string' ? row.path.split('/') : [];
    const safeParts = parts.length > 0 && parts.every(part => part && part !== '.' && part !== '..'
      && !/[\x00-\x1f\x7f\\]/.test(part));
    return safeParts && (recursive || parts.length === 1) && oid(row.sha)
      && (row.type === 'tree' && row.mode === '040000'
        || row.type === 'commit' && row.mode === '160000'
        || row.type === 'blob' && ['100644', '100755', '120000'].includes(row.mode)
          && Number.isSafeInteger(row.size) && row.size >= 0);
  }
  async function loadCompleteTree(root, recursive, ancestors = new Set()) {
    demand(!ancestors.has(root), 'routing-metadata-cyclic-tree');
    const value = await loadTree(root, recursive);
    const size = Buffer.byteLength(JSON.stringify(value));
    stats.tree_metadata_bytes += size; stats.tree_metadata_requests++;
    demand(value && value.sha === root && Array.isArray(value.tree), 'routing-metadata-invalid-tree-response');
    if (value.truncated !== true) {
      demand(value.truncated === false && value.tree.every(row => validEntry(row, recursive)), 'routing-metadata-invalid-tree-response');
      return value.tree;
    }
    demand(recursive, 'routing-metadata-invalid-tree-response');
    // GitHub may truncate a recursive tree inventory even when each direct
    // directory listing is complete. Discard the partial recursive rows and
    // rebuild the exact inventory from immutable child tree IDs.
    const direct = await loadTree(root, false);
    const directSize = Buffer.byteLength(JSON.stringify(direct));
    stats.tree_metadata_bytes += directSize; stats.tree_metadata_requests++;
    demand(direct && direct.sha === root && direct.truncated === false && Array.isArray(direct.tree)
      && direct.tree.every(row => validEntry(row, false)),
      'routing-metadata-incomplete-direct-tree-response');
    const entries = new Map(), nextAncestors = new Set(ancestors); nextAncestors.add(root);
    for (const row of direct.tree) {
      demand(!entries.has(row.path), 'routing-metadata-invalid-direct-tree-entry');
      entries.set(row.path, row);
    }
    for (const row of direct.tree) if (row.type === 'tree') {
      demand(oid(row.sha), 'routing-metadata-invalid-child-tree');
      const childRows = await loadCompleteTree(row.sha, true, nextAncestors);
      for (const child of childRows) {
        const name = row.path + '/' + child.path;
        demand(!entries.has(name), 'routing-metadata-duplicate-expanded-tree-path');
        entries.set(name, {...child, path: name});
      }
    }
    return [...entries.values()].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  }
  function tree(root, recursive) {
    demand(oid(root), 'routing-metadata-invalid-tree');
    const key = root + ':' + recursive;
    if (!trees.has(key)) {
      trees.set(key, (async () => {
        const rows = await loadCompleteTree(root, recursive);
        demand(new Set(rows.map(row => row.path)).size === rows.length, 'routing-metadata-invalid-tree-response');
        return rows;
      })());
    }
    return trees.get(key);
  }
  async function descriptor(version, name) {
    let original;
    try {
      const line = git(['ls-tree', '-z', version, '--', name]);
      const match = line.match(/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/);
      demand(match && match[3] === name, 'routing-metadata-invalid-locator');
      original = {mode: match[1], git_blob_oid: match[2]};
    } catch (error) {
      if (error.message !== 'routing-metadata-tree-unavailable') throw error;
      original = await acquisition.resolvePath(version, name);
    }
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
    let size = (await index).get(original.git_blob_oid);
    if (size === undefined) {
      const directory = path.posix.dirname(name);
      const root = original.tree_oid ?? git(['rev-parse', directory === '.' ? version + '^{tree}' : version + ':' + directory]);
      const rows = await tree(root, false), row = rows.find(row => row.path === path.posix.basename(name));
      demand(row && row.type === 'blob' && row.mode === original.mode && row.sha === original.git_blob_oid, 'routing-metadata-remote-identity');
      size = row.size;
    }
    // The exact remote size remains bound to the original Git identity before
    // acquisition; finite larger routing metadata is not a different input role.
    demand(Number.isSafeInteger(size) && size > 0, 'invalid-metadata-length');
    demand(!planned.has(original.git_blob_oid) || planned.get(original.git_blob_oid) === size, 'routing-metadata-conflicting-size');
    planned.set(original.git_blob_oid, size);
    return {path: name, type: 'blob', mode: original.mode, sha: original.git_blob_oid, size};
  }
  const acquisition = createAcquisition({repo, loadDescriptor: descriptor,
    loadTree: async root => ({sha: root, tree: await tree(root, false), truncated: false}), execute, token});
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
    resolvePath: acquisition.resolvePath,
    acquire(pin, expected) { return new Promise((resolve, reject) => {
      pending.push({pin, expected, resolve, reject});
      if (!scheduled) { scheduled = true; setImmediate(flush); }
    }); },
    summary() { return {...acquisition.stats, ...stats, scope: 'explicit-routing-metadata-only', scientific_leaf_imports: 0}; }
  };
}
