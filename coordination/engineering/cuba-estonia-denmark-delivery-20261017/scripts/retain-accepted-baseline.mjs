import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const [repo, archive, directory] = process.argv.slice(2);
assert.equal(process.argv.length, 5, 'Use REPO ORIGINAL_ACCEPTED_ARCHIVE FRESH_OWNED_DIRECTORY');
const {acquireAcceptedCheckpoint, readAcceptedCheckpoint, retainAcceptedCheckpoint, releaseAcceptedCheckpoint} = await import(pathToFileURL(path.resolve(repo, 'scripts/accepted-selected-checkpoint.mjs')));
const api = async route => {
  assert(route.startsWith('/repos/ChengshuLi/WorldAtlas/'), 'Only this repository read API');
  return JSON.parse(execFileSync('gh', ['api', '--method', 'GET', route], {maxBuffer: 32 * 1024 * 1024}));
};
const result = await acquireAcceptedCheckpoint({api, token: execFileSync('gh', ['auth', 'token'], {encoding: 'utf8'}).trim(), repo: 'ChengshuLi/WorldAtlas', locator: {
  pr_number: 2399, request_id: 'png-argentina-korea-2399-17ef5bc-20261017-001', head: '17ef5bc145ff17554b9cea8e958372b2c3801975'
}, retainedArchive: expectedBytes => {
  const body = fs.readFileSync(archive); assert.equal(body.length, expectedBytes); return body;
}});
assert(result.available, result.reason);
try {
  const proof = readAcceptedCheckpoint(result.handle);
  assert.equal(proof.receipt.merge_commit, '0ae269650196956723d32b0c0e068f384b006b14');
  assert.equal(proof.source.tree, '641fb025e0fce616b4956d32cefd92d1fd0b2585');
  assert.equal(proof.source.artifact_digest, '8f823a3c0ac6a65d132e1cf1d1e341af07aeff0a966053d68fe7e41041c8dbfc');
  const locator = retainAcceptedCheckpoint(result.handle, {repo, directory});
  console.log(JSON.stringify({locator, source: proof.source, archive_origin: proof.archive_origin, products: Object.keys(proof.products)}));
} finally { releaseAcceptedCheckpoint(result.handle); }
