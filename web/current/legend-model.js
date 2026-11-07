// Pure legend/search/count/filter helpers shared by the UI and its deterministic tests.
export const LEGEND_GROUPS = Object.freeze([
  {id:'africa',name:'Africa',codes:[1,17]},
  {id:'asia',name:'Asia',codes:[2,18]},
  {id:'europe',name:'Europe',codes:[3,19]},
  {id:'north-america',name:'North America',codes:[4,20]},
  {id:'south-america',name:'South America',codes:[5,21]},
  {id:'oceania',name:'Oceania',codes:[6,22]},
  {id:'atlantic',name:'Atlantic Ocean',codes:[7]},
  {id:'pacific',name:'Pacific Ocean',codes:[8]},
  {id:'indian',name:'Indian Ocean',codes:[9]},
  {id:'arctic',name:'Arctic Ocean',codes:[10]},
]);

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

export function makeLegendItems(categories, categoryCounts) {
  return LEGEND_GROUPS.map(group=>{
    const colorCategory=categories.find(c=>c.id===group.codes.find(code=>code>=17)) || categories.find(c=>c.id===group.codes[0]);
    return {...group,color:colorCategory?.rgb||[128,128,128],count:group.codes.reduce((sum,code)=>sum+(categoryCounts[code]||0),0)};
  });
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

export function mutedColor(value) {
  // Assignment codes 17–22 are land; 1–10 are water. Preserve that distinction.
  return value>=17 ? [88,96,99] : [194,202,205];
}
