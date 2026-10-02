import {locationAttributes,unresolvedAttributeStatuses} from './src/attributes.js';
import {ranks,validYear} from './src/model.js';
const text=v=>typeof v==='string'&&v.trim().length>0&&v.length<=2000;
const categorical=['owner','culture','religion'];
export function importAttributes(db,payload){
 for(const e of payload.attribute_entities||[]){if(!text(e.id)||!text(e.name)||!text(e.source)||!categorical.includes(e.kind))throw Error('Category identity, kind, name and source required');db.prepare('INSERT INTO attribute_entities VALUES (?,?,?,?)').run(e.id,e.kind,e.name,e.source);}
 for(const r of payload.attribute_records||[]){
  if(!text(r.id)||!text(r.location_id)||!text(r.source)||!Object.hasOwn(r,'value')||r.value===undefined||!locationAttributes.includes(r.attribute)||!validYear(r.valid_from)||!(validYear(r.valid_to)||r.valid_to===2027)||r.valid_to<=r.valid_from)throw Error('Invalid attribute evidence');
  if(r.value!=null){if(r.attribute==='population'){if(!Number.isSafeInteger(r.value)||r.value<0)throw Error('Invalid population');}else if(!text(r.value))throw Error('Attribute must have one scalar value');}
  if(unresolvedAttributeStatuses.includes(r.status)&&(r.value!==null||r.category_id!=null))throw Error('Unresolved attribute status requires null value and category_id');
  if(categorical.includes(r.attribute)&&r.value!=null&&!text(r.category_id))throw Error('Stable category_id required');
  if(r.category_id!=null&&(!categorical.includes(r.attribute)||r.value==null))throw Error('Category ID requires a known categorical value');
  if(r.attribute==='rank'&&r.value!=null&&!ranks.includes(r.value))throw Error('Invalid rank');
  if(r.attribute==='habitation'&&r.value!=null&&!['inhabited','uninhabited','unknown'].includes(r.value))throw Error('Invalid habitation');
  if(r.metadata!=null&&(typeof r.metadata!=='object'||Array.isArray(r.metadata)))throw Error('Attribute provenance metadata must be an object');
  const entity=db.prepare('SELECT valid_from,valid_to FROM entities WHERE id=?').get(r.location_id);
  if(entity&&(entity.valid_from!=null&&r.valid_from<entity.valid_from||entity.valid_to!=null&&r.valid_to>entity.valid_to))throw Error('Attribute record exceeds entity lifetime');
  db.prepare('INSERT INTO attribute_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)').run(r.id,r.location_id,r.attribute,JSON.stringify(r.value??null),r.category_id??null,r.valid_from,r.valid_to,r.method||'direct',r.status||(r.is_example?'example':'sourced'),r.source,r.is_example??0,JSON.stringify(r.metadata||{}));
 }
}
