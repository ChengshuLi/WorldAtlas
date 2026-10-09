import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {combineNativeBatch,retainedCountySourcePremises} from '../../../scripts/additive-gap-repair.mjs';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
import {nativePolygonIntervals} from '../../../src/native-grid.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const root=process.argv[2];if(!root)throw Error('Whole root assistance directory required');
const assistance=JSON.parse(fs.readFileSync(root+'/assistance-manifest.json'));
const read=name=>{const pin=assistance.files.find(pin=>pin.path.endsWith('/'+name));if(!pin)throw Error('Missing assistance pin');
 const body=fs.readFileSync(root+'/'+name);if(body.length!==pin.bytes||sha(body)!==pin.sha256)throw Error('Assistance body drift');return body;};
const owners=JSON.parse(read('complete-owner-rows.json'));
const prefix='research/geography/alaska-thirteen-source-fitness-20261008/sources/';
const measurementBody=fs.readFileSync('research/geography/alaska-thirteen-geometry-measurement-20261008/vintages/run-fourteen/measurement.json');
if(sha(measurementBody)!=='92c2ad119724ed9905943d94cb52c5bcb74310e38f331ebbd7f64bd6851821c5')throw Error('Original predecessor differs');
const measurement=JSON.parse(measurementBody),features=JSON.parse(fs.readFileSync(prefix+'candidate-components.geojson')).features;
const records=fs.readFileSync(prefix+'physical-query-rows.jsonl','utf8').trimEnd().split('\n').map(JSON.parse);
const old=JSON.parse(fs.readFileSync(prefix+'native-atlas-target-features.geojson')).features;
const contexts=['43500','45000','46500'].flatMap(part=>JSON.parse(gunzipSync(read('context/part-'+part+'.json.gz'))));
const latitudeBody=gunzipSync(execFileSync('git',['show','f2b129423c04d32b4b47ea36abae198651c50dae:coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'],{maxBuffer:32*1024*1024}));
if(sha(latitudeBody)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Latitude method drift');
const size=262166,latitudes=Float64Array.from({length:size},(_,y)=>latitudeBody.readDoubleLE(y*8)),sources=[],candidates=[];
const start=performance.now();
for(const sourceCase of measurement.cases){
 const target=contexts.find(row=>row.id===sourceCase.county_target.atlas_target_id),metadata=old.find(row=>row.id===target?.id);
 if(!target||!metadata)throw Error('Missing current complete target');
 const candidate=features.find(row=>row.id===sourceCase.component_id).geometry,record=records.find(row=>row.component_id===sourceCase.component_id);
 const premises=retainedCountySourcePremises({record,candidate,sourceCase,sourceScope:measurement,target:{...metadata,geometry:target.geometry}});
 sources.push({...premises,pixelIndex:target.pixelIndex});if(!premises.source_compatible)continue;
 const points=candidate.coordinates.flat(1),max=Math.max(...points.map(p=>p[1])),min=Math.min(...points.map(p=>p[1]));
 const first=Math.max(0,latitudes.findIndex(value=>value<=max)-1),stop=latitudes.findIndex(value=>value<min),end=stop<0?size:Math.min(size,stop+1);
 const native=nativePolygonIntervals(nativeRuntimeIndex([{id:target.id,pixelIndex:target.pixelIndex,geometry:candidate}]),{size,latitudes,rowStart:first,rowEnd:end});
 candidates.push({component_id:sourceCase.component_id,target_id:target.id,pixelIndex:target.pixelIndex,row_start:first,row_end:end,
  rows:Array.from({length:end-first},(_,i)=>({y:first+i,runs:(native.rows.get(first+i)??[]).map(span=>[span.start,span.end,target.pixelIndex])}))});
}
const result=combineNativeBatch({scopeIds:measurement.assigned_scope.component_ids,sourceRows:sources,candidates,ownerRows:owners,size});
process.stdout.write(JSON.stringify({kind:'bounded-native-batch-mechanism-control',qualifying_cold_execution:false,activation:false,
 source_approval:false,elapsed_ms:performance.now()-start,component_count:result.decisions.length,source_compatible:sources.filter(row=>row.source_compatible).length,
 source_exceptions:result.source_exceptions,native_conflicts:result.native_conflicts,assigned_components:result.assigned_components,zero_cell_components:result.zero_cell_components,
 assigned_cells:result.assigned_cells,removed_cells:result.removed_cells,reassigned_cells:result.reassigned_cells,
 decisions:result.decisions.map(({component_id,disposition,reason_kind,native_cells,failed_premises,native_conflicts})=>({component_id,disposition,reason_kind,native_cells,failed_premises,native_conflicts})),
 limits:['Mechanism control over complete supplied current windows; not yet independently frozen source/cold/release acceptance.','Explicit v8 baseline; N2 rebind required before activation.']},null,2)+'\n');
