import {createEntityRegistry, REGISTRY_SCHEMA, validateCategoryBindings} from './entity-registry.js';

// Only the historic V7 review uses low four bits for affiliation and bit 4 for
// source land. Never apply this decoding to the canonical location-ID grid.
export function registryFromV7Categories(categories, revision) {
  const entities = new Map(), seen = new Set();
  for (const category of categories) {
    const code = category.id;
    if (!Number.isInteger(code) || !((code >= 1 && code <= 10) || (code >= 17 && code <= 22)) || seen.has(code))
      throw Error('Invalid or duplicate V7 assignment code');
    seen.add(code);
    if (category.physical_class !== (code >= 17 ? 'land' : 'water'))
      throw Error(`V7 physical class mismatch: ${code}`);
    const id = code & 15, existing = entities.get(id);
    if (existing && existing.name !== category.name) throw Error(`Conflicting V7 entity names: ${id}`);
    entities.set(id, {id, name: category.name, level: 'continent', parent_id: null});
  }
  const snapshot = {
    schema_version: REGISTRY_SCHEMA, revision, status: 'draft',
    entities: [...entities.values()].sort((a, b) => a.id - b.id),
  };
  createEntityRegistry(snapshot);
  return snapshot;
}

export function withEntityRegistry(proposal, snapshot = null) {
  let bootstrap = false;
  if (!snapshot && proposal.entity_registry) snapshot = proposal.entity_registry;
  if (!snapshot) {
    if (proposal.categories.some(category => category.entity_id != null))
      throw Error('Explicit entity bindings require their matching registry snapshot');
    // Deterministic bootstrap identity, not an assertion of database acceptance.
    snapshot = registryFromV7Categories(proposal.categories, 'v7-category-bootstrap-v1');
    bootstrap = true;
  }
  const registry = createEntityRegistry(snapshot);
  const categories = proposal.categories.map(category => {
    if (!bootstrap && category.entity_id == null) throw Error('Missing explicit entity binding');
    const entity_id = bootstrap ? category.id & 15 : category.entity_id;
    return {...category, entity_id, name: registry.get(entity_id).name};
  });
  validateCategoryBindings(categories, registry);
  const byCode = new Map(categories.map(category => [category.id, category]));
  const waterEntities = new Set();
  for (const category of categories.filter(c => c.physical_class === 'water')) {
    if (waterEntities.has(category.entity_id)) throw Error('V7 water codes must bind to distinct entities');
    waterEntities.add(category.entity_id);
  }
  for (const category of categories) {
    const code = category.id;
    if (!((code >= 1 && code <= 10) || (code >= 17 && code <= 22)) ||
        category.physical_class !== (code >= 17 ? 'land' : 'water') ||
        registry.get(category.entity_id).level !== 'continent')
      throw Error(`Invalid V7 category binding: ${code}`);
    if (code >= 17 && byCode.get(code & 15)?.entity_id !== category.entity_id)
      throw Error(`V7 land and assigned water must share one entity: ${code}`);
  }
  return {...proposal, entity_registry: snapshot, categories};
}

// Legacy water-presentation sections retain raw V7 codes for compatibility.
// Their identities and display names are resolved through the registry.
export function v7ContinentSections(metadata) {
  const registry = createEntityRegistry(metadata.entity_registry);
  validateCategoryBindings(metadata.categories, registry);
  const landEntities = new Set(metadata.categories.filter(c => c.physical_class === 'land').map(c => c.entity_id));
  return metadata.categories.filter(c => c.physical_class === 'water' && landEntities.has(c.entity_id))
    .map(c => ({id: c.id, entity_id: c.entity_id, name: registry.get(c.entity_id).name}))
    .sort((a, b) => a.id - b.id);
}
