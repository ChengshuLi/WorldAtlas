import {normativeLatitudeBytes} from './native-latitudes.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {shuffleOwnershipBytes} from '../../src/ownership-codec.js';
import {prepareReferenceMetadataProjection} from '../../scripts/selected-reference-metadata.mjs';
import {valueSha} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const rectangle = x => ({type: 'Polygon', coordinates: [[[x, -1], [x + 1, -1], [x + 1, 1], [x, 1], [x, -1]]]});
const latitudePath = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';

// Three synthetic owners, one native run and one additive cell. Only the existing
// normative latitude bytes are reused; no geographic preparation is performed.
export function mapCellSelectionFixture(t) {
  const repo = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-cell-selection-')));
  t.after(() => fs.rmSync(repo, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {stdio: ['ignore', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const write = (name, value) => {
    const raw = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value));
    fs.mkdirSync(path.dirname(path.join(repo, name)), {recursive: true}); fs.writeFileSync(path.join(repo, name), raw); return raw;
  };
  const commit = () => { git('add', '.'); git('commit', '-m', 'Synthetic diagnostic input'); return git('rev-parse', 'HEAD'); };
  const read = p => {
    const object = p.commit + ':' + p.path;
    return execFileSync('git', ['-C', repo, 'show', object], {maxBuffer: Number(git('cat-file', '-s', object)) + 1});
  };
  const pin = (name, version) => {
    const raw = read({path: name, commit: version}), [mode, , git_blob_oid] = git('ls-tree', version, '--', name).split(/[ \t]/);
    return {commit: version, path: name, mode, git_blob_oid, bytes: raw.length, sha256: sha(raw)};
  };
  const plain = (name, value) => { const raw = write(name, value); return {path: name, bytes: raw.length, sha256: sha(raw)}; };
  const owners = ['A', 'B', 'C'].map((id, i) => ({id, index: i + 1, province_id: i === 2 ? 'Q' : 'P', province_index: i === 2 ? 2 : 1, bounds: [i * 4, -1, i * 4 + 1, 1]}));
  const features = owners.map((o, i) => ({type: 'Feature', id: o.id, properties: {id: o.id, name: 'Source ' + o.id, parent_id: o.province_id, metadata: {reference_year: 2024, source_url: 'https://example.invalid/source'}}, geometry: rectangle(i * 4)}));
  for(const feature of features){feature.properties.reference_owner='Recorded winner';Object.assign(feature.properties.metadata,{reference_polity:'Stale alias',reference_owner_id:'owner:Q1',reference_owner_evidence:{winner:{owner_id:'owner:Q1',name:'Recorded winner',share:.75}},semantic_review:{status:'open'}});}
  const units = [['c', 'continent', null], ['s', 'subcontinent', 'c'], ['r', 'region', 's'], ['a', 'area', 'r'], ['P', 'province', 'a'], ['Q', 'province', 'a']].map(([id, level, parent_id]) => ({id, name: id, level, parent_id}));
  const afterUnits = structuredClone(units); afterUnits.at(-1).name = 'Current Q';
  write('data/world-index.json', {parts: ['geography/fixture.json']}); write('data/administrative-sources.json', {});
  write('data/geography/fixture.json', {type: 'FeatureCollection', features});
  const beforeHierarchy = write('data/hierarchy.json', units);
  const bounds = write('data/canonical-grid/bounds.json.gz', gzipSync(Buffer.from(JSON.stringify(owners))));
  const latitudeBytes = write(latitudePath, normativeLatitudeBytes());
  write('inputs/rule.json', {synthetic: 'diagnostic fixture'}); write('inputs/source-authority.json', {synthetic: true});
  const original = commit(), size = 262166, y = size / 2, x = size / 2;
  const rows = new Uint32Array(size * 2);
  rows[y * 2 + 1] = 1; for (let row = y + 1; row < size; row++) rows[row * 2] = 1;
  const part = (kind, words) => {
    const raw = Buffer.from(words.buffer), encoded = gzipSync(shuffleOwnershipBytes(words));
    const name = `native-v1/ownership/${kind}.bin.gz`; write('data/canonical-grid/fixture/' + name, encoded);
    return {kind, offset: 0, words: words.length, path: name, bytes: encoded.length, sha256: sha(encoded), decoded_bytes: raw.length, decoded_sha256: sha(raw), encoding: 'byte-shuffle'};
  };
  const native = {id: 'geography:fixture-native', footprints_sha256: 'b'.repeat(64), hierarchy_sha256: sha(beforeHierarchy)};
  const manifest = {version: 2, method: 'native-linear-evenodd-first-owner-v1', size, coordinateBits: 19, runWords: 2,
    parts: [part('rows', rows), part('runs', Uint32Array.from([2 ** 19 + x, x]))], geographic_release: native.id,
    footprints_sha256: native.footprints_sha256, hierarchy_sha256: native.hierarchy_sha256,
    bounds: {sha256: sha(bounds), decoded_bytes: Buffer.byteLength(JSON.stringify(owners))},
    original_assets: {bounds: {role: 'original-identity-parent-camera-context', commit: original, path: 'data/canonical-grid/bounds.json.gz', sha256: sha(bounds)}},
    native_latitudes: {...pin(latitudePath, original), root: 'repository', role: 'immutable-normative-rule-input', decoded_bytes: size * 8, decoded_sha256: sha(gunzipSync(latitudeBytes))}};
  const manifestPath = 'data/canonical-grid/fixture/manifest.json', manifestPin = plain(manifestPath, manifest);
  const products = [{path: 'manifest.json', bytes: manifestPin.bytes, sha256: manifestPin.sha256}, ...manifest.parts];
  // A synthetic receipt shape for the reader contract, not evidence of a scientific run.
  const receipt = {method: manifest.method, checked_rows: size, checked_cells: size ** 2, unchecked_cells: 0, checked_runs: 1, installation_ready: false, products, two_run_products: products.length, run_one_sha256: sha(Buffer.from(JSON.stringify(products))), run_two_sha256: sha(Buffer.from(JSON.stringify(products)))};
  const proof = plain('inputs/synthetic-native-receipt.json', receipt), proofCommit = commit();
  write('scripts/native-ownership/verified-candidates.json', {version: 1, candidates: {[manifestPin.sha256]: {...proof, commit: proofCommit, role: 'reviewed-exhaustive-native-rule-comparison', installation_approval: false}}});
  const bank = {version: 1, kind: 'complete-world-index-with-exact-encoded-overrides', release_id: native.id, native_manifest_sha256: manifestPin.sha256, footprints_sha256: native.footprints_sha256, locations: owners.length, world_index: pin('data/world-index.json', original), unchanged_files: [pin('data/geography/fixture.json', original)], overrides: []};
  const selection = {version: 1, method: manifest.method, manifest_path: manifestPath, sha256: manifestPin.sha256, release_id: native.id,
    selected_geography: {version: 1, kind: bank.kind, ...plain('inputs/bank.json', bank)}};
  const entry = {rule_sha256: pin('inputs/rule.json', original).sha256, policy_id: 'synthetic', policy_version: 1, rule_preimage: pin('inputs/rule.json', original), source_authority: pin('inputs/source-authority.json', original)};
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [{...entry, authority_sha256: valueSha(entry)}]};
  const addition = rectangle(1), ledger = {version: 1, kind: 'native-additive-repair-ledger-v1', rule_sha256: entry.rule_sha256, scope_ids: ['gap'], rows: [{component_id: 'gap', disposition: 'assigned', target_id: 'A', pixelIndex: 1, base_geometry_sha256: valueSha(features[0].geometry), geometry: addition, geometry_sha256: valueSha(addition), source_receipt_sha256: 'c'.repeat(64), native_cells: 1}]};
  const sidecar = {base_selection: structuredClone(selection), authority_registry: plain('inputs/registry.json', registry), logical_asset_map: {ledger: plain('inputs/ledger.json', ledger), patch: plain('inputs/patch.json', {rows: [{y, runs: [[x + 1000, x + 1001, 1]]}]})}};
  selection.additive_release = plain('inputs/sidecar.json', sidecar);
  const setRelease = releases => { const p = plain('data/geographic-releases/releases.json.gz', gzipSync(Buffer.from(JSON.stringify({releases})))); write('data/geographic-releases/current-manifest.json', {path: 'releases.json.gz', sha256: p.sha256}); };
  setRelease([native]); write('data/ownership-selection.json', selection); const base = commit();
  const currentFeatures = structuredClone(features), after = currentFeatures[0].properties; after.parent_id = 'Q';
  after.metadata.reference_corrections = [{id: 'A', action: 'reparent', current_name: 'Source A', current_parent_id: 'P', new_parent_id: 'Q', rationale: 'Synthetic parent correction', evidence: [{url: 'https://example.invalid/reference', title: 'Fixture', inspected_fact: 'A belongs to Q'}]}];
  const changes = [{location_id: 'A', before_properties: features[0].properties, after_properties: after}];
  const afterHierarchy = write('data/hierarchy.json', afterUnits), reference = {...native, id: 'geography:fixture-current', hierarchy_sha256: sha(afterHierarchy)};
  write('data/geography/fixture.json', {type: 'FeatureCollection', features: currentFeatures});
  const correction = plain('inputs/correction.json', {before_sha256: native.hierarchy_sha256, after_sha256: reference.hierarchy_sha256, footprints_sha256_before: native.footprints_sha256, footprints_sha256_after: native.footprints_sha256, reference_only: true, historical_claims_transferred: false, summary: {geometry_changes: 0}, relationships: [], before_units: units, retired_units: [], group_changes: [{id: 'Q', before: units.at(-1), after: afterUnits.at(-1)}], changed_location_properties: changes, source_evidence: [{url: 'https://example.invalid/reference', source_sha256: 'c'.repeat(64)}]});
  setRelease([native, {...reference, metadata: {metadata_migration_sha256: {correction: correction.sha256}}}]); const inputs = commit();
  const projection = prepareReferenceMetadataProjection({selection, manifest, owners, reference, hierarchy: {before: pin('data/hierarchy.json', original), after: pin('data/hierarchy.json', inputs)}, receipts: [pin('inputs/correction.json', inputs)], source_updates: [{logical_path: 'data/geography/fixture.json', before: pin('data/geography/fixture.json', original), after: pin('data/geography/fixture.json', inputs)}], read});
  const project = () => { selection.reference_projection = plain('inputs/projection.json', projection); write('data/ownership-selection.json', selection); return commit(); };
  const current = project();
  return {repo, git, write, commit, pin, plain, selection, sidecar, projection, owners, features, currentFeatures, original, base, current, project, cells: [{x, y}, {x: x + 1000, y}]};
}

// The same three-owner source/projection fixture, now with a complete current E
// emitted by the ordinary encoder. The cells are synthetic, not qualified edits.
export async function finalMapCellSelectionFixture(t) {
  const f = mapCellSelectionFixture(t), root = 'data/canonical-grid/current-startup';
  const {prepareFinalBankStartupOwnership} = await import('../../scripts/prepare-startup-ownership.mjs');
  const {ownershipMetadata} = await import('../../src/ownership-method.js');
  const {scientificNativeSelection} = await import('../../src/reference-metadata.js');
  const nativeSelection = scientificNativeSelection(f.selection), manifest = JSON.parse(f.git('show', f.current + ':' + nativeSelection.manifest_path));
  const native = {...ownershipMetadata(manifest), canonical_grid_sha256: nativeSelection.sha256,
    native_latitudes: {...manifest.native_latitudes, transport_path: 'native-v1/native-row-latitudes.f64le.gz'},
    parts: manifest.parts.map(p => ({...p, path: p.kind === 'runs' ? 'ownership-vintages/' + nativeSelection.sha256 + '/native-v1/ownership/startup-runs-0.bin.gz' : p.path}))};
  const bodies = new Map(manifest.parts.map((pin, i) => [native.parts[i].path,
    fs.readFileSync(path.join(f.repo, path.posix.dirname(nativeSelection.manifest_path), pin.path))]));
  bodies.set(native.native_latitudes.transport_path, normativeLatitudeBytes());
  const compatibility = [...bodies].map(([name, bytes]) => ({path: name, bytes: bytes.length, sha256: sha(bytes)}));
  const ownerHash = sha(Buffer.from(JSON.stringify(f.owners.map(o => [o.index, o.id]))));
  const previous = {version: 2, native_manifest_sha256: nativeSelection.sha256, files: compatibility, compatibility_files: compatibility,
    preparedOwnership: {native_pixel_map: native, owners: f.owners.length, reference_owner_sha256: ownerHash}, pixelMap: {parts: []}};
  const referenceMetadata = {version: 1, asset: {...f.selection.reference_projection, path: 'reference-metadata/current.json'},
    native_reference: f.projection.native_reference, reference: f.projection.reference};
  const emit = async (owner = 1, {wordOwner = owner} = {}) => {
    fs.rmSync(path.join(f.repo, root), {recursive: true, force: true});
    for (const [name, raw] of bodies) f.write(root + '/' + name, raw);
    const [{x, y}, gap] = f.cells, rows = new Uint32Array(manifest.size * 2);
    const runs = Uint32Array.from([2 ** 19 + x, x, ...(wordOwner ? [wordOwner * 2 ** 19 + gap.x, gap.x] : [])]);
    rows[y * 2 + 1] = runs.length / 2; for (let row = y + 1; row < manifest.size; row++) rows[row * 2] = runs.length / 2;
    const features = f.currentFeatures.map((feature, i) => ({id: feature.id, pixelIndex: i + 1, properties: structuredClone(feature.properties),
      geometry: owner === i + 1 ? feature.geometry : null, gridBounds: f.owners[i].bounds,
      ...(owner === i + 1 ? {finishedFootprint: {version: 1, kind: 'complete-native-footprint-v1', reference_geometry_sha256: valueSha(feature.geometry),
        geometry: {type: 'MultiPolygon', coordinates: [feature.geometry.coordinates]}, native_rows: [{y, runs: [[gap.x, gap.x + 1]]}], native_bounds: [-180, -90, 180, 90]}} : {})}));
    const ownership = {...native, rows, runs, runWords: runs.length, reference_owner_sha256: ownerHash};
    const index = await prepareFinalBankStartupOwnership({manifest, manifestSha: nativeSelection.sha256, previous, ownership, features,
      baseReference: f.projection.reference, referenceMetadata, destination: path.join(f.repo, root)});
    index.files = fs.readdirSync(path.join(f.repo, root), {recursive: true}).filter(n => fs.statSync(path.join(f.repo, root, n)).isFile()).sort().map(name => {
      const bytes = fs.readFileSync(path.join(f.repo, root, name)); return {path: name, bytes: bytes.length, sha256: sha(bytes)};
    });
    const selection = {version: 2, kind: 'selected-final-native-bank-v2', native_selection: nativeSelection,
      prepared_bank: f.plain(root + '/index.json', index), reference: index.preparedOwnership.effective_reference,
      reference_projection: f.selection.reference_projection,
      // An old qualification hook must never become a current map operand.
      change_evidence: {commit: f.current, path: 'inputs/absent-old-registry.json', mode: '100644', git_blob_oid: 'a'.repeat(40), bytes: 1, sha256: 'b'.repeat(64)}};
    f.write('data/ownership-selection.json', selection);
    for (const name of ['inputs/sidecar.json', 'inputs/ledger.json', 'inputs/registry.json', 'inputs/patch.json']) fs.rmSync(path.join(f.repo, name), {force: true});
    return {commit: f.commit(), index, selection};
  };
  return {...f, emit};
}
