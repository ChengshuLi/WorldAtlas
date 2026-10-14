import {nativePolygonIntervals} from './native-grid.js';
// Native geometry input for location ownership. Camera projection is separate;
// this adapter does not change geographic facts or stable source identities.
import {compileNativeOwnership} from '../scripts/native-ownership/compile-native-ownership.mjs';

export function nativeRuntimeIndex(features) {
  if (!Array.isArray(features)) throw Error('Explicit native feature roster required');
  const ids=new Set(),owners=new Set();
  const index=features.map(feature=>{
    const owner=feature.pixelIndex,geometry=feature.geometry;
    if (typeof feature.id!=='string' || !feature.id || ids.has(feature.id) ||
        !Number.isInteger(owner) || owner<1 || owners.has(owner))
      throw Error('Native runtime requires unique original IDs and explicit stable owner indices');
    ids.add(feature.id);owners.add(owner);
    if (!['Polygon','MultiPolygon'].includes(geometry?.type)) throw Error('Original native geometry required');
    const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
    if (!Array.isArray(polygons) || !polygons.length) throw Error('Original native polygons required');
    return {index:owner,polygons:polygons.map(polygon=>{
      if (!Array.isArray(polygon) || !polygon.length) throw Error('Original native rings required');
      return polygon.map(ring=>{
        if (!Array.isArray(ring) || ring.length<4) throw Error('Original native closed ring required');
        const result=new Float64Array(ring.length*2);
        ring.forEach((point,i)=>{
          if (!Array.isArray(point) || point.length!==2 || !point.every(Number.isFinite) ||
              Math.abs(point[0])>180 || Math.abs(point[1])>90) throw Error('Original lon/lat coordinates required');
          result.set(point,i*2);
        });
        if (result[0]!==result.at(-2) || result[1]!==result.at(-1)) throw Error('Original native closed ring required');
        return result;
      });
    })};
  });
  return index.sort((a,b)=>a.index-b.index);
}

// Both renderers receive the same compact rows/words. No Float64 rule table is
// regenerated from browser Math functions; callers supply its verified bytes.
export async function compileNativeRuntime(features,{size,latitudes,rowBlock=4096,partWords=1048576,onBlock}={}) {
  const pieces=[],index=nativeRuntimeIndex(features);
  if(size!==262166 || !(latitudes instanceof Float64Array) || latitudes.length!==size)
    throw Error('Canonical native runtime requires the exact supplied latitude table');
  const table=new Float64Array(latitudes),raw=new Uint8Array(size*8),view=new DataView(raw.buffer);
  for(let y=0;y<size;y++)view.setFloat64(y*8,table[y],true);
  const checksum=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),
    byte=>byte.toString(16).padStart(2,'0')).join('');
  if(checksum!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')
    throw Error('Canonical native latitude bytes differ');
  let rows;
  const result=await compileNativeOwnership(index,{size,latitudes:table,rowBlock,partWords,onBlock,
    writePart:async(part,words)=>{
      if (part.kind==='rows') {
        if (!rows) rows=new Uint32Array(size*2);
        rows.set(words,part.offset);
      } else pieces.push({offset:part.offset,words});
      return part;
    }});
  const runs=new Uint32Array(result.runWords);
  for (const piece of pieces) runs.set(piece.words,piece.offset);
  return {version:result.version,coordinateBits:result.coordinateBits,size,method:result.method,rows,runs};
}

const hex=/^[a-f0-9]{64}$/;
function require(value,message){if(!value)throw Error(message);}
function exactKeys(value,keys,name){require(value&&typeof value==='object'&&!Array.isArray(value),name+' must be an object');require(Object.keys(value).sort().join('\0')===[...keys].sort().join('\0'),name+' has missing/foreign fields');}

export function polygonParts(geometry) {
  require(geometry && ['Polygon', 'MultiPolygon'].includes(geometry.type), 'Unsupported original native geometry / footprint primitive');
  exactKeys(geometry, ['type', 'coordinates'], 'Primitive geometry');
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  require(Array.isArray(polygons) && polygons.length > 0, 'Missing footprint polygons');
  for (const polygon of polygons) {
    require(Array.isArray(polygon) && polygon.length > 0, 'Missing footprint rings');
    for (const ring of polygon) {
      require(Array.isArray(ring) && ring.length >= 4, 'Incomplete footprint ring');
      for (const point of ring) require(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)
        && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Invalid native footprint coordinate');
      require(ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1], 'Unclosed footprint ring');
    }
  }
  return polygons;
}
export function nativeOnlyComponent(row, hashValue) {
  if (row?.representation !== 'native-cells') return false;
  require(typeof hashValue==='function','Explicit canonical native component hash required');
  exactKeys(row, ['representation','component_id','target_id','pixelIndex','disposition',
    'base_geometry','base_geometry_sha256','native_rows','native_bounds','native_cells',
    'source_receipt_sha256','authority_sha256','rule_sha256'], 'Native source-target component');
  require(typeof row.component_id === 'string' && row.component_id && typeof row.target_id === 'string'
    && Number.isSafeInteger(row.pixelIndex) && row.pixelIndex > 0 && row.disposition === 'assigned',
  'Invalid native source-target identity');
  polygonParts(row.base_geometry);
  require(hashValue(row.base_geometry) === row.base_geometry_sha256,
    'Native component current base changed');
  for (const key of ['base_geometry_sha256','source_receipt_sha256','authority_sha256','rule_sha256'])
    require(hex.test(row[key] ?? ''), 'Missing native source-target custody');
  require(Array.isArray(row.native_rows) && row.native_rows.length > 0, 'Missing native component rows');
  let last = -1, cells = 0;
  for (const item of row.native_rows) {
    exactKeys(item, ['y','runs'], 'Native component row');
    require(Number.isSafeInteger(item.y) && item.y > last && item.y < 262166
      && Array.isArray(item.runs) && item.runs.length > 0, 'Invalid native component row');
    last = item.y; let end = 0;
    for (const run of item.runs) {
      require(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger)
        && run[0] >= end && run[1] > run[0] && run[1] <= 262166 && run[2] === row.pixelIndex,
      'Invalid native component interval');
      end = run[1]; cells += run[1] - run[0];
    }
  }
  require(cells === row.native_cells && cells > 0, 'Native component cell count differs');
  require(Array.isArray(row.native_bounds) && row.native_bounds.length === 4
    && row.native_bounds.every(Number.isFinite) && row.native_bounds[0] >= -180
    && row.native_bounds[2] <= 180 && row.native_bounds[1] >= -90 && row.native_bounds[3] <= 90
    && row.native_bounds[0] <= row.native_bounds[2] && row.native_bounds[1] <= row.native_bounds[3],
  'Invalid native component bounds');
  return true;
}
export function deriveSourceTargetNativeDelta({targets, sourceFeatures, coverageFeatures,
  territorialExclusions = [], ownerRows, size, latitudes, rowStart, rowEnd}) {
  require(Array.isArray(targets) && targets.length > 0, 'Missing source targets');
  const targetByOwner = new Map(), targetById = new Map();
  for (const target of targets) {
    require(typeof target.id === 'string' && target.id && Number.isSafeInteger(target.pixelIndex)
      && target.pixelIndex > 0 && !targetByOwner.has(target.pixelIndex) && !targetById.has(target.id),
    'Duplicate or invalid source target');
    targetByOwner.set(target.pixelIndex, target); targetById.set(target.id, target);
  }
  require(Array.isArray(sourceFeatures) && sourceFeatures.length > 0, 'Missing complete source family');
  const sourceOwners = new Map();
  for (const feature of sourceFeatures) {
    require(typeof feature.id === 'string' && feature.id && Number.isSafeInteger(feature.pixelIndex)
      && feature.pixelIndex > 0 && !sourceOwners.has(feature.pixelIndex), 'Ambiguous source owner roster');
    sourceOwners.set(feature.pixelIndex, feature.id);
  }
  for (const target of targets) require(sourceOwners.get(target.pixelIndex) === target.id,
    'Source target differs from complete source owner roster');
  require(Array.isArray(coverageFeatures) && coverageFeatures.length > 0, 'Missing reviewed coverage');
  for (const feature of [...coverageFeatures, ...territorialExclusions])
    require(targetByOwner.get(feature.pixelIndex)?.id === feature.id, 'Foreign coverage or exclusion target');
  const options = {size, latitudes, rowStart, rowEnd};
  const scan = (features, masks = false) => {
    if (!features.length) return {rows:new Map(),ties:[]};
    if (masks) {
      const grouped=new Map();
      for (const feature of features) {
        const item=grouped.get(feature.id)??{id:feature.id,pixelIndex:feature.pixelIndex,geometry:{type:'MultiPolygon',coordinates:[]}};
        item.geometry.coordinates.push(...polygonParts(feature.geometry)); grouped.set(feature.id,item);
      }
      features=[...grouped.values()];
    }
    return nativePolygonIntervals(nativeRuntimeIndex(features),options);
  };
  const sources = scan(sourceFeatures), coverage = scan(coverageFeatures,true), excluded = scan(territorialExclusions,true);
  // Exact boundary cells require the existing boundary adjudication; withholding
  // them here must not silently choose whichever source happened to come first.
  const ties = new Map();
  for (const tie of [...sources.ties, ...coverage.ties, ...excluded.ties]) {
    const spans = ties.get(tie.y) ?? [];
    spans.push([tie.start ?? tie.x, tie.end ?? tie.x + 1]); ties.set(tie.y, spans);
  }
  const current = new Map();
  for (const row of ownerRows) {
    require(Number.isSafeInteger(row.y) && row.y >= rowStart && row.y < rowEnd
      && !current.has(row.y) && Array.isArray(row.complete_owner_intervals), 'Incomplete current owner rows');
    let end = 0;
    for (const run of row.complete_owner_intervals) {
      require(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger)
        && run[0] >= end && run[1] > run[0] && run[1] <= size && run[2] > 0,
      'Invalid current owner interval'); end = run[1];
    }
    current.set(row.y, row.complete_owner_intervals);
  }
  require(current.size === rowEnd - rowStart, 'Missing complete current native row extent');
  const counts = {assigned_cells: 0, already_owned_cells: 0, ambiguous_owner_cells: 0,
    unsupported_coverage_cells: 0, territorial_exclusion_cells: 0, boundary_cells: 0};
  const rows = [], perTarget = new Map(targets.map(target => [target.id, 0]));
  for (let y = rowStart; y < rowEnd; y++) {
    const source = sources.rows.get(y) ?? [], support = coverage.rows.get(y) ?? [];
    const holes = excluded.rows.get(y) ?? [], owned = current.get(y), boundary = ties.get(y) ?? [];
    const cuts = new Set();
    for (const run of [...source, ...support, ...holes]) { cuts.add(run.start); cuts.add(run.end); }
    for (const run of [...owned, ...boundary]) { cuts.add(run[0]); cuts.add(run[1]); }
    const points = [...cuts].sort((a, b) => a - b), runs = [];
    for (let i = 0; i + 1 < points.length; i++) {
      const start = points[i], end = points[i + 1];
      const owners = new Set(source.filter(run => run.start <= start && start < run.end).map(run => run.owner));
      if (![...owners].some(owner => targetByOwner.has(owner))) continue;
      const count = end - start;
      if (owned.some(run => run[0] <= start && start < run[1])) { counts.already_owned_cells += count; continue; }
      if (boundary.some(run => run[0] <= start && start < run[1])) { counts.boundary_cells += count; continue; }
      if (owners.size !== 1) { counts.ambiguous_owner_cells += count; continue; }
      const owner = [...owners][0], target = targetByOwner.get(owner);
      if (holes.some(run => run.owner === owner && run.start <= start && start < run.end)) {
        counts.territorial_exclusion_cells += count; continue;
      }
      if (!support.some(run => run.owner === owner && run.start <= start && start < run.end)) {
        counts.unsupported_coverage_cells += count; continue;
      }
      const previous = runs.at(-1);
      if (previous && previous[1] === start && previous[2] === owner) previous[1] = end;
      else runs.push([start, end, owner]);
      counts.assigned_cells += count; perTarget.set(target.id, perTarget.get(target.id) + count);
    }
    if (runs.length) rows.push({y, runs});
  }
  return {rows, ...counts, removed_cells: 0, reassigned_cells: 0,
    targets: targets.map(target => ({...target, native_cells: perTarget.get(target.id)}))};
}
