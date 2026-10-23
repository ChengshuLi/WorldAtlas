// Read-only adapter for an already acquired immutable packet. The production
// premerge entry point and nested immutable REST wrappers remain unchanged.
// No network, candidate execution, producer or selector write is performed.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {checkPremergeEvidence} from '../../../scripts/premerge-evidence.mjs';
import {memoizeImmutableGitBlobs} from '../../../scripts/immutable-git-blobs.mjs';
import {workSpec} from '../../../scripts/issue-claim-contract.mjs';

const [prFile, issueFile, filesFile] = process.argv.slice(2);
if (!prFile || !issueFile || !filesFile) throw Error('Supply actual PR, issue and complete changed-file JSON snapshots');
const json = name => JSON.parse(fs.readFileSync(name));
const pr = json(prFile), issue = json(issueFile), files = json(filesFile), spec = workSpec(issue.body);
const git = (...args) => execFileSync('git', args, {maxBuffer: 96 * 1024 * 1024,
  env: {...process.env, GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'protocol.allow', GIT_CONFIG_VALUE_0: 'never'}});
const trees = new Map(), sizes = new Map(), requests = new Map();
let transportBytes = 0, manifestBytes = 0;
const api = async (route, method = 'GET', body, options) => {
  if (method !== 'GET' || body !== undefined) throw Error('Read-only probe');
  const match = /^\/repos\/ChengshuLi\/WorldAtlas\/(.+)$/.exec(route);
  if (!match) throw Error('Unexpected repository route');
  const suffix = match[1];
  if (suffix.startsWith('git/commits/')) {
    const commit = suffix.slice('git/commits/'.length), sha = git('rev-parse', commit + '^{tree}').toString().trim();
    if (!trees.has(sha)) {
      const tree = git('ls-tree', '-r', '-l', '-z', commit).toString().split('\0').filter(Boolean).map(line => {
        const row = /^(\d{6}) (blob|commit) ([a-f0-9]{40})\s+(\d+|-)\t(.+)$/.exec(line);
        if (!row) throw Error('Malformed immutable tree entry');
        const entry = {mode: row[1], type: row[2], sha: row[3], size: row[4] === '-' ? undefined : Number(row[4]), path: row[5]};
        if (entry.type === 'blob') sizes.set(entry.sha, entry.size);
        return entry;
      });
      trees.set(sha, {sha, truncated: false, tree});
    }
    return {sha: commit, tree: {sha}};
  }
  if (suffix.startsWith('git/trees/')) return trees.get(suffix.slice('git/trees/'.length).split('?')[0]);
  if (suffix.startsWith('compare/')) {
    const [before, after] = suffix.slice('compare/'.length).split('...');
    git('merge-base', '--is-ancestor', before, after);
    return {status: before === after ? 'identical' : 'ahead'};
  }
  if (suffix.startsWith('git/blobs/')) {
    const sha = suffix.slice('git/blobs/'.length), size = sizes.get(sha);
    if (options?.expectedImmutableBytes !== size || !Number.isSafeInteger(options.maxResponseBytes)) throw Error('Exact size was not forwarded');
    const bytes = execFileSync('git', ['-c', 'protocol.allow=never', 'cat-file', 'blob', sha], {maxBuffer: size + 1});
    transportBytes += bytes.length; requests.set(sha, (requests.get(sha) ?? 0) + 1);
    if (bytes.length < 1024 * 1024 && bytes.includes(Buffer.from('"change_receipts"'))) manifestBytes = bytes.length;
    return {sha, size: bytes.length, encoding: 'base64', content: bytes.toString('base64')};
  }
  throw Error('Unexpected read route: ' + suffix);
};
const start = performance.now();
const result = await checkPremergeEvidence({api: memoizeImmutableGitBlobs(memoizeImmutableGitBlobs(api)), repo: 'ChengshuLi/WorldAtlas',
  pr, issue, files, reservation: {owned_paths: spec.owned_paths}, policy: {version: 1, mode: 'enforce-new', activation_time: '2026-10-03T00:00:00Z', legacy_follow_up: 624}});
const {checked, ...summary} = result;
console.log(JSON.stringify({...summary, files_checked: checked.length, immutable_body_requests: [...requests.values()].reduce((a, b) => a + b, 0),
  unique_blob_oids: requests.size, transport_bytes: transportBytes, manifest_bytes: manifestBytes,
  elapsed_seconds: (performance.now() - start) / 1000, scientific_producers_executed: false, transport: 'local immutable Git adapter; production REST wrappers and premerge entry point'}, null, 2));
