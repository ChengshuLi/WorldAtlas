import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../mmr7479-native-preparation-001/accepted-9f40/src/native-grid.js';
const root='.cache/worker3-mmr3483-opportunity-001/';
const sha=b=>createHash('sha256').update(b).digest('hex');
const proposalBytes=fs.readFileSync(root+'conflict28-source-choice-proposal.json');
if(sha(proposalBytes)!=='5bac08a94c3d8eb5f42350a20b7548f9133e3f251f75e1de94e35815b1ad3e47')throw Error('Proposal pin');
const proposal=JSON.parse(proposalBytes),custody=JSON.parse(fs.readFileSync(root+'conflict28-current-locations.json'));
const candidates=new Map(proposal.records.flatMap(r=>r.candidate_owner_details.map(c=>[c.id,c]))),features=[];
for(const desc of custody.parts){
 const git=spawnSync('/usr/bin/git',['-c','protocol.allow=never','--git-dir=/Users/chengshuli/world-atlas-workspace/WorldAtlas/.git','show',desc.commit+':'+desc.path],{env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_OPTIONAL_LOCKS:'0'},maxBuffer:20000000});
 if(git.status!==0)throw Error('Readonly selected part unavailable: '+String(git.stderr));
 const body=git.stdout;if(body.length!==desc.bytes||sha(body)!==desc.sha256||createHash('sha1').update('blob '+body.length+'\0').update(body).digest('hex')!==desc.git_blob_oid)throw Error('Complete selected part identity');
 for(const f of JSON.parse(body).features){const id=f.id??f.properties.id;if(candidates.has(id))features.push({id,pixelIndex:candidates.get(id).index,geometry:f.geometry});}
}
if(features.length!==14||new Set(features.map(f=>f.id)).size!==14)throw Error('Full candidate feature count');
const encoded=fs.readFileSync('.cache/mmr7479-native-preparation-001/native_latitudes.gz');if(sha(encoded)!=='ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147')throw Error('Latitude encoded pin');
const raw=gunzipSync(encoded);if(sha(raw)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Latitude decoded pin');
const latitudes=Float64Array.from({length:262166},(_,i)=>raw.readDoubleLE(i*8));
const index=nativeRuntimeIndex(features),records=proposal.records.map(r=>({...r,current_candidate_interiors:[],current_candidate_ties:[]}));let calls=0;
for(const block of [...new Set(records.map(r=>Math.floor(r.y/4096)))]){
 const points=records.filter(r=>Math.floor(r.y/4096)===block);const rowStart=Math.min(...points.map(r=>r.y)),rowEnd=Math.max(...points.map(r=>r.y))+1;if(rowEnd-rowStart>4096)throw Error('Bounded row frame');
 const scan=nativePolygonIntervals(index,{size:262166,latitudes,rowStart,rowEnd});calls++;
 for(const p of points){p.current_candidate_interiors=[...new Set((scan.rows.get(p.y)??[]).filter(r=>r.start<=p.x&&p.x<r.end).map(r=>r.owner))];p.current_candidate_ties=scan.ties.filter(t=>t.y===p.y&&(t.start??t.x)<=p.x&&p.x<(t.end??t.x+1)).map(t=>({owner:t.owner,kind:t.kind}));}
}
const result={kind:'original-conflict28-affected-native-centre-current-candidate-observation',proposal_sha256:sha(proposalBytes),current_accepted_commit:proposal.current_accepted_commit,complete_source_parts:custody.parts,operator:'Unchanged exact nativePolygonIntervals; complete original selected geometries, no clipping or source-priority preprocessing.',operator_source:'.cache/mmr7479-native-preparation-001/accepted-9f40/src/native-grid.js',calls,records,limits:['This observes all fourteen competing current-location geometries at the original28 centres. It is not the current complete selected owner table or source-target qualification.','All competing mappings, original SIDs and source-choice evidence are preserved. No exclusion/competitor input was removed or rewritten.','No new repair credit, selected bank mutation or adoption.']};
fs.writeFileSync(root+'conflict28-current-native-observation.json',JSON.stringify(result)+'\n',{flag:'wx'});
console.log(JSON.stringify({coordinates:records.length,calls,interior_counts:Object.fromEntries([...new Set(records.map(r=>r.current_candidate_interiors.length))].map(n=>[n,records.filter(r=>r.current_candidate_interiors.length===n).length])),tie_points:records.filter(r=>r.current_candidate_ties.length).length,selected_choice_interior:records.filter(r=>r.current_candidate_interiors.includes(r.selected_current_location.index)).length,rss_bytes:process.memoryUsage().rss}));
