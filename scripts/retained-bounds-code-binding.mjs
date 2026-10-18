import {createHash} from 'node:crypto';
const sha = body => createHash('sha256').update(body).digest('hex');
const require = (value, message) => { if (!value) throw Error(message); };
// These identify the authentic retained producer, never current whole modules.
export function requireHistoricalBoundsMethod(helper, grid) {
  require(sha(helper) === '7d3177e9fb2ed8d6eb1ec7723cf09de7a39c61b8892cd5e767a11012157c61d2' &&
    sha(grid) === '66b453bbb2e001b9ff56bd754d55087f5919845dceeefd886016494cefa1d3e0',
    'Unreviewed historical bounds producer');
}
export function requireBoundsExecutionIdentity(config) {
  const hash = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
  require(hash(config?.method_commit) && hash(config?.execution_commit) &&
    config.execution_commit === config.accepted_commit, 'Explicit historical method and accepted execution commits required');
  for (const key of ['current_bounds_module','native_selection','native_manifest','execution_package'])
    require(config.inputs?.[key]?.commit === config.execution_commit, 'Current execution input is not bound to accepted commit: '+key);
  require(config.inputs?.method_package?.commit === config.method_commit, 'Historical package provenance differs');
}
export function requireRetainedProducerIdentity(config, completion, previousConfig, previousDriver) {
  require(sha(previousDriver) === completion.driver_sha256 &&
    config.inputs.previous_config.sha256 === completion.config_sha256 &&
    previousConfig.method_commit === config.method_commit,
    'Reviewed prior producer identity differs');
  const identity = rows => rows.map(({commit,path,mode,git_blob_oid,bytes,sha256}) =>
    ({commit,path,mode,git_blob_oid,bytes,sha256})).sort((a,b)=>a.path.localeCompare(b.path));
  require(Array.isArray(previousConfig.code_closure) && Array.isArray(config.retained_code_closure) &&
    JSON.stringify(identity(previousConfig.code_closure)) === JSON.stringify(identity(config.retained_code_closure)),
    'Retained closure differs from authentic producer config');
}
