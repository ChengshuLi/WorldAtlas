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
  pr_number: 2377, request_id: 'eight-country-delivery-2377-0db52cf-20261017-002', head: '0db52cf5a1b7c06a1b27989ec044face48c65286'
}, retainedArchive: expectedBytes => {
  const body = fs.readFileSync(archive); assert.equal(body.length, expectedBytes); return body;
}});
assert(result.available, result.reason);
try {
  const proof = readAcceptedCheckpoint(result.handle);
  assert.equal(proof.receipt.merge_commit, '821d5eacfec816f9eb21eeec8a9ebb990f4e16f4');
  assert.equal(proof.source.tree, '44fe9c69e3807c1030186f4455cc96707b9e3eb0');
  assert.equal(proof.source.artifact_digest, 'bdd8cc3955dbfc805995a7a77b498441effb8e89fd0714efeeecbb46add32315');
  const locator = retainAcceptedCheckpoint(result.handle, {repo, directory});
  console.log(JSON.stringify({locator, source: proof.source, archive_origin: proof.archive_origin, products: Object.keys(proof.products)}));
} finally { releaseAcceptedCheckpoint(result.handle); }
