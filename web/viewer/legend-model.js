// Pure legend/search/count/filter helpers shared by the UI and its deterministic tests.
export function computeCategoryCounts(data) {
  const counts = new Float64Array(32), {rows,runs} = data;
  for(let y=0;y<rows.length-1;y++) {
    let start=0;
    for(let r=rows[y];r<rows[y+1];r++) {
      const end=runs[r*2],value=runs[r*2+1];
      counts[value]+=end-start;
      start=end;
    }
  }
  return counts;
}

export function makeLegendItems(categories, categoryCounts, waterColor) {
  const groups = new Map();
  for (const category of categories) {
    const id = category.entity_id;
    if (!groups.has(id)) {
      groups.set(id, { id, name: category.name, codes: [], color: waterColor, count: 0 });
    }
    const group = groups.get(id);
    group.codes.push(category.id);
    group.count += categoryCounts[category.id] || 0;
    if (category.physical_class === 'land') group.color = category.rgb;
  }
  return [...groups.values()];
}

export function matchingLegendItems(items, query='') {
  const needle=String(query).trim().toLocaleLowerCase();
  return needle ? items.filter(item=>item.name.toLocaleLowerCase().includes(needle)) : items;
}

export function clearLegendSelection() { return new Set(); }
export function collapseLegendHover() { return null; }

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

export function isCategoryActive(mask, value) {
  return mask===0 || ((mask & (1<<value))!==0);
}
