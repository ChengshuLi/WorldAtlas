import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {nativeDisplayContext} from '../src/native-location-context.js';
import {locationInventoryChanged,boundaryFootprintsChanged} from '../src/pixel-metadata.js';
import {NATIVE_METHOD} from '../src/ownership-method.js';
const source=fs.readFileSync(new URL('../src/main.js',import.meta.url),'utf8');
const start=source.indexOf('async function loadYear(next) {'),end=source.indexOf("\n$('#year-form')",start);
assert.ok(start>=0&&end>start);
// Execute the actual main function. Only DOM/network/render endpoints are
// isolated; state transition and cancellation control flow are not mirrored.
const body=source.slice(start,end);
const ring=[[0,0],[1,0],[1,1],[0,1],[0,0]];
const original={id:'A',pixelIndex:1,properties:{parent_id:'p',name:'A'},geometry:{type:'Polygon',coordinates:[ring]}};
function fixture({replacement=false}={}){
 const nodes=new Map(),renders=[],rebuilds=[],pending=[];let geometryReads=0;
 const $=id=>{if(!nodes.has(id))nodes.set(id,{checked:false,setAttribute(){}});return nodes.get(id);};
 const referenceData={features:[original],units:[],temporal:{history:[]},ownership:{method:NATIVE_METHOD},nativeLatitudes:new Float64Array(0)};
 const resolveTemporal=(reference,next)=>({features:replacement&&next===2020?[{...original,id:'D',pixelIndex:undefined}]:reference.features,units:[],entities:new Map()});
 const loadSnapshot=async next=>({boundaries:next===2020&&!replacement?[{location_id:'A',geometry:{type:'Polygon',coordinates:[[[0,0],[2,0],[2,1],[0,1],[0,0]]]}}]:[],states:[],attributes:[]});
 const prepareNativeLocationContext=(input,{signal})=>new Promise(resolve=>pending.push({input,signal,resolve:()=>resolve({grid:{method:NATIVE_METHOD},context:nativeDisplayContext(input.referenceFeatures,input.features)})}));
 const factory=new Function('$','referenceData','resolveTemporal','loadSnapshot','ensureGeometry','prepareNativeLocationContext','nativeDisplayContext',
  'locationInventoryChanged','boundaryFootprintsChanged','NATIVE_METHOD','renders','rebuilds',`
  let data=referenceData,year=2026,temporal,desiredYear,timer,controller,parents=new Map(),features=new Map(),polities,states=new Map(),boundaries=new Map();
  const formatYear=y=>String(y),yearToTick=y=>y;
  const resolveAttributes=()=>new Map();
  const geoLayer={updateMetadata(){}};
  const render=()=>renders.push({year,ids:data.features.map(f=>f.id)});
  const rebuildGeometry=value=>rebuilds.push(value);
  ${body}
  return {loadYear,getState:()=>({year,data,boundaries})};`);
 const app=factory($,referenceData,resolveTemporal,loadSnapshot,async()=>{geometryReads++;},prepareNativeLocationContext,nativeDisplayContext,
  locationInventoryChanged,boundaryFootprintsChanged,NATIVE_METHOD,renders,rebuilds);
 return {...app,referenceData,renders,rebuilds,pending,nodes,getGeometryReads:()=>geometryReads};
}
test('actual year-selection code retains coherent old date until changed native grid is ready',async()=>{
 const app=fixture(),loading=app.loadYear(2020);await new Promise(setImmediate);
 assert.equal(app.pending.length,1);assert.equal(app.getState().year,2026);
 assert.equal(app.getState().data,app.referenceData);assert.deepEqual(app.renders,[]);
 app.pending[0].resolve();await loading;
 assert.equal(app.getState().year,2020);assert.equal(app.rebuilds.length,1);
 assert.equal(app.rebuilds[0].grid.method,NATIVE_METHOD);
 assert.deepEqual(app.rebuilds[0].features.map(f=>f.id),['A']);
});
test('an old native result cannot replace a newer selected year even if worker completion ignores abort',async()=>{
 const app=fixture(),old=app.loadYear(2020);await new Promise(setImmediate);
 await app.loadYear(2021);assert.equal(app.getState().year,2021);
 assert.equal(app.pending[0].signal.aborted,true);
 app.pending[0].resolve();await old;
 assert.equal(app.getState().year,2021);assert.deepEqual(app.renders,[{year:2021,ids:['A']}]);
 assert.equal(app.rebuilds.length,0);
});
test('same-count identity replacement loads native source geometry and prepares a new display mapping',async()=>{
 const app=fixture({replacement:true}),loading=app.loadYear(2020);await new Promise(setImmediate);
 assert.equal(app.getGeometryReads(),1);assert.equal(app.pending.length,1);
 assert.equal(app.pending[0].input.features[0].id,'D');
 app.pending[0].resolve();await loading;
 assert.deepEqual(app.rebuilds[0].features.map(f=>f.id),['D']);
});
