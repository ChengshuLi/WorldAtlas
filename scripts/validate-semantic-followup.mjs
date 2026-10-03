#!/usr/bin/env node
/** Read-only six-continent inventory gate. Passing never approves geography.
 * Numeric lexemes are retained when hashing committed Python JSON: parsing
 * 1.0 through JS Number and stringifying 1 would silently change the hash.
 */
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { resolve, relative, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import {footprintHash} from './check-prepared.mjs';
import {validateMacroReviewProjection,loadProjectionPredecessors} from './prepare-macro-review-projection.mjs';

export const CONTINENTS = ['Africa', 'Asia', 'Europe', 'North America', 'Oceania', 'South America'];
export const LEDGERS = Object.fromEntries(CONTINENTS.map(name => [name, `data/geographic-semantic-followup/${name.toLowerCase().replaceAll(' ', '-')}.json.gz`]));
const TIERS = ['province', 'area', 'region', 'subcontinent', 'continent'];
const HEX = /^[a-f0-9]{64}$/;
export const hash = value => createHash('sha256').update(value).digest('hex');
const fail = message => { throw new Error(message); };
const requireThat = (value, message) => { if (!value) fail(message); };
const sorted = values => [...values].sort();
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function exactIds(expected, actual, label) {
  requireThat(Array.isArray(actual), `${label}: expected ID array`);
  requireThat(new Set(actual).size === actual.length, `${label}: duplicate IDs`);
  requireThat(equal(sorted(expected), sorted(actual)), `${label}: missing or unexpected IDs`);
}
function jsonString(value, ascii) {
  const text = JSON.stringify(value);
  return ascii ? text.replace(/[\u007f-\uffff]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`) : text;
}
/** Canonicalize raw JSON without losing the source's integer/float distinction. */
export function canonicalRawJson(text, { ascii = false } = {}) {
  let i = 0;
  const ws = () => { while (/\s/.test(text[i] ?? '') && i < text.length) i++; };
  function string() {
    const start = i++;
    while (i < text.length) {
      if (text[i] === '\\') { i += 2; continue; }
      if (text[i++] === '"') return JSON.parse(text.slice(start, i));
    }
    fail('Unterminated JSON string');
  }
  function value() {
    ws(); const c = text[i];
    if (c === '"') return jsonString(string(), ascii);
    if (c === '[') {
      i++; ws(); const values = [];
      if (text[i] !== ']') while (true) { values.push(value()); ws(); if (text[i] !== ',') break; i++; }
      requireThat(text[i++] === ']', 'Invalid JSON array'); return `[${values.join(',')}]`;
    }
    if (c === '{') {
      i++; ws(); const values = new Map();
      if (text[i] !== '}') while (true) {
        ws(); requireThat(text[i] === '"', 'Invalid JSON object key'); const key = string();
        requireThat(!values.has(key), 'Duplicate JSON object key'); ws(); requireThat(text[i++] === ':', 'Invalid JSON object');
        values.set(key, value()); ws(); if (text[i] !== ',') break; i++;
      }
      requireThat(text[i++] === '}', 'Invalid JSON object end');
      return `{${sorted(values.keys()).map(k => `${jsonString(k, ascii)}:${values.get(k)}`).join(',')}}`;
    }
    const token = /^(?:-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)/.exec(text.slice(i))?.[0];
    requireThat(token, 'Invalid JSON token'); i += token.length; return token;
  }
  const result = value(); ws(); requireThat(i === text.length, 'Trailing JSON data'); return result;
}
/** Return exact value spans in a top-level object/array without reserializing. */
export function rawEntries(text) {
  let i = 0; const ws = () => { while (i < text.length && /\s/.test(text[i])) i++; };
  function end() {
    ws(); const c = text[i];
    if (c === '"') { i++; while (i < text.length) { if (text[i] === '\\') i += 2; else if (text[i++] === '"') return; } fail('Unterminated JSON string'); }
    if (c === '[' || c === '{') {
      const close = c === '[' ? ']' : '}'; i++;
      while (i < text.length) { ws(); if (text[i] === close) { i++; return; } if (text[i] === ',' || text[i] === ':') i++; else end(); }
      fail('Unterminated JSON compound value');
    }
    while (i < text.length && !/[\s,\]}]/.test(text[i])) i++;
  }
  ws(); const type = text[i++]; requireThat(type === '{' || type === '[', 'Expected raw object or array');
  const out = []; let index = 0; const close = type === '{' ? '}' : ']';
  while (true) {
    ws(); if (text[i] === close) { i++; break; }
    let key = index++;
    if (type === '{') { const start = i; end(); key = JSON.parse(text.slice(start, i)); ws(); requireThat(text[i++] === ':', 'Invalid raw object'); }
    ws(); const start = i; end(); out.push([key, text.slice(start, i)]); ws();
    if (text[i] === close) { i++; break; } requireThat(text[i++] === ',', 'Invalid raw separator');
  }
  ws(); requireThat(i === text.length, 'Trailing raw JSON'); return out;
}
function chainFor(parent, groups) {
  const chain = [], seen = new Set();
  while (parent != null) {
    requireThat(!seen.has(parent), `Cyclic hierarchy: ${parent}`); seen.add(parent);
    const group = groups.get(parent); requireThat(group, `Missing parent: ${parent}`);
    chain.push(parent); parent = group.parent_id;
  }
  requireThat(equal(chain.map(id => groups.get(id).level), TIERS), 'Incomplete/nonadjacent location parent chain');
  return chain;
}
function policyEntries(report) {
  if (report.source_policy_assessments) return report.source_policy_assessments.map(p => [p.iso, p.policy]);
  if (report.territory_matrix) return report.territory_matrix.flatMap(t => Object.entries(t.policy_profiles ?? {}).filter(([, policy]) => policy));
  return (report.countries ?? []).flatMap(c => c.source_policy ? [[c.iso, c.source_policy]] : []);
}
function ownerRows(report) { return report.reference_owner_crosswalk ?? report.territory_matrix ?? report.countries ?? []; }
function ownerLabel(row) { return row.owner ?? row.reference_owner; }
function statusOf(row, group = false) { return group ? row.branch_semantic_status ?? row.status : row.semantic_status ?? row.status; }

/** Pure exhaustive gate; the reader separately verifies source-file hashes. */
export function validateFollowupSnapshot({ hierarchy, locations, reports, worldReview, policies, frozen, migrations, closure, groupRecordHashes = new Map(), expectedCounts = null }) {
  const groups = new Map(hierarchy.map(g => [g.id, g])); requireThat(groups.size === hierarchy.length, 'Duplicate active parent ID');
  exactIds(CONTINENTS, hierarchy.filter(g => g.level === 'continent').map(g => g.name), 'Six active continents');
  const byId = new Map(locations.map(loc => [loc.id, loc])); requireThat(byId.size === locations.length, 'Duplicate active location ID');
  requireThat([...groups.keys()].every(id => !byId.has(id)), 'Location and parent identities overlap');
  const children = new Map(hierarchy.map(g => [g.id, []]));
  const groupMembers = new Map(hierarchy.map(g => [g.id, []]));
  for (const g of hierarchy) if (g.parent_id != null) { requireThat(children.has(g.parent_id), `Missing group parent: ${g.id}`); children.get(g.parent_id).push(g.id); }
  for (const loc of locations) {
    loc.chain = chainFor(loc.parent_id, groups); loc.continent = groups.get(loc.chain.at(-1)).name;
    requireThat(CONTINENTS.includes(loc.continent), `Unexpected continent: ${loc.continent}`); children.get(loc.parent_id).push(loc.id);
    for (const parent of loc.chain) groupMembers.get(parent).push(loc.id);
  }
  const owners = new Set(locations.map(loc => loc.owner));
  exactIds(CONTINENTS, reports.map(r => r.continent), 'Six continent reports');
  const locationPartition = [], groupPartition = [], profiles = new Set(), continentResults = [];
  for (const report of reports) {
    requireThat(report.semantic_complete === false, `${report.continent}: report must preserve unfinished semantic status`);
    for (const flag of ['active_geography_modified', 'historical_claims_modified', 'active_geography_changed', 'historical_claims_changed']) requireThat(report[flag] !== true, `${report.continent}: unexpected mutation claim`);
    const current = locations.filter(loc => loc.continent === report.continent), currentIds = current.map(l => l.id);
    const currentGroups = hierarchy.filter(g => {
      let parent = g; const seen = new Set();
      while (parent.parent_id != null) { requireThat(!seen.has(parent.id), `Cyclic group ${g.id}`); seen.add(parent.id); parent = groups.get(parent.parent_id); }
      return parent.name === report.continent;
    });
    exactIds(currentIds, report.locations.map(r => r.id), `${report.continent} location inventory`);
    exactIds(currentGroups.map(g => g.id), report.groups.map(r => r.id), `${report.continent} parent inventory`);
    const byOwner = new Map(); for (const loc of current) { if (!byOwner.has(loc.owner)) byOwner.set(loc.owner, []); byOwner.get(loc.owner).push(loc.id); }
    exactIds([...byOwner.keys()], ownerRows(report).map(ownerLabel), `${report.continent} owner crosswalk`);
    for (const row of ownerRows(report)) {
      const ids = byOwner.get(ownerLabel(row));
      if (row.location_ids) exactIds(ids, row.location_ids, `${report.continent}/${ownerLabel(row)} owner IDs`);
      else requireThat((row.location_count ?? row.count) === ids.length, `${report.continent} owner count mismatch`);
    }
    for (const [iso, policy] of policyEntries(report)) { requireThat(policies[iso] && equal(JSON.parse(canonicalRawJson(JSON.stringify(policy))), JSON.parse(canonicalRawJson(JSON.stringify(policies[iso])))), `Stale or unexpected policy: ${iso}`); profiles.add(iso); }
    const localStatus = {}, groupStatus = {};
    for (const row of report.locations) {
      const actual = byId.get(row.id); const parent = row.parent_id ?? row.province_id;
      if (actual.name != null) requireThat(row.name === actual.name, `Stale location name: ${row.id}`);
      requireThat(parent === actual.parent_id, `Stale location parent: ${row.id}`);
      if (row.parent_chain) requireThat(equal(row.parent_chain, actual.chain), `Stale location chain: ${row.id}`);
      if (row.chain) requireThat(equal(row.chain, [...actual.chain].reverse()), `Stale reversed chain: ${row.id}`);
      requireThat((row.owner_reference ?? row.reference_owner) === actual.owner, `Stale reference owner: ${row.id}`);
      requireThat((row.geometry_sha256 ?? row.footprint_sha256) === actual.footprint_sha256, `Stale location footprint: ${row.id}`);
      if (actual.source) for (const [key, field] of [['source_id', 'id'], ['source_url', 'url'], ['source_role', 'declaredRole'], ['declared_role', 'declaredRole'], ['reference_year', 'referenceYear'], ['source_year', 'year'], ['license', 'license']]) {
        if (Object.hasOwn(row, key)) requireThat((row[key] ?? null) === (actual.source[field] ?? null), `Stale location source ${key}: ${row.id}`);
      }
      requireThat(statusOf(row) === closure.locations.get(row.id)?.status, `Unsubstantiated semantic location status: ${row.id}`);
      localStatus[statusOf(row)] = (localStatus[statusOf(row)] ?? 0) + 1; locationPartition.push(row.id);
    }
    for (const row of report.groups) {
      const actual = groups.get(row.id); requireThat(row.name === actual.name && row.level === actual.level && row.parent_id === actual.parent_id, `Stale parent unit: ${row.id}`);
      exactIds(children.get(row.id), row.children ?? row.child_ids, `Direct children: ${row.id}`);
      const members = sorted(groupMembers.get(row.id)); requireThat(members.length > 0, `Empty parent footprint: ${row.id}`);
      if (row.member_location_ids) exactIds(members, row.member_location_ids, `Member locations: ${row.id}`);
      if (row.membership_sha256) requireThat(row.membership_sha256 === hash(JSON.stringify(members)), `Stale membership hash: ${row.id}`);
      if (row.footprint_sha256) requireThat(row.footprint_sha256 === hash(canonicalRawJson(JSON.stringify(members.map(id => [id, byId.get(id).footprint_sha256])), { ascii: true })), `Stale parent footprint: ${row.id}`);
      if (row.record_sha256) requireThat(row.record_sha256 === groupRecordHashes.get(row.id), `Stale parent record: ${row.id}`);
      requireThat((row.descendant_location_count ?? row.locations ?? row.members) === members.length, `Stale descendant count: ${row.id}`);
      requireThat(statusOf(row, true) === closure.groups.get(row.id)?.status, `Unsubstantiated semantic parent status: ${row.id}`);
      groupStatus[statusOf(row, true)] = (groupStatus[statusOf(row, true)] ?? 0) + 1; groupPartition.push(row.id);
    }
    const previous = frozen[report.continent]; requireThat(previous, `Missing frozen inventory: ${report.continent}`);
    const prior = new Set(previous.inventory.location_ids), currentSet = new Set(currentIds);
    const lost = sorted([...prior].filter(id => !currentSet.has(id))), added = sorted(currentIds.filter(id => !prior.has(id)));
    const reconciliation = report.previous_snapshot_reconciliation ?? report.retained_inspection_reconciliation;
    if (reconciliation) {
      exactIds(lost, reconciliation.old_only_location_ids ?? reconciliation.prior_ids_outside_current_europe ?? reconciliation.prior_location_ids_not_current ?? reconciliation.removed_current_ids ?? reconciliation.retired_or_replaced_location_ids, `${report.continent} prior/current removed IDs`);
      exactIds(added, reconciliation.current_only_location_ids ?? reconciliation.added_current_ids ?? reconciliation.current_location_ids_not_prior ?? reconciliation.new_location_ids, `${report.continent} prior/current added IDs`);
      if (reconciliation.old_location_ids) exactIds(prior, reconciliation.old_location_ids, `${report.continent} frozen location IDs`);
      if (reconciliation.current_location_ids) exactIds(currentIds, reconciliation.current_location_ids, `${report.continent} current reconciliation IDs`);
      if (reconciliation.retained_location_ids) exactIds(currentIds.filter(id => prior.has(id)), reconciliation.retained_location_ids, `${report.continent} retained reconciliation IDs`);
    }
    const priorGroups = new Set(previous.inventory.group_ids), currentGroupIds = currentGroups.map(g => g.id), currentGroupSet = new Set(currentGroupIds);
    const lostGroups = sorted([...priorGroups].filter(id => !currentGroupSet.has(id))), addedGroups = sorted(currentGroupIds.filter(id => !priorGroups.has(id)));
    const groupReconciliation = report.inventory_delta_from_frozen_africa_review ?? reconciliation;
    if (groupReconciliation) {
      const declaredRemoved = groupReconciliation.previous_group_ids_not_current ?? groupReconciliation.prior_group_ids_outside_current_europe ?? groupReconciliation.retired_or_replaced_group_ids;
      const declaredAdded = groupReconciliation.current_group_ids_not_previous ?? groupReconciliation.added_current_group_ids ?? groupReconciliation.new_group_ids;
      if (declaredRemoved) exactIds(lostGroups, declaredRemoved, `${report.continent} removed parent reconciliation`);
      if (declaredAdded) exactIds(addedGroups, declaredAdded, `${report.continent} added parent reconciliation`);
    }
    for (const id of lost.filter(id => byId.has(id))) {
      const change = migrations.chainChanges?.get(id);
      if (migrations.chainChanges) requireThat(change && equal(change.after_chain.map(r => r.id), byId.get(id).chain), `Moved continent ID lacks exact dated-independent migration chain: ${id}`);
    }
    const declaredCounts = report.counts ?? report.summary;
    requireThat(declaredCounts.locations === current.length && declaredCounts.groups === currentGroups.length, `${report.continent}: stale summary counts`);
    if (declaredCounts.independently_approved_locations != null) requireThat(declaredCounts.independently_approved_locations === (localStatus.supported ?? 0), `${report.continent}: unsupported location approval count`);
    if (declaredCounts.independently_approved_branches != null) requireThat(declaredCounts.independently_approved_branches === (groupStatus.supported ?? 0), `${report.continent}: unsupported branch approval count`);
    continentResults.push({ continent: report.continent, locations: current.length, groups: currentGroups.length, owner_labels: byOwner.size, location_status_counts: localStatus, group_status_counts: groupStatus, prior_ids_outside_current_continent: lost.length, current_ids_not_in_prior_continent: added.length });
  }
  exactIds(byId.keys(), locationPartition, 'Global location partition'); exactIds(groups.keys(), groupPartition, 'Global parent partition');
  exactIds(Object.keys(policies), [...profiles], 'Global source-policy coverage');
  requireThat(worldReview.territories.length === owners.size, 'Reference-owner count mismatch'); exactIds(owners, worldReview.territories.map(t => t.owner), 'Canonical owner crosswalk');
  exactIds(Object.keys(policies), Object.keys(worldReview.policy_crosswalk), 'Canonical policy crosswalk');
  for (const [iso, labels] of Object.entries(worldReview.policy_crosswalk)) { requireThat(labels.length > 0 && labels.every(label => owners.has(label)), `Invalid canonical profile/owner crosswalk: ${iso}`); exactIds(labels, closure.policy_crosswalk[iso], `Closure profile crosswalk: ${iso}`); }
  const oldLocations = new Set(Object.values(frozen).flatMap(r => r.inventory.location_ids)), oldGroups = new Set(Object.values(frozen).flatMap(r => r.inventory.group_ids));
  const removedLocations = sorted([...oldLocations].filter(id => !byId.has(id))), newLocations = sorted([...byId.keys()].filter(id => !oldLocations.has(id)));
  const removedGroups = sorted([...oldGroups].filter(id => !groups.has(id))), newGroups = sorted([...groups.keys()].filter(id => !oldGroups.has(id)));
  for (const id of removedLocations) requireThat(migrations.retiredLocations.has(id), `Prior location missing retirement receipt: ${id}`);
  for (const id of newLocations) requireThat(migrations.createdLocations.has(id), `New location missing creation receipt: ${id}`);
  for (const id of removedGroups) requireThat(migrations.retiredGroups.has(id), `Prior parent missing retirement archive: ${id}`);
  for (const id of newGroups) requireThat(migrations.createdGroups.has(id), `New parent missing creation receipt: ${id}`);
  const counts = { locations: locations.length, groups: hierarchy.length, reference_owner_groups: owners.size, policy_profiles: Object.keys(policies).length };
  if (expectedCounts) requireThat(equal(counts, expectedCounts), 'Unexpected published baseline counts');
  return { version: 1, status: 'passed-inventory-and-provenance-consistency', semantic_complete: false, approvals_created: 0, corrections_installed: 0, counts, continents: continentResults, unique_global_partition: true, complete_adjacent_tier_chains: true, prior_current_identity_accounting: { frozen_locations: oldLocations.size, frozen_groups: oldGroups.size, retired_location_ids: removedLocations, new_location_ids: newLocations, retired_group_ids: removedGroups, new_group_ids: newGroups, every_changed_id_has_existing_receipt: true }, limitation: 'This gate checks inventories, current memberships, footprints, source pins and previous/current identity accounting. It neither approves local geographic purpose nor proves new geometry, current law, source completeness or historical accuracy.' };
}

export async function validateSemanticFollowup(root, { expectedCounts = { locations: 49589, groups: 5705, reference_owner_groups: 250, policy_profiles: 201 } } = {}) {
  root = resolve(root); const fileHashes = new Map(), reportSizes = new Set();
  function safePath(path) { const absolute = resolve(root, path); requireThat(!relative(root, absolute).startsWith(`..${sep}`) && relative(root, absolute) !== '..', 'Source path escapes repository'); return absolute; }
  let membershipProjection=null;
  try {membershipProjection=JSON.parse(gunzipSync(await readFile(safePath('data/macro-foundation/current-membership-projection.json.gz'))));} catch(error){if(error.code!=='ENOENT')throw error;}
  const physicalHashes=new Map();
  async function bytes(path) {
    const retained=membershipProjection?.baseline_files?.[path],actualPath=retained?.archive_path??path,raw=await readFile(safePath(actualPath));physicalHashes.set(actualPath,hash(raw));
    let body=raw;
    if(retained){requireThat(retained.compression==='gzip'&&hash(raw)===retained.archive_sha256,'Retained inspection archive differs from its original byte proof');body=gunzipSync(raw);requireThat(hash(body)===retained.original_sha256,'Retained inspection archive does not reconstruct exact original bytes');}
    fileHashes.set(path, hash(body));return body;
  }
  async function read(path) { const body = await bytes(path); return JSON.parse((path.endsWith('.gz') ? gunzipSync(body) : body).toString('utf8')); }
  async function pinned(path, expected) { requireThat(HEX.test(expected), `Invalid source hash: ${path}`); const actual = fileHashes.get(path) ?? hash(await bytes(path)); requireThat(actual === expected, `Stale source hash: ${path}`); }
  const reports = [];
  for (const name of CONTINENTS) {
    const path = LEDGERS[name]; let body;
    try { body = await bytes(path); } catch (error) { if (error.code === 'ENOENT') fail(`Missing continent follow-up: ${path}`); throw error; }
    requireThat(body.readUInt32LE(4) === 0, `Nondeterministic gzip timestamp: ${path}`);
    reportSizes.add(body.byteLength);
    const report = JSON.parse(gunzipSync(body)); requireThat(report.continent === name, `Incorrect continent label: ${path}`); reports.push(report);
    for (const [input, expected] of Object.entries(report.input_sha256 ?? {})) await pinned(input.startsWith('data/') ? input : `data/${input}`, expected);
    const producer = report.producer_sha256 ?? report.code_sha256;
    if (producer) {
      const script = ['Asia', 'Oceania'].includes(name) ? 'scripts/audit-asia-oceania-semantic-followup.py' : ['North America', 'South America'].includes(name) ? 'scripts/audit-americas-semantic-followup.py' : `scripts/audit-${name.toLowerCase().replaceAll(' ', '-')}-semantic-followup.py`;
      await pinned(script, producer);
    }
  }
  const hierarchyText = (await bytes('data/hierarchy.json')).toString('utf8'), hierarchy = JSON.parse(hierarchyText);
  const groupRecordHashes = new Map(rawEntries(hierarchyText).map(([, raw]) => [JSON.parse(raw).id, hash(canonicalRawJson(raw))]));
  const index = await read('data/world-index.json'), locations = [];
  for (const part of index.parts) {
    const path = `data/${part}`, text = (await bytes(path)).toString('utf8'); const parsed = JSON.parse(text);
    const featuresRaw = rawEntries(text).find(([key]) => key === 'features')?.[1]; requireThat(featuresRaw, `Missing feature collection: ${path}`);
    const rawFeatures = rawEntries(featuresRaw); requireThat(rawFeatures.length === parsed.features.length, `Raw/parsed feature mismatch: ${path}`);
    for (let i = 0; i < parsed.features.length; i++) {
      const feature = parsed.features[i], props = feature.properties, geometry = rawEntries(rawFeatures[i][1]).find(([key]) => key === 'geometry')?.[1];
      requireThat(geometry, `Missing location footprint: ${feature.id}`);
      const metadata = props.metadata ?? {};
      locations.push({ id: feature.id, name: props.name, parent_id: props.parent_id, owner: props.reference_owner, source: { id: metadata.source_id, url: metadata.source_url, declaredRole: metadata.source_role, referenceYear: metadata.reference_year, year: metadata.reference_year || metadata.location_source_date, license: metadata.license }, footprint_sha256: hash(canonicalRawJson(geometry, { ascii: true })) });
    }
  }
  const worldReview = await read('data/world-review.json'), policies = (await read('data/location-policy.json')).countries;
  const closureRaw = await read('data/global-semantic-closure.json.gz');
  for (const [path, expected] of Object.entries(closureRaw.input_sha256)) await pinned(`data/${path}`, expected);
  const closure = { locations: new Map(closureRaw.locations.map(r => [r.id, { status: r.status, footprint_sha256: r.footprint_sha256 }])), groups: new Map(closureRaw.groups.map(r => [r.id, { status: r.status, footprint_sha256: r.footprint_sha256 }])), policy_crosswalk: closureRaw.policy_crosswalk };
  exactIds(locations.map(r => r.id), [...closure.locations.keys()], 'Closure current location inventory');
  exactIds(hierarchy.map(r => r.id), [...closure.groups.keys()], 'Closure current parent inventory');
  for (const location of locations) requireThat(location.footprint_sha256 === closure.locations.get(location.id).footprint_sha256, `Committed geometry/closure hash mismatch: ${location.id}`);
  const frozen = Object.fromEntries(await Promise.all(CONTINENTS.map(async name => [name, await read(`data/geographic-decisions/${name.toLowerCase().replaceAll(' ', '-')}.json`)])));
  const decision = await read('data/geographic-decision-migration.json.gz'), macro = await read('data/macro-boundary-migration.json.gz'), repair = await read('data/geographic-repair-evidence/migration-receipt.json.gz');
  const migrations = {
    retiredLocations: new Set(repair.removed_ids), createdLocations: new Set(repair.added_ids),
    retiredGroups: new Set([...decision.retired_units, ...repair.retired_units, ...macro.retired_units].map(r => r.id)),
    createdGroups: new Set([...decision.group_changes, ...macro.group_changes].filter(r => !r.before && r.after).map(r => r.id)),
    chainChanges: new Map(macro.location_chain_crosswalk.map(r => [r.location_id, r])),
  };
  const retiredArchiveIds = new Set(repair.archives.map(r => r.id ?? r.properties?.id));
  for (const id of repair.removed_ids) requireThat(retiredArchiveIds.has(id), `Missing original location archive in repair receipt: ${id}`);
  const result = validateFollowupSnapshot({ hierarchy, locations, reports, worldReview, policies, frozen, migrations, closure, groupRecordHashes, expectedCounts });
  const admin = await read('data/administrative-sources.json'), currentLocationsById = new Map(locations.map(row => [row.id, row])); let declaredSourceHashes = 0, retainedSourceBytesVerified = 0, diagnosticContextsVerified = 0, evidenceHashDeclarations = 0;
  function validateEvidenceHashes(value, context) {
    if (Array.isArray(value)) { for (const item of value) validateEvidenceHashes(item, context); return; }
    if (!value || typeof value !== 'object') return;
    for (const [key, item] of Object.entries(value)) {
      if ((key === 'sha256' || key.endsWith('_sha256')) && typeof item === 'string') { requireThat(HEX.test(item), `Invalid declared evidence hash: ${context}/${key}`); evidenceHashDeclarations++; }
      else if (item && typeof item === 'object') validateEvidenceHashes(item, `${context}/${key}`);
    }
  }
  for (const report of reports) {
    validateEvidenceHashes(report.source_evidence, report.continent);
    validateEvidenceHashes(report.source_research, report.continent);
    validateEvidenceHashes(report.upstream_source_research, report.continent);
    for (const [path, expected] of Object.entries(report.source_evidence?.diagnostics?.additional_input_sha256 ?? {})) await pinned(path.startsWith('data/') ? path : `data/${path}`, expected);
    for (const [id, diagnostic] of Object.entries(report.source_evidence?.original_parent_geometry_diagnostics ?? {})) {
      requireThat(diagnostic.current_group_footprint_sha256 === closure.groups.get(id)?.footprint_sha256, `Stale original-parent diagnostic context: ${id}`); diagnosticContextsVerified++;
      for (const candidate of diagnostic.original_parent_candidates ?? []) for (const member of candidate.member_matches ?? []) {
        const location = currentLocationsById.get(member.id);
        requireThat(location?.chain.includes(id), `Original-parent diagnostic references a nonmember: ${member.id}`);
      }
    }
    for (const diagnostic of report.source_evidence?.diagnostics?.cases ?? []) if (diagnostic.current_geometry_sha256) {
      requireThat(diagnostic.current_geometry_sha256 === closure.locations.get(diagnostic.id)?.footprint_sha256, `Stale source geometry diagnostic context: ${diagnostic.id}`); diagnosticContextsVerified++;
    }
    for (const [id, receipt] of Object.entries(report.source_geometry_receipts ?? {})) {
      if (!receipt.sha256) continue; requireThat(HEX.test(receipt.sha256), `Invalid source geometry declaration: ${id}`); declaredSourceHashes++;
      if (admin[id]?.sha256) requireThat(receipt.sha256 === admin[id].sha256, `Source receipt differs from pinned metadata: ${id}`);
      if (receipt.tracked_source_file) {
        const path = receipt.tracked_source_file.startsWith('data/') ? receipt.tracked_source_file : `data/${receipt.tracked_source_file}`;
        const body = await bytes(path), decoded = path.endsWith('.gz') ? gunzipSync(body) : body;
        requireThat(hash(decoded) === receipt.sha256, `Retained source geometry byte mismatch: ${id}`); retainedSourceBytesVerified++;
      }
    }
  }
  result.report_sha256 = Object.fromEntries(CONTINENTS.map(name => [name, fileHashes.get(LEDGERS[name])]));
  const reportHashes = new Set(Object.values(result.report_sha256));
  let assetRoot = null;
  for (const path of ['dist/client', 'dist']) {
    try { if ((await stat(safePath(path))).isDirectory()) { assetRoot = path; break; } } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  let assetFilesChecked = 0;
  async function inspectAssets(path) {
    for (const entry of await readdir(safePath(path), { withFileTypes: true })) {
      const child = `${path}/${entry.name}`;
      requireThat(!child.includes('/geographic-semantic-followup/'), `Full semantic follow-up ledger directory is a deployment asset: ${child}`);
      if (entry.isDirectory()) await inspectAssets(child);
      else if (entry.isFile()) {
        assetFilesChecked++; const size = (await stat(safePath(child))).size;
        if (reportSizes.has(size)) requireThat(!reportHashes.has(hash(await readFile(safePath(child)))), `Full semantic follow-up ledger is a deployment asset: ${child}`);
      }
    }
  }
  if (assetRoot) await inspectAssets(assetRoot);
  result.deployment_asset_check = { existing_tree: assetRoot, files_checked: assetFilesChecked, full_followup_ledgers_found: 0, limitation: assetRoot ? 'Checks the existing asset tree only; rerun after future builds.' : 'No deployment artifact exists in this checkout; no build or publication was performed.' };
  result.source_verification = { current_repository_files_hashed: fileHashes.size, source_geometry_hash_declarations_checked: declaredSourceHashes, evidence_hash_declarations_format_checked: evidenceHashDeclarations, diagnostic_current_footprint_contexts_verified: diagnosticContextsVerified, retained_source_geometry_bytes_verified: retainedSourceBytesVerified, external_response_bytes_refetched: 0, limitation: 'External response/source hashes whose original bytes are not committed remain declarations. This validation neither refetches public sources nor claims unavailable original bytes were verified.' };
  result.critical_input_sha256 = Object.fromEntries(['data/hierarchy.json', 'data/world-index.json', 'data/world-review.json', 'data/location-policy.json', 'data/global-semantic-closure.json.gz', 'data/geographic-decision-migration.json.gz', 'data/macro-boundary-migration.json.gz', 'data/geographic-repair-evidence/migration-receipt.json.gz'].map(path => [path, fileHashes.get(path)]));
  if(membershipProjection){
    const currentHierarchyRaw=await readFile(safePath('data/hierarchy.json')),currentIndexRaw=await readFile(safePath('data/world-index.json')),currentHierarchy=JSON.parse(currentHierarchyRaw),currentIndex=JSON.parse(currentIndexRaw),currentFeatures=[];
    for(const part of currentIndex.parts)currentFeatures.push(...JSON.parse(await readFile(safePath(`data/${part}`))).features);
    const currentLocations=currentFeatures.map(feature=>({id:feature.id,name:feature.properties.name,parent_id:feature.properties.parent_id,owner:feature.properties.reference_owner}));
    const projected=validateMacroReviewProjection({projection:membershipProjection,hierarchy:currentHierarchy,locations:currentLocations,baselineHierarchy:hierarchy,baselineLocations:locations,predecessorProjections:loadProjectionPredecessors({data:resolve(root,'data'),projection:membershipProjection}),currentPins:{hierarchy_sha256:hash(currentHierarchyRaw),location_index_sha256:hash(currentIndexRaw),footprints_sha256:footprintHash(currentFeatures)}});
    for(const receipt of membershipProjection.crosswalks){const raw=await readFile(safePath(receipt.path));requireThat(hash(raw)===receipt.sha256,'Current membership projection receipt bytes changed');}
    result.retained_inspection_counts=result.counts;result.counts={...result.counts,locations:projected.counts.locations,groups:projected.counts.groups};result.current_membership_projection=projected;
    result.limitation+=' Original source inspections were checked against their exact archived baseline; current names/chains are a separately validated metadata projection, not a new inspection.';
  }
  for (const [path, expected] of physicalHashes) requireThat(hash(await readFile(safePath(path))) === expected, `Repository changed during validation: ${path}`);
  result.validator_sha256 = hash(await readFile(fileURLToPath(import.meta.url)));
  result.full_ledgers_are_deployment_assets = false;
  return result;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    const report = await validateSemanticFollowup(root); const target = resolve(root, report.current_membership_projection?'data/validation/macro-review-projection.json':'data/validation/geographic-semantic-followup.json');
    const text = `${JSON.stringify(report, null, 2)}\n`; requireThat(Buffer.byteLength(text) <= 128 * 1024, 'Validation summary exceeds bounded 128 KiB size');
    await mkdir(dirname(target), { recursive: true }); await writeFile(target, text);
    process.stdout.write(`${JSON.stringify({ status: report.status, counts: report.counts, semantic_complete: false, output: relative(root, target), bytes: Buffer.byteLength(text) })}\n`);
  } catch (error) { process.stderr.write(`Semantic follow-up validation failed: ${error.message}\n`); process.exitCode = 1; }
}
