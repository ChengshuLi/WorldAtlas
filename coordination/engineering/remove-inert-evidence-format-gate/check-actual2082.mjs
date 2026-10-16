// Run from the repository root. Original immutable objects must already be
// available; this verifier never fetches, checks out, unpacks, or runs sources.
// An optional Git directory supports an independently retained object store.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';
import {selectedDataCandidate, selectedDataSelection, candidateGeographyCode} from '../../../scripts/integration-profile.mjs';
const input = JSON.parse(fs.readFileSync(new URL('./pr2082.json', import.meta.url)));
const env = {...process.env, GIT_NO_LAZY_FETCH:'1', GIT_NO_REPLACE_OBJECTS:'1', GIT_TERMINAL_PROMPT:'0'};
const git = (...args) => execFileSync('git', [...(process.argv[2] ? ['--git-dir=' + process.argv[2]] : []), ...args],
  {env, maxBuffer:128 * 1024 * 1024});
const tree = commit => ({object:{sha:commit}, entries:new Map(git('ls-tree', '-r', '-l', commit).toString().trim().split('\n').map(line => {
  const [metadata, path] = line.split('\t'), [mode, type, sha, size] = metadata.trim().split(/\s+/);
  return [path, {path, mode, type, sha, size:Number(size)}];
}))});
const api = async route => {
  if (route.includes('/git/blobs/')) {
    const sha = route.split('/').at(-1), bytes = git('cat-file', 'blob', sha);
    return {sha, size:bytes.length, encoding:'base64', content:bytes.toString('base64')};
  }
  if (route.includes('/git/commits/')) {
    const sha = route.split('/').at(-1);
    return {sha, tree:{sha:git('rev-parse', sha + '^{tree}').toString().trim()}};
  }
  if (route.includes('/git/trees/')) return {truncated:false,
    tree:[...tree(route.split('/').at(-1).split('?')[0]).entries.values()]};
  if (route.includes('/compare/')) {
    const [base, head] = route.split('/').at(-1).split('...');
    git('merge-base', '--is-ancestor', base, head); return {status:'ahead'};
  }
  throw Error('Unexpected read-only route: ' + route);
};
const started = performance.now(), metadataDiagnostics = {};
assert.equal(selectedDataCandidate(input.branch, input.files, input.reservation), true);
const result = await selectedDataSelection({...input, api, repo:'ChengshuLi/WorldAtlas',
  baseline:tree(input.base), authored:tree(input.head), metadataDiagnostics});
assert.deepEqual(result, input.expected, metadataDiagnostics.failure);
const geography_software = candidateGeographyCode('full', input.files, result.test_selection);
assert.equal(geography_software, false);
console.log(JSON.stringify({head:input.head, base:input.base, changed_paths:input.files.length,
  result, geography_software, metadataDiagnostics, elapsed_ms:Math.round(performance.now() - started)}, null, 2));
