import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {nativeSequence,validateWitnessGeometry,witnessCellEffects,nativePolygonIntervals,nativeRowLatitudes} from '../src/native-grid.js';
import {validateWitnessGeometry as eagerValidate,witnessCellEffects as eagerEffects} from './fixtures/witness-primitives-eager.mjs';
const result=fn=>{try{return {value:fn()};}catch(error){return {name:error.name,message:error.message};}};
const cursor=values=>nativeSequence(values.length,()=>values.values());
const ring=[[0,0],[1,0],[1,1],[0,1],[0,0]];
const options={size:16,latitudes:nativeRowLatitudes(16),requestedRows:[{y:8,runs:[[0,16,1]]}],nativePolygonIntervals};
test('count-only witness traversal preserves the complete frozen primitive oracle',()=>{
 assert.equal(createHash('sha256').update(fs.readFileSync(new URL('./fixtures/witness-primitives-eager.mjs',import.meta.url))).digest('hex'),'a7584b775a0823157b6c38a0ac611b592890ff55ce5dea8a43acbd6462615041');
 const geometries=[];
 for(const points of [[],[[0,0]],[[0,0],[1,1]],ring,[...ring,[181,0]],[...ring,[NaN,0]],[...ring,null],[...ring,[0]],new Array(5)]){
  for(const coords of [points,cursor(points)]){
   for(const type of ['Point','MultiPoint','LineString'])geometries.push({type,coordinates:coords});
   for(const roster of [[coords],cursor([coords])]){
    geometries.push({type:'Polygon',coordinates:roster},{type:'MultiLineString',coordinates:roster});
    for(const polygons of [[roster],cursor([roster])])geometries.push({type:'MultiPolygon',coordinates:polygons});
   }
  }
 }
 geometries.push(null,{}, {type:'Unknown',coordinates:[]},{type:'Point',coordinates:[0,0],foreign:true},
  {type:'GeometryCollection',geometries:[]},{type:'GeometryCollection',geometries:new Array(1)});
 const cycle={type:'GeometryCollection',geometries:[]};cycle.geometries.push(cycle);geometries.push(cycle);
 geometries.push({type:'GeometryCollection',geometries:geometries.slice(0,12)});
 for(const geometry of geometries){
  assert.deepEqual(result(()=>validateWitnessGeometry(geometry)),result(()=>eagerValidate(geometry)));
  assert.deepEqual(result(()=>witnessCellEffects(geometry,options)),result(()=>eagerEffects(geometry,options)));
 }
});
test('count-only witness validation consumes complete coordinates without building flat polygons',t=>{
 const count=65537;let visits=0,closed=0,flats=0;
 const coordinates=nativeSequence(count,function*(){try{for(let i=0;i<count;i++){visits++;yield i===count-1?[0,0]:[i%2,i%3];}}finally{closed++;}});
 const flat=Array.prototype.flat;Array.prototype.flat=function(...args){flats++;return Reflect.apply(flat,this,args);};
 try{
 const geometry={type:'Polygon',coordinates:[coordinates]};
 assert.deepEqual(validateWitnessGeometry(geometry),{parts:1,vertices:count,polygons:1,segments:0,points:0,empty:false});
 assert.equal(visits,count);assert.equal(closed,1);assert.equal(flats,0);
 assert.deepEqual(eagerValidate(geometry),validateWitnessGeometry(geometry));assert.equal(flats,1);
 }finally{Array.prototype.flat=flat;}
});
test('count-only witness failure closes producer and preserves late failure precedence',()=>{
 for(const values of [[[0,0],[1,0],[1,1],[2,2]],[[0,0],[1,0],[1,1],[181,0]]]){
  let closes=0;const rows=nativeSequence(values.length,function*(){try{yield* values;}finally{closes++;}});
  const geometry={type:'Polygon',coordinates:[rows]};assert.deepEqual(result(()=>validateWitnessGeometry(geometry)),result(()=>eagerValidate(geometry)));assert.equal(closes,2);
 }
 const error=Error('late coordinate producer sentinel');let closes=0;
 const rows=nativeSequence(5,function*(){try{yield [0,0];yield [1,1];throw error;}finally{closes++;}});
 assert.throws(()=>validateWitnessGeometry({type:'Polygon',coordinates:[rows]}),e=>e===error);assert.equal(closes,1);
});
