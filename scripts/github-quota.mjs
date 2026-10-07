// Quota failures are distinct from permission errors and ambiguous writes.
export function quotaDelay(error, wallNow = Date.now()) {
  const row = error?.github;
  if (![403, 429].includes(row?.http_status)) return null;
  const seconds = Number(row.retry_after);
  if (/^\d+$/.test(row.retry_after ?? '') && seconds > 0 && seconds <= 3600) return seconds * 1000 + 1000;
  const reset = Number(row.rate_reset);
  if (row.rate_remaining === '0' && /^\d+$/.test(row.rate_reset ?? '') && Number.isSafeInteger(reset))
    return Math.max(1000, reset * 1000 - wallNow + 1000);
  return null;
}
export function requestCategory(route) {
  if (route === '/rate_limit') return 'generic-capacity';
  if (/\/git\/blobs\//.test(route)) return 'immutable-blob';
  if (/\/git\/(?:trees|commits)\//.test(route)) return 'immutable-metadata';
  if (/\/comments(?:\?|$|\/)/.test(route)) return 'comments';
  if (/\/actions\//.test(route)) return 'actions';
  if (/\/(?:check-runs|status)(?:\?|$)/.test(route)) return 'checks';
  if (/\/pulls(?:\?|$|\/)/.test(route)) return 'pulls';
  if (/\/issues(?:\?|$|\/)/.test(route)) return 'issues';
  return 'repository-authority';
}
export function requestAccounting(phase) {
  const counts = {};
  return {observe({route, method, status}) {
    const key = `${method}:${requestCategory(route)}:${status}`;
    counts[key] = (counts[key] ?? 0) + 1;
  }, receipt() {return {phase, actual_http_attempts: Object.values(counts).reduce((a,b)=>a+b,0), counts: {...counts}};}};
}
export function copyAPIFeatures(target, source) {
  for (const name of ['readRepositoryCapacity', 'prefetchGitBlobs'])
    if (typeof source[name] === 'function') target[name] = source[name].bind(source);
  return target;
}
