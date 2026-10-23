import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {runPackageBuild} from '../scripts/package-build.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const releaseDirectory = 'data/geographic-releases/';
// Use the actual repository declaration. A filename-only declaration must fail
// this test even if the complete checkout happens to contain its latest target.
const releaseInputs = loadPackageInputs().inputs.filter(name => name.startsWith(releaseDirectory));
const fixturePreflight = async () => ({passed:true, errors:[], synthetic_package_boundary_fixture:true});

async function fixture(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-package-release-'));
  t.after(() => fs.rm(root, {recursive:true, force:true}));
  const save = async (name, body) => {
    await fs.mkdir(path.dirname(path.join(root, name)), {recursive:true});
    await fs.writeFile(path.join(root, name), body);
  };
  const definition = {version:1, inputs:['.github/package-inputs.json', 'scripts/build-static-inner.mjs',
    'scripts/read-geographic-release-manifest.mjs', ...releaseInputs], optional_inputs:[], verification_paths:[], generated_outputs:['dist/']};
  await save('.github/package-inputs.json', JSON.stringify(definition));
  await save('scripts/read-geographic-release-manifest.mjs', await fs.readFile(new URL('../scripts/read-geographic-release-manifest.mjs', import.meta.url)));
  await save('scripts/build-static-inner.mjs', `import fs from 'node:fs';
import {readGeographicReleaseManifest} from './read-geographic-release-manifest.mjs';
const manifest=readGeographicReleaseManifest();
if(fs.existsSync('research/undeclared.json'))throw Error('Research crossed package boundary');
fs.mkdirSync('dist');fs.writeFileSync('dist/release.json',JSON.stringify(manifest));`);
  await save('research/undeclared.json', 'retained outside the package');
  await fs.mkdir(path.join(root, 'node_modules'));
  const base = {version:1, original_catalog_sha256:'original', releases:[{id:'release:1', version:1}],
    batches:[{path:'sources.json', route:'/api/records/import', sha256:sha('original')}],
    new_entities:0, total_memberships:2, changes:0, sources_batches:['sources.json']};
  const original = Buffer.from(JSON.stringify(base));
  await save(releaseDirectory+'index.json', original);
  await save(releaseDirectory+'sources.json', 'original');
  async function advance(version) {
    const next = {...base, releases:[...base.releases, {id:'release:'+version, version}],
      batches:[...base.batches, {path:`sources-${version}.json`, route:'/api/records/import', sha256:sha('new')}],
      sources_batches:[...base.sources_batches, `sources-${version}.json`], total_memberships:4};
    const encoded = gzipSync(Buffer.from(JSON.stringify(next)));
    await save(releaseDirectory+`releases-v${version}.json.gz`, encoded);
    await save(releaseDirectory+`sources-${version}.json`, 'new');
    await save(releaseDirectory+'current-manifest.json', JSON.stringify({path:`releases-v${version}.json.gz`, sha256:sha(encoded), predecessor_index_sha256:sha(original)}));
    return next;
  }
  return {root, advance, save};
}

test('stable release directory enters the actual isolated package for successive manifest pointers', async t => {
  assert.deepEqual(releaseInputs, [releaseDirectory]);
  const f = await fixture(t);
  for (const version of [2, 3]) {
    const expected = await f.advance(version);
    const result = await runPackageBuild('static', {root:f.root, preflight:fixturePreflight});
    assert.deepEqual(JSON.parse(await fs.readFile(path.join(f.root,'dist/release.json'))), expected);
    assert.ok(result.input_paths.includes(releaseDirectory));
  }
});

test('the isolated package still rejects a corrupt current manifest and preserves prior output', async t => {
  const f = await fixture(t), expected = await f.advance(2);
  await runPackageBuild('static', {root:f.root, preflight:fixturePreflight});
  await f.save(releaseDirectory+'releases-v2.json.gz', Buffer.from('corrupt retained bytes'));
  await assert.rejects(runPackageBuild('static', {root:f.root, preflight:fixturePreflight}), /build failed/);
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(f.root,'dist/release.json'))), expected);
});
