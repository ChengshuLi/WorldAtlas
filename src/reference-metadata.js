// Reference metadata is applied separately from the immutable native source.
// These projections confer no source, boundary, history or publication authority.
// Callers authenticate the existing correction receipt and complete input bytes.
const canonical = value => {
  if(Array.isArray(value))return value.map(canonical);
  if(value&&typeof value==='object'){
    if(![Object.prototype,null].includes(Object.getPrototypeOf(value)))throw Error('Non-JSON reference metadata object');
    return Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])]));
  }
  if(value===null||typeof value==='string'||typeof value==='boolean'||typeof value==='number'&&Number.isFinite(value))return value;
  throw Error('Nonfinite, missing or non-JSON reference metadata value');
};
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const need = (value, message) => { if (!value) throw Error(message); };
const text = value => typeof value === 'string' && value.length > 0;
const keys = (value, expected) => value && typeof value === 'object' && !Array.isArray(value)
  && same(Object.keys(value).sort(), [...expected].sort());
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const ordinaryPin = value => {
  const encoded=value?.encoding!==undefined;
  return keys(value,['commit','path','mode','git_blob_oid','bytes','sha256',...(encoded?['encoding','decoded_bytes','decoded_sha256']:[])])
    && /^[a-f0-9]{40}$/.test(value.commit??'') && typeof value.path==='string' && /^[A-Za-z0-9_./-]+$/.test(value.path)
    && value.path.split('/').every(part=>part&&part!=='.'&&part!=='..') && value.mode==='100644'
    && /^[a-f0-9]{40}$/.test(value.git_blob_oid??'') && Number.isSafeInteger(value.bytes)&&value.bytes>0&&hash(value.sha256)
    && (!encoded||value.encoding==='gzip'&&Number.isSafeInteger(value.decoded_bytes)&&value.decoded_bytes>0&&hash(value.decoded_sha256));
};
const reference = value => keys(value, ['id', 'footprints_sha256', 'hierarchy_sha256'])
  && typeof value.id === 'string' && value.id.startsWith('geography:')
  && hash(value.footprints_sha256) && hash(value.hierarchy_sha256);

export function originalNativeReference(manifest) {
  const value = {id: manifest?.geographic_release, footprints_sha256: manifest?.footprints_sha256,
    hierarchy_sha256: manifest?.hierarchy_sha256};
  need(reference(value), 'Complete original native reference required');
  return value;
}

// A metadata application pointer is not a new native/scientific selection.
// Original source, artifact authority, native words and rebind evidence retain
// their original identities. Applicability of the pointer is checked separately.
export function scientificNativeSelection(selection) {
  need(selection && typeof selection === 'object' && !Array.isArray(selection),
    'Complete original native selection required');
  const {additive_release, reference_projection, ...native} = selection;
  return native;
}

export function validateReferenceMetadataHeader(projection, {selection, manifest} = {}) {
  need(keys(projection, ['version', 'kind', 'native_selection', 'native_reference', 'reference',
    'original_owner_roster_sha256', 'hierarchy', 'receipts', 'source_updates', 'location_changes', 'group_changes', 'provinces'])
    && projection.version === 1 && projection.kind === 'native-reference-metadata-projection-v1',
  'Unsupported native reference metadata projection');
  const native = originalNativeReference(manifest);
  need(same(projection.native_selection, scientificNativeSelection(selection))
    && same(projection.native_reference, native) && reference(projection.reference)
    && projection.reference.footprints_sha256 === native.footprints_sha256
    && projection.reference.hierarchy_sha256 !== native.hierarchy_sha256
    && projection.reference.id !== native.id,
  'Reference metadata projection changes or misidentifies its original native selection');
  need(hash(projection.original_owner_roster_sha256)
    && projection.original_owner_roster_sha256 === manifest.original_assets?.bounds?.sha256,
  'Reference metadata projection changes the original owner roster');
  need(keys(projection.hierarchy, ['before', 'after']) && ordinaryPin(projection.hierarchy.before) && ordinaryPin(projection.hierarchy.after)
    && (projection.hierarchy.before.decoded_sha256 ?? projection.hierarchy.before.sha256) === native.hierarchy_sha256
    && (projection.hierarchy.after.decoded_sha256 ?? projection.hierarchy.after.sha256) === projection.reference.hierarchy_sha256,
  'Reference metadata projection hierarchy bytes differ');
  need(Array.isArray(projection.receipts) && projection.receipts.length > 0 && projection.receipts.every(ordinaryPin)
    && Array.isArray(projection.source_updates) && Array.isArray(projection.location_changes)
    && Array.isArray(projection.group_changes) && Array.isArray(projection.provinces)
    && projection.provinces.length > 0 && projection.provinces.every(text) && new Set(projection.provinces).size === projection.provinces.length
    && same(projection.provinces, [...projection.provinces].sort()),
  'Incomplete reference metadata projection');
  // This selected-native application route consumes the stock decision writer's
  // explicit correction history. Legacy macro receipts may change a parent
  // without that append, but they cannot be promoted into this current artifact
  // merely by copying their parent fields into an application pointer.
  for(const update of projection.source_updates)need(keys(update,['logical_path','before','after'])&&typeof update.logical_path==='string'
    && /^data\/geography\/[^/]+\.json$/.test(update.logical_path)&&ordinaryPin(update.before)&&ordinaryPin(update.after),
    'Incomplete reference metadata source pin');
  for(const change of projection.group_changes)need(keys(change,['id','before','after'])&&text(change.id)
    &&(change.before===null||change.before?.id===change.id)&&(change.after===null||change.after?.id===change.id),
    'Incomplete reference metadata group change');
  for (const change of projection.location_changes) {
    need(keys(change,['location_id','before_properties','after_properties'])&&change.location_id===change.before_properties?.id,
      'Incomplete reference metadata location change');
    assertReferenceOnlyLocationChange(change?.before_properties, change?.after_properties);
    if (change.before_properties.parent_id !== change.after_properties.parent_id)
      need((change.after_properties.metadata?.reference_corrections?.length ?? 0)
        > (change.before_properties.metadata?.reference_corrections?.length ?? 0),
      'Current reference parent requires its explicit sourced correction append');
  }
  return {native, reference: projection.reference};
}

// apply-geographic-decisions.py retains the original fallback/overlap metadata
// and appends an explicit correction. Permit only that exact append-only shape;
// ignoring all metadata would hide a source/name/identity or prior-history edit.
export function assertReferenceOnlyLocationChange(before, after) {
  need(before && after && text(before.id) && before.id === after.id,
    'Reference metadata location identity differs');
  const oldMetadata = before.metadata ?? {}, metadata = after.metadata ?? {};
  const oldCorrections = oldMetadata.reference_corrections ?? [];
  const corrections = metadata.reference_corrections ?? [];
  need(Array.isArray(oldCorrections) && Array.isArray(corrections)
    && corrections.length >= oldCorrections.length
    && same(oldCorrections, corrections.slice(0, oldCorrections.length)),
  'Reference correction history must retain the exact original prefix');
  const withoutAppliedParent = properties => {
    const result = {...properties, parent_id: null};
    if (Object.hasOwn(properties, 'metadata')) {
      const {reference_corrections, ...retained} = properties.metadata;
      result.metadata = retained;
    }
    return result;
  };
  need(same(withoutAppliedParent(before), withoutAppliedParent(after)),
    'Non-parent location mutation');
  need(text(before.parent_id) && text(after.parent_id), 'Missing reference parent identity');
  let parent = before.parent_id;
  for (const correction of corrections.slice(oldCorrections.length)) {
    need(keys(correction, ['id', 'action', 'current_name', 'current_parent_id', 'new_parent_id', 'rationale', 'evidence'])
      && correction.id === before.id && correction.action === 'reparent'
      && correction.current_name === before.name && correction.current_parent_id === parent
      && text(correction.new_parent_id) && correction.new_parent_id !== parent
      && text(correction.rationale) && Array.isArray(correction.evidence) && correction.evidence.length > 0
      && correction.evidence.every(row => keys(row, ['url', 'title', 'inspected_fact'])
        && /^https?:\/\//.test(row.url) && text(row.title) && text(row.inspected_fact)),
    'Reference correction append does not describe the exact sourced parent transition');
    parent = correction.new_parent_id;
  }
  if (corrections.length > oldCorrections.length)
    need(parent === after.parent_id, 'Reference correction history ends at a different parent');
}

// Catalog/API rows retain all source properties, with only the database's
// existing generated defaults. Never publish a corrected parent while dropping
// its correction history, original fallback metadata or any source property.
export function assertAppliedReferenceProperties(actual,expected) {
  need(actual&&expected&&typeof actual==='object'&&typeof expected==='object',
    'Current reference requires complete source properties');
  const application={...actual};
  if(!Object.hasOwn(expected,'active')&&application.active===1)delete application.active;
  if(!Object.hasOwn(expected,'reference_owner')&&application.reference_owner===null)delete application.reference_owner;
  if(!Object.hasOwn(expected,'metadata')&&application.metadata!==undefined&&same(application.metadata,{}))delete application.metadata;
  need(same(application,expected),'Current reference properties differ from the complete applied source');
}

export function assertReferenceOnlyFeatureChange(before, after) {
  need(before && after && before.id === after.id
    && same({...before, properties: null}, {...after, properties: null}),
  'Metadata projection changes original feature identity or geometry');
  assertReferenceOnlyLocationChange(before.properties, after.properties);
}

// Complete current feature properties are derived from the authenticated
// originals and exact receipted deltas. Geometry and non-properties fields are
// retained by reference; source bytes and their original hashes remain separate.
export function projectReferenceFeatures(features, changes) {
  need(Array.isArray(features) && features.length > 0 && Array.isArray(changes),
    'Complete reference feature inventory and explicit changes required');
  const byId = new Map(features.map(feature => [feature.id, feature]));
  need(byId.size === features.length && features.every(feature => text(feature.id)
    && feature.properties?.id === feature.id), 'Duplicate or missing reference feature identity');
  const updates = new Map();
  for (const change of changes) {
    const before = byId.get(change?.location_id);
    need(before && !updates.has(before.id) && same(before.properties, change.before_properties),
      'Reference location change has a duplicate, foreign or stale complete original');
    assertReferenceOnlyLocationChange(change.before_properties, change.after_properties);
    updates.set(before.id, {...before, properties: structuredClone(change.after_properties)});
  }
  return features.map(feature => updates.get(feature.id) ?? feature);
}

// The canonical ownership words address id/index, never a province label. This
// is the same parent/LUT projection used by install-macro-reference.gridProjection.
// Keep every original camera, bounds, ID and owner index while applying metadata.
export function projectReferenceOwners(owners, changes, provinces) {
  need(Array.isArray(owners) && owners.length > 0 && Array.isArray(changes)
    && Array.isArray(provinces) && provinces.length > 0
    && provinces.every(text) && new Set(provinces).size === provinces.length,
  'Complete original owners and current province inventory required');
  const ids = new Set(), byId = new Map(), indices = new Map(provinces.map((id, index) => [id, index + 1]));
  for (let i = 0; i < owners.length; i++) {
    const owner = owners[i];
    need(owner && text(owner.id) && !ids.has(owner.id) && owner.index === i + 1 && text(owner.province_id),
      'Duplicate, missing or noncanonical original reference owner');
    ids.add(owner.id); byId.set(owner.id, owner.province_id);
  }
  const changed = new Set();
  for (const change of changes) {
    const id = change?.location_id;
    need(byId.has(id) && !changed.has(id) && byId.get(id) === change.before_properties?.parent_id,
      'Reference owner change has a duplicate, foreign or stale original parent');
    assertReferenceOnlyLocationChange(change.before_properties, change.after_properties);
    need(id === change.before_properties.id, 'Reference owner and changed properties identities differ');
    changed.add(id); byId.set(id, change.after_properties.parent_id);
  }
  const used = new Set();
  const projected = owners.map(owner => {
    const province_id = byId.get(owner.id), province_index = indices.get(province_id);
    need(province_index !== undefined, 'Projected owner has an absent current province');
    used.add(province_id);
    return {...owner, province_id, province_index};
  });
  need(used.size === provinces.length, 'Current province inventory contains an empty or foreign province');
  return projected;
}

// Shared existing reference relationship validator, used by release preparation
// and current metadata application. Canonical values are compared directly.
const metadataTiers=['continent','subcontinent','region','area','province','location'];
const metadataContent=value=>JSON.stringify(canonical(value));
const metadataEqualIds=(a,b)=>a.size===b.size&&[...a].every(id=>b.has(id));
const metadataIdentity=row=>({id:row.id,name:row.name,parent_id:row.parent_id,kind:row.level??row.kind});
export function referenceDescendantInventory(groups,locations){
 const members=new Map([...groups.keys()].map(id=>[id,new Set()]));
 for(const group of groups.values()){
  const tier=metadataTiers.indexOf(group.kind);
  if(tier<0||tier===metadataTiers.length-1||tier===0&&group.parent_id!==null||tier>0&&groups.get(group.parent_id)?.kind!==metadataTiers[tier-1])throw Error('Metadata relationship has incomplete adjacent-tier group chains');
 }
 for(const location of locations.values()){
  if(location.kind!=='location')throw Error('Metadata relationship location identity has the wrong tier');
  let parent=location.parent_id;
  for(let tier=metadataTiers.length-2;tier>=0;tier--){
   const group=groups.get(parent);
   if(group?.kind!==metadataTiers[tier])throw Error('Metadata relationship has incomplete adjacent-tier location chains');
   members.get(parent).add(location.id);parent=group.parent_id;
  }
  if(parent!==null)throw Error('Metadata relationship continent has a parent');
 }
 if([...members.values()].some(ids=>!ids.size))throw Error('Metadata relationship has an empty active geographic group');
 return members;
}

/** Opt-in reference-only same-tier merges/splits, sourced creations and retirements. */
export function validateMetadataRelationships({beforeGroups,beforeLocations,beforeUnitRecords=null,receipt,receiptSha256,registry=null}){
 if(!Object.hasOwn(receipt,'relationships'))return [];
 if(!Array.isArray(receipt.relationships)||receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary?.geometry_changes!==0)throw Error('Metadata relationships require explicit reference-only evidence and zero history/geometry transfer');
 if(!/^[a-f0-9]{64}$/.test(receiptSha256??''))throw Error('Metadata relationship receipt hash is invalid');
 if(!Array.isArray(receipt.source_evidence)||!receipt.source_evidence.length||receipt.source_evidence.some(row=>!/^https?:\/\//.test(row.url??'')||!/^[a-f0-9]{64}$/.test(row.source_sha256??'')))throw Error('Metadata relationships require inspected source URLs and hashes');
 if(!Array.isArray(receipt.before_units)||receipt.before_units.some(row=>!row?.id)||new Set(receipt.before_units.map(row=>row.id)).size!==receipt.before_units.length)throw Error('Metadata relationships require the complete original unit archive');
 const archivedBefore=new Map(receipt.before_units.map(row=>[row.id,row]));
 if(!metadataEqualIds(new Set(archivedBefore.keys()),new Set(beforeGroups.keys()))||[...archivedBefore].some(([id,row])=>metadataContent(metadataIdentity(row))!==metadataContent(metadataIdentity(beforeGroups.get(id)))))throw Error('Metadata original unit archive differs from actual before identities');
 if(beforeUnitRecords&&(!metadataEqualIds(new Set(archivedBefore.keys()),new Set(beforeUnitRecords.keys()))||[...archivedBefore].some(([id,row])=>metadataContent(row)!==metadataContent(beforeUnitRecords.get(id)))))throw Error('Metadata original unit archive alters the exact retained before records');
 const groups=new Map(beforeGroups),locations=new Map(beforeLocations),deltas=new Map(),retired=new Set(),created=new Set();
 for(const delta of receipt.group_changes??[]){
  if(!delta?.id||deltas.has(delta.id))throw Error('Metadata group delta has an extra identity or altered original archive');
  if(!beforeGroups.has(delta.id)){
   if(delta.before!==null||!delta.after||delta.after.id!==delta.id||!metadataTiers.slice(1,-1).includes(delta.after.level??delta.after.kind))throw Error('New metadata group needs an explicit null before record and same-tier split receipt');
   if(registry?.has(delta.id)&&registry.get(delta.id).kind!==(delta.after.level??delta.after.kind))throw Error('New metadata group changes a registered stable identity tier');
   created.add(delta.id);groups.set(delta.id,metadataIdentity(delta.after));
  }else{
   if(!delta.before||delta.id!==delta.before.id||metadataContent(delta.before)!==metadataContent(archivedBefore.get(delta.id)))throw Error('Metadata group delta has an extra identity or altered original archive');
   if(delta.after){if(delta.id!==delta.after.id||(delta.after.level??delta.after.kind)!==beforeGroups.get(delta.id).kind)throw Error('Metadata group delta changes a stable identity tier');groups.set(delta.id,metadataIdentity(delta.after));}
   else{retired.add(delta.id);groups.delete(delta.id);}
  }
  deltas.set(delta.id,delta);
 }
 const archivedRetired=new Map();
 for(const row of receipt.retired_units??[]){if(!row?.id||archivedRetired.has(row.id))throw Error('Duplicate retired metadata unit archive');archivedRetired.set(row.id,row);}
 if(!metadataEqualIds(new Set(archivedRetired.keys()),retired)||[...archivedRetired].some(([id,row])=>metadataContent(row)!==metadataContent(archivedBefore.get(id))))throw Error('Retired metadata units must retain their complete exact original records');
 const changedLocations=new Set();
 for(const delta of receipt.changed_location_properties??[]){
  const old=beforeLocations.get(delta.location_id),p=delta.after_properties,b=delta.before_properties;
  if(!old||changedLocations.has(delta.location_id)||!p||!b||p.id!==old.id||b.id!==old.id||metadataContent(metadataIdentity({...b,kind:'location'}))!==metadataContent(metadataIdentity(old)))throw Error('Metadata location delta has an extra identity or mismatched original properties');
  changedLocations.add(old.id);locations.set(old.id,metadataIdentity({...p,kind:'location'}));
 }
 const beforeMembers=referenceDescendantInventory(beforeGroups,beforeLocations),afterMembers=referenceDescendantInventory(groups,locations),covered=new Set(),targets=new Map(),splits=new Map(),splitTargets=new Set(),createTargets=new Set(),oldTypes=new Map(),pairs=[];
 for(const relationship of receipt.relationships){
  const old=relationship?.old_entity_id,target=relationship?.new_entity_id,oldGroup=beforeGroups.get(old),survivor=groups.get(target),type=relationship?.change_type;
  if(!['merge','split','retire','create'].includes(type)||relationship.reference_only!==true||relationship.history_transfer!=='none')throw Error('Metadata relationship must be an explicit reference-only merge/split/retire/create without history transfer');
  if(type==='create'){
   if(old!==null||!created.has(target)||!survivor||createTargets.has(target)||splitTargets.has(target))throw Error('Metadata creation requires a unique new-group endpoint and explicit null old identity');
   const derived=relationship.derived_from_id;
   if(derived!==undefined&&(!beforeGroups.has(derived)||beforeGroups.get(derived).kind!==survivor.kind||registry&&(!registry.has(derived)||registry.get(derived).kind!==survivor.kind)))throw Error('Metadata creation derived-from identity must be an existing registered same-tier group');
   createTargets.add(target);pairs.push({old_entity_id:null,new_entity_id:target,change_type:type,receipt_sha256:receiptSha256,relationship,source_evidence:receipt.source_evidence});continue;
  }
  if(!retired.has(old)||!oldGroup||old===target||oldTypes.has(old)&&(oldTypes.get(old)!==type||type!=='split'))throw Error('Metadata relationship has extra, duplicate, unretired or missing endpoints');
  if(registry&&(!registry.get(old)||registry.get(old).kind!==oldGroup.kind))throw Error('Metadata relationship endpoints lack registered stable same-tier identities');
  oldTypes.set(old,type);covered.add(old);
  if(type==='retire'){
   if(target!==null||!['province','area'].includes(oldGroup.kind))throw Error('Explicit metadata retirement requires a null successor and a local province/area identity');
   for(const id of beforeMembers.get(old))if(!locations.has(id))throw Error('Metadata retirement cannot drop descendant locations');
  }else if(type==='merge'){
   if(!beforeGroups.has(target)||!survivor)throw Error('Metadata merge has extra, duplicate, unretired or missing endpoints');
   if(oldGroup.kind==='continent'||oldGroup.kind!==survivor.kind||oldGroup.parent_id!==beforeGroups.get(target).parent_id||survivor.parent_id!==beforeGroups.get(target).parent_id)throw Error('Metadata merge requires existing same-tier groups with the same unchanged adjacent-tier parent');
   if(registry&&(!registry.get(target)||registry.get(target).kind!==survivor.kind))throw Error('Metadata merge endpoints lack registered stable same-tier identities');
   if(!targets.has(target))targets.set(target,new Set(beforeMembers.get(target)));
   const union=targets.get(target);for(const id of beforeMembers.get(old)){if(union.has(id))throw Error('Metadata merge original member footprints overlap');union.add(id);}
  }else{
   if(!created.has(target)||!survivor||splitTargets.has(target)||createTargets.has(target))throw Error('Metadata split has extra, duplicate, or unreceipted successor endpoints');
   if(oldGroup.kind==='continent'||oldGroup.kind!==survivor.kind||survivor.parent_id!==oldGroup.parent_id||!groups.has(oldGroup.parent_id)||groups.get(oldGroup.parent_id).parent_id!==beforeGroups.get(oldGroup.parent_id)?.parent_id)throw Error('Metadata split requires same-tier successors under the same unchanged adjacent-tier parent');
   splitTargets.add(target);if(!splits.has(old))splits.set(old,[]);splits.get(old).push(target);
  }
  pairs.push({old_entity_id:old,new_entity_id:target,change_type:type,receipt_sha256:receiptSha256,relationship,source_evidence:receipt.source_evidence});
 }
 if(!metadataEqualIds(covered,retired))throw Error('Metadata crosswalk must account for every retired parent exactly once (or every explicit split successor)');
 if(!metadataEqualIds(new Set([...splitTargets,...createTargets]),created))throw Error('Every new metadata group requires exactly one explicit split successor or create relationship');
 for(const [target,union] of targets)if(!metadataEqualIds(union,afterMembers.get(target)))throw Error('Metadata merge must conserve the exact union of original descendant location footprints');
 for(const [old,successors] of splits){
  if(successors.length<2)throw Error('Metadata split requires at least two unique successors');
  const union=new Set();for(const target of successors)for(const id of afterMembers.get(target)){if(union.has(id))throw Error('Metadata split successor member footprints overlap');union.add(id);}
  if(!metadataEqualIds(union,beforeMembers.get(old)))throw Error('Metadata split must conserve the exact disjoint union of original descendant location footprints');
 }
 for(const pair of pairs.filter(pair=>['merge','split'].includes(pair.change_type))){const parent=beforeGroups.get(pair.old_entity_id).parent_id;if(!metadataEqualIds(beforeMembers.get(parent),afterMembers.get(parent)))throw Error('Metadata merge/split changes its containing parent footprint');}

 return pairs;
}
