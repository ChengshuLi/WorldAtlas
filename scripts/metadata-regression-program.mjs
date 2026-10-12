import {createHash} from 'node:crypto';

export const METADATA_PROGRAMS = '.github/metadata-regression-programs.json';
export const METADATA_FRESH_TESTS = ['test/job-deadline.test.mjs', 'test/supported-programs.test.mjs',
  'test/selected-data-profile.test.mjs', 'test/integration-profile-restoration.test.mjs'];
const EXECUTABLE = /\.(?:mjs|cjs|js|jsx|ts|tsx|py|sh|html|wasm|node|so|dylib)$/;
const CODE_IMAGES = [
  'coordination/engineering/eastern-two-gap-repair-native-20261007/current-consumer-code/',
  'coordination/engineering/eastern-two-gap-repair-native-20261007/prior-v1/',
  'coordination/engineering/subject-descriptor-decode-20261007/legacy-context-v1/'
];
const POLICY_ROLES = new Set([
  'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json',
  'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'
]);
const hash = value => createHash('sha256').update(JSON.stringify(value) + '\n').digest('hex');
const need = (value, reason) => {if (!value) throw Error(reason);};

// This is deliberately conservative known-program admission, not dependency
// inference. Whole test discovery and ordinary execution namespaces are fixed;
// archived executable images retain their existing complete custody. Unrelated
// code inside the NEW receiving packet is excluded only after its audited
// package/scientific non-consumption and base-directory absence are established.
export function metadataRegressionProgram(entries, receivingPrefix) {
  need(entries instanceof Map && entries.size > 0 && entries.size <= 100000, 'invalid-program-tree');
  const rows = [];
  for (const [name, row] of entries) {
    if (row.type === 'tree' || name === METADATA_PROGRAMS || name.startsWith(receivingPrefix)) continue;
    const selected = ['test/', 'scripts/', 'src/', 'hosted/', '.github/'].some(prefix => name.startsWith(prefix)) ||
      !name.includes('/') || row.mode !== '100644' || EXECUTABLE.test(name) ||
      CODE_IMAGES.some(prefix => name.startsWith(prefix)) || POLICY_ROLES.has(name);
    if (!selected) continue;
    need(row.type === 'blob' && ['100644', '100755'].includes(row.mode) && /^[a-f0-9]{40}$/.test(row.sha), 'nonordinary-program-role');
    rows.push({path: name, mode: row.mode, git_blob: row.sha});
  }
  rows.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  need(rows.length > 0 && METADATA_FRESH_TESTS.every(name => rows.some(row => row.path === name)), 'incomplete-program-roster');
  return {roles: rows.length, vector_sha256: hash(rows)};
}

export function matchMetadataRegressionProgram({source, current, trusted, branch, catalogue}) {
  need(/^engineering\/[A-Za-z0-9_-]+$/.test(branch ?? ''), 'unsupported-receiving-branch');
  const prefix = `coordination/engineering/${branch.slice('engineering/'.length)}/`;
  need(![...trusted.entries.keys()].some(name => name === prefix.slice(0, -1) || name.startsWith(prefix)), 'receiving-packet-already-on-base');
  need(catalogue?.version === 1 && catalogue.kind === 'audited-metadata-regression-programs-v1' &&
    Array.isArray(catalogue.programs) && catalogue.programs.length > 0 && catalogue.programs.length <= 64,
    'unsupported-regression-program-catalogue');
  const before = metadataRegressionProgram(source.entries, prefix), after = metadataRegressionProgram(current.entries, prefix);
  need(before.vector_sha256 === after.vector_sha256 && before.roles === after.roles, 'changed-regression-program');
  const matches = catalogue.programs.filter(row => row.vector_sha256 === before.vector_sha256 && row.roles === before.roles);
  need(matches.length === 1 && typeof matches[0].id === 'string' && /^[a-z0-9-]{1,100}$/.test(matches[0].id), 'unknown-regression-program');
  return {id: matches[0].id, ...before, fresh_tests: [...METADATA_FRESH_TESTS], receiving_prefix: prefix};
}
