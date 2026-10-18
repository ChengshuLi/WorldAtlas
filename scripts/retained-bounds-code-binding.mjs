import {createHash} from 'node:crypto';
const sha = body => createHash('sha256').update(body).digest('hex');
const require = (value, message) => { if (!value) throw Error(message); };
// This reviewed compatibility edge is restricted to JSON.parse-produced geometries.
// It is not an allowlist for native qualification or arbitrary future code.
// Full bodies bind local same/valueSha/isNativeSequence dependencies as well.
const reviewed = Object.freeze({
  retained_helper: '7d3177e9fb2ed8d6eb1ec7723cf09de7a39c61b8892cd5e767a11012157c61d2',
  current_helper: 'f24083355e967cea6310fb002a0387e4a9c627475e6a25dd35f378664464a24f',
  retained_grid: '66b453bbb2e001b9ff56bd754d55087f5919845dceeefd886016494cefa1d3e0',
  current_grid: 'f8691d492770fd8131f5e8341adacbf33b17625c6d735ccb1460cde3213a37cf'
});
export function retainedBoundsCodeCompatibility(bodies) {
  for (const name of Object.keys(reviewed))
    require(typeof bodies?.[name] === 'string' || Buffer.isBuffer(bodies?.[name]), 'Complete bounds code bodies required');
  const hashes = Object.fromEntries(Object.keys(reviewed).map(name => [name, sha(bodies[name])]));
  // Do not infer method equivalence from a manifest, commit label or sample alone.
  // Unknown changes require an independently reviewed dependency proof.
  const identical = hashes.retained_helper === hashes.current_helper && hashes.retained_grid === hashes.current_grid;
  require(identical || Object.entries(reviewed).every(([key, value]) => hashes[key] === value),
    'Unreviewed retained/current bounds code compatibility');
  return {kind:'retained-bounds-json-coordinate-compatibility-v1',input_domain:'JSON.parse dense coordinate arrays',
    basis:identical?'literal whole-code identity':'reviewed dense-array bounds and unchanged numerical scanner dependency',
    hashes, native_qualification_authorized:false};
}
export function requireBoundsExecutionIdentity(config) {
  const hash = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
  require(hash(config?.method_commit) && hash(config?.execution_commit) &&
    config.execution_commit === config.accepted_commit, 'Explicit historical method and accepted execution commits required');
  for (const key of ['current_coordinate_helper','current_native_grid','native_selection','native_manifest','execution_package'])
    require(config.inputs?.[key]?.commit === config.execution_commit, 'Current execution input is not bound to accepted commit: '+key);
  require(config.inputs?.method_package?.commit === config.method_commit, 'Historical package provenance differs');
}

export function requireRetainedProducerIdentity(config, completion, previousConfig, previousDriver) {
  require(sha(previousDriver) === completion.driver_sha256 &&
    config.inputs.previous_config.sha256 === completion.config_sha256 &&
    previousConfig.method_commit === config.method_commit,
    'Reviewed prior producer identity differs');
}
