// Fixed atlas vocabulary. IDs identify classes; source wording remains evidence.
// Accept only listed spellings, never arbitrary text or inferred finer classes.
const entry=(id,label,aliases=[])=>Object.freeze({id,label,aliases:Object.freeze(aliases)});
export const environmentClassifications=Object.freeze({
 topography:Object.freeze([
  entry('topography:flat','Flatland',['flat','flatland']),
  entry('topography:peak','Peak',['peak']),
  entry('topography:ridge','Ridge',['ridge']),
  entry('topography:shoulder','Shoulder',['shoulder']),
  entry('topography:spur','Spur',['spur']),
  entry('topography:slope','Slope',['slope']),
  entry('topography:hollow','Hollow',['hollow']),
  entry('topography:footslope','Footslope',['footslope']),
  entry('topography:valley','Valley',['valley']),
  entry('topography:pit','Pit',['pit']),
  entry('topography:hills','Hills',['hills']),
  entry('topography:mountains','Mountains',['mountains']),
 ]),
 vegetation:Object.freeze([
  entry('vegetation:tropical-moist-broadleaf-forest','Tropical & Subtropical Moist Broadleaf Forests'),
  entry('vegetation:tropical-dry-broadleaf-forest','Tropical & Subtropical Dry Broadleaf Forests'),
  entry('vegetation:tropical-conifer-forest','Tropical & Subtropical Coniferous Forests'),
  entry('vegetation:temperate-broadleaf-mixed-forest','Temperate Broadleaf & Mixed Forests'),
  entry('vegetation:temperate-conifer-forest','Temperate Conifer Forests'),
  entry('vegetation:boreal-forest','Boreal Forests/Taiga'),
  entry('vegetation:tropical-grassland-savanna-shrubland','Tropical & Subtropical Grasslands, Savannas & Shrublands'),
  entry('vegetation:temperate-grassland-savanna-shrubland','Temperate Grasslands, Savannas & Shrublands'),
  entry('vegetation:flooded-grassland-savanna','Flooded Grasslands & Savannas'),
  entry('vegetation:montane-grassland-shrubland','Montane Grasslands & Shrublands'),
  entry('vegetation:tundra','Tundra',['tundra']),
  entry('vegetation:mediterranean-forest-woodland-scrub','Mediterranean Forests, Woodlands & Scrub'),
  entry('vegetation:desert-xeric-shrubland','Deserts & Xeric Shrublands'),
  entry('vegetation:mangroves','Mangroves',['mangroves']),
  entry('vegetation:farmlands','Farmlands',['farmlands']),
  entry('vegetation:woodlands','Woodlands',['woodlands']),
 ]),
 climate:Object.freeze([
  entry('climate:Af','Af tropical rainforest',['Af']),
  entry('climate:Am','Am tropical monsoon',['Am']),
  entry('climate:Aw','Aw tropical savanna',['Aw']),
  entry('climate:BWh','BWh hot desert',['BWh']),
  entry('climate:BWk','BWk cold desert',['BWk']),
  entry('climate:BSh','BSh hot steppe',['BSh']),
  entry('climate:BSk','BSk cold steppe',['BSk']),
  entry('climate:Csa','Csa hot-summer Mediterranean',['Csa']),
  entry('climate:Csb','Csb warm-summer Mediterranean',['Csb']),
  entry('climate:Csc','Csc cold-summer Mediterranean',['Csc']),
  entry('climate:Cwa','Cwa dry-winter humid subtropical',['Cwa']),
  entry('climate:Cwb','Cwb subtropical highland',['Cwb']),
  entry('climate:Cwc','Cwc cold subtropical highland',['Cwc']),
  entry('climate:Cfa','Cfa humid subtropical',['Cfa']),
  entry('climate:Cfb','Cfb oceanic',['Cfb']),
  entry('climate:Cfc','Cfc subpolar oceanic',['Cfc']),
  entry('climate:Dsa','Dsa hot dry-summer continental',['Dsa']),
  entry('climate:Dsb','Dsb warm dry-summer continental',['Dsb']),
  entry('climate:Dsc','Dsc cold dry-summer continental',['Dsc']),
  entry('climate:Dsd','Dsd very cold dry-summer continental',['Dsd']),
  entry('climate:Dwa','Dwa hot dry-winter continental',['Dwa']),
  entry('climate:Dwb','Dwb warm dry-winter continental',['Dwb']),
  entry('climate:Dwc','Dwc dry-winter subarctic',['Dwc']),
  entry('climate:Dwd','Dwd very cold dry-winter subarctic',['Dwd']),
  entry('climate:Dfa','Dfa hot humid continental',['Dfa']),
  entry('climate:Dfb','Dfb warm humid continental',['Dfb']),
  entry('climate:Dfc','Dfc subarctic',['Dfc']),
  entry('climate:Dfd','Dfd very cold subarctic',['Dfd']),
  entry('climate:ET','ET tundra',['ET']),
  entry('climate:EF','EF ice cap',['EF']),
  entry('climate:oceanic','Oceanic',['oceanic']),
  entry('climate:mediterranean','Mediterranean',['mediterranean']),
 ]),
});
const lookups=new Map(Object.entries(environmentClassifications).map(([attribute,entries])=>{
 const values=new Map();
 for(const classification of entries)for(const value of [classification.id,classification.label,...classification.aliases]){
  if(values.has(value)&&values.get(value)!==classification)throw Error('Conflicting environmental classification alias');
  values.set(value,classification);
 }
 return [attribute,values];
}));
export const environmentalAttributes=Object.freeze(Object.keys(environmentClassifications));
export function environmentalClassification(attribute,value){return lookups.get(attribute)?.get(value)??null;}
export function validEnvironmentalClassification(attribute,value){return !lookups.has(attribute)||value===null||Boolean(environmentalClassification(attribute,value));}
export function classificationValues(attribute){return [...(lookups.get(attribute)?.keys()??[])];}
export function requireEnvironmentalClassification(attribute,value){
 if(!validEnvironmentalClassification(attribute,value))throw Error(`Invalid ${attribute} classification; choose a fixed classification ID or label, or null for unknown.`);
}
