// Point sampling is only an explicitly labelled estimate, never evidence of whole-location ownership.
export function pointInGeometry(point, geometry) {
  function ringContains(ring) {
    let inside=false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
      const [xi,yi]=ring[i], [xj,yj]=ring[j];
      if((yi>point[1])!==(yj>point[1]) && point[0]<(xj-xi)*(point[1]-yi)/(yj-yi)+xi) inside=!inside;
    }
    return inside;
  }
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
  return polygons.some(rings=>ringContains(rings[0]) && !rings.slice(1).some(ringContains));
}
