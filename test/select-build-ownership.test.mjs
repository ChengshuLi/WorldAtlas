import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {selectBuildOwnership} from '../scripts/select-build-ownership.mjs';
const candidate = 'coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json';
const bytes = await fs.readFile(candidate), manifest = JSON.parse(bytes);
const sha256 = createHash('sha256').update(bytes).digest('hex');
const reference = {id: manifest.geographic_release, footprints_sha256: manifest.footprints_sha256, hierarchy_sha256: manifest.hierarchy_sha256};
const scratch = fileURLToPath(new URL('../.cache/build-selection-controls/', import.meta.url));
await fs.mkdir(scratch, {recursive: true});
const root = await fs.mkdtemp(path.join(scratch, 'run-'));
after(() => fs.rm(root, {recursive: true}));

test('explicit reviewed candidate preserves metadata and retrieves immutable original bounds', async () => {
  const selected = await selectBuildOwnership({manifestPath: candidate, expectedSha256: sha256, expectedReference: reference});
  assert.equal(selected.sha256, sha256);
  assert.equal(selected.metadata.method, manifest.method);
  assert.equal(selected.source, path.dirname(candidate));
  assert.equal(createHash('sha256').update(selected.bounds).digest('hex'), manifest.bounds.sha256);
  assert.equal(selected.manifest.installation_ready, false);
});

test('native selection rejects unpinned, altered and wrong-release candidates', async () => {
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedReference: reference}), /reviewed manifest/);
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedSha256: '0'.repeat(64), expectedReference: reference}), /manifest checksum/);
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedSha256: sha256,
    expectedReference: {...reference, id: 'geography:different'}}), /reference release/);
  const changed = {...manifest, original_assets: {...manifest.original_assets, bounds: {...manifest.original_assets.bounds, path: '../wrong'}}};
  const altered = Buffer.from(JSON.stringify(changed)), file = path.join(root, 'bad.json');
  await fs.writeFile(file, altered);
  await assert.rejects(selectBuildOwnership({manifestPath: file,
    expectedSha256: createHash('sha256').update(altered).digest('hex'), expectedReference: reference}), /original bounds/);
});
