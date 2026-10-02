/** Reference owners may span continents. Scope geography by each location's
 * parent chain, never by a territory profile's single continent label. */
export function coverageScope(features,parents,territories,{continent='',owner=''}={}){
 const roots=new Map();
 const root=id=>{
  if(roots.has(id))return roots.get(id);
  const visited=new Set();let node=parents.get(id),name;
  while(node){
   if(visited.has(node.id))throw Error('Coverage hierarchy contains a cycle');visited.add(node.id);
   if(node.level==='continent'){name=node.name;break;}node=parents.get(node.parent_id);
  }
  if(!name)throw Error('Coverage location has no continent parent');
  for(const key of visited)roots.set(key,name);return name;
 };
 const selected=features.filter(feature=>(!owner||feature.properties.reference_owner===owner)&&(!continent||root(feature.properties.parent_id)===continent));
 const counts=new Map();for(const feature of selected){const key=feature.properties.reference_owner;counts.set(key,(counts.get(key)||0)+1);}
 const profiles=territories.filter(profile=>counts.has(profile.owner)).map(profile=>({...profile,selected_locations:counts.get(profile.owner),open_group_ids:continent?profile.open_group_ids.filter(id=>root(id)===continent):profile.open_group_ids}));
 return {features:selected,profiles};
}
