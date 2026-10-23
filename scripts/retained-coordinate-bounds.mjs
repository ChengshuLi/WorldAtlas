// Pure whole-primitive bounds for JSON.parse-produced dense coordinate arrays.
// No source qualification, raster/scanner, storage, hashing or I/O dependency.
export const RETAINED_BOUNDS_CONTRACT = 'dense-json-whole-primitive-bounds-v1';
const need = (v, m) => { if (!v) throw Error(m); };
const dense = a => Array.isArray(a) && Object.keys(a).length === a.length &&
  Object.keys(a).every((key, i) => key === String(i));
export function retainedCoordinateBounds(g) {
  need(g && ['Polygon','MultiPolygon'].includes(g.type) &&
    Object.keys(g).sort().join(',') === 'coordinates,type', 'Unsupported whole primitive');
  const polygons = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  need(dense(polygons) && polygons.length > 0, 'Missing polygons');
  const boxes = [];
  for (const polygon of polygons) {
    need(dense(polygon) && polygon.length > 0, 'Missing rings');
    let lo=Infinity, hi=-Infinity, south=Infinity, north=-Infinity, seam=false;
    for (const ring of polygon) {
      need(dense(ring) && ring.length >= 4, 'Incomplete ring');
      let first, prior;
      for (const point of ring) {
        need(dense(point) && point.length === 2 && point.every(Number.isFinite) &&
          Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Invalid/nonfinite coordinate');
        first ??= point;
        lo=Math.min(lo,point[0]);hi=Math.max(hi,point[0]);
        south=Math.min(south,point[1]);north=Math.max(north,point[1]);
        if (prior && Math.abs(prior[0]-point[0]) > 180) seam=true;
        prior=point;
      }
      // Finite JSON numbers use JSON's -0/0 equality, as the historical hash did.
      need(first[0] === prior[0] && first[1] === prior[1], 'Unclosed original ring');
    }
    if (seam || hi-lo > 180) { lo=-180;hi=180; }
    boxes.push([lo,south,hi,north]);
  }
  return boxes;
}
