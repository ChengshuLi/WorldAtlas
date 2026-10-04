import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {packageStartupOwnership} from '../scripts/package-startup-ownership.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
async function fixture(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-startup-ownership-'));
  t.after(() => fs.rm(directory, {recursive:true, force:true}));
  const source = path.join(directory, 'source'), destination = path.join(directory, 'candidate');
  await fs.mkdir(path.join(source, 'ownership'), {recursive:true});
  const rows = Uint32Array.of(0,2,2,2), runs = Uint32Array.of(0,2,7,0,0,2,8,0);
  const manifest = {version:2, coordinateBits:1, size:2, runWords:8, parts:[]};
  const bytesByPath = new Map();
  for (const [kind, words] of [['rows', rows], ['runs', runs]]) {
    const relative = `ownership/${kind}-0.bin.gz`, bytes = gzipSync(shuffleOwnershipBytes(words));
    await fs.writeFile(path.join(source, relative), bytes);
    bytesByPath.set(relative, bytes);
    manifest.parts.push({kind, path:relative, offset:0, words:words.length, encoding:'byte-shuffle',
      sha256:digest(bytes), decoded_sha256:digest(Buffer.from(words.buffer))});
  }
  return {source, destination, manifest, rows, runs, bytesByPath};
}

test('startup ownership packaging preserves original GPU words and source files', async t => {
  const f = await fixture(t);
  const receipt = await packageStartupOwnership(f);
  const reconstructed = await loadOwnershipAssets(receipt.pixelMap, async url => {
    const relative = url.slice(2);
    return new Response(await fs.readFile(path.join(relative.includes('startup-runs-') ? f.destination : f.source, relative)));
  });
  assert.deepEqual(reconstructed.rows, f.rows);
  assert.deepEqual(reconstructed.runs, f.runs);
  assert.equal(receipt.runs_word_stream_sha256, digest(Buffer.from(f.runs.buffer)));
  for (const [relative, original] of f.bytesByPath) assert.deepEqual(await fs.readFile(path.join(f.source,relative)), original);
  const second = await packageStartupOwnership({...f, destination:f.destination+'-second'});
  assert.deepEqual(second.outputs, receipt.outputs);
  await assert.rejects(packageStartupOwnership(f), /EEXIST/);
});

test('startup ownership rejects altered, unpinned or unsafe canonical sources', async t => {
  const f = await fixture(t);
  await fs.writeFile(path.join(f.source, f.manifest.parts[1].path), Buffer.from('altered source'));
  await assert.rejects(packageStartupOwnership(f), /input changed/);
  for (const patch of [{path:'../runs-0.bin.gz'}, {decoded_sha256:null}, {sha256:'bad'}]) {
    const manifest = {...f.manifest, parts:f.manifest.parts.map((part,i) => i === 1 ? {...part,...patch} : part)};
    await assert.rejects(packageStartupOwnership({...f,manifest}), /Invalid canonical/);
  }
  await assert.rejects(packageStartupOwnership({...f,manifest:{...f.manifest,version:1}}), /Invalid canonical/);
});
