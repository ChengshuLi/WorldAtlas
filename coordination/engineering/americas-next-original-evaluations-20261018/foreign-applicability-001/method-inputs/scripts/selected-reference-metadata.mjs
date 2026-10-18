// Apply existing, source-backed reference correction receipts to a selected
// native bank. This is metadata preparation/application, never a new native or
// geographic authority. Original scientific products and their pins stay literal.
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual as same} from 'node:util';
import {assertReferenceOnlyFeatureChange,assertReferenceOnlyLocationChange,projectReferenceOwners,
  originalNativeReference,scientificNativeSelection,validateReferenceMetadataHeader,validateMetadataRelationships} from '../src/reference-metadata.js';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const need = (value, message) => { if (!value) throw Error(message); };
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && /^[A-Za-z0-9_./-]+$/.test(value)
  && value.split('/').every(piece => piece && piece !== '.' && piece !== '..');
const identity = row => ({id: row.id, name: row.name, parent_id: row.parent_id, kind: row.level ?? row.kind});
const sorted = rows => rows.sort((a, b) => a.id.localeCompare(b.id));
const pinIdentity = pin => Object.fromEntries(['commit', 'path', 'mode', 'git_blob_oid', 'bytes', 'sha256',
  'encoding', 'decoded_bytes', 'decoded_sha256'].filter(key => Object.hasOwn(pin, key)).map(key => [key, pin[key]]));

function reader(read) {
  need(typeof read === 'function', 'Whole pinned reference metadata reader required');
  return pin => {
    need(pin && /^[a-f0-9]{40}$/.test(pin.commit ?? '') && safe(pin.path) && pin.mode === '100644'
      && /^[a-f0-9]{40}$/.test(pin.git_blob_oid ?? '') && Number.isSafeInteger(pin.bytes)
      && pin.bytes > 0 && pin.bytes <= 32 * 1024 * 1024 && hash(pin.sha256),
    'Complete ordinary whole reference metadata pin required');
    const raw = read(pin);
    need(Buffer.isBuffer(raw) && raw.length === pin.bytes && sha(raw) === pin.sha256
      && createHash('sha1').update('blob ' + raw.length + '\0').update(raw).digest('hex') === pin.git_blob_oid,
    'Whole reference metadata input differs');
    let decoded = raw;
    if (pin.encoding !== undefined) {
      need(pin.encoding === 'gzip' && Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0
        && pin.decoded_bytes <= 32 * 1024 * 1024 && hash(pin.decoded_sha256),
      'Bounded reference metadata decoding required');
      decoded = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes + 1});
      need(decoded.length === pin.decoded_bytes && sha(decoded) === pin.decoded_sha256,
        'Whole decoded reference metadata differs');
    }
    return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(decoded));
  };
}

function unitMap(rows) {
  need(Array.isArray(rows) && rows.length > 0 && rows.every(row => typeof row.id === 'string'),
    'Complete reference hierarchy required');
  const map = new Map(rows.map(row => [row.id, row]));
  need(map.size === rows.length, 'Duplicate reference hierarchy identity');
  return map;
}

function validateImmediateCounts(units,locations) {
  const counts=new Map();
  for(const row of [...units.values(),...locations.values()])counts.set(row.parent_id,(counts.get(row.parent_id)??0)+1);
  for(const row of units.values())if(row.metadata?.child_count!==undefined)
    need(Number.isSafeInteger(row.metadata.child_count)&&row.metadata.child_count===(counts.get(row.id)??0),
      'Reference hierarchy child_count differs from complete immediate membership');
}

function collapsedLocations(receipts) {
  const changes = new Map();
  for (const receipt of receipts) for (const change of receipt.changed_location_properties ?? []) {
    assertReferenceOnlyLocationChange(change.before_properties, change.after_properties);
    const prior = changes.get(change.location_id);
    need(!prior || same(prior.after_properties, change.before_properties),
      'Reference receipt chain replaces an intermediate complete location');
    changes.set(change.location_id, {location_id: change.location_id,
      before_properties: prior?.before_properties ?? change.before_properties, after_properties: change.after_properties});
  }
  return [...changes.values()].sort((a, b) => a.location_id.localeCompare(b.location_id));
}

function groupChanges(before, after) {
  return sorted([...new Set([...before.keys(), ...after.keys()])].filter(id => !same(before.get(id) ?? null, after.get(id) ?? null))
    .map(id => ({id, before: before.get(id) ?? null, after: after.get(id) ?? null})));
}

export function prepareReferenceMetadataProjection({selection, manifest, owners, reference, hierarchy, receipts, source_updates, read}) {
  const json = reader(read), before = unitMap(json(hierarchy.before)), after = unitMap(json(hierarchy.after));
  const values = receipts.map(json);
  const projection = {version: 1, kind: 'native-reference-metadata-projection-v1',
    native_selection: scientificNativeSelection(selection), native_reference: originalNativeReference(manifest), reference,
    original_owner_roster_sha256: manifest.original_assets?.bounds?.sha256, hierarchy, receipts, source_updates,
    location_changes: collapsedLocations(values), group_changes: groupChanges(before, after),
    provinces: [...after.values()].filter(row => row.level === 'province').map(row => row.id).sort()};
  validateReferenceMetadataProjection({projection, selection, manifest, owners, read});
  return projection;
}

export function validateReferenceMetadataProjection({projection, selection, manifest, owners, read, originalSources}) {
  const references = validateReferenceMetadataHeader(projection, {selection, manifest}), json = reader(read);
  const originalUnits = unitMap(json(projection.hierarchy.before)), finalUnits = unitMap(json(projection.hierarchy.after));
  const units = new Map(originalUnits), changes = projection.receipts.map(json);
  const allLocationChanges = collapsedLocations(changes);
  need(same(allLocationChanges, projection.location_changes)
    && same(groupChanges(originalUnits, finalUnits), projection.group_changes),
  'Reference projection changes differ from complete original/current records');
  const first = new Map(allLocationChanges.map(row => [row.location_id, row.before_properties]));
  const locations = new Map(owners.map(row => [row.id, {id: row.id, name: first.get(row.id)?.name ?? row.id,
    parent_id: row.province_id, kind: 'location'}]));
  need(locations.size === owners.length, 'Duplicate original metadata owner identity');
  validateImmediateCounts(units,locations);
  let hierarchy = references.native.hierarchy_sha256;
  for (let i = 0; i < changes.length; i++) {
    const receipt = changes[i];
    need(receipt.before_sha256 === hierarchy && hash(receipt.after_sha256)
      && receipt.footprints_sha256_before === references.native.footprints_sha256
      && receipt.footprints_sha256_after === references.native.footprints_sha256
      && receipt.reference_only === true && receipt.historical_claims_transferred === false
      && receipt.summary?.geometry_changes === 0 && Array.isArray(receipt.relationships),
    'Stale, reordered or non-metadata reference receipt');
    validateMetadataRelationships({beforeGroups: new Map([...units].map(([id, row]) => [id, identity(row)])),
      beforeLocations: locations, beforeUnitRecords: units, receipt, receiptSha256: projection.receipts[i].sha256});
    for (const change of receipt.group_changes ?? []) {
      if (change.after) units.set(change.id, change.after); else units.delete(change.id);
    }
    for (const change of receipt.changed_location_properties ?? []) locations.set(change.location_id,
      identity({...change.after_properties, kind: 'location'}));
    validateImmediateCounts(units,locations);
    hierarchy = receipt.after_sha256;
  }
  need(hierarchy === references.reference.hierarchy_sha256 && same(sorted([...units.values()]), sorted([...finalUnits.values()])),
    'Reference receipts do not reconstruct the exact current hierarchy');
  const provinces = [...finalUnits.values()].filter(row => row.level === 'province').map(row => row.id).sort();
  need(same(provinces, projection.provinces), 'Reference projection province inventory differs');
  const projectedOwners = projectReferenceOwners(owners, projection.location_changes, provinces);
  const updates = new Map(), seenChanges = new Set(), byChange = new Map(projection.location_changes.map(row => [row.location_id, row]));
  for (const update of projection.source_updates) {
    need(update && Object.keys(update).sort().join(',') === 'after,before,logical_path'
      && /^data\/geography\/[^/]+\.json$/.test(update.logical_path) && !updates.has(update.logical_path),
    'Duplicate or foreign metadata source update');
    if (originalSources) need(same(pinIdentity(update.before), pinIdentity(originalSources.get(update.logical_path) ?? {})),
      'Reference metadata update does not start at the actual selected source');
    const before = json(update.before), after = json(update.after);
    need(before?.type === 'FeatureCollection' && after?.type === 'FeatureCollection'
      && Array.isArray(before.features) && before.features.length > 0 && Array.isArray(after.features)
      && before.features.length === after.features.length
      && same({...before, features: null}, {...after, features: null}),
    'Reference metadata changes a complete source inventory');
    let actualChanges = 0;
    for (let i = 0; i < before.features.length; i++) {
      const old = before.features[i], current = after.features[i];
      assertReferenceOnlyFeatureChange(old, current);
      if (!same(old, current)) {
        const change = byChange.get(old.id);
        need(change && !seenChanges.has(old.id) && same(change.before_properties, old.properties)
          && same(change.after_properties, current.properties), 'Whole source contains an unreceipted metadata change');
        seenChanges.add(old.id); actualChanges++;
      }
    }
    need(actualChanges > 0, 'Reference metadata source update is vacuous');
    updates.set(update.logical_path, update);
  }
  need(seenChanges.size === byChange.size, 'Reference projection omits an actually changed whole source');
  return {projection, nativeReference: references.native, reference: references.reference,
    owners: projectedOwners, units: [...finalUnits.values()], sourceUpdates: updates};
}
