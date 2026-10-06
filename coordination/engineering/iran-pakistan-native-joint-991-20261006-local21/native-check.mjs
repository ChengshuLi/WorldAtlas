// Exhaustive bounded native ownership comparison. Does not install a candidate.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
import {nativePolygonIntervals} from '../../../src/native-grid.js';
import {coverageRow} from '../../../scripts/audit-grid-intervals.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix=path.relative(root,path.dirname(fileURLToPath(import.meta.url)));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const inputCommit='06bf4087bf5aec0e7071830ba61e99105f2c3697';
const latitudeCommit='86ad8281a47ce77caa250952e0b7a69c6969d98f';
const latitudePath='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
const stagedPath='coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json';
const read=(commit,p)=>execFileSync('git',['show',commit+':'+p],{cwd:root,maxBuffer:32*1024*1024});
const descriptor=(commit,p,raw)=>({commit,path:p,bytes:raw.length,sha256:sha(raw),hash_kind:'file-bytes'});

export function check(staged,candidates,latitudes){
  const {bbox,size}=staged;
  if(size!==262166 || bbox.width*bbox.height!==4257008 || bbox.height>4096 ||
     Object.keys(candidates).sort().join('|')!==staged.subject_ids.slice().sort().join('|'))
    throw Error('Exact target and full-shape domain required');
  const beforeFeatures=staged.baseline.map(f=>({...f,pixelIndex:staged.owner_indices[f.id]}));
  const afterFeatures=beforeFeatures.map(f=>({...f,geometry:candidates[f.id]??f.geometry}));
  const options={size,rowStart:bbox.y,rowEnd:bbox.y+bbox.height,latitudes};
  const before=nativePolygonIntervals(nativeRuntimeIndex(beforeFeatures),options);
  const after=nativePolygonIntervals(nativeRuntimeIndex(afterFeatures),options);
  const component=nativePolygonIntervals(nativeRuntimeIndex([{...staged.component,id:'component',pixelIndex:1}]),options);
  const counts={cells:bbox.width*bbox.height,changed:0,lost:0,outside_component_changed:0,
    new_multiple:0,baseline_component_uncovered:0,candidate_component_uncovered:0};
  const records=[],changedRuns=[];
  for(let y=bbox.y;y<bbox.y+bbox.height;y++){
    const old=coverageRow(before.rows.get(y)??[],size),next=coverageRow(after.rows.get(y)??[],size);
    const mask=coverageRow(component.rows.get(y)??[],size);
    records.push({y,before:old,after:next,component:mask});
    let i=0,j=0,k=0,last=null;
    for(let x=bbox.x;x<bbox.x+bbox.width;x++){
      while(old[i].end<=x)i++;
      while(next[j].end<=x)j++;
      while(mask[k].end<=x)k++;
      const a=old[i].owners,b=next[j].owners,within=mask[k].owners.length>0;
      if(within){counts.baseline_component_uncovered+=!a.length;counts.candidate_component_uncovered+=!b.length;}
      counts.lost+=a.some(owner=>!b.includes(owner));
      counts.new_multiple+=b.length>1&&a.length<=1;
      if(a.join(',')!==b.join(',')){
        counts.changed++;counts.outside_component_changed+=!within;
        const signature=JSON.stringify([a,b,within]);
        if(last&&last.y===y&&last.end===x&&last.signature===signature)last.end++;
        else {last={y,start:x,end:x+1,before:a,after:b,component:within,signature};changedRuns.push(last);}
      }else last=null;
    }
  }
  return {counts,rows:records,changed_runs:changedRuns.map(({signature,...r})=>r),
    boundary_ties:{baseline:before.ties,candidate:after.ties,component:component.ties},
    method:after.method,limits:['Native before/after comparison, not legacy grid parity or geographic approval.',
      'Complete supplied neighbor shapes and every cell in the pinned rectangle; full-world comparison separately required.']};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const args=Object.fromEntries(Array.from({length:(process.argv.length-2)/2},(_,i)=>
    [process.argv[2+i*2],process.argv[3+i*2]]));
  const evaluation=args['--evaluation-commit'],candidatePath=args['--candidates'],out=args['--out'];
  if(!/^[a-f0-9]{40}$/.test(evaluation??'')||!candidatePath||!out)throw Error('Require pinned code/candidate and exclusive output');
  const producers=[];
  for(const p of [prefix+'/native-check.mjs','src/native-runtime.js','src/native-grid.js',
    'scripts/audit-grid-intervals.mjs','scripts/native-ownership/compile-native-ownership.mjs']){
    const raw=read(evaluation,p);
    if(!raw.equals(fs.readFileSync(path.join(root,p))))throw Error('Code differs from immutable execution pin: '+p);
    producers.push(descriptor(evaluation,p,raw));
  }
  const latitudeRaw=read(latitudeCommit,latitudePath),decoded=gunzipSync(latitudeRaw);
  if(decoded.length!==262166*8||sha(decoded)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')
    throw Error('Normative original latitude bytes differ');
  const latitudes=Float64Array.from({length:262166},(_,i)=>decoded.readDoubleLE(i*8));
  const stagedRaw=read(inputCommit,stagedPath),candidateRaw=read(evaluation,candidatePath);
  const result=check(JSON.parse(stagedRaw),JSON.parse(candidateRaw),latitudes);
  result.inputs=[descriptor(inputCommit,stagedPath,stagedRaw),descriptor(latitudeCommit,latitudePath,latitudeRaw),
    descriptor(evaluation,candidatePath,candidateRaw)];
  result.producer=producers;
  const target=path.resolve(root,out);
  if(!target.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(target))throw Error('Fresh owned output required');
  fs.mkdirSync(target,{recursive:true});
  fs.writeFileSync(path.join(target,'native-cells.json'),JSON.stringify(result)+'\n',{flag:'wx'});
  fs.writeFileSync(path.join(target,'latitude-bytes.f64le'),decoded,{flag:'wx'});
  console.log(JSON.stringify({counts:result.counts,boundary_ties:Object.fromEntries(
    Object.entries(result.boundary_ties).map(([k,v])=>[k,v.length])),output:out}));
}
