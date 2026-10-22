// Actual emitted selected-delivery check. Expectations are caller-reviewed
// rosters, not a new source-authority or scientific approval mechanism.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {repairComponentKey} from '../src/native-grid.js';
import {repositoryReader, sha256} from './evidence-quality.mjs';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {additiveBaseReference, decodedAdditiveAssetIdentity, loadAdditiveNativePatch, effectivePrimitiveGeometries, footprintValueSha256,
  verifyAdditiveLedgerSelection, nativeOnlyComponent, loadPreparedNativeContext, nativeReferenceForData} from '../src/effective-footprint.js';
import {scientificNativeSelection,originalNativeReference,validateReferenceMetadataHeader} from '../src/reference-metadata.js';
import {readPreparedFinalOwnership} from './package-startup-ownership.mjs';
import {ownershipRun, pickOwnership, samplePackedOwnership} from '../src/pixel-ownership.js';

const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
function exactKeys(value, keys, label) {
  assert(value && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
  assert.deepEqual(Object.keys(value).sort(), [...keys].sort(), `${label} has missing/foreign fields`);
}
function uniqueStrings(values, label) {
  assert(Array.isArray(values) && values.length > 0 && values.every(text), `${label} must be nonempty`);
  assert.equal(new Set(values).size, values.length, `Duplicate ${label}`);
}

export function validateDeliveryExpectations(value) {
  if(value?.version===2){exactKeys(value,['version','kind','bank','reference'],'Final bank expectations');assert.equal(value.kind,'selected-final-bank-consumer-v2');assert(value.bank&&hash(value.bank.sha256)&&Number.isSafeInteger(value.bank.bytes)&&value.bank.bytes>0);return value;}
  exactKeys(value, ['version', 'selected_ledger_sha256', 'cumulative_native_cells', 'cohorts'], 'Expectations');
  assert.equal(value.version, 1, 'Unsupported expectations version');
  assert(hash(value.selected_ledger_sha256), 'Missing selected ledger hash');
  assert(Number.isSafeInteger(value.cumulative_native_cells) && value.cumulative_native_cells >= 0,
    'Invalid expected cumulative native cells');
  assert(Array.isArray(value.cohorts) && value.cohorts.length > 0, 'Missing expected cohorts');
  const batches = new Set(), components = new Set();
  for (const cohort of value.cohorts) {
    exactKeys(cohort, ['original_batch_id', 'component_ids', 'members'], 'Expected cohort');
    assert(text(cohort.original_batch_id) && !batches.has(cohort.original_batch_id), 'Missing/duplicate original batch ID');
    batches.add(cohort.original_batch_id);
    uniqueStrings(cohort.component_ids, 'expected component roster');
    assert(Array.isArray(cohort.members), 'Missing expected members');
    for (const member of cohort.members) {
      const representationHash = Object.hasOwn(member,'native_rows_sha256') ? 'native_rows_sha256' : 'geometry_sha256';
      exactKeys(member, ['component_id', 'target_id', 'disposition', representationHash], 'Expected member');
      assert(text(member.component_id) && !components.has(JSON.stringify([cohort.original_batch_id, member.component_id])), 'Missing/duplicate expected member');
      components.add(JSON.stringify([cohort.original_batch_id, member.component_id]));
      assert(text(member.target_id) && ['assigned', 'zero-cell'].includes(member.disposition)
        && hash(member[representationHash]), 'Invalid expected target/disposition/geometry');
    }
    assert.deepEqual(cohort.members.map(member => member.component_id).sort(), [...cohort.component_ids].sort(),
      'Expected members must cover the complete component roster exactly');
  }
  return value;
}

// Select current before-state controls from the authenticated emitted base.
// Every affected occupied row contributes one existing owner; an all-empty
// affected span falls back to the first occupied base row, never a vacuous pass.
export function selectedStableOwnerControls(base, patch) {
  const controls = [];
  const add = y => {
    if (!base.rows[y * 2 + 1]) return;
    const run = ownershipRun(base, base.rows[y * 2]);
    assert(Number.isInteger(run.start) && Number.isInteger(run.end) && Number.isInteger(run.id)
      && run.start >= 0 && run.end > run.start && run.end <= base.size && run.id > 0,
      'Invalid occupied base control');
    controls.push({x: run.start, y, id: run.id});
  };
  for (const y of new Set(patch.rows.map(row => row.y))) add(y);
  if (!controls.length) for (let y = 0; y < base.size && !controls.length; y++) add(y);
  assert(controls.length > 0, 'Missing occupied base owner control');
  return controls;
}

// Shared actual cell consumer. Generic application regression has no reviewed
// cohort expectations; selected-map admission adds those separately below.
function verifyEmittedDelivery({ledger, ledgerSha256, patch, patchSha256,
  features, base, effective, beforeControls}) {
  assert.equal(patch.ledger_sha256, ledgerSha256, 'Patch ledger differs');
  verifyAdditiveLedgerSelection(ledger, features, patch);
  let added = 0;
  for (const row of patch.rows) for (const [start, end, id] of row.runs) for (let x = start; x < end; x++) {
    assert.equal(pickOwnership(base, x, row.y), 0, 'Patch cell was already occupied');
    assert.equal(pickOwnership(effective, x, row.y), id, 'Patched picker owner differs');
    assert.equal(samplePackedOwnership(effective, {x, y: row.y, width: 1, height: 1})[0], id,
      'Patched sampler owner differs');
    added++;
  }
  assert.equal(added, effective.additive_added_cells, 'Loaded effective native cell count differs');
  assert(Array.isArray(beforeControls) && beforeControls.length > 0, 'Missing occupied base owner control');
  for (const {x, y, id} of beforeControls) {
    assert(Number.isInteger(x) && Number.isInteger(y) && Number.isInteger(id)
      && x >= 0 && x < base.size && y >= 0 && y < base.size && id > 0, 'Invalid occupied base control');
    assert.equal(pickOwnership(base, x, y), id, 'Stable base owner changed');
    assert.equal(pickOwnership(effective, x, y), id, 'Stable effective owner changed');
    assert.equal(samplePackedOwnership(effective, {x, y, width: 1, height: 1})[0], id,
      'Stable sampled owner changed');
  }
  return {version: 1, kind: 'actual-emitted-additive-consumer', passed: true,
    feature_count: features.length, selected_ledger_sha256: ledgerSha256, selected_patch_sha256: patchSha256,
    cumulative_native_cells_picked_and_sampled: added, stable_owner_controls: beforeControls.length,
    limitation: 'Production asset loader, picker and renderer sampler on every emitted additive cell, plus occupied base controls. GPU and Canvas execution still require hosted browser testing. No reviewed cohort or source approval is inferred.'};
}

// Exported kernel uses the actual production effective primitive, picker and
// sampler entry points. The CLI obtains all arguments from authenticated bytes.
export function verifySelectedDelivery({expectations, ledger, ledgerSha256, patch, patchSha256,
  features, base, effective, beforeControls}) {
  validateDeliveryExpectations(expectations);
  assert.equal(ledgerSha256, expectations.selected_ledger_sha256, 'Wrong selected ledger hash');
  const selected = new Map(), loaded = new Map(), covered = new Set();
  for (const row of ledger.rows) {
    assert(!selected.has(repairComponentKey(row)), 'Duplicate selected component');
    selected.set(repairComponentKey(row), row);
  }
  for (const feature of features) {
    assert(text(feature.id) && !loaded.has(feature.id), 'Duplicate/missing loaded target');
    loaded.set(feature.id, feature);
  }
  const cohorts = expectations.cohorts.map(cohort => ({
    original_batch_id: cohort.original_batch_id,
    members: cohort.members.map(member => {
      const authority = /^retained-authority-scope:([a-f0-9]{64})$/.exec(cohort.original_batch_id)?.[1];
      const found = [...selected.values()].filter(row => row.component_id === member.component_id
        && (!authority || row.authority_sha256 === authority));
      assert.equal(found.length, 1, 'Missing or ambiguous selected member authority');
      const row = found[0], key = repairComponentKey(row);
      assert(!covered.has(key), 'Duplicate selected member coverage'); covered.add(key);
      assert(row, `Missing selected member: ${member.component_id}`);
      const nativeOnly = nativeOnlyComponent(row);
      for (const field of ['target_id', 'disposition', ...(nativeOnly ? [] : ['geometry_sha256'])])
        assert.equal(row[field], member[field], `Selected member ${field} differs: ${member.component_id}`);
      const target = loaded.get(member.target_id);
      assert(target && target.pixelIndex === row.pixelIndex, `Missing/wrong loaded target: ${member.target_id}`);
      const components = target.additiveFootprint?.components;
      assert(Array.isArray(components), 'Expected selected V2 target components');
      const matches = components.filter(component => repairComponentKey(component) === key);
      assert.equal(matches.length, 1, 'Expected exactly one loaded component');
      assert.deepEqual(matches[0], row, 'Loaded component differs from selected row');
      if (nativeOnly) {
        assert.equal(footprintValueSha256(row.native_rows),member.native_rows_sha256,'Actual selected native intervals differ');
        return {...member,native_intervals_verified:true};
      }
      assert.equal(footprintValueSha256(row.geometry), member.geometry_sha256, 'Actual selected geometry differs');
      assert(effectivePrimitiveGeometries(target).some(geometry =>
        footprintValueSha256(geometry) === member.geometry_sha256), 'Actual geometry absent from effective primitives');
      return {...member, effective_primitive_verified: true};
    })
  }));
  const report = verifyEmittedDelivery({ledger, ledgerSha256, patch, patchSha256,
    features, base, effective, beforeControls});
  assert.equal(report.cumulative_native_cells_picked_and_sampled, expectations.cumulative_native_cells, 'Wrong cumulative native cell count');
  return {...report, kind: 'actual-emitted-selected-consumer',
    expected_components_verified: cohorts.reduce((n, cohort) => n + cohort.members.length, 0), cohorts,
    limitation: 'Production Node-compatible asset loader, effective primitive, picker and renderer-sampler entry points on actual emitted assets. GPU and Canvas execution still require hosted browser testing. Original batch IDs and complete rosters are supplied reviewed expectations, not independent source or whole-batch approval. Zero-cell inclusion is not visible-pixel gain. Emitted geometry chunks are not decoded here; catalog identities and selected ledger primitives are checked. Stable-owner controls sample one occupied emitted-base cell per affected nonempty row, or the first occupied base row when all affected rows are empty.'};
}

function admitOutput(filename) {
  assert(text(filename) && !filename.includes('\0'), 'Missing output path');
  const output = path.resolve(filename), parent = path.dirname(output);
  assert.equal(fs.realpathSync(parent), parent, 'Output symlink parent refused');
  assert(fs.lstatSync(parent).isDirectory(), 'Output parent must be an existing directory');
  assert(!fs.lstatSync(output, {throwIfNoEntry: false}), 'Output collision');
  return output;
}

export async function checkEmittedSelectedDelivery({root = process.cwd(), emittedDirectory = path.join(root, 'dist/client'),
  expectations} = {}) {
  const inputs = new Map();
  const readRoot = repositoryReader(root), readEmitted = repositoryReader(emittedDirectory);
  const read = (scope, name, pin, {nativePart = false} = {}) => {
    // Authenticate the declaration before passing its exact size to the reader.
    // Dropping it here silently reinstates the legacy unpinned-file ceiling.
    const omittedNativeBytes = pin && nativePart && !Object.hasOwn(pin, 'bytes')
      && hash(pin.decoded_sha256) && Number.isSafeInteger(pin.words) && pin.words > 0;
    if (pin) assert(hash(pin.sha256)
      && ((Number.isSafeInteger(pin.bytes) && pin.bytes >= 0) || omittedNativeBytes),
    'Missing whole-file asset pin');
    const bytes = (scope === 'root' ? readRoot : readEmitted)(name, 'candidate',
      pin && !omittedNativeBytes ? pin : undefined);
    const descriptor = {scope, path: name, bytes: bytes.length, sha256: sha256(bytes)};
    if (pin) {
      // packageStartupOwnership omits encoded bytes on its native run
      // descriptors. The encoded hash remains mandatory; production loading
      // separately authenticates decoded words and their complete coverage.
      if (!omittedNativeBytes) assert.equal(descriptor.bytes, pin.bytes, `Whole asset bytes differ: ${name}`);
      assert.equal(descriptor.sha256, pin.sha256, `Whole asset hash differs: ${name}`);
    }
    const key = `${scope}:${name}`;
    if (inputs.has(key)) assert.deepEqual(inputs.get(key), descriptor, `Consumed asset changed: ${name}`);
    else inputs.set(key, descriptor);
    return bytes;
  };
  const whole = (scope, pin) => {
    assert(pin && typeof pin.path === 'string', 'Missing required asset');
    let body=read(scope,pin.path,pin);
    if(pin.encoding==='gzip'){
      body=gunzipSync(body,{maxOutputLength:pin.decoded_bytes+1});
      assert.equal(body.length,pin.decoded_bytes,'Decoded whole asset bytes differ: '+pin.path);
      assert.equal(sha256(body),pin.decoded_sha256,'Decoded whole asset hash differs: '+pin.path);
    }
    return JSON.parse(body);
  };
  const selection = JSON.parse(read('root', 'data/ownership-selection.json'));
  if(selection.version===2)return checkFinalBankEmitted({selection,expectations,read,inputs});
  const sidecar = whole('root', selection.additive_release);
  const wrapped = whole('root', sidecar.runtime_envelope),source=wrapped.additiveRelease??wrapped;
  const atlas = JSON.parse(read('emitted', 'atlas-geography.json')),envelope=atlas.additiveRelease;
  additiveBaseReference({additiveRelease:source,reference_release:source.effective_reference});
  additiveBaseReference(atlas);
  // Only ledger/patch transport may differ from the accepted source envelope.
  // Original scientific JSON identities and every other field stay exact.
  assert.deepEqual({...envelope,ledger:source.ledger,patch:source.patch},source,'Actual emitted envelope differs from selected release');
  for(const role of ['ledger','patch']){
    if(source[role].encoding==='gzip'||envelope[role].encoding===undefined)
      assert.deepEqual(envelope[role],source[role],'Actual emitted asset differs from selected release: '+role);
    else{
      assert.equal(envelope[role].path,source[role].path.replace(/\.json(?:\.gz)?$/,'.json.gz'),'Derived transport path differs: '+role);
      assert.deepEqual(decodedAdditiveAssetIdentity(envelope[role]),decodedAdditiveAssetIdentity(source[role]),'Decoded transport identity differs: '+role);
    }
  }
  if (expectations !== undefined) assert.equal(decodedAdditiveAssetIdentity(envelope.ledger).sha256, expectations.selected_ledger_sha256, 'Wrong selected ledger hash');
  const final=atlas.preparedOwnership!==undefined;
  if(final)assert.equal(atlas.preparedOwnership.version,2,'Unsupported prepared final bank');
  const logical=final?{}:null;
  if(final)for(const role of ['base_manifest','ledger','owner_roster','patch']) {
    const pin=sidecar.logical_asset_map?.[role],asset=source[role];
    assert(pin,'Missing original scientific asset pin: '+role);
    assert(pin.bytes===asset.bytes&&pin.sha256===asset.sha256
      &&(pin.decoded_bytes??pin.bytes)===(asset.decoded_bytes??asset.bytes)
      &&(pin.decoded_sha256??pin.sha256)===(asset.decoded_sha256??asset.sha256),
      'Original scientific identity differs: '+role);
    // Git pins bind physical bytes; only the authenticated envelope owns decoding.
    logical[role]={...pin,encoding:asset.encoding};
  }
  const ledger = whole(final?'root':'emitted', final?logical.ledger:envelope.ledger), patch = whole(final?'root':'emitted', final?logical.patch:envelope.patch);
  const assets = new Map(), nativeParts = new Set(atlas.pixelMap?.method === 'native-linear-evenodd-first-owner-v1'
    ? (atlas.pixelMap.parts ?? []).map(part => part.path) : []);
  const original=final?{...atlas,pixelMap:atlas.preparedOwnership.native_pixel_map}:atlas;
  if(final)delete original.preparedOwnership;
  const scientific=new Map(final?['base_manifest','ledger','owner_roster','patch'].map(role=>[source[role].path,logical[role]]):[]);
  for (const descriptor of [...(atlas.pixelMap?.parts ?? []), ...(final?original.pixelMap.parts:[]),
    ...(final?atlas.preparedOwnership.context_parts:[envelope.ledger,envelope.patch,envelope.owner_roster,envelope.base_manifest]),
    ...(atlas.referenceMetadata?[atlas.referenceMetadata.asset]:[])]) {
    assert(descriptor, 'Missing emitted asset path');
    if(assets.has(descriptor.path)){assert.deepEqual(assets.get(descriptor.path),descriptor,'Conflicting emitted asset path');continue;}
    assets.set(descriptor.path, descriptor);
  }
  const fetcher = async name => {
    assert(typeof name === 'string', 'Invalid asset fetch path');
    const relative = name.startsWith('./') ? name.slice(2) : name;
    if(scientific.has(relative)){const pin=scientific.get(relative);return new Response(read('root',pin.path,pin));}
    const descriptor = assets.get(relative);
    assert(descriptor, `Unlisted emitted asset: ${relative}`);
    const bytes = read('emitted', relative, descriptor, {nativePart: nativeParts.has(relative)});
    return new Response(bytes, {status: 200, headers: {'Content-Length': String(bytes.length)}});
  };
  for(const part of original.pixelMap?.parts??[])nativeParts.add(part.path);
  const base = await loadOwnershipAssets(original.pixelMap, fetcher,final?{requireNative:true,expectedReference:nativeReferenceForData(original)}:{});
  const beforeControls = selectedStableOwnerControls(base, patch);
  uniqueStrings(atlas.parts, 'emitted feature parts');
  const features = atlas.parts.flatMap(name => {
    const bytes = read('emitted', name);
    const body = name.endsWith('.gz') ? gunzipSync(bytes, {maxOutputLength: 32 * 1024 * 1024}) : bytes;
    const rows = JSON.parse(body);
    assert(Array.isArray(rows) && rows.length > 0, 'Missing emitted feature records');
    return rows;
  });
  let effective;
  if(final){
    const expectedFeatures=structuredClone(features);
    const expected=await loadAdditiveNativePatch(original,expectedFeatures,base,{fetcher});
    const emitted=await loadOwnershipAssets(atlas.pixelMap,fetcher,{requireNative:true,expectedReference:atlas.reference_release});
    effective=await loadPreparedNativeContext(atlas,features,emitted,{fetcher});
    // E is now a committed operand, so sampled stable cells are not sufficient:
    // preserve every old/held word against the existing scientific consumer.
    for(const key of ['rows','runs'])assert(Buffer.from(effective[key].buffer,effective[key].byteOffset,effective[key].byteLength)
      .equals(Buffer.from(expected[key].buffer,expected[key].byteOffset,expected[key].byteLength)),'Complete emitted '+key+' differ from accepted native composition');
    assert.deepEqual(features,expectedFeatures,'Complete emitted effective context differs');
    for(const key of ['additive_patch_sha256','additive_ledger_sha256','additive_added_cells','reference_owner_sha256',
      'reference_owner_source_sha256','effective_footprint_domain','additive_authority_registry_sha256','additive_rule_sha256'])
      assert.deepEqual(effective[key],expected[key],'Emitted provenance differs: '+key);
  }else effective=await loadAdditiveNativePatch(atlas,features,base,{fetcher});
  const report = (expectations === undefined ? verifyEmittedDelivery : verifySelectedDelivery)({expectations, ledger, ledgerSha256: decodedAdditiveAssetIdentity(envelope.ledger).sha256,
    patch, patchSha256: decodedAdditiveAssetIdentity(envelope.patch).sha256, features, base, effective, beforeControls});
  report.inputs = [...inputs.values()].sort((a, b) => `${a.scope}:${a.path}`.localeCompare(`${b.scope}:${b.path}`));
  return report;
}

// Current publication is parity against the accepted whole final bank. Source
// qualification is the existing selected-joint transition, not historical replay.
async function checkFinalBankEmitted({selection,expectations,read,inputs}) {
  const native=scientificNativeSelection(selection),manifestRaw=read('root',native.manifest_path);
  assert.equal(sha256(manifestRaw),native.sha256,'Original native manifest differs');
  const manifest=JSON.parse(manifestRaw),indexRaw=read('root',selection.prepared_bank.path,selection.prepared_bank),index=JSON.parse(indexRaw);
  let base=originalNativeReference(manifest),referenceMetadata;
  if(selection.reference_projection){const raw=read('root',selection.reference_projection.path,selection.reference_projection),projection=JSON.parse(raw);
    const references=validateReferenceMetadataHeader(projection,{selection,manifest});base=references.reference;
    referenceMetadata={version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:sha256(raw)},native_reference:references.native,reference:base};}
  assert.deepEqual(index.referenceMetadata,referenceMetadata,'Final bank projection identity differs');
  const atlas=JSON.parse(read('emitted','atlas-geography.json'));
  assert.equal(atlas.additiveRelease,undefined,'Final map cannot retain a historical repair envelope');
  assert.deepEqual(atlas.pixelMap,index.pixelMap,'Emitted final words descriptor differs');
  assert.deepEqual(atlas.preparedOwnership,index.preparedOwnership,'Emitted final context descriptor differs');
  assert.deepEqual(atlas.reference_release,selection.reference,'Emitted final identity differs');
  assert.deepEqual(atlas.referenceMetadata?Object.fromEntries(Object.entries(atlas.referenceMetadata).filter(([key])=>key!=='application_reference_revision')):undefined,referenceMetadata);
  assert.deepEqual(additiveBaseReference(atlas),base,'Emitted content reference differs');
  if(expectations!==undefined){validateDeliveryExpectations(expectations);assert.equal(expectations.version,2,'Historical repair expectations cannot admit a final bank');
    assert.deepEqual(expectations.bank,selection.prepared_bank);assert.deepEqual(expectations.reference,selection.reference);}
  uniqueStrings(atlas.parts,'emitted feature parts');
  const features=atlas.parts.flatMap(name=>{const raw=read('emitted',name),rows=JSON.parse(name.endsWith('.gz')?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);assert(Array.isArray(rows)&&rows.length);return rows;});
  const prefix='data/canonical-grid/current-startup/',pins=new Map(index.files.map(pin=>[pin.path,pin]));
  // Every fixed compatibility URL and current operand must be the actual committed body.
  for(const pin of index.files){read('root',prefix+pin.path,{...pin,path:prefix+pin.path});read('emitted',pin.path,pin);}
  if(referenceMetadata)read('emitted',referenceMetadata.asset.path,referenceMetadata.asset);
  const expected=await readPreparedFinalOwnership({indexRaw,manifest,manifestSha:native.sha256,
    selected:{finalBank:selection.prepared_bank,reference_release:selection.reference,base,referenceMetadata},features:structuredClone(features),
    read:pin=>read('root',prefix+pin.path,{...pin,path:prefix+pin.path})});
  const fetcher=async name=>{const relative=String(name).replace(/^\.\//,'');const pin=pins.get(relative);assert(pin,'Unlisted emitted final bank operand');return new Response(read('emitted',relative,pin));};
  const words=await loadOwnershipAssets(atlas.pixelMap,fetcher,{requireNative:true,expectedReference:selection.reference});
  const effective=await loadPreparedNativeContext(atlas,features,words,{fetcher});
  assert.deepEqual(effective.rows,expected.ownership.rows,'Every emitted final row word equals its accepted bank');
  assert.deepEqual(effective.runs,expected.ownership.runs,'Every emitted final run word equals its accepted bank');
  assert.deepEqual(features,expected.features,'Complete emitted finished context differs');
  let controls=0;
  for(let y=0;y<effective.size;y++)if(effective.rows[y*2+1]){const run=ownershipRun(expected.ownership,expected.ownership.rows[y*2]);
    assert.equal(pickOwnership(effective,run.start,y),run.id);assert.equal(samplePackedOwnership(effective,{x:run.start,y,width:1,height:1})[0],run.id);controls++;}
  assert(controls>0,'Missing occupied final owner controls');
  return {version:2,kind:'actual-emitted-final-bank-consumer',passed:true,bank:selection.prepared_bank,reference:selection.reference,
    feature_count:features.length,complete_row_words:effective.rows.length,complete_run_words:effective.runs.length,
    occupied_controls_picked_and_sampled:controls,inputs:[...inputs.values()].sort((a,b)=>`${a.scope}:${a.path}`.localeCompare(`${b.scope}:${b.path}`)),
    limitation:'Whole accepted bank/context publication parity plus real picker/sampler controls. No historical repair replay, new science qualification or browser GPU claim.'};
}

export async function runSelectedDeliverySmoke({expectationsPath, outputPath, ...options}) {
  const output = admitOutput(outputPath);
  assert(text(expectationsPath), 'Missing expectations path');
  const expectationsFile = path.resolve(expectationsPath);
  const expectationsBytes = repositoryReader(path.dirname(expectationsFile))(path.basename(expectationsFile), 'candidate');
  const expectations = validateDeliveryExpectations(JSON.parse(expectationsBytes));
  const report = await checkEmittedSelectedDelivery({...options, expectations});
  report.expectations_sha256 = sha256(expectationsBytes);
  // Failures before this point create nothing. Exclusive creation rejects both
  // ordinary collisions and dangling symlinks; parent symlinks are refused too.
  admitOutput(output);
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n',
    {flag: fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW});
  return report;
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 1 && args[0] === '--help') {
    console.log('Usage: node scripts/selected-delivery-smoke.mjs --expectations FILE --output NEW_FILE [--root REPO] [--emitted-directory DIR]');
    return;
  }
  const names = new Map([['--root', 'root'], ['--emitted-directory', 'emittedDirectory'],
    ['--expectations', 'expectationsPath'], ['--output', 'outputPath']]), options = {};
  for (let i = 0; i < args.length; i += 2) {
    const name = names.get(args[i]);
    assert(name && !Object.hasOwn(options, name) && text(args[i + 1]) && !args[i + 1].startsWith('--'),
      `Unknown, duplicate or incomplete option: ${args[i]}`);
    options[name] = args[i + 1];
  }
  const report = await runSelectedDeliverySmoke(options);
  console.log(JSON.stringify(report));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {console.error(error.message); process.exitCode = 1;});
}
