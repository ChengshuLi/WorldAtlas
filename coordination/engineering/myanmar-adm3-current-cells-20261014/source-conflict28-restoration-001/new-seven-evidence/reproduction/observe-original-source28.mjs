import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../../src/native-grid.js';
const G='.takeover/private-recovery.git', C='34981099cd03677b9ba374a4de6bf73cf65b0646';
const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_OPTIONAL_LOCKS:'0'};
const sha=b=>createHash('sha256').update(b).digest('hex');
const git=(...a)=>execFileSync('git',['-c','protocol.allow=never','--git-dir='+G,...a],{env,maxBuffer:24*1024*1024});
if(git('rev-parse',C).toString().trim()!==C)throw Error('Actual accepted commit unavailable');
const read=(commit,path)=>{const entry=git('ls-tree',commit,'--',path).toString().trim();const m=/^100644 blob ([a-f0-9]{40})\t/.exec(entry);if(!m)throw Error('Ordinary whole-body tree path required '+path);const b=git('cat-file','blob',m[1]);if(createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex')!==m[1])throw Error('Git identity');return {b,pin:{commit,path,mode:'100644',git_blob_oid:m[1],bytes:b.length,sha256:sha(b)}};};
const source='.takeover/local-recovery/.cache/worker3-mmr3483-opportunity-001/conflict28-source-choice-final.json';
const proposal=fs.readFileSync(source);if(sha(proposal)!=='b95b12c91aec5cebb5bdde64a6c640c3dce577d7e84382104171cd6b00a73c60')throw Error('Literal original proposal');
const original=JSON.parse(proposal), records=original.records.map(r=>({y:r.y,x:r.x,chosen:r.selected_current_location,candidate_owners:r.candidate_owners,source_sids:r.source_sids,source_hits:[],source_boundary_contacts:[]}));
if(records.length!==28||new Set(records.map(p=>p.y+':'+p.x)).size!==28)throw Error('Exact28 roster');
const cat=read(C,'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'), catalogue=JSON.parse(cat.b);
const lp=read(C,'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz');if(lp.pin.sha256!=='ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147')throw Error('Normative encoded latitude');
const lat=gunzipSync(lp.b,{maxOutputLength:2097328});if(lat.length!==2097328||sha(lat)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Normative decoded latitude');
const latitudes=Float64Array.from({length:262166},(_,i)=>lat.readDoubleLE(i*8));
const rows=[...new Set(records.map(r=>r.y))].sort((a,b)=>a-b);const familyObservations=[];let calls=0;
const started=performance.now();
for(const key of ['gb:MMR:ADM1','gb:MMR:ADM2','gb:MMR:ADM3','gb:THA:ADM1','gb:THA:ADM2']){
 const family=catalogue.products.find(p=>p.key===key);if(!family)throw Error('Missing complete family');
 const partPins=[],pieces=[];
 for(const p of family.parts){const r=read(C,p.path);if(r.pin.bytes!==p.bytes||r.pin.sha256!==p.sha256)throw Error('Retained part identity');const decoded=gunzipSync(r.b,{maxOutputLength:p.uncompressed_bytes});if(decoded.length!==p.uncompressed_bytes||sha(decoded)!==p.uncompressed_sha256)throw Error('Decoded retained part');pieces.push(decoded);partPins.push({...r.pin,decoded_bytes:decoded.length,decoded_sha256:sha(decoded)});}
 const body=Buffer.concat(pieces);if(body.length!==family.original_bytes||sha(body)!==family.original_sha256)throw Error('Whole original family');const features=JSON.parse(body).features;if(features.length!==family.feature_count)throw Error('Complete original feature roster');
 const identities=features.map(f=>key+':'+f.properties.shapeID);if(new Set(identities).size!==features.length)throw Error('Original feature identity');
 const idx=nativeRuntimeIndex(features.map((f,i)=>({id:identities[i],pixelIndex:i+1,geometry:f.geometry})));
 for(const y of rows){const scan=nativePolygonIntervals(idx,{size:262166,latitudes,rowStart:y,rowEnd:y+1});calls++;for(const p of records.filter(r=>r.y===y)){for(const span of scan.rows.get(y)??[])if(span.start<=p.x&&p.x<span.end)p.source_hits.push({family:key,source_id:identities[span.owner-1],feature_ordinal:span.owner-1});for(const t of scan.ties)if((t.start??t.x)<=p.x&&p.x<(t.end??t.x+1))p.source_boundary_contacts.push({family:key,source_id:identities[t.owner-1],feature_ordinal:t.owner-1,kind:t.kind});}}
 familyObservations.push({key,whole_original_bytes:body.length,whole_original_sha256:sha(body),features:features.length,parts:partPins});
}
for(const p of records){p.chosen_original_source_interior=p.source_hits.some(h=>h.source_id===p.chosen.id);p.chosen_original_family_hits=p.source_hits.filter(h=>h.family===p.chosen.id.split(':').slice(0,3).join(':'));}
const result={kind:'bounded-original-source28-native-centre-contact-feasibility',actual_executing_accepted_commit:C,proposal:{path:source,bytes:proposal.length,sha256:sha(proposal)},catalogue:cat.pin,native_latitudes:{...lp.pin,decoded_bytes:lat.length,decoded_sha256:sha(lat)},operator:'Actual accepted src/native-grid.js nativeRuntimeIndex/nativePolygonIntervals; complete original family geometries, exact normative latitudes, only the28 original native centres observed',operator_code:read(C,'src/native-grid.js').pin,complete_original_families:familyObservations,native_calls:calls,distinct_native_rows:rows.length,elapsed_seconds:(performance.now()-started)/1000,rss_bytes:process.memoryUsage().rss,records,limitations:['This is a new bounded feasibility observation, not a replay of the original source-choice or whole scientific producer.','Source contacts do not establish physical qualification, source applicability adoption, current-owner zero, native authority or selected delivery.','Every complete original geometry and both source mappings remain unchanged.']};
fs.writeFileSync('.takeover/source28-native-feasibility/original-source28-native-contact-observation.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({coordinates:records.length,chosen_source_interior:records.filter(p=>p.chosen_original_source_interior).length,chosen_family_nonunique:records.filter(p=>p.chosen_original_family_hits.length!==1).length,boundary_points:records.filter(p=>p.source_boundary_contacts.length).length,calls,elapsed_seconds:result.elapsed_seconds,rss_bytes:result.rss_bytes}));
