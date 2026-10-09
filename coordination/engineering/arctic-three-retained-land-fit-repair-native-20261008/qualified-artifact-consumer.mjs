import {completeReleaseProductInputs} from './release-product-inputs.mjs';
// Distinct application-consumption authority for immutable, qualified products.
// Scientific validation brands remain private to their original validators.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {restoreWholeImage} from '../eastern-two-gap-repair-native-20261007/whole-image.mjs';
import {restoredContextMember} from '../eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';
import {validateNativeSelectionReceipt} from '../../../scripts/native-ownership/require-verified-selection.mjs';
import {requireCurrentExecution} from '../eastern-two-gap-repair-native-20261007/current-execution.mjs';
import {validateRetainedAssociation} from './qualified-artifact-association.mjs';

const N2 = 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
const MEMBER_CAP = 32 * 1024 * 1024;
const BEFORE = 'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
const AFTER = '2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9';
const MANIFEST = 'd9954fa51d18e4ce785679f920e4b6ac1ebd3cf07ce03fa7e7e674cb2a42faba';
const SUBJECTS = ['atlas:physical:CAN-15:NWT', 'atlas:physical:CAN-25:NUN'];
const consumed = new WeakMap();
const sha = raw => createHash('sha256').update(raw).digest('hex');
const fingerprint = value => sha(JSON.stringify(value));
const authorityFingerprint = context => {
  const {installation, ...authority} = context;
  return fingerprint(authority);
};
const same = (a, b) => ['dev', 'ino', 'size', 'mode', 'mtimeMs', 'ctimeMs'].forEach(key => assert.equal(a[key], b[key]));

function statBody(root, pin) {
  assert(pin && typeof pin.path === 'string' && !path.isAbsolute(pin.path));
  assert(pin.path.split('/').every(piece => piece && piece !== '.' && piece !== '..') && !pin.path.includes('\\'));
  assert.equal(pin.mode, '100644');
  assert(Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && pin.bytes <= MEMBER_CAP);
  assert(/^[a-f0-9]{64}$/.test(pin.sha256));
  const file = path.join(root, pin.path);
  for (let ancestor = file;; ancestor = path.dirname(ancestor)) {
    assert(!fs.lstatSync(ancestor).isSymbolicLink(), 'Ordinary input ancestors required');
    if (ancestor === path.dirname(ancestor)) break;
  }
  const stat = fs.lstatSync(file);
  assert(stat.isFile() && (stat.mode & 511) === 420);
  assert.equal(stat.size, pin.bytes);
  return {file, stat};
}

function descriptor(pin, space = pin.space ?? 'root') {
  return {space, path: pin.path, mode: pin.mode ?? '100644', bytes: pin.bytes, sha256: pin.sha256,
    ...(pin.decoded_bytes === undefined ? {} : {decoded_bytes: pin.decoded_bytes, decoded_sha256: pin.decoded_sha256})};
}
function declarationKey(pin) { return pin.space + ':' + pin.path; }
function reader(root, ledger, defaultSpace = 'root') {
  return supplied => {
    const pin = {...supplied, mode: supplied.mode ?? '100644'};
    const declared = descriptor(pin, pin.space ?? defaultSpace);
    const key = declarationKey(declared);
    if (ledger.declarations) {
      assert.deepEqual(ledger.declarations.get(key), declared, 'Undeclared or changed application input role');
      ledger.consumed.add(key);
    }
    const base = pin.space === 'prior' ? restoredContextMember(root, pin.path, {prior: true}).file.slice(0, -pin.path.length - 1) : root;
    assert(pin.space === undefined || ['root', 'prior', 'image'].includes(pin.space));
    if (pin.space === 'prior') {
      const original = restoredContextMember(root, pin.path, {prior: true}).pin;
      for (const key of ['bytes', 'sha256', 'mode']) assert.equal(original[key], pin[key]);
    }
    const {file, stat} = statBody(base, pin);
    const previous = ledger.members.get(file);
    if (previous) assert.deepEqual(descriptor(previous), descriptor(pin));
    else ledger.members.set(file, pin);
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    let raw;
    try {
      same(stat, fs.fstatSync(fd));
      raw = fs.readFileSync(fd);
      same(stat, fs.fstatSync(fd));
    } finally { fs.closeSync(fd); }
    same(stat, fs.lstatSync(file));
    assert.equal(raw.length, pin.bytes);
    assert.equal(sha(raw), pin.sha256, 'Whole selected artifact changed');
    ledger.encoded_read_bytes += raw.length;
    if (pin.decoded_bytes !== undefined) {
      assert(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0 && pin.decoded_bytes <= MEMBER_CAP);
      assert(/^[a-f0-9]{64}$/.test(pin.decoded_sha256));
      const decoded = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes});
      assert.equal(decoded.length, pin.decoded_bytes);
      assert.equal(sha(decoded), pin.decoded_sha256);
      ledger.decoded_read_bytes += decoded.length;
      return decoded;
    }
    return raw;
  };
}

export function requireConsumedArcticArtifacts(context) {
  const saved = consumed.get(context);
  assert(saved, 'Actual completed immutable artifact consumption required');
  requireCurrentExecution(saved.currentExecution);
  assert.equal(authorityFingerprint(context), saved.fingerprint, 'Artifact consumption result changed');
  return saved;
}

export function validateRetainedRegistryPrefixes(registry, originalRegistry) {
  assert(Array.isArray(registry.releases) && Array.isArray(originalRegistry.releases));
  assert.equal(registry.releases.length, originalRegistry.releases.length + 1);
  assert.deepEqual(registry.releases.slice(0, -1), originalRegistry.releases);
  for (const key of ['batches', 'sources_batches', 'memberships_batches']) {
    const originalHas = Object.hasOwn(originalRegistry, key);
    assert.equal(Object.hasOwn(registry, key), originalHas, 'Original registry field presence changed');
    if (!originalHas) {
      assert.equal(key, 'memberships_batches', 'Required original registry array absent');
      continue;
    }
    assert(Array.isArray(originalRegistry[key]) && Array.isArray(registry[key]));
    assert(registry[key].length >= originalRegistry[key].length);
    assert.deepEqual(registry[key].slice(0, originalRegistry[key].length), originalRegistry[key]);
  }
}

// The stock registry carries encoded/payload hashes, not file lengths. Bind
// its actual final343 descriptors to independently qualified ordinary pins.
export function normalizedReleaseProductPins(registry, products) {
  assert(Array.isArray(registry.batches) && registry.batches.length >= 343);
  assert(Array.isArray(products) && products.length === 343);
  const descriptors = registry.batches.slice(-343);
  assert.equal(new Set(descriptors.map(row => row.path)).size, 343);
  assert.equal(new Set(products.map(pin => pin.path)).size, 343);
  return descriptors.map((row, ordinal) => {
    assert.equal(row.encoding, 'gzip');
    assert(typeof row.path === 'string' && !path.isAbsolute(row.path) && !row.path.includes('\\'));
    assert(row.path.split('/').every(piece => piece && piece !== '.' && piece !== '..'));
    const pin = products[ordinal];
    assert.equal(pin.space ?? 'root', 'root');
    assert.equal(pin.path, 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/release-v9/' + row.path);
    assert.equal(pin.mode, '100644');
    assert(Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && pin.bytes <= MEMBER_CAP);
    assert(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0 && pin.decoded_bytes <= MEMBER_CAP);
    assert.equal(pin.sha256, row.sha256);
    assert.equal(pin.decoded_sha256, row.payload_sha256);
    return pin;
  });
}

// Preserve the actual launch protocol. These earlier producers had no phase
// plan argument; their qualified command and pre-import code proof are the
// original authority, rather than a retrospectively invented plan.
export function validateOriginalQualificationInvocation(phase, run, codeSource) {
  const invocation = run.original_invocation;
  const command = run.actual_terminal.command;
  assert(Array.isArray(command) && command.every(value => typeof value === 'string'));
  assert.deepEqual(command.slice(0, 2), ['/usr/bin/time', '-l']);
  if (run.complete_original_plans.length) {
    assert.equal(invocation.kind, 'original-whole-plan-invocation');
    assert.deepEqual(invocation.plan_pins, run.complete_original_plans.map(item => item.pin));
    for (const item of run.complete_original_plans) assert(command.includes(item.pin.path));
    return;
  }
  assert(codeSource && invocation.code_source);
  assert.deepEqual(codeSource, invocation.code_source.original_whole_code_source);
  if (phase === 'pair-execution-043') {
    assert.equal(invocation.kind, 'original-producer-code-source-arguments');
    assert.equal(command.length, 14);
    assert.equal(command[3], 'coordination/engineering/arctic-three-retained-land-fit-repair-20261008/producer.py');
    const argument = flag => { const index = command.indexOf(flag); assert(index >= 0); return command[index + 1]; };
    assert.equal(argument('--commit'), '043af92647438f21e1464c1dccc8b7aaf8a2ea35');
    assert.equal(argument('--code-source'), invocation.original_code_source_argument);
    assert.equal(argument('--code-source-sha'), invocation.code_source.pin.sha256);
    assert.equal(Number(argument('--code-source-bytes')), invocation.code_source.pin.bytes);
  } else {
    assert.equal(phase, 'operand-acquisition-7b0d0d35');
    assert.equal(invocation.kind, 'original-ordinal-acquisition-code-source');
    assert.equal(command.length, 7);
    assert.equal(command[3], N2 + '/acquire-operand.mjs');
    assert.equal(command[4], '7b0d0d35a240e2cb9a185d91917f065afa7ba29a');
    assert.equal(codeSource.head, command[4]);
    assert.equal(run.actual_terminal.head, command[4]);
    assert(Number.isInteger(invocation.ordinal) && invocation.ordinal >= 0 && invocation.ordinal < 34);
    assert.equal(command[5], String(invocation.ordinal));
    assert.equal(run.actual_terminal.ordinal, invocation.ordinal);
    assert.equal(run.actual_terminal.run, invocation.run);
    assert.equal(run.actual_terminal.preimport_code_source_sha256, invocation.code_source.pin.sha256);
  }
}

function qualificationCustody(read, certificate, qualification, ledger) {
  const indexPin = certificate.qualification_custody.index;
  const index = JSON.parse(read(indexPin));
  assert.equal(index.kind, 'ordered-exact-original-byte-fragments');
  assert.equal(index.files.length, qualification.complete_operating_custody.length);
  assert.equal(index.parts.length, 1);
  const part = index.parts[0];
  assert.equal(part.offset, 0);
  const raw = read({...part, path: path.posix.join(path.posix.dirname(indexPin.path), part.path), mode: '100644'});
  assert.equal(raw.length, index.whole_bytes);
  assert.equal(sha(raw), index.whole_sha256);
  const originals = new Map(qualification.complete_operating_custody.map(pin => [pin.path, pin]));
  assert.equal(originals.size, qualification.complete_operating_custody.length);
  const bodies = new Map();
  let offset = 0;
  for (const member of index.files) {
    assert.equal(member.offset, offset);
    assert.equal(member.mode, '100644');
    const binding = member.original_binding;
    assert.equal(binding.kind, 'actual-completed-qualification-custody');
    assert.deepEqual(binding.original_whole_pin, originals.get(binding.original_logical_path));
    for (const key of ['bytes', 'sha256', 'mode']) assert.equal(member[key], binding.original_whole_pin[key]);
    assert(!bodies.has(binding.original_logical_path));
    const body = raw.subarray(offset, offset + member.bytes);
    assert.equal(body.length, member.bytes);
    assert.equal(sha(body), member.sha256);
    bodies.set(binding.original_logical_path, body);
    offset += member.bytes;
  }
  assert.equal(offset, raw.length);
  ledger.retained_metadata_member_bytes = offset;
  return pin => {
    assert.deepEqual(originals.get(pin.path), pin, 'Original custody pin absent from authenticated bank');
    const body = bodies.get(pin.path); assert(body);
    return body;
  };
}

// The review snapshot is a retained whole GitHub GET, not an author approval
// boolean. Its exact certificate/source/policy binding is independently checked
// before this route is published and again by the final ordinary PR gate.
function requireReview(certificate, certificatePin, snapshot) {
  assert(Number.isSafeInteger(snapshot.id) && snapshot.id > 0);
  assert(snapshot.user && typeof snapshot.user.login === 'string');
  assert.equal(typeof snapshot.body, 'string');
  const match = snapshot.body.match(/<!-- worldatlas-qualified-artifact-consumption:v1\s*\n([\s\S]*?)\n-->/);
  assert(match, 'Independent typed artifact-consumption disposition required');
  const review = JSON.parse(match[1]);
  assert.equal(review.version, 1);
  assert.equal(review.issue, 1520);
  assert.equal(review.decision, 'accept-qualified-artifact-consumption');
  assert.equal(review.certificate_sha256, certificatePin.sha256);
  assert.equal(review.certificate_bytes, certificatePin.bytes);
  assert.equal(review.native_manifest_sha256, MANIFEST);
  assert.equal(review.source_policy_sha256, certificate.source_policy.sha256);
  assert.equal(review.qualification_inventory_sha256, certificate.qualification_inventory.sha256);
  assert.equal(review.selected_artifact_bindings_sha256, fingerprint(certificate.selected_artifact_bindings));
  assert.equal(review.application_consumer_code_sha256, certificate.application_consumer_code.sha256);
  assert.equal(review.github_user_id, snapshot.user.id);
  assert.equal(review.github_login, snapshot.user.login);
  assert.equal(snapshot.id, review.comment_id);
  assert(snapshot.html_url === `https://github.com/ChengshuLi/WorldAtlas/issues/1520#issuecomment-${snapshot.id}`);
  assert.equal(review.complete_original_qualification_inventory_reviewed, true);
  assert.equal(review.complete_selected_outputs_and_policy_reviewed, true);
  assert(typeof review.reviewer_id === 'string' && review.reviewer_id !== certificate.author_worker_id);
  assert.equal(snapshot.html_url, review.comment_url);
  assert.equal(review.scientific_reexecutions_required_for_application_consumption, false);
  return review;
}

export async function consumeQualifiedArcticArtifacts({root, stage, selection, restoredReceipt, currentExecution}) {
  assert.equal(process.env.WORLDATLAS_PACKAGE_STAGE, root);
  assert.equal(fs.realpathSync(root), root);
  assert.notEqual(root, fs.realpathSync(process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT));
  assert.equal(stage.version, 4);
  assert.equal(stage.kind, 'arctic-qualified-artifact-application-consumption-v1');
  assert.equal(stage.issue, 1520);
  assert.equal(selection.sha256, MANIFEST);
  assert.equal(selection.manifest_path, N2 + '/native-v9/manifest.json');
  assert.deepEqual(selection.artifact_consumption, stage.artifact_consumption);
  assert.equal(restoredReceipt.canonical_paths, 302);
  assert.equal(restoredReceipt.prior_paths, 122);
  assert.equal(restoredReceipt.scientific_producers_invoked, false);
  const originalPixel = restoredContextMember(root, 'data/pixel-audit.json');
  assert.equal(originalPixel.complete_inverse_preserved, true);
  assert.equal(originalPixel.original_index_sha256, 'b82b195d94530d9b1f48153f7e47616f8b841cb1438ddf59994ba4869a1d7876');
  assert.equal(originalPixel.pin.sha256, 'a49773818f963c15c27b52a0cad7be6dabcb6dddf9523bdbc253118e177c9cd8');
  assert.equal(restoredReceipt.canonical_index_sha256, originalPixel.original_index_sha256);
  assert.equal(restoredReceipt.prior_index_sha256, 'ca1ab5fc3ef24470bcb79412f1d47a88281c6df0931461c5eb356079b75986fe');
  const issued = requireCurrentExecution(currentExecution);
  assert.equal(issued.stage_root, root);
  const ledger = {members: new Map(), consumed: new Set(), encoded_read_bytes: 0, decoded_read_bytes: 0};
  const read = reader(root, ledger);
  const certificatePin = stage.artifact_consumption.certificate;
  const certificate = JSON.parse(read(certificatePin));
  const review = requireReview(certificate, certificatePin, JSON.parse(read(stage.artifact_consumption.review)));
  assert.equal(certificate.kind, 'qualified-arctic-immutable-product-certificate-v1');
  assert.equal(certificate.issue, 1520);
  assert.deepEqual(certificate.subjects, SUBJECTS);
  assert.equal(certificate.before_footprints_sha256, BEFORE);
  assert.equal(certificate.after_footprints_sha256, AFTER);
  assert.equal(certificate.native_manifest_sha256, MANIFEST);
  assert.equal(certificate.complete_locations, 49625);
  assert.equal(certificate.unchanged_complete_records, 49623);
  assert.equal(certificate.added_native_cells, 141);
  ledger.declarations = new Map();
  for (const pin of certificate.application_inputs) {
    const declared = descriptor(pin);
    assert(['root', 'prior', 'image'].includes(declared.space));
    const key = declarationKey(declared);
    assert(!ledger.declarations.has(key), 'Duplicate input role');
    ledger.declarations.set(key, declared);
  }
  const releaseCatalogue=JSON.parse(read(certificate.release_product_catalogue));
  const completeInputs=completeReleaseProductInputs(certificate,releaseCatalogue);
  for(const pin of completeInputs){const declared=descriptor(pin),key=declarationKey(declared);if(ledger.declarations.has(key))assert.deepEqual(ledger.declarations.get(key),declared);else ledger.declarations.set(key,declared);}
  // Complete qualification inventories remain whole immutable source custody.
  // Ordinary application consumption verifies these records and delivered
  // artifacts; it does not relabel historical inputs as freshly executed.
  const qualification = JSON.parse(read(certificate.qualification_inventory));
  assert.deepEqual(certificate.selected_artifact_bindings, {
    native_manifest: stage.nativeManifest, native_comparison: stage.nativeComparison,
    migration_receipt: stage.migrationReceipt, geometry_manifest: stage.geometryManifest,
    registry: stage.registry, pixel_audit: stage.pixelAudit, selected_geography: selection.selected_geography
  });
  const consumerCode = JSON.parse(read(certificate.application_consumer_code));
  assert.equal(consumerCode.kind, 'qualified-artifact-application-code-closure-v1');
  assert(consumerCode.critical_files.length > 0);
  const critical = new Map(consumerCode.critical_files.map(pin => [pin.path, pin]));
  assert.equal(critical.size, consumerCode.critical_files.length);
  const wrapperPaths = Object.values(consumerCode.entry_roles[issued.entry_point]).flat();
  assert(wrapperPaths.every(name => typeof name === 'string'));
  assert.equal(new Set(wrapperPaths).size, wrapperPaths.length);
  assert(wrapperPaths.every(name => !critical.has(name)), 'Execution roles must be disjoint');
  assert.deepEqual([...critical.keys(), ...wrapperPaths].sort(), issued.files.map(pin => pin.path).sort(), 'Complete actual execution role closure required');
  for (const pin of issued.files) {
    if (critical.has(pin.path)) assert.deepEqual(pin, critical.get(pin.path), 'Reviewed critical consumer semantics changed');
    // The remaining explicit role files use their genuine current package-issued
    // whole source/stage pins. They are not relabelled as historical SCI code.
    const declared = descriptor(pin);
    const key = declarationKey(declared);
    if (ledger.declarations.has(key)) assert.deepEqual(ledger.declarations.get(key), declared);
    else ledger.declarations.set(key, declared);
    read(pin);
  }
  assert.deepEqual(certificate.registry, stage.registry);
  assert.deepEqual(certificate.native_comparison, stage.nativeComparison);
  assert.deepEqual(certificate.steps.at(-1).selected_grid, stage.nativeManifest);
  assert.deepEqual(certificate.steps.at(-1).migration_receipt, stage.migrationReceipt);
  assert.deepEqual(certificate.steps.at(-1).geometry_manifest, stage.geometryManifest);
  assert.equal(certificate.steps.at(-1).selected_grid.sha256, MANIFEST);
  assert.equal(fingerprint(qualification.source_policy), certificate.source_policy.sha256);
  assert.equal(qualification.kind, 'complete-qualified-scientific-artifact-inventory-v1');
  assert.equal(qualification.issue, 1520);
  const expectedPhases = {
    'pair-execution-043':2,'operand-acquisition-7b0d0d35':68,
    'selected-native-29b67f33':2,'native-repack-c7799a18':4,
    'footprint-2295dcc2':2,'context-part-b081aafb':2,
    'pixel-native-group-12a41992':56,'pixel-accounting-join-d67d521f':2,
    'pixel-source-area-25060cf2':2,'release-issuer-5e428510':2,
    'release-serializer-165d6141':14,'release-comparison-165d6141':7,
    'registry-issuer-ff95d34d-attempt2':1,'registry-encoding-ae42e1e9':1,
    'native-asset-copy-cf2a5966':1,'native-asset-group-5135b29e':2,
    'native-asset-index-join-f66635c1-attempt2':1,'v9-bindings-f484642d':2
  };
  assert.deepEqual(Object.fromEntries(qualification.complete_phase_inventory.map(phase => [phase.phase, phase.complete_actual_runs])), expectedPhases);
  assert.equal(qualification.complete_phase_inventory.length, Object.keys(expectedPhases).length);
  const originalBody = qualificationCustody(read, certificate, qualification, ledger);
  for (const phase of qualification.complete_phase_inventory) {
    assert.equal(phase.runs.length, expectedPhases[phase.phase]);
    for (const run of phase.runs) {
      const terminal = run.actual_terminal;
      assert.deepEqual(JSON.parse(originalBody(run.terminal_pin)), terminal, 'Literal original terminal required');
      assert.equal(terminal.qualified, true);
      assert.equal(terminal.exit_code, 0);
      assert.equal(terminal.guard_reason, null);
      assert.deepEqual(terminal.owned_group_survivors, []);
      assert(terminal.time_l_lifetime_max_rss_bytes <= (terminal.lifetime_ceiling_bytes ?? terminal.original_ceiling_bytes));
      assert(terminal.sampled_group_peak_bytes <= terminal.sampled_stop_bytes);
      for (const plan of run.complete_original_plans) {
        assert.deepEqual(JSON.parse(originalBody(plan.pin)), plan.original_whole_plan);
      }
      const codeSource = run.complete_original_plans.length ? undefined : JSON.parse(read(run.original_invocation.code_source.pin));
      validateOriginalQualificationInvocation(phase.phase, run, codeSource);
      for (const pin of run.operating_custody) originalBody(pin);
      assert(run.operating_custody.some(pin => pin.path.endsWith('.stderr.log')));
      assert(run.operating_custody.some(pin => pin.path.endsWith('.samples.jsonl')));
    }
  }
  assert.equal(qualification.original_source_and_qualification_publications.length, 6);
  for (const publication of qualification.original_source_and_qualification_publications) {
    const pin = publication.pin;
    assert.equal(pin.custody.commit, '859ca4643d61d472650dbda5a7c3682556ab78a4');
    assert(pin.path.startsWith('coordination/engineering/arctic-three-retained-land-fit-repair-20261008/'));
    assert.equal(pin.mode, '100644');
    assert(/^[a-f0-9]{64}$/.test(pin.sha256));
    assert.deepEqual(JSON.parse(read(pin)), publication.whole_publication);
  }
  assert.equal(qualification.prior_integrated_delivery_publications.length, 11);
  for (const publication of qualification.prior_integrated_delivery_publications) {
    const body = read(publication.pin);
    if (publication.original_immutable_pin) {
      const original = publication.original_immutable_pin;
      assert(/^[a-f0-9]{40}$/.test(original.commit));
      for (const key of ['mode', 'bytes', 'sha256']) assert.equal(publication.pin[key], original[key]);
    } else {
      for (const key of ['mode', 'bytes', 'sha256']) assert.equal(publication.pin[key], publication.original_retained_pin[key]);
    }
    if (publication.whole_publication) assert.deepEqual(JSON.parse(body), publication.whole_publication);
  }
  const priorTransition = qualification.prior_integrated_delivery_publications.find(item => item.pin.path.endsWith('/transition-inputs.json')).whole_publication;
  assert.equal(priorTransition.merge_commit, '689fa0618ce61827adc8862c3e065bcfcf97417b');
  assert.equal(priorTransition.selected_native_manifest_ref.sha256, 'a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885');
  assert.equal(priorTransition.rows.length, 2);
  assert.deepEqual(qualification.precise_registry_completion_readbacks.map(item => item.phase),
    ['registry-issuer-ff95d34d-attempt2', 'registry-encoding-ae42e1e9']);
  const registryReadbacks = qualification.precise_registry_completion_readbacks.map(item => {
    const actual = JSON.parse(read(item.pin));
    assert.deepEqual(actual, item.whole_readback);
    for (const key of ['mode', 'bytes', 'sha256']) assert.equal(item.pin[key], item.original_retained_pin[key]);
    return actual;
  });
  assert.equal(registryReadbacks[0].complete_old_release_objects_preserved, 8);
  assert.equal(registryReadbacks[0].complete_old_batch_descriptors_preserved, 3042);
  assert.equal(registryReadbacks[0].new_complete_product_descriptors, 343);
  assert.equal(registryReadbacks[0].original_membership_records_reused, 84833);
  assert.equal(registryReadbacks[1].actual_complete_qualified_encoding, true);
  assert.equal(registryReadbacks[1].whole_raw_source_object_equal, true);
  assert.equal(registryReadbacks[1].encoded_and_decoded_whole_original_codec_equal, true);
  const encodedRegistry = registryReadbacks[1].wholeproducts.find(pin => pin.sha256 === certificate.registry.sha256);
  assert(encodedRegistry);
  for (const key of ['mode', 'bytes', 'sha256']) assert.equal(encodedRegistry[key], certificate.registry[key] ?? (key === 'mode' ? '100644' : undefined));
  assert.equal(qualification.limits.historical_runtime_unknown, true);
  assert.equal(qualification.limits.current_old_source_area_recomputation_pass, false);
  assert.equal(qualification.limits.new_geographic_approval, false);
  assert.equal(qualification.limits.science_reexecuted_for_this_inventory, false);
  const registry = JSON.parse(read(certificate.registry));
  const originalRegistry = JSON.parse(read(certificate.predecessor_registry));
  validateRetainedRegistryPrefixes(registry, originalRegistry);
  const releaseProducts = normalizedReleaseProductPins(registry, releaseCatalogue.products);
  for (const pin of releaseProducts) read(pin);
  const steps = certificate.steps.map(item => {
    const predecessor = registry.releases.find(release => release.id === item.predecessor_release_id);
    const release = registry.releases.find(release => release.id === item.successor_release_id);
    assert(predecessor && release);
    const manifest = JSON.parse(read(item.geometry_manifest));
    const receipt = JSON.parse(read(item.migration_receipt));
    const selected_grid = JSON.parse(read(item.selected_grid));
    const step = {...item, predecessor, release, manifest, receipt, selected_grid,
      receipt_sha256: item.migration_receipt.sha256, manifest_sha256: item.geometry_manifest.sha256,
      selected_grid_sha256: item.selected_grid.sha256};
    validateRetainedAssociation(step);
    assert.equal(manifest.before_footprints_sha256, predecessor.footprints_sha256);
    assert.equal(manifest.after_footprints_sha256, release.footprints_sha256);
    const receiptPins = Object.values(manifest.files).filter(pin => pin.sha256 === item.migration_receipt.sha256);
    assert.equal(Object.keys(manifest.files).length, 1, 'Every migration member must be authenticated');
    assert.equal(receiptPins.length, 1, 'Actual immutable manifest must name the consumed whole receipt');
    assert.equal(receiptPins[0].bytes, item.migration_receipt.bytes);
    assert.equal(selected_grid.geographic_release, release.id);
    assert.equal(selected_grid.footprints_sha256, release.footprints_sha256);
    return step;
  });
  assert.deepEqual(steps.map(step => [step.predecessor.version, step.release.version]), [[6, 7], [7, 8], [8, 9]]);
  assert.deepEqual(steps.at(-1).receipt.changed_ids, SUBJECTS);
  const manifest = steps.at(-1).selected_grid;
  const pixel = JSON.parse(read(stage.pixelAudit));
  assert.equal(pixel.locations, 49625);
  assert.equal(pixel.records.length, 49625);
  assert.equal(new Set(pixel.records.map(record => record.id)).size, 49625);
  assert.equal(pixel.footprints_sha256, AFTER);
  assert.equal(pixel.reference_release, steps.at(-1).release.id);
  assert.equal(pixel.hierarchy_sha256, manifest.hierarchy_sha256);
  assert.deepEqual(pixel.native_manifest, {path: stage.nativeManifest.path, sha256: MANIFEST});
  const geography = JSON.parse(read({...selection.selected_geography, mode: '100644'}));
  assert.equal(geography.kind, 'complete-world-index-with-exact-encoded-overrides');
  assert.equal(geography.native_manifest_sha256, MANIFEST);
  assert.equal(geography.footprints_sha256, AFTER);
  assert.equal(geography.release_id, steps.at(-1).release.id);
  assert.equal(geography.unchanged_files.length, 35);
  const world = JSON.parse(read(geography.world_index));
  assert.equal(world.parts.length, 36);
  assert.equal(new Set(geography.unchanged_files.map(pin => pin.path)).size, 35);
  assert.equal(geography.overrides.length, 1);
  assert.deepEqual(geography.changed_ids, SUBJECTS);
  assert.equal(geography.locations, 49625);
  assert.equal(geography.unchanged_full_records, 49623);
  assert.equal(geography.prior_two_repairs_retained, true);
  const override = geography.overrides[0];
  assert.equal(override.logical_path, 'data/geography/part-29.json');
  assert.deepEqual([...geography.unchanged_files.map(pin => pin.path), override.logical_path].sort(), world.parts.map(name => 'data/' + name).sort());
  for (const pin of geography.unchanged_files) read(pin);
  read(override);
  // The single complete changed containing file is authenticated by the actual
  // selected map and installer; no unselected proposal substitutes for it.
  const comparison = JSON.parse(read(certificate.native_comparison));
  validateNativeSelectionReceipt(manifest, MANIFEST, comparison);
  assert.equal(comparison.scope_proof.selected_rows, 60);
  assert.equal(comparison.scope_proof.retained_rows, 262106);
  assert.equal(comparison.scope_proof.whole_world_rule_reexecuted, false);
  const indexPin = manifest.native_asset_transport.index;
  const index = JSON.parse(read({...indexPin, mode: '100644'}));
  assert.equal(index.files.length, 56);
  assert.equal(index.whole_bytes, 47604645);
  assert.deepEqual(index.files.map(pin => pin.path).sort(), manifest.parts.map(pin => pin.path).sort());
  const temporary = fs.mkdtempSync(path.join(root, '.cache/native-v9-consumption-'));
  const image = path.join(temporary, 'image');
  for (const part of index.parts) {
    const pin = {...part, path: path.posix.join(path.posix.dirname(indexPin.path), part.path), mode: '100644'};
    const {file} = statBody(root, pin);
    const declared = descriptor(pin);
    const key = declarationKey(declared);
    assert.deepEqual(ledger.declarations.get(key), declared, 'Transport read absent from complete roster');
    ledger.consumed.add(key);
    ledger.members.set(file, pin);
    ledger.encoded_read_bytes += part.bytes;
    ledger.decoded_read_bytes += part.decoded_bytes;
  }
  for (const pin of index.files) {
    const declared = descriptor(pin, 'image');
    assert.deepEqual(ledger.declarations.get(declarationKey(declared)), declared, 'Reconstructed member absent from complete roster');
  }
  // All fragment/member roles have been admitted before the unchanged restorer
  // opens a fragment. The real encoded+decoded reads are charged, including its
  // second index read, separately from later authenticated member consumption.
  restoreWholeImage(path.dirname(path.join(root, indexPin.path)), image, {expectedIndexSha: indexPin.sha256});
  ledger.encoded_read_bytes += indexPin.bytes;
  const imageReader = reader(image, ledger, 'image');
  for (const pin of index.files) {
    const part = manifest.parts.find(part => part.path === pin.path);
    for (const key of ['bytes', 'sha256']) assert.equal(pin[key], part[key]);
    imageReader({...pin, mode: '100644'});
  }
  assert.deepEqual([...ledger.consumed].sort(), [...ledger.declarations.keys()].sort(), 'Complete declared application consumption required');
  const context = {kind: 'authenticated-qualified-artifact-consumption-v1', issue: 1520, steps,
    receipt: {status: 'verified-artifact-consumption', certificate_sha256: certificatePin.sha256,
      independent_review_comment: review.comment_url, migration: {locations: 49625, changed_locations: 2,
        unchanged_locations: 49623, changed_ids: SUBJECTS}, scientific_producers_invoked: false,
      historical_science_reexecuted: false, ordinary_normal_package_contract: true,
      current_execution: {source_head: issued.source_commit, runtime: issued.runtime,
        full_code_closure: issued.files, critical_consumer_code_sha256: certificate.application_consumer_code.sha256},
      consumed_input_bytes: {encoded: ledger.encoded_read_bytes, decoded: ledger.decoded_read_bytes},
      qualification_inventory_sha256: certificate.qualification_inventory.sha256},
    releaseProducts, predecessorRelease: steps.at(-1).predecessor,
    sourceAssociations: steps.slice(1).map(step => ({release: step.release, changed_ids: step.receipt.changed_ids}))};
  consumed.set(context, {currentExecution: issued, fingerprint: authorityFingerprint(context), nativeImage: image,
    releaseProducts, manifest_sha256: MANIFEST, release_id: manifest.geographic_release,
    certificate_sha256: certificatePin.sha256});
  return context;
}
