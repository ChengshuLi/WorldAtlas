// Legend entries come from the release. Category bindings connect them to cells.
export function makeLegendItems(entries, categories) {
  const groups = new Map(entries.map(entry => [entry.id, { ...entry, codes: [] }]));
  for (const category of categories) {
    const group = groups.get(category.entity_id);
    if (!group) throw Error('Map legend is missing an entity');
    group.codes.push(category.id);
  }
  return [...groups.values()];
}

export function matchingLegendItems(items, query='') {
  const needle=String(query).trim().toLocaleLowerCase();
  return needle ? items.filter(item=>item.name.toLocaleLowerCase().includes(needle)) : items;
}

export function toggleSelection(selection, id) {
  const next=new Set(selection);
  if(next.has(id)) next.delete(id); else next.add(id);
  return next;
}

export function activeCategoryMask(items, selected=new Set(), hovered=null) {
  const active=new Set(selected);
  if(hovered) active.add(hovered);
  if(!active.size) return 0;
  let mask=0;
  for(const item of items) if(active.has(item.id)) for(const code of item.codes) mask=(mask|(1<<code))>>>0;
  return mask>>>0;
}
