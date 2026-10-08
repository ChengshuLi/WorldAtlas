import fs from 'node:fs';
import filesystemPath from 'node:path';
import {execFileSync} from 'node:child_process';
import zlib, {gzipSync} from 'node:zlib';
import {syncBuiltinESMExports} from 'node:module';
import {validateEvidence,sha256,subjectsHash} from '../../../scripts/evidence-quality.mjs';
const packet=new URL('.',import.meta.url).pathname;
const repo=execFileSync('git',['rev-parse','--show-toplevel'],{cwd:packet,encoding:'utf8'}).trim();
const [destination,base]=process.argv.slice(2);
if(!destination||!/^([a-f0-9]{40})$/.test(base??'')||filesystemPath.resolve(destination)!==destination||filesystemPath.dirname(destination)!==packet+'vintages'||fs.existsSync(destination))throw Error('Fresh owned destination and exact original base required');
const executionCommit=execFileSync('git',['-C',repo,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const codeNames=['scripts/evidence-quality.mjs','coordination/engineering/immutable-family-record-subject-bindings-20261008/verify-original-records.mjs'];
function codeGuard(){return codeNames.map(name=>{const raw=execFileSync('git',['-C',repo,'show',executionCommit+':'+name],{maxBuffer:32*1024*1024});const live=fs.readFileSync(repo+'/'+name);if(!raw.equals(live)||!fs.lstatSync(repo+'/'+name).isFile())throw Error('Executing code differs from immutable commit');return {commit:executionCommit,path:name,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'};});}
const codeBindings=codeGuard();
const out=destination+'/';
const commit='c9122b55d20c4992fca5b0332e4faacbc08b139a';
const path='coordination/engineering/global-actionability-routing-20261007/results/families-005.bin.gz';
const ids=['gap-source-batch:65911e15791d12ebb2ccacf5','gap-source-batch:74be953b1fb31c15200742da'];
const rows=[{record_offset:2281306,record_bytes:6281,record_sha256:'4b9610e86b7d6517b6c32fdead65bd6c3f73e868ac3413e6a506947071097c1b'},
{record_offset:8377128,record_bytes:8380,record_sha256:'dd8da79354e25b034da7e739534be89c87bc15a2906a6924cf500eb579229610'}];
const file={path,commit,bytes:1026831,sha256:'03f13761ce67af5a826a98468ef2dc77d2f4a5c4ab9f25b6e6a1e3bd396bf141',hash_kind:'file-bytes',uncompressed_bytes:8388608,uncompressed_sha256:'6f7ba9a502dd9229365c522f25e3f05e6d3c2e8c329ceef6644618ebc9da930d'};
function manifest(file,ids,rows){return {version:1,issue:1475,lane:'geography',worker_id:'01a11935-1ccd-7fa3-a01f-563ff29045ee',subject_ids:ids,subject_ids_sha256:subjectsHash(ids),baseline:{version:2,commit,files:[file],pins:{},subject_files:Object.fromEntries(ids.map((id,n)=>[id,{version:2,kind:'gzip-jsonl-record',path:file.path,commit:file.commit,...rows[n]}]))},sources:[],outputs:[],methods:[{id:'original-family-identity',kind:'source',description:'Whole original family record identity only',software:'Trusted whole gzip decoder and JSON reader',units:'Original bytes and native IDs'}],metrics:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'not-proposed',geographic_approval:'unapproved'},commands:['Metadata-only original source identity verification']};}
const actual=manifest(file,ids,rows);
if(file.bytes+file.uncompressed_bytes+codeBindings.reduce((n,x)=>n+x.bytes,0)+1048576+4096>268435456)throw Error('Prospective complete control phase exceeds budget');
const raw=execFileSync('git',['-C',repo,'show',commit+':'+path],{maxBuffer:32*1024*1024});
const ancestors={original_commit:commit,pr_base:base,exit:0};
execFileSync('git',['-C',repo,'merge-base','--is-ancestor',commit,base]);
function ancestor(c){execFileSync('git',['-C',repo,'merge-base','--is-ancestor',c,base]);}
const actualReader=Object.assign((p,c)=>{if(p!==path||c!==commit)throw Error('Wrong immutable origin');return raw;},{assertAncestor:ancestor});
const actualResult=validateEvidence(actual,{readFile:actualReader,expectedIssue:1475,expectedLane:'geography',expectedSubjects:ids});
let passed=[];
let deniedReads=0,deniedDecodes=0;const originalGunzip=zlib.gunzipSync;
zlib.gunzipSync=(...args)=>{deniedDecodes++;return originalGunzip(...args)};syncBuiltinESMExports();
const deniedReader=Object.assign(()=>{deniedReads++;return raw},{assertAncestor:ancestor});
try {validateEvidence(actual,{readFile:deniedReader,maxTotalBytes:file.bytes+file.uncompressed_bytes-1});throw Error('CONTROL ACCEPTED');}
catch(e){if(e.message==='CONTROL ACCEPTED'||deniedReads!==0||deniedDecodes!==0)throw Error('Prospective admission failed: '+e.message);passed.push({name:'complete-phase-reject-before-any-read-or-gunzip',rejection:e.message,body_reads:deniedReads,gunzips:deniedDecodes});}
zlib.gunzipSync=originalGunzip;syncBuiltinESMExports();
function reject(name,m,b=raw,opts={}){try{validateEvidence(m,{readFile:Object.assign(()=>b,{assertAncestor:ancestor}),...opts});throw Error('CONTROL ACCEPTED');}catch(e){if(e.message==='CONTROL ACCEPTED')throw e;passed.push({name,rejection:e.message});}}
const copy=()=>structuredClone(actual);
reject('whole-encoded-plus-decoded-phase-over-cap',copy(),raw,{maxTotalBytes:file.bytes+file.uncompressed_bytes-1});
let m=copy();delete m.baseline.subject_files[ids[0]];reject('missing-original-subject-binding',m);
m=copy();m.baseline.subject_files[ids[0]].record_offset++;reject('interior-record-offset',m);
m=copy();m.baseline.subject_files[ids[0]].record_bytes--;reject('truncated-complete-record',m);
m=copy();m.baseline.subject_files[ids[0]].record_sha256='0'.repeat(64);reject('changed-record-byte-hash',m);
m=copy();m.baseline.subject_files[ids[1]]={...m.baseline.subject_files[ids[0]]};reject('duplicate-record-for-distinct-family',m);
m=copy();m.baseline.subject_files[ids[0]].record_offset=8388608;reject('record-range-escape',m);
m=copy();m.baseline.subject_files[ids[0]].record_bytes=33554433;reject('over-cap-record',m);
m=copy();m.baseline.files[0].uncompressed_sha256='0'.repeat(64);reject('changed-whole-decoded-binding',m);
m=copy();delete m.baseline.files[0].uncompressed_sha256;delete m.baseline.files[0].uncompressed_bytes;reject('missing-whole-decoded-source-pin',m);
m=copy();m.baseline.files[0].uncompressed_bytes=33554433;reject('over-cap-whole-decoded-source',m);
m=copy();m.baseline.subject_files[ids[0]].commit='0'.repeat(40);reject('foreign-unpinned-vintage',m);
m=copy();m.baseline.files[0].commit='b91d38254bc7fb901fefcb6112f5878fbc52d463';m.baseline.subject_files[ids[0]].commit=m.baseline.files[0].commit;m.baseline.subject_files[ids[1]].commit=m.baseline.files[0].commit;reject('candidate-branch-is-not-base-ancestor',m);
let altered=Buffer.from(raw);altered[100]^=1;reject('altered-whole-encoded-source',copy(),altered);
function fixture(lines){const body=Buffer.from(lines.join('')),raw=gzipSync(body),f={path:'original-family-part.bin.gz',commit,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes',uncompressed_bytes:body.length,uncompressed_sha256:sha256(body)},r={record_offset:0,record_bytes:Buffer.byteLength(lines[0]),record_sha256:sha256(Buffer.from(lines[0]))};return {m:manifest(f,[ids[0]],[r]),raw};}
let line=JSON.stringify({id:ids[0],complete_component_ids:['original-component']})+'\n';
let f=fixture([line,line]);reject('duplicate-native-original-family-rows',f.m,f.raw);
f=fixture([JSON.stringify({id:'physical-component:'+'a'.repeat(64)})+'\n']);reject('foreign-original-record-type',f.m,f.raw);
f=fixture([JSON.stringify({id:ids[1]})+'\n']);reject('wrong-original-family-ID',f.m,f.raw);
f=fixture([line.slice(0,-1)]);reject('unterminated-partial-record',f.m,f.raw);
f=fixture([line,'{broken}\n']);reject('malformed-interior-complete-record',f.m,f.raw);
const result={scope:'Bounded source-record schema proposal only; no GIS, author edits, hosted ancestry bypass or full PR acceptance',actual_original_two_family_records:actualResult,original_ancestry:ancestors,negative_controls:passed,counts:{actual_positive:1,negative:passed.length},executing_reader_sha256:codeBindings[0].sha256,execution_commit:executionCommit,code_bindings:codeBindings,runtime:{node:process.version,versions:process.versions,platform:process.platform,architecture:process.arch,proof_scope:'Actual runtime version metadata; native runtime/kernel bodies are not retained or scientifically certified'},geographic_operations:0,complete_original_source:{...file},decoded_phase_charge:file.bytes+file.uncompressed_bytes,postexecution_code_bindings:codeGuard()};
const output=Buffer.from(JSON.stringify(result,null,2)+'\n');
if(output.length>1048576||file.bytes+file.uncompressed_bytes+codeBindings.reduce((n,x)=>n+x.bytes,0)+output.length+4096>268435456)throw Error('Complete control/output phase exceeds budget');
fs.mkdirSync(packet+'vintages',{recursive:true});if(fs.realpathSync(packet+'vintages')!==packet+'vintages')throw Error('Nonordinary output parent');fs.mkdirSync(destination,{recursive:false});fs.writeFileSync(out+'record-binding-controls.json',output,{flag:'wx'});
const publication={version:1,status:'complete',execution_commit:executionCommit,outputs:[{path:destination.slice(repo.length+1)+'/record-binding-controls.json',bytes:output.length,sha256:sha256(output),hash_kind:'file-bytes'}]};
fs.writeFileSync(out+'publication.json',JSON.stringify(publication)+'\n',{flag:'wx'});
console.log(JSON.stringify({positive:1,negative:passed.length,execution_commit:executionCommit,reader_sha256:result.executing_reader_sha256}));
