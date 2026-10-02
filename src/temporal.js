// Shared, deterministic resolver: no interpolation or inferred habitation.
export function resolveTemporal(reference,year,examples=false){
  const catalog=reference.temporal || {entities:[],history:[],links:[]};
  const entities=new Map(catalog.entities.filter(e=>!e.is_example||examples).map(e=>[e.id,{...e,reference_name:e.name,status:year===2026?'reference':'unknown',attributes:{}}]));
  const available=catalog.history.filter(r=>!r.is_example||examples),chosen=new Map(),names=new Map();
  for(const r of available)if(r.field==='name'){if(!names.has(r.entity_id))names.set(r.entity_id,[]);names.get(r.entity_id).push(r.value);}
  for(const r of available){
    if(r.valid_from>year || r.valid_to<=year || r.name_role==='alias')continue;
    const key=`${r.entity_id}/${r.field}`,old=chosen.get(key);
    const priority=x=>Number(Boolean(x.is_example))*100+(x.field==='name'&&(x.method==='reference'||x.source_status==='reference')?10:0)+(x.language==='en'?0:x.language==='und'?1:2);
    if(!old || priority(r)<priority(old)||priority(r)===priority(old)&&String(r.id)<String(old.id))chosen.set(key,r);
  }
  for(const e of entities.values()){
    if(e.valid_from!=null && year<e.valid_from || e.valid_to!=null && year>=e.valid_to)e.status='not_exists';
    const name=chosen.get(`${e.id}/name`),parent=chosen.get(`${e.id}/parent`),existence=chosen.get(`${e.id}/existence`),attrs=chosen.get(`${e.id}/attributes`);
    e.display_name=name?.value || (year===2026?e.name:null);e.name_record=name;e.name_status=name?'dated':'reference';
    if(parent)e.parent_id=parent.value;e.parent_record=parent;
    if(existence && e.status!=='not_exists')e.status=existence.value;
    e.attribute_record=attrs;
    if(attrs)e.attributes={...attrs.value,source:attrs.source,is_example:attrs.is_example};
    e.search_names=[e.name,...(names.get(e.id)||[])];
  }
  const referenceUnits=new Map(reference.units.map(u=>[u.id,u]));
  const unitKinds=new Set(['province','area','region','subcontinent','continent']);
  const units=[...entities.values()].filter(e=>unitKinds.has(e.kind)).map(e=>({...referenceUnits.get(e.id),...e,level:e.kind,metadata:referenceUnits.get(e.id)?.metadata || {basis:'Dated entity registry'}}));
  const features=reference.features.filter(f=>entities.get(f.id)?.status!=='not_exists').map(f=>{
    const e=entities.get(f.id);return {...f,properties:{...f.properties,parent_id:e?.parent_id??f.properties.parent_id,temporal:e}};
  });
  return {units,features,entities,history:available,links:catalog.links.filter(r=>!r.is_example||examples)};
}
