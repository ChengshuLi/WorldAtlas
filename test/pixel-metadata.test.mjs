import {test} from 'node:test';
import assert from 'node:assert/strict';
import {updateLocationMetadata,locationInventoryChanged,boundaryFootprintsChanged} from '../src/pixel-metadata.js';
import {resolveTemporal} from '../src/temporal.js';
import {compileOwnership,packOwnership,pickOwnership} from '../src/pixel-ownership.js';
import {borderKind} from '../src/pixel-grid.js';

const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1],[0,0]]]};
const feature=(id,parent_id)=>({id,geometry,properties:{id,name:id,parent_id}});
const ring=(left,right)=>new Float64Array([left,0,right,0,right,4,left,4,left,0]);
const units=[['c','continent',null],['s','subcontinent','c'],['r','region','s'],['a','area','r'],['p','province','a'],['p2','province','a']].map(([id,level,parent_id])=>({id,level,name:id,parent_id}));
const reference={units,features:[feature('l','p'),feature('n','p2')],temporal:{entities:[...units.map(u=>({...u,kind:u.level})),{id:'l',kind:'location',name:'l',parent_id:'p'},{id:'n',kind:'location',name:'n',parent_id:'p2'}],history:[{id:'dated-parent',entity_id:'l',field:'parent',value:'p2',valid_from:1000,valid_to:1100,source:'Explicit unit-test membership evidence',method:'direct',is_example:0}],links:[]}};

test('dated membership changes province lookup and picking records while retaining exact grid cells and geometry',()=>{
 const index=reference.features.map((f,i)=>({index:i+1,feature:f,polygons:[[ring(i*2,i*2+2)]],bounds:[i*2,0,i*2+2,4]}));
 const ownership=packOwnership(compileOwnership(index,8));
 const rows=ownership.rows,runs=ownership.runs,footprints=index.map(item=>item.feature.geometry),polygons=index.map(item=>item.polygons),bounds=index.map(item=>item.bounds);
 assert.equal(borderKind(1,2,updateLocationMetadata(index,resolveTemporal(reference,999).features)),'province');
 const dated=resolveTemporal(reference,1000);assert.equal(locationInventoryChanged(reference.features,dated.features),false);
 const provinces=updateLocationMetadata(index,dated.features);
 assert.equal(borderKind(1,2,provinces),'location');assert.equal(index[pickOwnership(ownership,.5,.5)-1].feature.properties.parent_id,'p2');
 assert.equal(index[0].feature.properties.temporal.parent_record.source,'Explicit unit-test membership evidence');
 assert.equal(ownership.rows,rows);assert.equal(ownership.runs,runs);
 index.forEach((item,i)=>{assert.equal(item.feature.geometry,footprints[i]);assert.equal(item.polygons,polygons[i]);assert.equal(item.bounds,bounds[i]);});
 assert.equal(borderKind(1,2,updateLocationMetadata(index,resolveTemporal(reference,1100).features)),'province');
 assert.equal(index[pickOwnership(ownership,.5,.5)-1].feature.properties.parent_id,'p');
 assert.equal(reference.features[0].properties.parent_id,'p','Reference membership remains immutable');
 for(let y=0;y<4;y++)for(let x=0;x<4;x++)assert.equal(pickOwnership(ownership,x+.5,y+.5),x<2?1:2);
});

test('metadata refresh accepts reordered identities and atomically rejects replacements, missing and duplicate locations',()=>{
 const original=[feature('l','p'),feature('n','p2')],index=original.map((f,i)=>({index:i+1,feature:f}));
 const next=[feature('n','p'),feature('l','p2')];
 assert.equal(locationInventoryChanged(original,next),false);assert.deepEqual(updateLocationMetadata(index,next),[null,'p2','p']);
 const before=index.map(item=>item.feature);
 for(const invalid of [[feature('l','p')],[feature('l','p'),feature('l','p2')],[feature('l','p'),feature('replacement','p2')]]){
  assert.equal(locationInventoryChanged(original,invalid),true);assert.throws(()=>updateLocationMetadata(index,invalid),/inventory changed/);
  assert.deepEqual(index.map(item=>item.feature),before,'Failed refresh cannot leave partially updated picking metadata');
 }
 assert.throws(()=>updateLocationMetadata([{index:1,feature:original[0]},{index:2,feature:original[0]}],original),/inventory changed/,'An invalid duplicate renderer identity cannot omit a real location');
});

test('boundary geometry cache ignores source/date/provenance changes but detects actual dated footprints',()=>{
 const previous=new Map([['l',{geometry,source:'Original evidence',valid_from:1000,valid_to:1100}]]);
 const copied=JSON.parse(JSON.stringify(geometry));
 const next=new Map([['l',{geometry:{coordinates:copied.coordinates,type:copied.type},source:'Independent corroboration',valid_from:1050,valid_to:1060,metadata:{source_sha256:'another-source'}}]]);
 assert.equal(boundaryFootprintsChanged(previous,next),false);
 assert.equal(boundaryFootprintsChanged(previous,new Map([...next].reverse())),false);
 const moved=JSON.parse(JSON.stringify(geometry));moved.coordinates[0][1][0]=2;
 assert.equal(boundaryFootprintsChanged(previous,new Map([['l',{geometry:moved}]])),true);
 assert.equal(boundaryFootprintsChanged(previous,new Map()),true);
 assert.equal(boundaryFootprintsChanged(previous,new Map([['other-location',{geometry}]])),true);
 assert.equal(previous.get('l').source,'Original evidence','Render-cache comparison never changes provenance');
});
