import test from 'node:test';
import assert from 'node:assert/strict';
import {createEntityRegistry} from '../web/entity-registry.js';
import {withEntityRegistry, v7ContinentSections} from '../web/v7-entity-adapter.js';
import {makeLegendItems, activeCategoryMask, activeCategoryCodes, matchingLegendItems} from '../web/legend-model.js';
import {prepareEntityMetadata} from '../scripts/prepare_entity_metadata.mjs';

const categories = [
  {id:1,name:'Africa',physical_class:'water',rgb:[1,2,3]},
  {id:2,name:'Asia',physical_class:'water',rgb:[4,5,6]},
  {id:7,name:'Atlantic Ocean',physical_class:'water',rgb:[7,8,9]},
  {id:17,name:'Africa',physical_class:'land',rgb:[10,11,12]},
  {id:18,name:'Asia',physical_class:'land',rgb:[13,14,15]},
];
const bootstrap = () => withEntityRegistry({categories});

test('legend preserves counts, colors, ordering, searching, and V7 selection', () => {
  const meta=bootstrap(), items=makeLegendItems(meta, {1:10,2:20,7:30,17:40,18:50});
  assert.deepEqual(items.map(({name,count,color,codes})=>({name,count,color,codes})), [
    {name:'Africa',count:50,color:[10,11,12],codes:[1,17]},
    {name:'Asia',count:70,color:[13,14,15],codes:[2,18]},
    {name:'Atlantic Ocean',count:30,color:[7,8,9],codes:[7]},
  ]);
  assert.equal(matchingLegendItems(items,' AFR ')[0].name,'Africa');
  assert.equal(activeCategoryMask(items,new Set([items[0].id])),(1<<1)|(1<<17));
  assert.deepEqual([...activeCategoryCodes(items,new Set([items[0].id]))],[1,17]);
  assert.deepEqual(v7ContinentSections(meta).map(x=>x.name),['Africa','Asia']);
});

test('Neon export controls identity and display names, with land and water bound together', () => {
  const original=bootstrap();
  const entities=original.entity_registry.entities.map(e=>({...e,id:e.id+100,name:e.id===1?'Renamed':e.name}));
  const exported={entity_registry:{...original.entity_registry, revision:'draft-2', entities},
    category_bindings:original.categories.map(c=>({code:c.id,entity_id:c.entity_id+100,physical_class:c.physical_class}))};
  const meta=prepareEntityMetadata({categories},exported), items=makeLegendItems(meta,{1:2,17:3});
  assert.equal(items[0].name,'Renamed'); assert.equal(items[0].entity_id,101); assert.equal(items[0].count,5);
  exported.category_bindings.find(b=>b.code===17).entity_id=102;
  assert.throws(()=>prepareEntityMetadata({categories},exported),/share one entity/);
  exported.category_bindings.find(b=>b.code===17).entity_id=101;
  exported.category_bindings.find(b=>b.code===2).entity_id=101;
  assert.throws(()=>prepareEntityMetadata({categories},exported),/distinct entities/);
});

test('hierarchy resolves parents and rejects invalid IDs, levels, and bindings', () => {
  const levels=['continent','subcontinent','region','area','province','location'];
  const entities=levels.map((level,i)=>({id:i+1,name:level,level,parent_id:i?i:null,...(level==='location'?{physical_class:'land'}:{})}));
  const snapshot={schema_version:'worldatlas-entity-registry-v1',revision:'r',status:'draft',entities};
  const registry=createEntityRegistry(snapshot);
  assert.equal(registry.ancestorAtLevel(6,'region').id,3);
  assert.equal(registry.childrenOf(1)[0].id,2);
  assert.equal(makeLegendItems({entity_registry:snapshot,categories:[{id:31,entity_id:6,physical_class:'land',rgb:[0,0,0]}]}, {31:2})[0].entity_id,1);
  assert.throws(()=>createEntityRegistry({...snapshot,entities:entities.map(e=>e.id===4?{...e,parent_id:1}:e)}),/parent/);
  assert.throws(()=>makeLegendItems({entity_registry:snapshot,categories:[{id:31,entity_id:6,physical_class:'water',rgb:[0,0,0]}]},{}),/physical class/);
  assert.throws(()=>makeLegendItems({entity_registry:snapshot,categories:[{id:31,entity_id:999,physical_class:'land',rgb:[0,0,0]}]},{}),/Unknown entity/);
});
