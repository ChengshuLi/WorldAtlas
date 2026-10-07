import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import {execFileSync} from 'node:child_process';

const here = path.dirname(new URL(import.meta.url).pathname);
const packet = path.resolve(here, '..');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const git = (...args) => execFileSync('git', args, {cwd: path.resolve(packet, '../../..'), encoding: 'utf8', maxBuffer: 16 * 1024 * 1024}).trim();
const fail = message => { throw new Error(message); };
const input = name => fs.readFileSync(path.join(packet, 'inputs', name));

export function validate(handoff, contract, lock) {
  const familyRows = handoff.complete_family_scope_and_diagnostics.whole_families;
  if (familyRows.length !== 2) fail('family-count');
  const expectedFamilies = ['gap-source-batch:61a32ae390d6bc77599ca035', 'gap-source-batch:aae5d81537d301c52e5303d1'];
  const families = familyRows.map(row => row.accounting.family).sort();
  if (canonical(families) !== canonical(expectedFamilies.slice().sort())) fail('foreign-or-missing-family');
  const components = familyRows.flatMap(row => row.accounting.complete_component_ids);
  if (components.length !== 50 || new Set(components).size !== 50) fail('component-omission-or-duplicate');
  if (canonical(components.slice().sort()) !== canonical(lock.component_ids.slice().sort())) fail('foreign-or-missing-component');
  const contacts = familyRows.flatMap(row => row.accounting.complete_contact_ids);
  if (contacts.length !== 14 || new Set(contacts).size !== 14) fail('contact-omission-or-duplicate');
  if (canonical(contacts.slice().sort()) !== canonical(contract.evidence_quality.subject_ids.slice().sort())) fail('foreign-or-missing-contact');
  if (Object.keys(handoff.complete_candidate_pointsets).length !== 50) fail('candidate-pointset-count');
  for (const id of components) {
    const feature = handoff.complete_candidate_pointsets[id];
    if (!feature || feature.id !== id || !feature.geometry) fail(`candidate-binding:${id}`);
    if (sha(Buffer.from(canonical(feature.geometry))) !== lock.candidate_geometry_sha256[id]) fail(`candidate-geometry-binding:${id}`);
  }
  if (Object.keys(handoff.full_contacts_and_original_source_members).length !== 14) fail('contact-record-count');
  for (const row of familyRows) if (row.accounting.family_row_sha256 !== lock.family_row_sha256[row.accounting.family]) fail(`family-row-hash:${row.accounting.family}`);
  const sourcePin = handoff.source_encoded_ordinary_pins[0];
  if (sourcePin.sha256 !== lock.encoded_source_sha256 || sourcePin.bytes !== lock.encoded_source_bytes
    || sourcePin.uncompressed_sha256 !== lock.decoded_source_sha256 || sourcePin.uncompressed_bytes !== lock.decoded_source_bytes) fail('source-body-hash-pin');
  for (const id of contract.evidence_quality.subject_ids) {
    const row = handoff.full_contacts_and_original_source_members[id];
    const binding = lock.contact_feature_bindings[id];
    if (!row || !binding || sha(Buffer.from(canonical(row.original_complete_feature))) !== binding.original_feature_sha256
      || sha(Buffer.from(canonical(row.original_complete_feature.geometry))) !== binding.original_geometry_sha256
      || sha(Buffer.from(canonical(row.current_atlas_contact.full_feature))) !== binding.current_feature_sha256
      || sha(Buffer.from(canonical(row.current_atlas_contact.full_feature.geometry))) !== binding.current_geometry_sha256) fail(`contact-feature-binding:${id}`);
  }
  const metadata = handoff.complete_source_metadata;
  if (metadata.boundaryType !== 'ADM2' || metadata.boundaryYearRepresented !== '2017' || metadata.boundaryCanonical !== 'County Level') fail('source-role-or-date');
  if (metadata.boundaryLicense !== 'Open Data Commons Public Domain Dedication and License (PDDL) v1.0') fail('source-license');
  const consumed = handoff.complete_original_consumed_source;
  if (!consumed.recorded_consumed_url.endsWith('geoBoundaries-CHN-ADM2_simplified.geojson')) fail('consumed-source-url');
  if (consumed.original_bytes !== 7018287 || consumed.original_sha256 !== '8c7dfa8e40842f9162453d9b0b614276a48bf635559ba371c7982cb288e7b303') fail('decoded-source-body-pin');
  for (const row of familyRows) {
    if (row.accounting.complete_component_ids.length !== row.whole_family.component_count
      || !Array.isArray(row.whole_family.complete_positive_length_neighbor_ids)
      || row.whole_family.id !== row.accounting.family) fail(`family-completeness:${row.accounting.family}`);
    const routeIds = row.complete_routing_rows.map(item => item.component);
    if (new Set(routeIds).size !== routeIds.length
      || canonical(routeIds.slice().sort()) !== canonical(row.accounting.complete_component_ids.slice().sort())
      || row.complete_routing_rows.some(item => item.family !== row.accounting.family)) fail(`routing-family-binding:${row.accounting.family}`);
  }
  return true;
}

export function makeLock(handoffBytes, contractBytes) {
  const handoff = JSON.parse(handoffBytes);
  const contract = JSON.parse(contractBytes);
  const componentIds = handoff.complete_family_scope_and_diagnostics.whole_families.flatMap(row => row.accounting.complete_component_ids);
  const candidate_geometry_sha256 = Object.fromEntries(componentIds.map(id => [id, sha(Buffer.from(canonical(handoff.complete_candidate_pointsets[id].geometry)))]));
  const contact_feature_bindings = Object.fromEntries(contract.evidence_quality.subject_ids.map(id => {
    const row = handoff.full_contacts_and_original_source_members[id];
    return [id, {original_feature_sha256: sha(Buffer.from(canonical(row.original_complete_feature)),),
      original_geometry_sha256: sha(Buffer.from(canonical(row.original_complete_feature.geometry))),
      current_feature_sha256: sha(Buffer.from(canonical(row.current_atlas_contact.full_feature))),
      current_geometry_sha256: sha(Buffer.from(canonical(row.current_atlas_contact.full_feature.geometry)))}];
  }));
  return {version: 1, handoff_sha256: sha(handoffBytes), handoff_bytes: handoffBytes.length,
    contract_sha256: sha(contractBytes), component_ids: componentIds.slice().sort(), contact_ids: contract.evidence_quality.subject_ids.slice().sort(),
    family_row_sha256: Object.fromEntries(handoff.complete_family_scope_and_diagnostics.whole_families.map(row => [row.accounting.family, row.accounting.family_row_sha256])),
    encoded_source_sha256: handoff.source_encoded_ordinary_pins[0].sha256, encoded_source_bytes: handoff.source_encoded_ordinary_pins[0].bytes,
    decoded_source_sha256: handoff.source_encoded_ordinary_pins[0].uncompressed_sha256, decoded_source_bytes: handoff.source_encoded_ordinary_pins[0].uncompressed_bytes,
    candidate_geometry_sha256, contact_feature_bindings};
}

function build() {
  const handoffBytes = input('complete-source-ready-handoff.json');
  const contractBytes = input('candidate-contract.json');
  const lockBytes = input('frozen-input-lock.json');
  const handoff = JSON.parse(handoffBytes);
  const contract = JSON.parse(contractBytes);
  const lock = JSON.parse(lockBytes);
  if (sha(handoffBytes) !== lock.handoff_sha256 || handoffBytes.length !== lock.handoff_bytes) fail('handoff-whole-body-pin');
  if (sha(contractBytes) !== lock.contract_sha256) fail('contract-whole-body-pin');
  validate(handoff, contract, lock);

  const root = path.resolve(packet, '../../..');
  const head = git('rev-parse', 'HEAD');
  if (head !== git('rev-parse', 'origin/main')) fail('branch-is-not-current-main-base');
  const verifyPin = pin => {
    const body = fs.readFileSync(path.resolve(root, pin.path));
    if (body.length !== pin.bytes || sha(body) !== pin.sha256) fail(`whole-file-pin:${pin.path}`);
    const row = git('ls-tree', '-l', 'HEAD', '--', pin.path).split('\t');
    const [mode, type, oid, bytes] = row[0].split(/\s+/);
    if (mode !== (pin.mode ?? '100644') || type !== 'blob' || (pin.oid && oid !== pin.oid) || Number(bytes) !== pin.bytes) fail(`git-identity-pin:${pin.path}`);
    return {path: pin.path, bytes: body.length, sha256: sha(body), mode, oid, historical_commit: pin.commit ?? null,
      historical_oid: pin.oid ?? null, current_main_head: head};
  };
  const sourcePins = [handoff.world_index_pin, handoff.source_metadata_whole_containing_file_pin,
    handoff.source_attribution_pin, handoff.source_catalogue_pin, handoff.terms_pin, ...handoff.source_encoded_ordinary_pins];
  const currentPins = handoff.actual_current_main_scoped_whole_byte_equality;
  const verifiedSourcePins = sourcePins.map(verifyPin);
  const verifiedCurrentPins = currentPins.map(row => {
    const pin = {path: row.path, bytes: row.bytes, sha256: row.sha256, mode: row.mode, oid: row.oid, commit: row.original_read_commit};
    return {...verifyPin(pin), whole_byte_equal_to_handoff_current_pin: row.whole_byte_equal,
      earlier_recorded_current_head: row.actual_current_main};
  });
  const termsText = fs.readFileSync(path.resolve(root, handoff.terms_pin.path), 'utf8');
  if (!termsText.includes('Attribution is required for use of this product') || !termsText.includes('CC BY 4.0')) fail('data-product-attribution-terms');

  const sourcePin = handoff.source_encoded_ordinary_pins[0];
  const archivePath = path.resolve(root, sourcePin.path);
  const encoded = fs.readFileSync(archivePath);
  if (encoded.length !== sourcePin.bytes || sha(encoded) !== sourcePin.sha256) fail('encoded-source-body-pin');
  const decoded = zlib.gunzipSync(encoded, {maxOutputLength: sourcePin.uncompressed_bytes + 1});
  if (decoded.length !== sourcePin.uncompressed_bytes || sha(decoded) !== sourcePin.uncompressed_sha256) fail('decoded-source-body-pin');
  const original = JSON.parse(decoded);
  if (original.type !== 'FeatureCollection' || original.features.length !== handoff.complete_original_consumed_source.feature_count) fail('original-source-feature-count');
  const originalById = new Map(original.features.map(feature => [feature.properties?.shapeID, feature]));
  if (originalById.size !== original.features.length) fail('duplicate-original-source-id');

  const contactBytes = fs.readFileSync(path.resolve(root, 'data/geography/part-3.json'));
  if (sha(contactBytes) !== handoff.full_contacts_and_original_source_members[contract.evidence_quality.subject_ids[0]].current_atlas_contact.containing_file.sha256) fail('current-contact-part-body-pin');
  const current = JSON.parse(contactBytes);
  const currentById = new Map(current.features.map(feature => [feature.properties?.id, feature]));

  const contacts = {};
  for (const id of contract.evidence_quality.subject_ids) {
    const row = handoff.full_contacts_and_original_source_members[id];
    if (!row || row.source_shape_id !== row.original_complete_feature.properties.shapeID) fail(`source-contact-id:${id}`);
    const raw = originalById.get(row.source_shape_id);
    const part = currentById.get(id);
    if (!raw || canonical(raw) !== canonical(row.original_complete_feature)) fail(`original-contact-feature-binding:${id}`);
    if (!part || canonical(part) !== canonical(row.current_atlas_contact.full_feature)) fail(`current-contact-feature-binding:${id}`);
    contacts[id] = {source_shape_id: row.source_shape_id, source_feature_sha256: row.original_feature_sha256,
      source_geometry_sha256: row.original_geometry_sha256, original_full_feature: row.original_complete_feature,
      current_full_feature_sha256: row.current_atlas_contact.full_feature_sha256,
      current_geometry_sha256: row.current_atlas_contact.geometry_sha256,
      current_containing_file: row.current_atlas_contact.containing_file,
      current_full_feature: row.current_atlas_contact.full_feature};
  }

  const candidateMap = {};
  for (const row of handoff.complete_family_scope_and_diagnostics.whole_families) {
    candidateMap[row.accounting.family] = {accounting: row.accounting, whole_family: row.whole_family,
      complete_numeric_row_bindings: row.complete_numeric_row_bindings,
      complete_routing_rows: row.complete_routing_rows,
      complete_component_pointsets: Object.fromEntries(row.accounting.complete_component_ids.map(id => [id, handoff.complete_candidate_pointsets[id]]))};
  }
  const output = {version: 1, issue: 1337, disposition: 'source-fitness-only; no source authority, geometry clearance, repair permission, or import authorization',
    produced_by: {path: 'tools/assemble-source-closure.mjs', node: process.version, executable: process.execPath},
    input_pins: {handoff_sha256: sha(handoffBytes), handoff_bytes: handoffBytes.length, contract_sha256: sha(contractBytes),
      frozen_input_lock_sha256: sha(lockBytes), current_main_head: head},
    original_consumed_source: {url: handoff.complete_original_consumed_source.recorded_consumed_url,
      encoded_git_pin: sourcePin, decoded_bytes: decoded.length, decoded_sha256: sha(decoded), feature_count: original.features.length,
      metadata: handoff.complete_source_metadata, metadata_whole_file_pin: handoff.source_metadata_whole_containing_file_pin,
      source_attribution_pin: handoff.source_attribution_pin, source_catalogue_pin: handoff.source_catalogue_pin,
      terms_pin: handoff.terms_pin,
      license_assessment: {metadata_boundaryLicense_claim: handoff.complete_source_metadata.boundaryLicense,
        pinned_product_terms_claim: 'geoBoundaries code and derivative works are CC BY 4.0; attribution is required; cite the source recorded in per-file metadata.',
        source_specific_applicability: 'Unresolved: preserve both source metadata and product terms claims; do not treat a hash or metadata license field as a legal determination.'}},
    current_contact_file: {path: 'data/geography/part-3.json', head, bytes: contactBytes.length, sha256: sha(contactBytes),
      mode: '100644', oid: git('rev-parse', `HEAD:data/geography/part-3.json`)},
    verified_current_main_source_pins: verifiedSourcePins, verified_current_main_scoped_pins: verifiedCurrentPins,
    complete_family_ids: Object.keys(candidateMap), component_count: 50, contact_ids: Object.keys(contacts), contact_count: 14,
    families: candidateMap, contacts};
  return Buffer.from(JSON.stringify(output, null, 2) + '\n');
}

if (process.argv[1] && path.resolve(process.argv[1]) === decodeURI(new URL(import.meta.url).pathname)) {
  if (process.argv[2] === '--write-lock') {
    const lock = makeLock(input('complete-source-ready-handoff.json'), input('candidate-contract.json'));
    fs.writeFileSync(path.join(packet, 'inputs', 'frozen-input-lock.json'), JSON.stringify(lock, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({components: lock.component_ids.length, contacts: lock.contact_ids.length, handoff_sha256: lock.handoff_sha256}));
    process.exit(0);
  }
  const output = path.resolve(process.argv[2] ?? path.join(packet, 'runs', 'final.json'));
  const bytes = build();
  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.writeFileSync(output, bytes);
  console.log(JSON.stringify({output, bytes: bytes.length, sha256: sha(bytes), node: process.version, head: git('rev-parse', 'HEAD')}));
}
