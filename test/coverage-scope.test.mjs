import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {coverageScope} from '../src/coverage-scope.js';

test('continent filters follow location membership for overseas and transcontinental reference owners',()=>{
 const parents=new Map(['Europe','North America','South America','Oceania'].flatMap(name=>[{id:name,level:'continent',name,parent_id:null},{id:`province:${name}`,level:'province',name:'Province',parent_id:name}]).map(row=>[row.id,row]));
 const features=[['France','Europe'],['France','South America'],['United States','North America'],['United States','Oceania']].map(([owner,continent],i)=>({id:String(i),properties:{reference_owner:owner,parent_id:`province:${continent}`}}));
 const territories=[{owner:'France',continent:'Europe',open_group_ids:['Europe','South America']},{owner:'United States',continent:'Oceania',open_group_ids:['North America','Oceania']}];
 const north=coverageScope(features,parents,territories,{continent:'North America'});assert.equal(north.features.length,1);assert.equal(north.profiles[0].owner,'United States');assert.deepEqual(north.profiles[0].open_group_ids,['North America']);
 const france=coverageScope(features,parents,territories,{continent:'South America',owner:'France'});assert.equal(france.features.length,1);assert.equal(france.profiles[0].selected_locations,1);
 assert.equal(coverageScope(features,parents,territories,{owner:'France'}).features.length,2);assert.equal(coverageScope(features,parents,territories).features.length,4);
 assert.throws(()=>coverageScope([{properties:{parent_id:'missing'}}],parents,territories,{continent:'Europe'}),/no continent parent/);
});

test('all six continent scopes partition every prepared location and reconcile reference profiles',()=>{
 const indexPath=new URL('../data/world-index.json',import.meta.url);assert.ok(fs.existsSync(indexPath),'Prepared hierarchy required for exhaustive coverage check');
 const index=JSON.parse(fs.readFileSync(indexPath)),hierarchy=JSON.parse(fs.readFileSync(new URL('../data/hierarchy.json',import.meta.url))),parents=new Map(hierarchy.map(row=>[row.id,row])),features=[];
 for(const part of index.parts)for(const row of JSON.parse(fs.readFileSync(new URL(`../data/${part}`,import.meta.url))).features)features.push({id:row.id,properties:{reference_owner:row.properties.reference_owner,parent_id:row.properties.parent_id}});
 const review=JSON.parse(fs.readFileSync(new URL('../data/world-review.json',import.meta.url))),seen=new Set();
 for(const continent of hierarchy.filter(row=>row.level==='continent')){
  const scope=coverageScope(features,parents,review.territories,{continent:continent.name});assert.ok(scope.features.length>0);assert.equal(scope.profiles.reduce((sum,p)=>sum+p.selected_locations,0),scope.features.length);
  for(const feature of scope.features){assert.equal(seen.has(feature.id),false,'A location appears in only one continent');seen.add(feature.id);}
 }
 assert.equal(seen.size,features.length);assert.equal(features.length,49589);
});
