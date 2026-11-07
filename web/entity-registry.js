// Identity and hierarchy come from a revisioned data snapshot, never a name list.
export const ENTITY_LEVELS = Object.freeze([
  'continent', 'subcontinent', 'region', 'area', 'province', 'location',
]);
export const REGISTRY_SCHEMA = 'worldatlas-entity-registry-v1';

export function createEntityRegistry(snapshot) {
  if (snapshot?.schema_version !== REGISTRY_SCHEMA ||
      typeof snapshot.revision !== 'string' || !snapshot.revision.trim() ||
      !['draft', 'accepted', 'rejected'].includes(snapshot.status) ||
      !Array.isArray(snapshot.entities) || !snapshot.entities.length)
    throw Error('Invalid entity registry snapshot');
  const entities = new Map(), children = new Map();
  for (const record of snapshot.entities) {
    if (!Number.isInteger(record.id) || record.id < 1 || record.id > 0xffffffff || entities.has(record.id))
      throw Error('Invalid or duplicate entity ID');
    if (typeof record.name !== 'string' || !record.name.trim() || !ENTITY_LEVELS.includes(record.level))
      throw Error(`Invalid entity name or level: ${record.id}`);
    if (record.level === 'continent' ? record.parent_id !== null :
        !Number.isInteger(record.parent_id) || record.parent_id < 1)
      throw Error(`Invalid entity parent: ${record.id}`);
    if (record.level === 'location' ? !['land', 'water'].includes(record.physical_class) :
        record.physical_class != null)
      throw Error(`Only locations have a physical class: ${record.id}`);
    entities.set(record.id, Object.freeze({...record}));
  }
  for (const entity of entities.values()) {
    if (entity.parent_id === null) continue;
    const parent = entities.get(entity.parent_id);
    if (!parent || ENTITY_LEVELS.indexOf(parent.level) + 1 !== ENTITY_LEVELS.indexOf(entity.level))
      throw Error(`Missing or wrong-level parent: ${entity.id}`);
    if (!children.has(parent.id)) children.set(parent.id, []);
    children.get(parent.id).push(entity);
  }
  function get(id) {
    const entity = entities.get(id);
    if (!entity) throw Error(`Unknown entity ID: ${id}`);
    return entity;
  }
  function ancestorAtLevel(id, level) {
    if (!ENTITY_LEVELS.includes(level)) throw Error(`Unknown hierarchy level: ${level}`);
    let entity = get(id);
    while (ENTITY_LEVELS.indexOf(entity.level) > ENTITY_LEVELS.indexOf(level)) entity = get(entity.parent_id);
    return entity.level === level ? entity : null;
  }
  return Object.freeze({
    revision: snapshot.revision, status: snapshot.status, size: entities.size, get, ancestorAtLevel,
    values: () => [...entities.values()],
    childrenOf: id => { get(id); return [...(children.get(id) || [])]; },
  });
}

// Categories are a review-encoding adapter. Their raw codes and RGB values are
// not entity IDs or properties of the entity registry.
export function validateCategoryBindings(categories, registry) {
  if (!Array.isArray(categories) || !categories.length) throw Error('Missing assignment categories');
  const codes = new Set();
  for (const category of categories) {
    if (!Number.isInteger(category.id) || category.id < 1 || category.id > 0xffffffff || codes.has(category.id))
      throw Error('Invalid or duplicate assignment code');
    codes.add(category.id);
    const entity = registry.get(category.entity_id);
    if (!['land', 'water'].includes(category.physical_class) ||
        (entity.level === 'location' && entity.physical_class !== category.physical_class))
      throw Error(`Invalid physical class for assignment code: ${category.id}`);
    if (!Array.isArray(category.rgb) || category.rgb.length !== 3 ||
        category.rgb.some(value => !Number.isInteger(value) || value < 0 || value > 255))
      throw Error(`Invalid presentation color: ${category.id}`);
  }
  return true;
}
