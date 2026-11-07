import {createEntityRegistry, validateCategoryBindings} from './entity-registry.js';
import {withEntityRegistry} from './v7-entity-adapter.js';

export function computeCategoryCounts({rows, runs}) {
  const counts = new Map();
  for (let y = 0; y < rows.length - 1; y++) {
    let start = 0;
    for (let r = rows[y]; r < rows[y + 1]; r++) {
      const end = runs[r * 2], code = runs[r * 2 + 1];
      counts.set(code, (counts.get(code) || 0) + end - start);
      start = end;
    }
  }
  return counts;
}

export function makeLegendItems(source, categoryCounts, {level = 'continent', parent_id = null} = {}) {
  // The array form exists only for older V7 callers. New callers supply the
  // complete proposal, including its explicit registry and code bindings.
  const metadata = Array.isArray(source) ? withEntityRegistry({categories: source}) : source;
  const registry = createEntityRegistry(metadata.entity_registry);
  validateCategoryBindings(metadata.categories, registry);
  const knownCodes = new Set(metadata.categories.map(category => category.id));
  const countEntries = categoryCounts instanceof Map ? categoryCounts : Object.entries(categoryCounts || {});
  for (const [code, count] of countEntries) {
    if (!Number.isSafeInteger(count) || count < 0 || (count && !knownCodes.has(Number(code))))
      throw Error(`Invalid or unbound category count: ${code}`);
  }
  const groups = new Map();
  for (const category of metadata.categories) {
    const entity = registry.ancestorAtLevel(category.entity_id, level);
    if (!entity || (parent_id !== null && entity.parent_id !== parent_id)) continue;
    if (!groups.has(entity.id)) groups.set(entity.id, {
      id: String(entity.id), entity_id: entity.id, name: entity.name, level: entity.level,
      parent_id: entity.parent_id, codes: [], count: 0, color: category.rgb,
    });
    const item = groups.get(entity.id);
    item.codes.push(category.id);
    item.count += categoryCounts instanceof Map ? categoryCounts.get(category.id) || 0 : categoryCounts?.[category.id] || 0;
    if (!Number.isSafeInteger(item.count)) throw Error('Entity cell count exceeds safe integer range');
    if (category.physical_class === 'land') item.color = category.rgb;
  }
  return [...groups.values()].sort((a, b) => a.entity_id - b.entity_id);
}

export function matchingLegendItems(items, query = '') {
  const needle = String(query).trim().toLocaleLowerCase();
  return needle ? items.filter(item => item.name.toLocaleLowerCase().includes(needle)) : items;
}
export function clearLegendSelection() { return new Set(); }
export function collapseLegendHover() { return null; }
export function toggleSelection(selection, id) {
  const next = new Set(selection);
  if (next.has(id)) next.delete(id); else next.add(id);
  return next;
}

// Generic selection supports uint32 IDs. null means no filter, not an empty set.
export function activeCategoryCodes(items, selected = new Set(), hovered = null) {
  const active = new Set(selected);
  if (hovered !== null) active.add(hovered);
  if (!active.size) return null;
  return new Set(items.filter(item => active.has(item.id)).flatMap(item => item.codes));
}

// The current V7 shader has a 32-category mask. Keep this boundary explicit so
// future location IDs cannot silently collide through JavaScript bit shifts.
export function activeCategoryMask(items, selected = new Set(), hovered = null) {
  const codes = activeCategoryCodes(items, selected, hovered);
  let mask = 0;
  for (const code of codes || []) {
    if (!Number.isInteger(code) || code < 0 || code > 31) throw Error('V7 mask cannot encode this assignment code');
    mask = (mask | (1 << code)) >>> 0;
  }
  return mask;
}
export function isCategoryActive(mask, value) {
  if (!Number.isInteger(value) || value < 0 || value > 31) throw Error('V7 mask cannot encode this assignment code');
  return mask === 0 || ((mask & (1 << value)) !== 0);
}
export function mutedColor(value) {
  // Historic V7 raw encoding only. Registry records never encode colors.
  return value >= 17 ? [88, 96, 99] : [194, 202, 205];
}
