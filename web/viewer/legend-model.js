// Project canonical map codes onto the selected level without changing the grid.
export function makeModeDisplay(mode, config) {
  const { legend, entity_ids_by_category: ids, unbuilt_cells: unbuiltCells } = mode;
  if (ids.length !== config.categories.length)
    throw Error("Map legend does not match the map categories");

  const groups = new Map(legend.map((item) => [item.id, { ...item, codes: [] }]));
  const categoriesByCode = new Map();
  const palette = new Map();
  config.categories.forEach(({ id, physical_class }, index) => {
    const owner = ids[index];
    const group = groups.get(owner);
    if (owner !== null && !group) throw Error("Map legend is missing an entity");
    group?.codes.push(id);
    categoriesByCode.set(id, { name: group?.name ?? "Unbuilt at this level", physical_class });
    palette.set(id, physical_class === "water" ? config.water_rgb
      : group?.color ?? config.unbuilt_land_rgb);
  });
  return { items: [...groups.values()], categoriesByCode, palette, unbuiltCells };
}

export function matchingLegendItems(items, query = "") {
  const needle = String(query).trim().toLocaleLowerCase();
  return needle
    ? items.filter((item) => item.name.toLocaleLowerCase().includes(needle))
    : items;
}

export function toggleSelection(selection, id) {
  const next = new Set(selection);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}

export function activeCategoryCodes(
  items,
  selected = new Set(),
  hovered = null,
) {
  const active = new Set(selected);
  if (hovered !== null) active.add(hovered);
  const codes = new Set();
  for (const item of items)
    if (active.has(item.id)) for (const code of item.codes) codes.add(code);
  return codes;
}
