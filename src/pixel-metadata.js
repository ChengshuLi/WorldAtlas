// Geometry and integer ownership stay immutable across dated names/membership.
// Validate the complete identity inventory before changing any picking metadata.
export function updateLocationMetadata(index,features){
  const byId=new Map(features.map(feature=>[feature.id,feature]));
  if(byId.size!==features.length||index.length!==features.length||new Set(index.map(item=>item.feature.id)).size!==index.length||index.some(item=>!byId.has(item.feature.id)))throw Error('Location inventory changed; rebuild geographic ownership');
  const provinces=[null];
  for(const item of index){
    const next=byId.get(item.feature.id);
    item.feature={...item.feature,properties:next.properties};
    provinces[item.index]=next.properties.parent_id;
  }
  return provinces;
}

export function locationInventoryChanged(previous,next){
  if(previous.length!==next.length)return true;
  const ids=new Set(previous.map(feature=>feature.id));
  return ids.size!==previous.length||new Set(next.map(feature=>feature.id)).size!==next.length||next.some(feature=>!ids.has(feature.id));
}

// Parsed boundary geometries are immutable source objects. Cache exact content,
// rather than a lossy hash or evidence/date fields which do not move land.
const geometryContent=new WeakMap();
const content=geometry=>{
  if(!geometry||typeof geometry!=='object')throw Error('Dated boundary requires geometry');
  if(!geometryContent.has(geometry))geometryContent.set(geometry,JSON.stringify({type:geometry.type,coordinates:geometry.coordinates,geometries:geometry.geometries}));
  return geometryContent.get(geometry);
};
export function boundaryFootprintsChanged(previous,next){
  if(previous.size!==next.size)return true;
  for(const [id,boundary] of next){
    const old=previous.get(id);
    if(!old||content(old.geometry)!==content(boundary.geometry))return true;
  }
  return false;
}
