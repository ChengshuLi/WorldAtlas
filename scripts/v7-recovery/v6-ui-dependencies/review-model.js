// Data validation and view geometry for the bounded V2/V3 assignment review.
// Coordinates are native grid cells: row, start inclusive, end exclusive.
export const REQUIRED_GRID = Object.freeze({ width: 131072, height: 54614 });

export function wrapColumn(x, width) { return ((x % width) + width) % width; }

export async function verifyBufferChecksum(buffer, expected) {
  const digest=await globalThis.crypto.subtle.digest('SHA-256',buffer);
  const actual=[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(actual!==expected)throw Error('Native map checksum mismatch');
  return actual;
}

export function canonicalStringify(value) {
  if(Array.isArray(value))return `[${value.map(canonicalStringify).join(',')}]`;
  if(value&&typeof value==='object')return `{${Object.keys(value).sort().map(k=>`${JSON.stringify(k)}:${canonicalStringify(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}

export function createReviewInteraction() {
  let hovered=null, pinned=null;
  return {
    hover(value) { hovered=value; },
    click(value) { pinned=value; },
    clear() { pinned=null; },
    get pinned() { return pinned; },
    get hovered() { return hovered; },
    highlight() { return pinned?.spans?.length ? pinned.spans : hovered?.spans?.length ? hovered.spans : null; }
  };
}

// Exactly one grid reference is retained by the viewer. A new selection first
// releases the prior buffer, aborts the prior request, and ignores stale loads.
export function createSingleGridSlot() {
  let value=null, name=null, ticket=0, controller=null;
  return {
    get current(){return value;}, get name(){return name;}, get loading(){return !!controller;},
    async load(nextName,loader){
      const id=++ticket;controller?.abort();controller=new AbortController();
      value=null;name=null;
      const signal=controller.signal;
      try{
        const next=await loader(nextName,signal);
        if(id!==ticket)return false;
        value=next;name=nextName;return true;
      }catch(e){if(id===ticket)throw e;return false}
      finally{if(id===ticket)controller=null}
    },
    cancel(){++ticket;controller?.abort();controller=null;},
    clear(){this.cancel();value=null;name=null;}
  };
}

export function normalizeExtent(spans, width) {
  if (!spans.length) return null;
  const xs = [];
  let minY = Infinity, maxY = -Infinity;
  for (const s of spans) {
    if (!Number.isInteger(s.row) || !Number.isInteger(s.start) || !Number.isInteger(s.end) || s.row < 0 || s.start < 0 || s.end <= s.start || s.end > width)
      throw Error('Invalid row span');
    xs.push([s.start, s.end]); minY = Math.min(minY, s.row); maxY = Math.max(maxY, s.row + 1);
  }
  xs.sort((a,b) => a[0] - b[0]);
  const merged=[];
  for (const part of xs) {
    const last=merged[merged.length-1];
    if (last && part[0] <= last[1]) last[1]=Math.max(last[1],part[1]); else merged.push(part.slice());
  }
  // The map is periodic. Exclude the largest empty arc to get a minimal
  // longitude extent; preserve a two-part extent if it crosses the dateline.
  if (merged.length === 1) return { x: [merged[0].slice()], y: [minY,maxY], wraps:false, width:merged[0][1]-merged[0][0] };
  let gap=-1, after=0;
  for(let i=0;i<merged.length;i++) {
    const end=merged[i][1], next=(i+1<merged.length?merged[i+1][0]:merged[0][0]+width), g=next-end;
    if(g>gap){gap=g;after=(i+1)%merged.length;}
  }
  const start=merged[after][0]; let end=start;
  for(let step=0;step<merged.length;step++){
    const part=merged[(after+step)%merged.length];
    let left=part[0]; while(left<end)left+=width;
    end=Math.max(end,left+part[1]-part[0]);
  }
  return { x: [[start,end]], y: [minY,maxY], wraps: start<0 || end>width, width: end-start };
}

export function validateRows(meta, rows, runs, {strictSize=false}={}) {
  if(strictSize && (meta.width!==REQUIRED_GRID.width || meta.height!==REQUIRED_GRID.height)) throw Error('Review grid must be 131072 × 54614');
  if(rows.length!==meta.height+1 || rows[0]!==0 || rows[meta.height]!==runs.length/2 || runs.length%2) throw Error('Native grid dimensions do not match');
  for(let y=0;y<meta.height;y++){
    if(rows[y+1]<=rows[y]) throw Error('Empty native row');
    let end=0;
    for(let r=rows[y];r<rows[y+1];r++){
      const next=runs[2*r], value=runs[2*r+1];
      if(next<=end || next>meta.width || value<0 || value>31) throw Error('Invalid native run');
      end=next;
    }
    if(end!==meta.width) throw Error('Native row is incomplete');
  }
}

function spansOf(record) { return (record.members||[]).flatMap(m=>(m.spans||[]).map(s=>({...s, memberId:m.id, recordId:record.id}))); }

// Exhaustively compare run boundaries row by row. Any V2/V3 change must be
// attributed to a visible island or >22.224 km continental-water record;
// listed no-change cells and unlisted changes are both hard errors.
export function validateExceptionAccounting(v2, v3, groups, width, height) {
  const byId=new Map();
  for(const g of groups){
    if(!g.id || byId.has(g.id)) throw Error('Duplicate exception record id');
    if(!['island-convention','continental-water-22.224km','enclosed-ocean-pocket'].includes(g.type)) throw Error('Unknown exception list type');
    if(!g.destination || !g.reason || !Array.isArray(g.ruleIds) || !g.ruleIds.length || new Set(g.ruleIds).size!==g.ruleIds.length || !Array.isArray(g.members) || !g.members.length) throw Error('Incomplete exception group');
    const memberIds=new Set();
    for(const m of g.members){
      if(!m.id || memberIds.has(m.id) || !m.name || !Array.isArray(m.spans)) throw Error('Invalid exception member');
      memberIds.add(m.id);
      for(const s of m.spans){
        if(!Number.isInteger(s.row)||s.row<0||s.row>=height||!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start<0||s.end<=s.start||s.end>width) throw Error('Invalid exception row span');
        if(!Array.isArray(s.ruleIds)||!s.ruleIds.length||s.ruleIds.some(x=>typeof x!=='string')||new Set(s.ruleIds).size!==s.ruleIds.length) throw Error('Missing or duplicate attribution');
        if(s.ruleIds.some(x=>!g.ruleIds?.includes(x))) throw Error('Attribution references unknown rule record');
      }
    }
    byId.set(g.id,g);
  }
  // Per row collect boundaries from both grids and all declared spans.
  const spans=groups.flatMap(g=>spansOf(g));
  const indexed=Array.from({length:height},()=>[]);
  for(const s of spans) indexed[s.row].push(s);
  let changed=0, attributed=0;
  for(let y=0;y<height;y++){
    let a=v2.rows[y], b=v3.rows[y], ae=v2.rows[y+1], be=v3.rows[y+1], x=0;
    const declared=indexed[y].slice().sort((p,q)=>p.start-q.start||p.end-q.end);
    let di=0; const active=[];
    while(x<width){
      const ax=v2.runs[a*2], bx=v3.runs[b*2];
      while(di<declared.length&&declared[di].start<=x)active.push(declared[di++]);
      for(let i=active.length-1;i>=0;i--)if(active[i].end<=x)active.splice(i,1);
      let end=Math.min(ax,bx);
      if(di<declared.length)end=Math.min(end,declared[di].start);
      for(const s of active)end=Math.min(end,s.end);
      const av=v2.runs[a*2+1], bv=v3.runs[b*2+1];
      const coverage=active;
      const seenRecords=new Set(), seenTypes=new Set();
      for(const s of coverage){const g=byId.get(s.recordId);if(seenRecords.has(s.recordId)||seenTypes.has(g.type))throw Error(`Duplicate attribution at row ${y}, column ${x}`);seenRecords.add(s.recordId);seenTypes.add(g.type);}
      if(av!==bv){
        changed+=end-x;
        if(!seenRecords.size) throw Error(`Unattributed V3 change at row ${y}, column ${x}`);
        attributed+=end-x;
      } else if(coverage.length) throw Error(`Exception item has no V2/V3 change at row ${y}, column ${x}`);
      x=end;
      if(ax===end)a++; if(bx===end)b++;
      if(a>=ae||b>=be) break;
    }
  }
  return { changedCells:changed, attributedCells:attributed, records:groups.length };
}

export function validateReview(meta, v2, v3, physical, groups, {strictSize=false,ruleRecords=null}={}) {
  if(meta.width!==v2.width||meta.height!==v2.height||meta.width!==v3.width||meta.height!==v3.height||meta.width!==physical.width||meta.height!==physical.height) throw Error('V2, V3, and physical-mask grids must have identical dimensions');
  if(strictSize && (meta.width!==REQUIRED_GRID.width||meta.height!==REQUIRED_GRID.height)) throw Error('Review grid must be 131072 × 54614');
  validateRows(meta,v2.rows,v2.runs); validateRows(meta,v3.rows,v3.runs); validateRows(meta,physical.rows,physical.runs);
  if(ruleRecords){const ids=new Set();for(const r of ruleRecords){if(!r.id||!r.title||ids.has(r.id))throw Error('Invalid or duplicate rule record');ids.add(r.id);}for(const g of groups)for(const id of g.ruleIds||[])if(!ids.has(id))throw Error(`Unknown rule record ${id}`);}
  const counts=validateExceptionAccounting(v2,v3,groups,meta.width,meta.height);
  return counts;
}

// Build-time safeguard: an assignment category may change the continent/ocean
// label, but its land/water class must remain identical to the one shared OSM
// physical mask for both versions.
export function validatePhysicalMaskInvariance(meta, assignments, physical, categories) {
  const land=new Set(meta.physical_mask.land_values||[]), water=new Set(meta.physical_mask.water_values||[]);
  if(!land.size||!water.size||[...land].some(v=>water.has(v)))throw Error('Physical mask must declare disjoint land_values and water_values');
  const physicalClass=new Map(categories.map(c=>[c.id,c.physical_class]));
  for(const [versionName,grid] of Object.entries(assignments)){
    for(let y=0;y<meta.height;y++){
      let a=grid.rows[y],b=physical.rows[y],x=0;
      while(x<meta.width){
        const ae=grid.runs[a*2],be=physical.runs[b*2],end=Math.min(ae,be);
        const category=physicalClass.get(grid.runs[a*2+1]), raw=physical.runs[b*2+1];
        const expected=land.has(raw)?'land':water.has(raw)?'water':null;
        if(!expected)throw Error(`Unknown physical-mask value ${raw} at row ${y}, column ${x}`);
        if(category!==expected)throw Error(`${versionName} changes physical land/water at row ${y}, column ${x}`);
        x=end;if(ae===end)a++;if(be===end)b++;
        if(a>=grid.rows[y+1]||b>=physical.rows[y+1])break;
      }
    }
  }
  return true;
}
