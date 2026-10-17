// Frozen numerical/validation oracle from26a4616c9305a6ae005a11471568f34ef199d158.
import {isNativeSequence} from '../../src/native-grid.js';
const mapGeometryArray=(values,visit)=>Array.isArray(values)?values.map(visit):Array.from(values,visit);
// Private exact-witness arithmetic has no shared mutable policy state.
export const {witnessCellEffects, validateWitnessGeometry} = (() => {
// Exact candidate-cell witness operator. The caller authenticates the passed stock scanner,
// supplies the complete geometry and requested native rows.
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
function coordinateArray(value,name){return Array.isArray(value)?denseArray(value,name):(require(isNativeSequence(value),`${name} must be an array`),value);}
function primitives(geometry) {
  const polygons = [], segments = [], points = [], stack = [{value: geometry}];
  const activeCollections = new WeakSet();
  let parts = 0, vertices = 0;
  function point(value) { vertices++; return position(value); }
  function line(value) {
    coordinateArray(value, 'Line positions');
    require(value.length >= 2, 'Incomplete line witness');
    const positions = mapGeometryArray(value,point);
    for (let i = 1; i < positions.length; i++) segments.push([positions[i - 1], positions[i]]);
  }
  function polygon(value) {
    coordinateArray(value, 'Polygon rings');
    require(value.length > 0, 'Missing polygon rings');
    const rings = mapGeometryArray(value,ring => {
      coordinateArray(ring, 'Ring positions');
      require(ring.length >= 4, 'Incomplete footprint ring in witness polygon');
      const positions = mapGeometryArray(ring,point), first = positions[0], last = positions.at(-1);
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
    const coords = coordinateArray(value.coordinates, 'Witness coordinates');
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
function validateWitnessGeometry(geometry) {
  const p = primitives(geometry);
  return {parts:p.parts, vertices:p.vertices, polygons:p.polygons.length,
    segments:p.segments.length, points:p.points.length,
    empty:p.polygons.length+p.segments.length+p.points.length===0};
}

return {witnessCellEffects, validateWitnessGeometry};
})();
