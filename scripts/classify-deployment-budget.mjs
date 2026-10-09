import fs from 'node:fs';
import {quotaDelay,requestAccounting} from './github-quota.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadPackageInputs, readPackageInputs, packagePathRequired, safePackagePath, validatePackageInputs} from './package-inputs.mjs';

export function classifyBudgetFiles(files, definition = loadPackageInputs()) {
  validatePackageInputs(definition);
  const independent = file => {
    if (!safePackagePath(file) || file.endsWith('/')) throw Error('Invalid changed-file path');
    return !packagePathRequired(file, definition);
  };
  if (!Array.isArray(files)) throw Error('Missing changed-file inventory');
  const paths = new Set();
  for (const file of files) {
    if (!file || !['added', 'modified', 'removed', 'renamed', 'copied', 'changed', 'unchanged'].includes(file.status) ||
        typeof file.filename !== 'string' || paths.has(file.filename)) throw Error('Invalid changed-file inventory');
    paths.add(file.filename);
    if (['renamed', 'copied'].includes(file.status) && typeof file.previous_filename !== 'string') throw Error('Missing rename source');
    if (file.previous_filename !== undefined) {
      if (typeof file.previous_filename !== 'string') throw Error('Invalid rename source');
      // Include rename/copy origins even when the destination is a receipt.
      if (!independent(file.previous_filename)) return {full: true, reason: 'Package-relevant original path', paths: [...paths, file.previous_filename]};
    }
    if (!independent(file.filename)) return {full: true, reason: 'Declared package input or verification path', paths: [...paths]};
  }
  return {full: false, reason: 'No declared package input or verification path changed', paths: [...paths]};
}

const commit = value => /^[a-f0-9]{40}$/.test(value ?? '') && !/^0+$/.test(value);

export async function deploymentBudgetProfile({event, eventName, repository, api}) {
  try {
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository ?? '') ||
        event?.repository?.full_name !== repository) throw Error('Unknown repository');
    const route = `/repos/${repository}`;
    let files, base;
    if (eventName === 'pull_request') {
      const pr = event.pull_request;
      if (!Number.isSafeInteger(pr?.number) || pr.number < 1 || !commit(pr.base?.sha) || !commit(pr.head?.sha)) throw Error('Incomplete PR identity');
      base = pr.base.sha;
      const actual = await api(`${route}/pulls/${pr.number}`);
      if (actual.base?.sha !== pr.base.sha || actual.head?.sha !== pr.head.sha ||
          !Number.isSafeInteger(actual.changed_files) || actual.changed_files < 0) throw Error('PR changed or inventory size unavailable');
      if (actual.changed_files >= 3000) throw Error('PR file API inventory capped');
      files = [];
      for (let page = 1; page <= 100; page++) {
        const rows = await api(`${route}/pulls/${pr.number}/files?per_page=100&page=${page}`);
        if (!Array.isArray(rows) || rows.length > 100) throw Error('Invalid PR file page');
        files.push(...rows);
        if (rows.length < 100) break;
        if (page === 100) throw Error('PR inventory capped');
      }
      if (files.length !== actual.changed_files) throw Error('Incomplete PR inventory');
      const settled = await api(`${route}/pulls/${pr.number}`);
      if (settled.head?.sha !== pr.head.sha || settled.base?.sha !== pr.base.sha ||
          settled.changed_files !== files.length) throw Error('PR changed during file enumeration');
    } else if (eventName === 'push') {
      if (!commit(event.before) || !commit(event.after)) throw Error('Missing push comparison');
      base = event.before;
      const comparison = await api(`${route}/compare/${event.before}...${event.after}`);
      if (comparison.base_commit?.sha !== event.before || !['ahead', 'identical'].includes(comparison.status) ||
          !Array.isArray(comparison.files) || comparison.files.length >= 300 ||
          comparison.truncated === true) throw Error('Push comparison unavailable or capped');
      if (event.after !== event.before && comparison.commits?.at(-1)?.sha !== event.after) throw Error('Push head unavailable in comparison');
      files = comparison.files;
    } else throw Error('Unsupported event');
    const definition = await readPackageInputs({route, base, api});
    return {version: 2, event: eventName, ...classifyBudgetFiles(files, definition)};
  } catch (error) {
    const delay=quotaDelay(error);
    return {version: 2, event: eventName, full: true,
      ...(delay!==null?{blocked:true,api_error:error.github,retry_at:new Date(Date.now()+delay).toISOString()}:{}),
      reason: error instanceof Error ? error.message : 'Inventory lookup failed', paths: [], fallback: true};
  }
}

export async function githubBudgetAPI(route, {token = process.env.GH_TOKEN, fetchImpl = fetch, onRequest=()=>{}} = {}) {
  if (!token) throw Error('Read-only GitHub token unavailable');
  let response;try{response = await fetchImpl(`https://api.github.com${route}`, {
    headers: {Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
    signal: AbortSignal.timeout(15000),
  });}catch(error){onRequest({route,method:'GET',status:'transport-error'});throw error;}
  const numeric=name=>{const value=response.headers?.get(name);return /^\d{1,13}$/.test(value??'')?value:undefined;};
  onRequest({route,method:'GET',status:response.status,capacity:{resource:response.headers?.get('x-ratelimit-resource'),
    limit:Number(numeric('x-ratelimit-limit')),remaining:Number(numeric('x-ratelimit-remaining')),reset:Number(numeric('x-ratelimit-reset'))}});
  if (!response.ok) {
    const error=Error(`GitHub inventory HTTP ${response.status}`);
    const requestId=response.headers?.get('x-github-request-id');
    error.github={http_status:response.status,...(/^[a-fA-F0-9:]{1,100}$/.test(requestId??'')?{request_id:requestId}:{}),...Object.fromEntries([
      ['rate_remaining',numeric('x-ratelimit-remaining')],['rate_reset',numeric('x-ratelimit-reset')],
      ['retry_after',numeric('retry-after')]].filter(([,value])=>value!==undefined))};
    throw error;
  }
  return response.json();
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let result;const accounting=requestAccounting('deployment-classifier');
  try {
    result = await deploymentBudgetProfile({event: JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8')),
      eventName: process.env.GITHUB_EVENT_NAME, repository: process.env.GITHUB_REPOSITORY, api: route=>githubBudgetAPI(route,{onRequest:accounting.observe})});
  } catch { result = {version: 2, full: true, reason: 'Classifier inputs unavailable', paths: [], fallback: true}; }
  fs.mkdirSync('.cache', {recursive: true});
  fs.writeFileSync('.cache/deployment-budget-scope.json', JSON.stringify(result, null, 2) + '\n');
  fs.appendFileSync(process.env.GITHUB_OUTPUT, `full=${result.full}\nblocked=${Boolean(result.blocked)}\n`);
  console.log(JSON.stringify({...result,request_accounting:accounting.receipt()}));
  // A structured blocked decision makes the package job fail before setup.
  // Unknown non-quota inventories keep the conservative full-build fallback.
}
