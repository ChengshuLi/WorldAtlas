import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validate} from './assemble-source-closure.mjs';

const packet = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = name => JSON.parse(fs.readFileSync(path.join(packet, 'inputs', name), 'utf8'));
const original = read('complete-source-ready-handoff.json');
const contract = read('candidate-contract.json');
const lock = read('frozen-input-lock.json');
const clone = value => JSON.parse(JSON.stringify(value));
const rejected = (handoff, changedContract = contract) => assert.throws(() => validate(handoff, changedContract, lock));

test('accepts the full frozen 50 component, 14 contact, two-family closure', () => {
  assert.equal(validate(original, contract, lock), true);
});

test('rejects an omitted component', () => {
  const h = clone(original);
  h.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_component_ids.pop();
  rejected(h);
});

test('rejects duplicate membership and a foreign component subject', () => {
  const duplicate = clone(original);
  const members = duplicate.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_component_ids;
  members.push(members[0]);
  rejected(duplicate);
  const foreign = clone(original);
  foreign.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_component_ids[0] = 'physical-component:foreign';
  rejected(foreign);
});

test('rejects altered original source body and hash pins', () => {
  const h = clone(original);
  h.source_encoded_ordinary_pins[0].sha256 = '0'.repeat(64);
  rejected(h);
  const raw = clone(original);
  raw.complete_original_consumed_source.original_sha256 = '0'.repeat(64);
  rejected(raw);
});

test('rejects contact omission, duplication, and foreign subject IDs', () => {
  const omitted = clone(original);
  omitted.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_contact_ids.pop();
  rejected(omitted);
  const duplicate = clone(original);
  const ids = duplicate.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_contact_ids;
  ids.push(ids[0]);
  rejected(duplicate);
  const foreign = clone(original);
  foreign.complete_family_scope_and_diagnostics.whole_families[0].accounting.complete_contact_ids[0] = 'gb:CHN:ADM2:foreign';
  rejected(foreign);
});

test('rejects re-bound contact geometry and candidate geometry', () => {
  const contact = clone(original);
  const contactId = contract.evidence_quality.subject_ids[0];
  contact.full_contacts_and_original_source_members[contactId].original_complete_feature.geometry.coordinates[0][0][0] += 0.00001;
  rejected(contact);
  const candidate = clone(original);
  const componentId = lock.component_ids[0];
  candidate.complete_candidate_pointsets[componentId].geometry.coordinates[0][0][0] += 0.00001;
  rejected(candidate);
});

test('rejects family-row and family identity rebinding', () => {
  const row = clone(original);
  row.complete_family_scope_and_diagnostics.whole_families[0].accounting.family_row_sha256 = '0'.repeat(64);
  rejected(row);
  const foreign = clone(original);
  foreign.complete_family_scope_and_diagnostics.whole_families[0].accounting.family = 'gap-source-batch:foreign';
  rejected(foreign);
});
