// Versioned offline rule. Existing projected grids keep their original meaning.
export const NATIVE_GRID_METHOD='native-linear-evenodd-first-owner-v1';

export function nativeRowLatitudes(size){
  if(!Number.isSafeInteger(size)||size<2||size>2**31)throw Error('Invalid grid size');
  return Float64Array.from({length:size},(_,y)=>
    Math.atan(Math.sinh(Math.PI*(1-2*(y+.5)/size)))*180/Math.PI);
}

// Exact rational representation of the actual finite IEEE coordinate. No
// epsilon, snapping or approximate intersection determines a column endpoint.
const bits=new DataView(new ArrayBuffer(8));
function binary(value){
  if(!Number.isFinite(value))throw Error('Nonfinite native coordinate');
  if(value===0)return {n:0n,e:0};
  bits.setFloat64(0,value,false);
  const word=bits.getBigUint64(0,false),power=Number(word>>52n&2047n);
  let n=(word&((1n<<52n)-1n))+(power?1n<<52n:0n);
  let e=power?power-1075:-1074;
  if(word>>63n)n=-n;
  while(n%2n===0n){n/=2n;e++;}
  return {n,e};
}
function integers(values){
  const q=Math.max(0,...values.map(v=>-v.e)),scale=1n<<BigInt(q);
  return {values:values.map(v=>v.n<<BigInt(v.e+q)),scale};
}
function ceilDivision(n,d){
  if(d<=0n)throw Error('Invalid rational denominator');
  return n/d+(n%d>0n?1n:0n);
}
function floorDivision(n,d){return n/d-(n%d<0n?1n:0n);}
function columnFraction(longitude,size){
  const {values:[lon],scale}=integers([binary(longitude)]),width=BigInt(size);
  return {n:width*lon+(180n*width-180n)*scale,d:360n*scale};
}
function vertexColumn(longitude,size){
  const {n,d}=columnFraction(longitude,size);
  return n%d===0n?Number(n/d):null;
}
function prepareEdge(edge){
  edge.exact=[edge.x1,edge.y1,edge.x2,edge.y2].map(binary);
}
function crossing(edge,latitude,size){
  const {values:[x1,y1,x2,y2,lat],scale}=integers([...edge.exact,latitude]);
  const dy=y2-y1,dx=x2-x1,width=BigInt(size);
  const numerator=width*(x1*dy+(lat-y1)*dx)+(180n*width-180n)*dy*scale;
  const denominator=360n*dy*scale;
  return {column:Number(ceilDivision(numerator,denominator)),tie:numerator%denominator===0n};
}
// Latitude is decreasing with row number. Binary search schedules edges using
// min-latitude-exclusive/max-latitude-inclusive, equivalent to the legacy
// projected scanline's vertical half-open convention after inversion.
function firstAtOrBelow(latitudes,value,start,end){
  let lo=start,hi=end;
  while(lo<hi){const mid=Math.floor((lo+hi)/2);if(latitudes[mid]>value)lo=mid+1;else hi=mid;}
  return lo;
}

export function nativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes}){
  if(!Number.isSafeInteger(size)||size<2||size>2**31||
     !Number.isInteger(rowStart)||!Number.isInteger(rowEnd)||rowStart<0||rowEnd>size||
     rowStart>=rowEnd||rowEnd-rowStart>4096||latitudes?.length!==size)
    throw Error('Require explicit latitude table and at most4096 native rows');
  for(let y=0;y<size;y++)if(!Number.isFinite(latitudes[y])||Math.abs(latitudes[y])>=90||
    y&&latitudes[y]>=latitudes[y-1])throw Error('Invalid decreasing native latitude table');
  const rows=new Map(),ties=[];let previousOwner=0;
  for(const item of index){
    if(!Number.isInteger(item.index)||item.index<=previousOwner||item.index>2**32-1)
      throw Error('Noncanonical native owner order');
    previousOwner=item.index;
    if(!Array.isArray(item.polygons)||!item.polygons.length)throw Error('Missing native polygons');
    for(const polygon of item.polygons){
      if(!Array.isArray(polygon)||!polygon.length)throw Error('Missing native polygon rings');
      const edges=[];
      for(const ring of polygon){
        if(ring.length<8||ring.length%2||ring[0]!==ring.at(-2)||ring[1]!==ring.at(-1))
          throw Error('Unclosed native ring');
        for(let k=0;k<ring.length;k+=2)if(!Number.isFinite(ring[k])||!Number.isFinite(ring[k+1])||
          Math.abs(ring[k])>180||Math.abs(ring[k+1])>90)throw Error('Invalid native lon/lat coordinate');
        for(let k=0;k<ring.length-2;k+=2){
          let x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];
          if(y1>y2){[x1,x2]=[x2,x1];[y1,y2]=[y2,y1];}
          const excluded=firstAtOrBelow(latitudes,y1,rowStart,rowEnd);
          if(excluded<rowEnd&&latitudes[excluded]===y1){
            if(y1===y2){
              const a=columnFraction(Math.min(x1,x2),size),b=columnFraction(Math.max(x1,x2),size);
              const start=Math.max(0,Number(ceilDivision(a.n,a.d)));
              const end=Math.min(size,Number(floorDivision(b.n,b.d))+1);
              if(start<end)ties.push({y:excluded,start,end,owner:item.index,kind:'horizontal-native-boundary-centres'});
            }else{
              const x=vertexColumn(x1,size);
              if(x!==null&&x>=0&&x<size)ties.push({y:excluded,x,owner:item.index,kind:'excluded-native-lower-vertex-centre'});
            }
          }
          if(y1===y2)continue;
          const first=firstAtOrBelow(latitudes,y2,rowStart,rowEnd),end=excluded;
          if(first<end)edges.push({first,end,x1,y1,x2,y2});
        }
      }
      edges.sort((a,b)=>a.first-b.first);
      let next=0,active=[];
      for(let y=edges[0]?.first??rowEnd;y<rowEnd&&(active.length||next<edges.length);y++){
        active=active.filter(edge=>edge.end>y);
        while(next<edges.length&&edges[next].first===y){const edge=edges[next++];prepareEdge(edge);active.push(edge);}
        const latitude=binary(latitudes[y]),columns=[];
        for(const edge of active){
          const hit=crossing(edge,latitude,size);columns.push(hit.column);
          if(hit.tie&&hit.column>=0&&hit.column<size)
            ties.push({y,x:hit.column,owner:item.index,kind:'native-intersection-on-cell-centre'});
        }
        if(columns.length%2)throw Error('Unpaired native intersections; domain unmeasured');
        // Ceil is monotone, so sorting exact integer thresholds gives the same
        // paired cell spans as sorting the underlying rational intersections.
        columns.sort((a,b)=>a-b);
        for(let k=0;k<columns.length;k+=2){
          const start=Math.max(0,columns[k]),end=Math.min(size,columns[k+1]);
          if(start<end){if(!rows.has(y))rows.set(y,[]);rows.get(y).push({start,end,owner:item.index});}
        }
      }
    }
  }
  // Membership under this numerical rule is not source/topology approval.
  return {rows,ties,size,rowStart,rowEnd,method:NATIVE_GRID_METHOD,
    scientific_approval:false,native_topology_verified:false};
}

// Source-native input and additive interval admission share this dependency-free
// numerical boundary with trusted readers and runtime consumers.
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
  const sourceOwners = new Map(), sourceIds = new Map(), ownerById = new Map();
  for (const feature of sourceFeatures) {
    const ownerId = feature.target_id ?? feature.id;
    require(typeof feature.id === 'string' && feature.id && !sourceIds.has(feature.id)
      && typeof ownerId === 'string' && ownerId && Number.isSafeInteger(feature.pixelIndex)
      && feature.pixelIndex > 0 && feature.pixelIndex <= 2**32-1, 'Ambiguous source owner roster');
    require((!sourceOwners.has(feature.pixelIndex) || sourceOwners.get(feature.pixelIndex) === ownerId)
      && (!ownerById.has(ownerId) || ownerById.get(ownerId) === feature.pixelIndex),
    'Conflicting source owner identity');
    sourceIds.set(feature.id,{owner:feature.pixelIndex,id:ownerId,index:sourceIds.size+1}); sourceOwners.set(feature.pixelIndex, ownerId);
    ownerById.set(ownerId, feature.pixelIndex);
  }
  for (const target of targets) require(sourceOwners.get(target.pixelIndex) === target.id,
    'Source target differs from complete source owner roster');
  require(Array.isArray(coverageFeatures) && coverageFeatures.length > 0, 'Missing reviewed coverage');
  for (const feature of [...coverageFeatures, ...territorialExclusions])
    require(targetByOwner.get(feature.pixelIndex)?.id === feature.id, 'Foreign coverage or exclusion target');
  for (const feature of coverageFeatures) {
    const source=sourceIds.get(feature.source_id ?? feature.id);
    require(source?.owner===feature.pixelIndex && source.id===feature.id,
      'Coverage lacks exact original source membership');
  }
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
  // Internal scan ordinals preserve each original member's geometry and holes.
  // Ownership below unions their accepted owners, while coverage must still meet
  // its own measured member. A member's mask cannot borrow a sibling's geometry.
  const originals=[...sourceIds], remap=result=>{
    for(const spans of result.rows.values())for(const span of spans){
      const [id,source]=originals[span.owner-1];span.owner=source.owner;span.source_id=id;
    }
    return result;
  };
  const sources=remap(scan(sourceFeatures.map(feature=>({...feature,pixelIndex:sourceIds.get(feature.id).index})))),
    coverage=remap(scan(coverageFeatures.map(feature=>{
      const id=feature.source_id??feature.id;
      return {id,pixelIndex:sourceIds.get(id).index,geometry:feature.geometry};
    }),true)), excluded=scan(territorialExclusions,true);
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
      const activeMembers=new Set(source.filter(run=>run.owner===owner&&run.start<=start&&start<run.end).map(run=>run.source_id));
      if (!support.some(run => run.owner === owner && activeMembers.has(run.source_id) && run.start <= start && start < run.end)) {
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
