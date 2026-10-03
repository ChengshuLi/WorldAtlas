import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {expectedNeonProjectId} from './verify-neon-project.mjs';

class ReadError extends Error {
  constructor(code, status = null) { super(code); this.code = code; this.status = status; }
}
const need = (condition, code) => { if (!condition) throw new ReadError(code); };
const id = value => {
  need(typeof value === 'string' && /^[a-z0-9][a-z0-9-]{1,199}$/.test(value), 'invalid-metadata-id');
  return value;
};
const integer = (value, minimum = 0) => {
  if (value == null) return null;
  need(Number.isSafeInteger(value) && value >= minimum, 'invalid-integer-setting'); return value;
};
const compute = value => {
  if (value == null) return null;
  need(typeof value === 'number' && Number.isFinite(value) && value > 0 && value <= 1024, 'invalid-compute-setting'); return value;
};

/** GET-only management metadata. Never requests credentials/connection URIs,
 * creates resources, connects SQL, or persists arbitrary account fields. */
export async function verifyNeonCapacity({apiKey, projectId, fetchImpl = fetch} = {}) {
  need(typeof apiKey === 'string' && apiKey.trim() && !/[\r\n]/.test(apiKey), 'missing-or-invalid-api-key');
  need(projectId === expectedNeonProjectId, 'unexpected-project-id');
  const requests = [], prefix = 'projects/' + projectId;
  async function get(route) {
    need(requests.length < 4, 'bounded-request-limit');
    const log = {route}; requests.push(log);
    let response;
    try {
      response = await fetchImpl(new URL(route, 'https://console.neon.tech/api/v2/'), {
        method: 'GET', headers: {Authorization: 'Bearer ' + apiKey.trim(), Accept: 'application/json'},
        redirect: 'error', signal: AbortSignal.timeout(15000)
      });
    } catch { throw new ReadError('api-request-unavailable'); }
    log.status = response.status;
    if (!response.ok) { await response.body?.cancel(); throw new ReadError('neon-api-http-error', response.status); }
    const chunks = []; let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length; need(size <= 2 * 1024 * 1024, 'bounded-response-limit'); chunks.push(chunk);
    }
    let result;
    try { result = JSON.parse(Buffer.concat(chunks)); } catch { throw new ReadError('invalid-api-json'); }
    need(result && typeof result === 'object' && !Array.isArray(result), 'invalid-api-object'); return result;
  }
  const {project} = await get(prefix);
  need(project?.id === projectId, 'project-response-mismatch');
  const quota = project.settings?.quota ?? {};
  const quotas = Object.fromEntries(['active_time_seconds', 'compute_time_seconds', 'written_data_bytes', 'data_transfer_bytes', 'logical_size_bytes']
    .map(key => [key, integer(quota[key])]));
  const branchResponse = await get(prefix + '/branches?limit=100');
  need(Array.isArray(branchResponse.branches) && branchResponse.branches.length <= 100 &&
    !branchResponse.pagination?.cursor && !branchResponse.next_cursor, 'bounded-branch-inventory-incomplete');
  const production = branchResponse.branches.filter(branch => branch.name === 'production');
  need(production.length === 1, 'production-branch-not-unique');
  const productionBranch = id(production[0].id);
  const {endpoints} = await get(prefix + '/endpoints');
  need(Array.isArray(endpoints) && endpoints.length <= 100, 'invalid-endpoint-inventory');
  const configuredEndpoints = endpoints.filter(endpoint => endpoint.branch_id === productionBranch).map(endpoint => {
    need(endpoint.project_id == null || endpoint.project_id === projectId, 'endpoint-project-mismatch');
    return {id: id(endpoint.id), branch_id: productionBranch,
      autoscaling_limit_min_cu: compute(endpoint.autoscaling_limit_min_cu),
      autoscaling_limit_max_cu: compute(endpoint.autoscaling_limit_max_cu),
      suspend_timeout_seconds: integer(endpoint.suspend_timeout_seconds, -1)};
  });
  need(configuredEndpoints.length > 0, 'production-branch-endpoint-unavailable');
  let accountPlan = {status: 'unavailable', reason: 'project-does-not-expose-organization'};
  if (project.org_id) {
    const organizationId = id(project.org_id);
    try {
      const organization = await get('organizations/' + organizationId);
      need(organization.id === organizationId, 'organization-response-mismatch');
      need(typeof organization.plan === 'string' && /^[a-z0-9_-]{1,80}$/.test(organization.plan), 'organization-plan-unavailable');
      accountPlan = {status: 'verified', organization_id: organizationId, plan: organization.plan};
    } catch (error) {
      accountPlan = {status: 'unavailable', organization_id: organizationId,
        reason: error instanceof ReadError ? error.code : 'metadata-unavailable',
        ...(error instanceof ReadError && error.status != null ? {http_status: error.status} : {})};
    }
  }
  const receipt = {version: 1, status: 'verified', read_only: true, checked_at_utc: new Date().toISOString(),
    project_id: projectId, production_branch_id: productionBranch,
    production_is_default: typeof production[0].default === 'boolean' ? production[0].default : null, account_plan: accountPlan,
    configuration: {history_retention_seconds: integer(project.history_retention_seconds),
      branch_logical_size_limit_mib: integer(project.branch_logical_size_limit), project_quotas: quotas,
      production_branch_endpoints: configuredEndpoints}, requests,
    limitations: [
      'Configured metadata, not measured use, restore rehearsal or a guaranteed future allowance.',
      'ProjectQuota zero/empty means unlimited at this project-quota layer per official API schema; it does not prove billing-plan allowances are unlimited.',
      'branch_logical_size_limit is MiB; logical_size_bytes quota is logical branch bytes, not pg_database_size physical database bytes.',
      'Endpoint compute settings are configuration, not a monthly consumed-compute measurement.',
      'No SQL connection, connection URI, password, account contacts, migration, provisioning or plan change.'
    ]};
  need(!JSON.stringify(receipt).includes(apiKey.trim()), 'unsafe-receipt'); return receipt;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  let receipt;
  try { receipt = await verifyNeonCapacity({apiKey: process.env.NEON_API_KEY, projectId: process.env.NEON_PROJECT_ID}); }
  catch (error) {
    receipt = {version: 1, status: 'failed', read_only: true, checked_at_utc: new Date().toISOString(),
      error_code: error instanceof ReadError ? error.code : 'verification-unavailable', credentials_logged: false};
    process.exitCode = 1;
  }
  const output = process.argv[2] ?? 'data/validation/neon-capacity-verification.json';
  fs.mkdirSync(path.dirname(output), {recursive: true}); fs.writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n', {mode: 0o600});
  console.log(JSON.stringify(receipt));
}
