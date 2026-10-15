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
  territorialExclusions = [], ownerRows, size, latitudes, rowStart, rowEnd, diagnosticRows, coverageFeatureGroups,
  coverageCentres, coverageCentreGroups}) {
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
  const validateCentres = centres => {
    require(Array.isArray(centres), 'Invalid reviewed centre coverage');const seen=new Set();
    for(const point of centres){
      exactKeys(point,['source_id','pixelIndex','y','x'],'Reviewed coverage centre');
      const source=sourceIds.get(point.source_id),key=point.pixelIndex+':'+point.y+':'+point.x;
      require(source&&targetByOwner.get(point.pixelIndex)?.id===source.id&&source.owner===point.pixelIndex
        &&Number.isSafeInteger(point.y)&&point.y>=rowStart&&point.y<rowEnd
        &&Number.isSafeInteger(point.x)&&point.x>=0&&point.x<size&&!seen.has(key),
      'Coverage centre lacks exact original source membership');seen.add(key);
    }
  };
  if(coverageCentres!==undefined)validateCentres(coverageCentres);
  const validateCoverage = (features,centres) => {
    require(Array.isArray(features) && (features.length > 0 || centres?.length > 0), 'Missing reviewed coverage');
    for (const feature of [...features, ...territorialExclusions])
      require(targetByOwner.get(feature.pixelIndex)?.id === feature.id, 'Foreign coverage or exclusion target');
    for (const feature of features) {
      const source=sourceIds.get(feature.source_id ?? feature.id);
      require(source?.owner===feature.pixelIndex && source.id===feature.id,
        'Coverage lacks exact original source membership');
    }
  };
  validateCoverage(coverageFeatures,coverageCentres);
  if (coverageFeatureGroups !== undefined) {
    require(Array.isArray(coverageFeatureGroups), 'Invalid additional coverage groups');
    require(coverageCentreGroups===undefined||Array.isArray(coverageCentreGroups)
      &&coverageCentreGroups.length===coverageFeatureGroups.length,'Invalid centre coverage groups');
    for (const [i,features] of coverageFeatureGroups.entries()) {
      const centres=coverageCentreGroups?.[i];if(centres!==undefined)validateCentres(centres);
      validateCoverage(features,centres);
    }
  } else require(coverageCentreGroups===undefined,'Centre groups require coverage groups');
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
  const sources=remap(scan(sourceFeatures.map(feature=>({...feature,pixelIndex:sourceIds.get(feature.id).index}))));
  const scanCoverage = features => remap(scan(features.map(feature=>{
    const id=feature.source_id??feature.id;
    return {id,pixelIndex:sourceIds.get(id).index,geometry:feature.geometry};
  }),true));
  // Exact adopted centres add positive spans only. The unchanged decision below
  // still requires the same active original member and every negative guard.
  const withCentres=(coverage,centres=[])=>{
    for(const point of centres){
      const spans=coverage.rows.get(point.y)??[];
      spans.push({start:point.x,end:point.x+1,owner:point.pixelIndex,source_id:point.source_id});
      coverage.rows.set(point.y,spans);
    }
    return coverage;
  };
  let coverage=withCentres(scanCoverage(coverageFeatures),coverageCentres);
  const excluded=scan(territorialExclusions,true);
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
  // Only this invocation shares complete source/exclusion scans and current rows.
  // Each coverage retains its own member mask, boundary ties and decision order.
  const evaluate = (coverage, diagnosticRows) => {
    // Exact boundary cells require the existing boundary adjudication; withholding
    // them here must not silently choose whichever source happened to come first.
    const ties = new Map();
    for (const tie of [...sources.ties, ...coverage.ties, ...excluded.ties]) {
      const spans = ties.get(tie.y) ?? [];
      spans.push([tie.start ?? tie.x, tie.end ?? tie.x + 1]); ties.set(tie.y, spans);
    }
    // Optional observations are restricted to complete, nonoverlapping requested
    // intervals. They share the scans and decision order below; no second geometry
    // operator or alternate coverage policy is used.
    const requested = new Map(), diagnostic = [];
    if (diagnosticRows !== undefined) {
      require(Array.isArray(diagnosticRows), 'Invalid native diagnostic request');
      let previousY = -1;
      for (const row of diagnosticRows) {
        require(Number.isSafeInteger(row.y) && row.y >= rowStart && row.y < rowEnd
          && row.y > previousY && Array.isArray(row.runs), 'Invalid native diagnostic row');
        previousY = row.y; let end = 0;
        for (const run of row.runs) {
          require(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger)
            && run[0] >= end && run[1] > run[0] && run[1] <= size && targetByOwner.has(run[2]),
          'Invalid native diagnostic interval'); end = run[1];
        }
        requested.set(row.y, row.runs);
      }
    }
    const counts = {assigned_cells: 0, already_owned_cells: 0, ambiguous_owner_cells: 0,
      unsupported_coverage_cells: 0, territorial_exclusion_cells: 0, boundary_cells: 0};
    const rows = [], perTarget = new Map(targets.map(target => [target.id, 0]));
    for (let y = rowStart; y < rowEnd; y++) {
      const source = sources.rows.get(y) ?? [], support = coverage.rows.get(y) ?? [];
      const holes = excluded.rows.get(y) ?? [], owned = current.get(y), boundary = ties.get(y) ?? [];
      const cuts = new Set();
      for (const run of requested.get(y) ?? []) { cuts.add(run[0]); cuts.add(run[1]); }
      for (const run of [...source, ...support, ...holes]) { cuts.add(run.start); cuts.add(run.end); }
      for (const run of [...owned, ...boundary]) { cuts.add(run[0]); cuts.add(run[1]); }
      const points = [...cuts].sort((a, b) => a - b), runs = [], trace = [];
      const decide = start => {
        const owners = new Set(source.filter(run => run.start <= start && start < run.end).map(run => run.owner));
        if (![...owners].some(owner => targetByOwner.has(owner))) return {reason: 'no-target-source-domain'};
        if (owned.some(run => run[0] <= start && start < run[1])) return {reason: 'already_owned_cells'};
        if (boundary.some(run => run[0] <= start && start < run[1])) return {reason: 'boundary_cells'};
        if (owners.size !== 1) return {reason: 'ambiguous_owner_cells'};
        const owner = [...owners][0];
        if (holes.some(run => run.owner === owner && run.start <= start && start < run.end))
          return {reason: 'territorial_exclusion_cells'};
        const activeMembers = new Set(source.filter(run => run.owner === owner && run.start <= start && start < run.end).map(run => run.source_id));
        if (!support.some(run => run.owner === owner && activeMembers.has(run.source_id) && run.start <= start && start < run.end))
          return {reason: 'unsupported_coverage_cells'};
        return {reason: 'assigned_cells', owner};
      };
      for (let i = 0; i + 1 < points.length; i++) {
        const start = points[i], end = points[i + 1], decision = decide(start), count = end - start;
        const request = (requested.get(y) ?? []).find(run => run[0] <= start && start < run[1]);
        if (request) {
          const reason = decision.reason === 'assigned_cells' && decision.owner !== request[2]
            ? 'source-target-owner-mismatch' : decision.reason;
          const previous = trace.at(-1);
          if (previous && previous[1] === start && previous[2] === request[2] && previous[3] === reason) previous[1] = end;
          else trace.push([start, end, request[2], reason]);
        }
        if (decision.reason === 'no-target-source-domain') continue;
        if (decision.reason !== 'assigned_cells') { counts[decision.reason] += count; continue; }
        const owner = decision.owner, target = targetByOwner.get(owner);
        const previous = runs.at(-1);
        if (previous && previous[1] === start && previous[2] === owner) previous[1] = end;
        else runs.push([start, end, owner]);
        counts.assigned_cells += count; perTarget.set(target.id, perTarget.get(target.id) + count);
      }
      if (runs.length) rows.push({y, runs});
      if (trace.length) diagnostic.push({y, runs: trace});
    }
    return {rows, ...counts, removed_cells: 0, reassigned_cells: 0,
      targets: targets.map(target => ({...target, native_cells: perTarget.get(target.id)})),
      ...(diagnosticRows === undefined ? {} : {diagnostic_rows: diagnostic})};
  };
  const result=evaluate(coverage,diagnosticRows);
  if (coverageFeatureGroups === undefined) return result;
  // Drop the combined mask before sequential class scans; no cross-call state.
  coverage=null;
  result.coverage_groups=[];
  for (const [i,features] of coverageFeatureGroups.entries())
    result.coverage_groups.push(evaluate(withCentres(scanCoverage(features),coverageCentreGroups?.[i]),undefined));
  return result;
}

// Private exact-witness arithmetic has no shared mutable policy state.
export const {witnessCellEffects, validateWitnessGeometry} = (() => {
// Exact candidate-cell witness operator. The caller authenticates the passed stock scanner,
// admits the complete geometry/runtime/scan/output phase and supplies a deadline.
// This function establishes cell effects only, never scientific qualification.
const BLOCK_ROWS = 4096;
const VIEW = new DataView(new ArrayBuffer(8));
const KNOWN_KINDS = ['interior', 'boundary', 'line', 'point'];

function require(value, message) {
  if (!value) throw Error(message);
}
function exactKeys(value, keys, name) {
  require(value && typeof value === 'object' && !Array.isArray(value), `${name} must be an object`);
  require(Object.keys(value).sort().join(',') === [...keys].sort().join(','), `Primitive geometry/request: ${name} has missing/foreign fields`);
}
function position(value) {
  require(Array.isArray(value) && value.length === 2 && value.every(Number.isFinite)
    && Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90, 'Invalid complete lon/lat position');
  return value;
}
function denseArray(value, name) {
  require(Array.isArray(value), `${name} must be an array`);
  for (let i = 0; i < value.length; i++) require(Object.hasOwn(value, i), `${name} has a missing member`);
  return value;
}

// Exact dyadic representation of a finite IEEE-754 binary64 value: n * 2**e.
function binary(value) {
  require(Number.isFinite(value), 'Nonfinite exact coordinate');
  if (value === 0) return {n: 0n, e: 0};
  VIEW.setFloat64(0, value, false);
  const word = VIEW.getBigUint64(0, false);
  const exponent = Number((word >> 52n) & 2047n);
  let n = (word & ((1n << 52n) - 1n)) + (exponent ? 1n << 52n : 0n);
  let e = exponent ? exponent - 1075 : -1074;
  if (word >> 63n) n = -n;
  while (n % 2n === 0n) { n /= 2n; e++; }
  return {n, e};
}
function integers(values) {
  const q = Math.max(0, ...values.map(value => -value.e));
  return {values: values.map(value => value.n << BigInt(value.e + q)), scale: 1n << BigInt(q)};
}
function min(a, b) { return a < b ? a : b; }
function max(a, b) { return a > b ? a : b; }

function requestedIndex(requestedRows, size, latitudes) {
  denseArray(requestedRows, 'Requested rows');
  const rows = new Map(), blocks = new Map();
  let previousY = -1, cells = 0;
  for (const row of requestedRows) {
    exactKeys(row, ['y', 'runs'], 'Requested row');
    require(Number.isSafeInteger(row.y) && row.y > previousY && row.y < size, 'Unordered/duplicate/out-of-domain requested row');
    previousY = row.y;
    denseArray(row.runs, 'Requested runs');
    require(row.runs.length > 0, 'Empty requested row');
    let end = 0;
    for (const run of row.runs) {
      require(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger)
        && run[0] >= end && run[1] > run[0] && run[1] <= size
        && run[2] > 0 && run[2] <= 2**32 - 1, 'Unordered/overlapping/invalid requested run');
      end = run[1]; cells += run[1] - run[0];
      require(Number.isSafeInteger(cells), 'Requested cell count is not finite/safe');
    }
    const item = {y: row.y, runs: row.runs, latitude: latitudes[row.y], exactLatitude: binary(latitudes[row.y])};
    rows.set(row.y, item);
    const block = Math.floor(row.y / BLOCK_ROWS);
    const group = blocks.get(block) ?? [];
    group.push(item); blocks.set(block, group);
  }
  return {rows, blocks, cells};
}

// Validate every supplied primitive before any stock scan or predicate work.
// Empty top-level coordinates of a recognized type are explicit empty witnesses;
// empty members inside a nonempty multi-primitive are rejected rather than dropped.
function primitives(geometry) {
  const polygons = [], segments = [], points = [], stack = [{value: geometry}];
  const activeCollections = new WeakSet();
  let parts = 0, vertices = 0;
  function point(value) { vertices++; return position(value); }
  function line(value) {
    denseArray(value, 'Line positions');
    require(value.length >= 2, 'Incomplete line witness');
    const positions = value.map(point);
    for (let i = 1; i < positions.length; i++) segments.push([positions[i - 1], positions[i]]);
  }
  function polygon(value) {
    denseArray(value, 'Polygon rings');
    require(value.length > 0, 'Missing polygon rings');
    const rings = value.map(ring => {
      denseArray(ring, 'Ring positions');
      require(ring.length >= 4, 'Incomplete footprint ring in witness polygon');
      const positions = ring.map(point), first = positions[0], last = positions.at(-1);
      require(first[0] === last[0] && first[1] === last[1], 'Unclosed polygon witness');
      return positions.flat();
    });
    polygons.push(rings);
  }
  while (stack.length) {
    const frame = stack.pop(), value = frame.value;
    if (frame.exit) { activeCollections.delete(value); continue; }
    parts++;
    require(value && typeof value.type === 'string', 'Unsupported original native geometry: missing witness geometry type');
    if (value.type === 'GeometryCollection') {
      exactKeys(value, ['type', 'geometries'], 'Geometry collection');
      denseArray(value.geometries, 'Collection members');
      require(!activeCollections.has(value), 'Cyclic witness geometry collection');
      activeCollections.add(value);
      // Iterative traversal avoids a recursion limit silently dropping parts.
      stack.push({value, exit: true});
      for (let i = value.geometries.length - 1; i >= 0; i--) stack.push({value: value.geometries[i]});
      continue;
    }
    require(['Point', 'MultiPoint', 'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon'].includes(value.type), 'Unknown witness primitive');
    exactKeys(value, ['type', 'coordinates'], 'Witness geometry');
    const coords = denseArray(value.coordinates, 'Witness coordinates');
    if (coords.length === 0) continue;
    if (value.type === 'Point') points.push(point(coords));
    else if (value.type === 'MultiPoint') for (const member of coords) points.push(point(member));
    else if (value.type === 'LineString') line(coords);
    else if (value.type === 'MultiLineString') for (const member of coords) line(member);
    else if (value.type === 'Polygon') polygon(coords);
    else for (const member of coords) polygon(member);
  }
  return {polygons, segments, points, parts, vertices};
}

/**
 * Return {hits, counts, work}. Each hit {y,x,kind} is unique by cell AND kind;
 * counts.cells is the distinct cell union, so mixed contacts never double-count
 * affected cells. Counts by kind preserve every interior/boundary/line/point effect.
 * Polygon interior means stock span membership excluding any returned boundary
 * tie; every tie is separately retained, including ties excluded by stock spans.
 * Lines/points use binary64 endpoint/latitude values, but the exact ideal rational
 * native longitude (360*x + 180 - 180*size)/size rather than a rounded JS longitude.
 */
function witnessCellEffects(geometry, {size, latitudes, requestedRows, nativePolygonIntervals}) {
  require(Number.isSafeInteger(size) && size >= 2 && size <= 2**31, 'Invalid native grid size');
  require(latitudes?.length === size, 'Missing complete normative latitude table');
  for (let y = 0; y < size; y++) require(Number.isFinite(latitudes[y]) && Math.abs(latitudes[y]) < 90
    && (y === 0 || latitudes[y] < latitudes[y - 1]), 'Invalid decreasing native latitude table');
  require(typeof nativePolygonIntervals === 'function', 'Authenticated stock polygon scanner required');
  const request = requestedIndex(requestedRows, size, latitudes);
  const witness = primitives(geometry);
  const width = BigInt(size), hits = new Map(), cells = new Set();
  const work = {requested_cells: request.cells, requested_rows: request.rows.size,
    geometry_parts: witness.parts, vertices: witness.vertices, polygon_parts: witness.polygons.length,
    line_segments: witness.segments.length, points: witness.points.length, stock_scan_blocks: 0,
    exact_line_cell_tests: 0, exact_point_cell_tests: 0};
  function add(y, x, kind) {
    require(KNOWN_KINDS.includes(kind), 'Unknown cell effect');
    const key = `${y}:${x}`;
    if (kind === 'boundary') hits.delete(`${key}:interior`);
    if (kind === 'interior' && hits.has(`${key}:boundary`)) return;
    cells.add(key); hits.set(`${key}:${kind}`, {y, x, kind});
  }
  function applySpan(y, start, end, kind) {
    const row = request.rows.get(y);
    if (!row) return;
    for (const run of row.runs) for (let x = Math.max(start, run[0]); x < Math.min(end, run[1]); x++) add(y, x, kind);
  }
  if (witness.polygons.length) for (const [block] of request.blocks) {
    const rowStart = block * BLOCK_ROWS, rowEnd = Math.min(size, rowStart + BLOCK_ROWS);
    const scan = nativePolygonIntervals([{index: 1, polygons: witness.polygons}], {size, latitudes, rowStart, rowEnd});
    work.stock_scan_blocks++;
    require(scan?.rows instanceof Map && Array.isArray(scan.ties), 'Incomplete stock witness scan');
    for (const [y, spans] of scan.rows) {
      require(Number.isSafeInteger(y) && y >= rowStart && y < rowEnd && Array.isArray(spans), 'Malformed stock scan row');
      for (const span of spans) {
        exactKeys(span, ['start', 'end', 'owner'], 'Stock span');
        require(span.owner === 1 && Number.isSafeInteger(span.start) && Number.isSafeInteger(span.end)
          && span.start >= 0 && span.start < span.end && span.end <= size, 'Invalid stock witness span');
        applySpan(y, span.start, span.end, 'interior');
      }
    }
    for (const tie of scan.ties) {
      require(tie && Number.isSafeInteger(tie.y) && tie.y >= rowStart && tie.y < rowEnd && tie.owner === 1
        && ['horizontal-native-boundary-centres', 'excluded-native-lower-vertex-centre', 'native-intersection-on-cell-centre'].includes(tie.kind), 'Unknown/malformed stock boundary tie');
      if (Object.hasOwn(tie, 'x')) {
        exactKeys(tie, ['y', 'x', 'owner', 'kind'], 'Stock point tie');
        require(Number.isSafeInteger(tie.x) && tie.x >= 0 && tie.x < size, 'Invalid stock boundary column');
        applySpan(tie.y, tie.x, tie.x + 1, 'boundary');
      } else {
        exactKeys(tie, ['y', 'start', 'end', 'owner', 'kind'], 'Stock interval tie');
        require(Number.isSafeInteger(tie.start) && Number.isSafeInteger(tie.end) && tie.start >= 0
          && tie.start < tie.end && tie.end <= size, 'Invalid stock boundary interval');
        applySpan(tie.y, tie.start, tie.end, 'boundary');
      }
    }
  }
  for (const [a, b] of witness.segments) {
    const endpointValues = [binary(a[0]), binary(a[1]), binary(b[0]), binary(b[1])];
    for (const row of request.rows.values()) {
      // Comparisons of finite binary64 inputs are exact order comparisons;
      // no approximate native longitude is used even for a bounding-box filter.
      if (row.latitude < Math.min(a[1], b[1]) || row.latitude > Math.max(a[1], b[1])) continue;
      const {values: [ax, ay, bx, by, py], scale} = integers([...endpointValues, row.exactLatitude]);
      const lowerX = min(ax, bx) * width, upperX = max(ax, bx) * width;
      require(py >= min(ay, by) && py <= max(ay, by), 'Exact segment latitude filtering drift');
      const dx = bx - ax, dy = by - ay;
      for (const run of row.runs) for (let x = run[0]; x < run[1]; x++) {
        work.exact_line_cell_tests++;
        const px = (360n * BigInt(x) + 180n - 180n * width) * scale;
        if (px < lowerX || px > upperX) continue;
        // Inclusive endpoints, horizontal/vertical segments and zero-length
        // segments all follow this same exact collinearity equation.
        if ((px - ax * width) * dy === (py - ay) * dx * width) add(row.y, x, 'line');
      }
    }
  }
  for (const point of witness.points) {
    const pointValues = [binary(point[0]), binary(point[1])];
    for (const row of request.rows.values()) {
      if (row.latitude !== point[1]) continue;
      const {values: [px, py, latitude], scale} = integers([...pointValues, row.exactLatitude]);
      require(py === latitude, 'Exact point latitude filtering drift');
      for (const run of row.runs) for (let x = run[0]; x < run[1]; x++) {
        work.exact_point_cell_tests++;
        const longitude = (360n * BigInt(x) + 180n - 180n * width) * scale;
        if (longitude === px * width) add(row.y, x, 'point');
      }
    }
  }
  const ordered = [...hits.values()].sort((a, b) => a.y - b.y || a.x - b.x || a.kind.localeCompare(b.kind));
  const counts = {cells: cells.size};
  for (const kind of KNOWN_KINDS) counts[kind] = ordered.filter(hit => hit.kind === kind).length;
  return {hits: ordered, counts, work};
}

// Validation retains every recognized primitive, including empty and mixed parts.
// Statistics permit the caller to reserve the full flattened/scan scratch phase.
function validateWitnessGeometry(geometry, options) {
  const p = primitives(geometry);
  const stats = {parts:p.parts, vertices:p.vertices, polygons:p.polygons.length,
    segments:p.segments.length, points:p.points.length,
    empty:p.polygons.length+p.segments.length+p.points.length===0};
  if(options){
    const {latitudes,rowStart,rowEnd,requestedCells=0}=options;
    require(Number.isInteger(rowStart)&&Number.isInteger(rowEnd)&&rowStart>=0
      &&rowEnd<=latitudes.length&&rowEnd>rowStart&&rowEnd-rowStart<=4096
      &&Number.isSafeInteger(requestedCells)&&requestedCells>=0,'Invalid witness scratch admission extent');
    // The caller already authenticates/validates the normative decreasing table.
    // These schedules exactly match stock half-open crossings; tie bounds remain
    // inclusive. No polygon predicate is executed to establish admission.
    const first=value=>{let lo=rowStart,hi=rowEnd;while(lo<hi){const mid=Math.floor((lo+hi)/2);
      if(latitudes[mid]>value)lo=mid+1;else hi=mid;}return lo;};
    let crossings=0,lowerTies=0,edges=0;
    for(const polygon of p.polygons)for(const ring of polygon)
      for(let i=0;i<ring.length-2;i+=2){
        edges++;const low=Math.min(ring[i+1],ring[i+3]),high=Math.max(ring[i+1],ring[i+3]);
        const end=first(low),start=first(high);
        if(low!==high)crossings+=Math.max(0,end-start);
        if(end<rowEnd&&latitudes[end]===low)lowerTies++;
      }
    const spans=Math.ceil(crossings/2),ties=crossings+lowerTies;
    // Edges, exact dyadic arithmetic, flattened coordinates and active columns;
    // all retained stock rows/ties; complete helper hit/kind/output inventory.
    const scratch=p.vertices*1024+p.parts*128+(spans+ties)*192
      +(rowEnd-rowStart)*128+requestedCells*1024+4096;
    require(Number.isSafeInteger(scratch),'Nonfinite witness scratch admission');
    Object.assign(stats,{edges,crossing_edge_rows:crossings,span_upper_bound:spans,
      tie_upper_bound:ties,scratch_bytes:scratch});
  }
  return stats;
}

return {witnessCellEffects, validateWitnessGeometry};
})();
