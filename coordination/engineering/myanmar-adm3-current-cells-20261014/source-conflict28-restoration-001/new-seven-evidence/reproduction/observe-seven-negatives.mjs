import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../../src/native-grid.js';
import {valueSha} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const G='.takeover/private-recovery.git';
const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'};
const git=(...a)=>execFileSync('git',['-c','protocol.allow=never','--git-dir='+G,...a],{env,maxBuffer:24*1024*1024});
const sha=b=>createHash('sha256').update(b).digest('hex');
const evidence=JSON.parse(fs.readFileSync('.takeover/source28-native-feasibility/source-evidence.json'));
const original=JSON.parse(fs.readFileSync('.takeover/source28-native-feasibility/original-source28-native-contact-observation.json'));
const points=original.records.filter(r=>r.chosen.id.startsWith('gb:MMR:'));
const lookup=new Map();
for(const family of original.complete_original_families){
 const pieces=family.parts.map(pin=>{const encoded=git('cat-file','blob',pin.git_blob_oid);if(encoded.length!==pin.bytes||sha(encoded)!==pin.sha256)throw Error('Original encoded identity');const raw=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});if(raw.length!==pin.decoded_bytes||sha(raw)!==pin.decoded_sha256)throw Error('Original decoded identity');return raw;});
 const body=Buffer.concat(pieces);if(body.length!==family.whole_original_bytes||sha(body)!==family.whole_original_sha256)throw Error('Whole original family');
 const features=JSON.parse(body).features;
 for(const [ordinal,f] of features.entries()){
  const h=valueSha(f.geometry);const matches=lookup.get(h)??[];
  matches.push({family:family.key,source_id:family.key+':'+f.properties.shapeID,pointer:'/features/'+ordinal+'/geometry',parts:family.parts});lookup.set(h,matches);
 }
}
const raw=gunzipSync(git('cat-file','blob',original.native_latitudes.git_blob_oid),{maxOutputLength:2097328});if(sha(raw)!==original.native_latitudes.decoded_sha256)throw Error('Native latitude identity');
const latitudes=Float64Array.from({length:262166},(_,i)=>raw.readDoubleLE(i*8));
const records=[];let calls=0;const started=performance.now();
for(const target of evidence.targets){
 const features=target.territorial_exclusions.map((geometry,i)=>({id:String(i),pixelIndex:i+1,geometry}));const index=nativeRuntimeIndex(features);
 for(const y of [...new Set(points.filter(p=>p.chosen.id===target.id).map(p=>p.y))]){
  const scan=nativePolygonIntervals(index,{size:262166,latitudes,rowStart:y,rowEnd:y+1});calls++;
  for(const point of points.filter(p=>p.chosen.id===target.id&&p.y===y)){
   const contacts=(scan.rows.get(y)??[]).filter(r=>r.start<=point.x&&point.x<r.end).map(r=>{const ordinal=r.owner-1;const geometry_sha256=valueSha(target.territorial_exclusions[ordinal]);return {negative_ordinal:ordinal,geometry_sha256,complete_original_source_matches:lookup.get(geometry_sha256)??[]};});
   const boundaries=scan.ties.filter(t=>(t.start??t.x)<=point.x&&point.x<(t.end??t.x+1)).map(t=>({negative_ordinal:t.owner-1,kind:t.kind}));
   records.push({source_id:target.id,pixelIndex:target.pixelIndex,y,x:point.x,contacts,boundaries});
  }
 }
}
if(records.length!==7)throw Error('Exact seven point partition');
const result={kind:'seven-original-source-conflict-native-negative-contact-observation',actual_executing_accepted_commit:original.actual_executing_accepted_commit,source_evidence_input_commit:'82a195a8585a4f13f7e6ac924a1ada090c4a377f',whole_original_negative_geometries:evidence.targets.reduce((n,t)=>n+t.territorial_exclusions.length,0),records,calls,elapsed_seconds:(performance.now()-started)/1000,rss_bytes:process.memoryUsage().rss,limits:['Every original negative retained. This identifies exact interior contacts and whole-original source pointers; it does not adopt their contextual role or create native authority.','A boundary remains a veto; no geometry, positive coverage or native owner record was changed.']};
fs.writeFileSync('.takeover/source28-native-feasibility/seven-original-negative-contacts.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({keys:records.length,interior_contacts:records.reduce((n,r)=>n+r.contacts.length,0),boundary_keys:records.filter(r=>r.boundaries.length).length,unmatched_source_contacts:records.flatMap(r=>r.contacts).filter(c=>c.complete_original_source_matches.length!==1).length,calls,elapsed_seconds:result.elapsed_seconds,rss_bytes:result.rss_bytes}));
