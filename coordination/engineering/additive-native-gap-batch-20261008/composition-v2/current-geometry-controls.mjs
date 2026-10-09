import assert from 'node:assert/strict';
import fs from 'node:fs';
import {preservedNativePolygonGroups,requireDisjointAddedGeometry} from './current-geometry.mjs';
const rect=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const old=rect(0,0,1,1),candidate=rect(4,4,5,5),added=rect(2,2,3,3);
const reversed=structuredClone(old);reversed.coordinates[0].reverse();
assert.equal(preservedNativePolygonGroups(old,reversed).preserved_polygons,1);
const current={type:'MultiPolygon',coordinates:[reversed.coordinates,added.coordinates]};
assert.equal(requireDisjointAddedGeometry(old,current,[candidate]).added_polygon_bounds.length,1);
const hole=rect(.2,.2,.3,.3).coordinates[0],hole2=rect(.5,.5,.6,.6).coordinates[0];
const holed={type:'Polygon',coordinates:[old.coordinates[0],hole,hole2]};
const holedNext={type:'Polygon',coordinates:[reversed.coordinates[0],hole2.slice(1,-1).concat([hole2[0],hole2[1]]),[...hole].reverse()]};
assert.equal(preservedNativePolygonGroups(holed,holedNext).preserved_polygons,1);
let negatives=0;const rejects=fn=>{assert.throws(fn);negatives++;};
rejects(()=>preservedNativePolygonGroups(old,added));
const drift=structuredClone(old);drift.coordinates[0][1][0]+=Number.EPSILON;rejects(()=>preservedNativePolygonGroups(old,drift));
rejects(()=>requireDisjointAddedGeometry(old,current,[added]));
rejects(()=>requireDisjointAddedGeometry(old,current,[rect(3,2,4,3)]));
const dateline={type:'Polygon',coordinates:[[[170,0],[-170,0],[-170,1],[170,1],[170,0]]]};
rejects(()=>requireDisjointAddedGeometry(old,{type:'MultiPolygon',coordinates:[old.coordinates,dateline.coordinates]},[rect(175,.2,176,.3)]));
const zero=rect(0,0,1,1),signed=structuredClone(zero);signed.coordinates[0][0][0]=-0;signed.coordinates[0].at(-1)[0]=-0;rejects(()=>preservedNativePolygonGroups(zero,signed));
rejects(()=>preservedNativePolygonGroups({type:'MultiPolygon',coordinates:[old.coordinates,old.coordinates]},old));
const root='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/';
const composed=JSON.parse(fs.readFileSync(root+'composed-original-ledger.json'));
const targets=new Map();for(const row of composed.rows)if(['assigned','zero-cell'].includes(row.disposition)){
 const value=targets.get(row.target_id)??{base:row.base_geometry,primitives:[]};value.primitives.push(row.geometry);targets.set(row.target_id,value);}
for(const value of targets.values())assert.equal(requireDisjointAddedGeometry(value.base,value.base,value.primitives).added_polygon_bounds.length,0);
fs.writeFileSync(root+'current-geometry-controls.json',JSON.stringify({kind:'exact-native-polygon-group-applicability-controls',
 fixture_positives:3,original_target_groups:targets.size,negative_controls:negatives,
 limits:['Actual original target pointsets with unchanged before-state plus conservative fixtures. Proposed/current v9 pointsets not yet qualified; bounding-box overlap refuses rather than inferring disjointness.']},null,2)+'\n');
console.log(JSON.stringify({fixture_positives:3,original_targets:targets.size,negatives}));
