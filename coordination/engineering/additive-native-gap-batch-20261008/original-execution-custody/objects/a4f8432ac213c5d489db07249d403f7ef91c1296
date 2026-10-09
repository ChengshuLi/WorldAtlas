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
