import {attributes,ranks,levels,validYear} from './src/model.js';
import {validEnvironmentalClassification} from './src/environment-classifications.js';
export function syncEntities(db){
  db.exec(`INSERT INTO entities(id,kind,name,parent_id) SELECT id,level,name,parent_id FROM units WHERE true ON CONFLICT(id) DO UPDATE SET name=excluded.name,parent_id=excluded.parent_id;
    INSERT INTO entities(id,kind,name,parent_id) SELECT id,'location',name,parent_id FROM locations WHERE true ON CONFLICT(id) DO UPDATE SET name=excluded.name,parent_id=excluded.parent_id;`);
}
export function temporalCatalog(db){
  return {entities:db.prepare('SELECT * FROM entities').all(),history:db.prepare('SELECT * FROM entity_history').all().map(r=>({...r,value:JSON.parse(r.value)})),links:db.prepare('SELECT * FROM entity_links').all()};
}
const text=(v)=>typeof v==='string' && v.trim().length>0 && v.length<=2000;
export function importTemporal(db,payload){
  syncEntities(db);
  const get=id=>db.prepare('SELECT * FROM entities WHERE id=?').get(id);
  for(const e of payload.entities || []){
    if(!text(e.id)||!text(e.name))throw Error('Entity ID and reference name are required');
    if(e.kind!=='settlement' && !get(e.id))throw Error('Import geographic entities through units or polygon locations first');
    const existing=get(e.id);if(existing && e.parent_id!=null && e.parent_id!==existing.parent_id)throw Error('Use dated parent history to change entity membership');if(existing && existing.kind!==e.kind)throw Error('Entity kind is immutable');
    if((e.valid_from!=null||e.valid_to!=null) && !text(e.source))throw Error('Entity lifetime needs a source');
    db.prepare('INSERT INTO entities(id,kind,name,parent_id,valid_from,valid_to,source,is_example) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET valid_from=excluded.valid_from,valid_to=excluded.valid_to,source=excluded.source').run(e.id,e.kind,e.name,e.parent_id??existing?.parent_id??null,e.valid_from??null,e.valid_to??null,e.source??null,e.is_example??0);
  }
  function parentCheck(entity,parent){
    const expected=entity.kind==='settlement'?'location':levels[levels.indexOf(entity.kind)+1];
    if(entity.kind==='continent'){if(parent!=null)throw Error('Continent has no parent');return;}
    if(get(parent)?.kind!==expected)throw Error('Temporal parent must be the adjacent hierarchy level');
  }
  for(const e of payload.entities || [])parentCheck(get(e.id),get(e.id).parent_id);
  for(const r of payload.entity_history || []){
    const e=get(r.entity_id);if(!e)throw Error('Unknown historical entity');
    if(!text(r.id)||!text(r.source)||!validYear(r.valid_from)||!(validYear(r.valid_to)||r.valid_to===2027)||r.valid_to<=r.valid_from)throw Error('Invalid dated entity record');
    if(r.field!=='existence' && (e.valid_from!=null && r.valid_from<e.valid_from || e.valid_to!=null && r.valid_to>e.valid_to))throw Error('Record exceeds entity lifetime');
    if(r.name_role==='alias' && r.field!=='name')throw Error('Aliases are names only');
    if(r.field!=='name' && r.language && r.language!=='und')throw Error('Only names have a language');
    if(r.field==='name' && !text(r.value))throw Error('Invalid historical name');
    if(r.field==='parent')parentCheck(e,r.value);
    if(r.field==='existence' && !['exists','not_exists','unknown'].includes(r.value))throw Error('Invalid existence status');
    if(r.field==='attributes'){
      if(!r.value || typeof r.value!=='object' || Array.isArray(r.value))throw Error('Invalid attributes');
      for(const [k,v] of Object.entries(r.value)){
        if(![...attributes,'habitation'].includes(k))throw Error('Unknown dated attribute');
        if(v==null)continue;
        if(k==='population' ? !Number.isSafeInteger(v)||v<0 : !text(v))throw Error('Invalid dated attribute');
        if(k==='rank'&&!ranks.includes(v))throw Error('Invalid rank');
        if(k==='habitation'&&!['inhabited','uninhabited','unknown'].includes(v))throw Error('Invalid habitation');
        if(!validEnvironmentalClassification(k,v))throw Error(`Invalid fixed ${k} classification`);
      }
      if(r.value.habitation==='uninhabited' && (r.value.rank!=null&&r.value.rank!=='unsettled' || r.value.population>0))throw Error('Uninhabited cannot have an inhabited settlement rank or positive population');
      if(r.value.rank==='unsettled' && (r.value.habitation==='inhabited'||r.value.population>0))throw Error('Unsettled conflicts with inhabited evidence or positive population');
    }
    db.prepare('INSERT INTO entity_history(id,entity_id,field,valid_from,valid_to,language,name_role,value,source,is_example) VALUES (?,?,?,?,?,?,?,?,?,?)').run(r.id,r.entity_id,r.field,r.valid_from,r.valid_to,r.language||'und',r.name_role||'preferred',JSON.stringify(r.value),r.source,r.is_example??0);
  }
  for(const r of payload.entity_links || []){
    if(!text(r.id)||!text(r.source)||get(r.predecessor_id)?.kind!==get(r.successor_id)?.kind)throw Error('Invalid successor link');
    db.prepare('INSERT INTO entity_links VALUES (?,?,?,?,?,?,?)').run(r.id,r.predecessor_id,r.successor_id,r.kind,r.year,r.source,r.is_example??0);
  }
  // Check membership and existence together at every event, including interval ends.
  // Strict adjacent levels make cycles impossible.
  if((payload.entities?.length||0)+(payload.entity_history?.length||0)){
    const catalog=temporalCatalog(db),entities=new Map(catalog.entities.map(e=>[e.id,e]));
    const relevant=new Set((payload.entity_history||[]).filter(r=>['parent','existence'].includes(r.field)).map(r=>r.entity_id));
    for(const e of payload.entities||[])relevant.add(e.id);
    const dependents=catalog.history.filter(r=>r.field==='parent');
    for(const e of catalog.entities)if(relevant.has(e.parent_id))relevant.add(e.id);
    for(const r of dependents)if(relevant.has(r.value))relevant.add(r.entity_id);
    const events=[...new Set([-3000,2026,...catalog.history.flatMap(r=>[r.valid_from,r.valid_to]),...catalog.entities.flatMap(e=>[e.valid_from,e.valid_to]).filter(v=>v!=null)])].filter(validYear);
    for(const examples of [false,true])for(const year of events){
      const records=new Map();for(const r of catalog.history)if(r.valid_from<=year && r.valid_to>year && (!r.is_example||examples) && ['parent','existence'].includes(r.field)){
        const k=`${r.entity_id}/${r.field}`,old=records.get(k);if(!old||r.is_example<old.is_example)records.set(k,r);
      }
      const exists=e=>e && (!e.is_example||examples) && (e.valid_from==null||e.valid_from<=year) && (e.valid_to==null||e.valid_to>year) && records.get(`${e.id}/existence`)?.value!=='not_exists';
      for(const e of entities.values()){const id=e.id;if(!exists(e)||e.kind==='continent')continue;
        const p=entities.get(records.get(`${id}/parent`)?.value??e.parent_id);
        if(!exists(p))throw Error(`Dated hierarchy has an absent parent: ${id} at ${year}`);
      }
    }
  }
}
