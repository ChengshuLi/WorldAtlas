// Reconstruct bounded case ownership with pinned application code. Never install.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createGridIndex,rasterize,GRID_WIDTH} from '../../../src/pixel-grid.js';
import {compileOwnership,packOwnership,sampleOwnership,samplePackedOwnership,pickOwnership} from '../../../src/pixel-ownership.js';
import {shuffleOwnershipBytes,unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
export function caseIndex(features,ownerIndices){
  const ordered=features.map(f=>({...f,pixelIndex:ownerIndices[f.id]}));
  const index=createGridIndex(ordered);
  for(const item of index){
    const id=ownerIndices[item.feature.id];
    if(!Number.isSafeInteger(id)||id<1)throw Error('Missing exact baseline owner index');
    item.index=id;
  }
  return index;
}

function encodedRoundtrip(packed){
  const output={...packed};
  for(const kind of ['rows','runs']){
    const words=packed[kind];
    output[kind]=unshuffleOwnershipBytes(gunzipSync(gzipSync(shuffleOwnershipBytes(words))),words.length);
    if(!same(words,output[kind]))throw Error('Lossy ownership packing/codec roundtrip');
  }
  return output;
}

export function inspect(staged){
  if(staged.size!==GRID_WIDTH)throw Error('Pinned application width differs from baseline grid');
  const oldIds=staged.baseline.map(f=>f.id).sort(),newIds=staged.candidate.map(f=>f.id).sort();
  if(new Set(oldIds).size!==oldIds.length||!same(oldIds,newIds)||!same(oldIds,Object.keys(staged.owner_indices).sort()))throw Error('Incomplete or duplicate neighbor inventory');
  const bbox=staged.bbox,total=bbox.width*bbox.height;
  if(!Number.isSafeInteger(total)||total<1||total>16000000)throw Error('Unbounded pixel inspection');
  const before=caseIndex(staged.baseline,staged.owner_indices),after=caseIndex(staged.candidate,staged.owner_indices);
  for(const item of before)if(!same(item.bounds,staged.stored_bounds[item.feature.id]))throw Error('Stored bounds differ from pinned application projection: '+item.feature.id);
  const selected=staged.subject_ids;
  for(const items of [before,after])for(const item of items.filter(i=>selected.includes(i.feature.id))){
    const b=item.bounds;
    if(b[0]<bbox.x||b[1]<bbox.y||b[2]>bbox.x+bbox.width||b[3]>bbox.y+bbox.height)throw Error('Changed full shape extends beyond inspected pixel domain');
  }
  const component=rasterize(createGridIndex([{...staged.component,id:'component'}]),bbox);
  const records={};
  for(const [category,index] of [['baseline',before],['candidate',after]]){
    const direct=rasterize(index,bbox),compiled=compileOwnership(index,GRID_WIDTH);
    const sampled=sampleOwnership(compiled,bbox),packed=packOwnership(compiled),decoded=encodedRoundtrip(packed);
    const packedSample=samplePackedOwnership(decoded,bbox);
    const multiplicity=new Uint16Array(total);
    for(const item of index){
      const mask=rasterize([item],bbox);
      for(let n=0;n<total;n++)if(mask[n]){
        if(multiplicity[n]===65535)throw Error('Multiplicity overflow');
        multiplicity[n]++;
      }
    }
    const counts={component_cells:0,component_uncovered:0,component_single:0,component_multiple:0,
                  full_bbox_cells:total,full_bbox_uncovered:0,full_bbox_multiple:0,
                  raster_compiler_mismatch:0,packed_sample_mismatch:0,packed_pick_mismatch:0};
    for(let n=0;n<total;n++){
      counts.raster_compiler_mismatch+=direct[n]!==sampled[n];
      counts.packed_sample_mismatch+=direct[n]!==packedSample[n];
      const x=bbox.x+n%bbox.width,y=bbox.y+Math.floor(n/bbox.width);
      counts.packed_pick_mismatch+=direct[n]!==pickOwnership(decoded,x+.5,y+.5);
      counts.full_bbox_uncovered+=multiplicity[n]===0;
      counts.full_bbox_multiple+=multiplicity[n]>1;
      if(component[n]){
        counts.component_cells++;counts.component_uncovered+=multiplicity[n]===0;
        counts.component_single+=multiplicity[n]===1;counts.component_multiple+=multiplicity[n]>1;
      }
    }
    records[category]={counts,direct,multiplicity,
                       packed_rows_sha256:hash(Buffer.from(packed.rows.buffer)),
                       packed_runs_sha256:hash(Buffer.from(packed.runs.buffer))};
  }
  const changes=[];
  let changed=0,inside=0,outside=0,lost=0,newMultiple=0;
  for(let row=0;row<bbox.height;row++){
    let start=0;
    while(start<bbox.width){
      const offset=row*bbox.width+start,a=records.baseline.direct[offset],b=records.candidate.direct[offset];
      if(a===b){start++;continue;}
      const region=Boolean(component[offset]);let end=start+1;
      while(end<bbox.width){
        const n=row*bbox.width+end;
        if(records.baseline.direct[n]!==a||records.candidate.direct[n]!==b||Boolean(component[n])!==region)break;
        end++;
      }
      changes.push({y:bbox.y+row,start:bbox.x+start,end:bbox.x+end,baseline_owner:a,candidate_owner:b,component_mask:region});
      changed+=end-start;if(region)inside+=end-start;else outside+=end-start;
      if(a&&!b)lost+=end-start;
      start=end;
    }
  }
  for(let n=0;n<total;n++)newMultiple+=records.candidate.multiplicity[n]>1&&records.baseline.multiplicity[n]<=1;
  return {version:1,method_id:'bounded-application-compilation',bbox,size:GRID_WIDTH,
          owner_indices:staged.owner_indices,inspected_subjects:staged.baseline.map(f=>f.id),
          baseline:Object.fromEntries(Object.entries(records.baseline).filter(([k])=>!['direct','multiplicity'].includes(k))),
          candidate:Object.fromEntries(Object.entries(records.candidate).filter(([k])=>!['direct','multiplicity'].includes(k))),
          change_counts:{changed_cells:changed,inside_component_mask:inside,outside_component_mask:outside,lost_previously_owned_cells:lost,new_multiple_cells:newMultiple},
          changes,installation_ready:false,geographic_approval:'unapproved',
          limits:['Every full-shape rectangle cell plus halo checked with all world-bounds-selected current neighbors. Half-open even-odd component mask, not strict GEOS containment.',
                  'Actual pinned rasterizer, compiler, packing, byte-shuffle/gzip roundtrip and picking agree only where reported mismatch counters are zero.',
                  'Reconstructed baseline/candidate neighbor compilation; original encoded canonical partitions and delivery are not checked.',
                  'Projected invalidity and geographic positive residuals remain blockers; rendering behavior cannot confer geographic/source/physical approval.']};
}

function main(){
  const args=process.argv.slice(2),options={};
  for(let n=0;n<args.length;n+=2){if(!['--repo','--commit','--registry','--registry-sha256','--staged','--out'].includes(args[n])||!args[n+1]||options[args[n]])throw Error('Require explicit immutable registry, staged descriptor and fresh output');options[args[n]]=args[n+1];}
  if(!/^[a-f0-9]{40}$/.test(options['--commit']??''))throw Error('Immutable commit required');
  const out=options['--out'];if(!out||fs.existsSync(out))throw Error('Refuse to overwrite output');
  const read=descriptor=>{
    if(!descriptor.path||descriptor.path.startsWith('/')||descriptor.path.split('/').some(v=>!v||v==='.'||v==='..'))throw Error('Unsafe descriptor');
    const raw=execFileSync('git',['-C',options['--repo'],'show',options['--commit']+':'+descriptor.path],{maxBuffer:32*1024*1024});
    if(raw.length!==descriptor.bytes||hash(raw)!==descriptor.sha256)throw Error('Immutable input hash/size mismatch');
    return raw;
  };
  const registryDescriptor=JSON.parse(options['--registry']);
  if(registryDescriptor.sha256!==options['--registry-sha256'])throw Error('Registry pin differs from command');
  const registry=JSON.parse(read(registryDescriptor));
  for(const name of ['src/pixel-grid.js','src/pixel-ownership.js','src/ownership-codec.js']){
    const pin=registry.baseline_files.find(f=>f.path===name);
    const raw=fs.readFileSync(path.join(root,name));
    if(!pin||raw.length!==pin.bytes||hash(raw)!==pin.sha256)throw Error('Application code differs from immutable baseline');
  }
  const staged=JSON.parse(read(JSON.parse(options['--staged'])));
  if(staged.baseline_commit!==registry.baseline_commit||staged.registry_sha256!==registryDescriptor.sha256)throw Error('Staged input differs from pinned registry');
  const result={...inspect(staged),evaluation_commit:options['--commit'],baseline_commit:registry.baseline_commit,registry_sha256:registryDescriptor.sha256};
  fs.writeFileSync(out,JSON.stringify(result)+'\n',{flag:'wx'});
  console.log(JSON.stringify({baseline:result.baseline.counts,candidate:result.candidate.counts,changes:result.change_counts}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main();
