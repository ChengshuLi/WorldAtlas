import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

export const TOPOLOGY_ROOT = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/';
const digest = raw => createHash('sha256').update(raw).digest('hex');

// Bind retained numerical validity evidence to every native input. This is not
// source authority, coverage completeness, physical-water approval or a new audit.
export function bindNativeTopology(repo, commit, inputs) {
  if (!/^[a-f0-9]{40}$/.test(commit ?? '')) throw Error('Immutable topology evidence commit required');
  const files = [];
  function read(name) {
    const tree = execFileSync('git', ['-C', repo, 'ls-tree', '-z', commit, '--', name], {encoding: 'utf8'});
    if (!/^100644 blob /.test(tree) || tree.slice(tree.indexOf('\t') + 1) !== name + '\0')
      throw Error('Missing ordinary retained topology evidence');
    const blob = tree.split(' ')[2].split('\t')[0];
    const length = Number(execFileSync('git', ['-C', repo, 'cat-file', '-s', blob], {encoding: 'utf8'}));
    if (!Number.isSafeInteger(length) || length < 1 || length > 32 * 1024 * 1024)
      throw Error('Topology evidence exceeds whole-file budget');
    const raw = execFileSync('git', ['-C', repo, 'cat-file', 'blob', blob], {maxBuffer: 32 * 1024 * 1024});
    if (raw.length !== length) throw Error('Incomplete retained topology evidence');
    files.push({path: name, commit, bytes: raw.length, sha256: digest(raw)});
    return {raw, value: JSON.parse(raw)};
  }
  const topology = read(TOPOLOGY_ROOT + 'native-topology-v1.json');
  const inventory = read(TOPOLOGY_ROOT + 'results-v1/inputs.json');
  const report = topology.value, frozen = inventory.value;
  if (report.version !== 1 || report.method !== 'geos-native-planar-validity-v1' ||
      report.baseline_commit !== inputs.baselineCommit || frozen.baseline_commit !== inputs.baselineCommit ||
      report.evaluation_commit !== frozen.evaluation_commit || report.inputs_sha256 !== digest(inventory.raw) ||
      report.checked_features !== inputs.roster.length || report.valid_nonempty_features !== inputs.roster.length ||
      report.invalid_or_empty_features !== 0 || report.unchecked_features !== 0 ||
      !Array.isArray(report.failures) || report.failures.length)
    throw Error('Retained native topology evidence differs or is incomplete');
  if (!Array.isArray(frozen.source_files) || new Set(frozen.source_files.map(file => file.path)).size !== frozen.source_files.length)
    throw Error('Invalid topology source inventory');
  const sources = new Map(frozen.source_files.map(file => [file.path, file]));
  const identityOnly = [];
  for (const source of inputs.sourceFiles) {
    const previous = sources.get(source.path);
    // The previous numerical audit did not read the province crosswalk. The
    // native loader checks it against the byte-pinned original manifest and
    // every stable owner; retain that distinct validation scope explicitly.
    if (!previous && source.path === 'data/canonical-grid/province-membership.bin.gz' &&
        source.sha256 === inputs.manifest.province_membership.sha256) {
      identityOnly.push(source); continue;
    }
    if (!previous || previous.bytes !== source.bytes || previous.sha256 !== source.sha256)
      throw Error('Native source bytes differ from retained topology audit: ' + source.path);
  }
  if (!Array.isArray(report.partitions) || report.partitions.length !== inputs.partitions.length ||
      new Set(report.partitions.map(part => part.path)).size !== report.partitions.length)
    throw Error('Incomplete topology partitions');
  for (const partition of inputs.partitions) {
    const previous = report.partitions.find(part => part.path === partition.path);
    if (!previous || previous.checked_features !== partition.features ||
        previous.valid_nonempty_features !== partition.features || previous.vertices !== partition.vertices)
      throw Error('Native topology partition accounting differs');
  }
  if (inputs.partitions.reduce((sum, part) => sum + part.features, 0) !== inputs.roster.length ||
      inputs.partitions.reduce((sum, part) => sum + part.vertices, 0) !== inputs.vertices)
    throw Error('Incomplete actual native partition accounting');
  return {files, baseline_commit: report.baseline_commit, audit_evaluation_commit: report.evaluation_commit,
    identity_crosswalk_inputs_not_used_by_topology_audit: identityOnly,
    method: report.method, checked_features: report.checked_features, native_audit_source_bytes_match: true,
    limits: ['Retained numerical planar validity only; not a new audit or source/coverage/water approval.']};
}
