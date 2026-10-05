// Original canonical partitions are read from pinned Git blobs; no installation.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../../../src/ownership-assets.js';
import {ownershipRun,samplePackedOwnership} from '../../../src/pixel-ownership.js';
import {rasterize} from '../../../src/pixel-grid.js';
import {caseIndex} from '../iran-pakistan-grid-proof-971-20261005-local11/compile.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const hash=raw=>createHash('sha256').update(raw).digest('hex');
export function validateRuns(grid,maxOwner){
 if(grid.version!==2||!Number.isSafeInteger(maxOwner)||maxOwner<1)throw Error('Invalid original run inventory context');
 let offset=0,cells=0;
 for(let y=0;y<grid.size;y++){
  if(grid.rows[y*2]!==offset)throw Error('Row offset mismatch');
  const count=grid.rows[y*2+1];let previousEnd=0;
  for(let n=0;n<count;n++){
   const r=ownershipRun(grid,offset+n);
   if(r.start<previousEnd||r.end<=r.start||r.end>grid.size||r.id<1||r.id>maxOwner)throw Error('Invalid original run coordinate/owner');
   previousEnd=r.end;cells+=r.end-r.start;
  }
  offset+=count;
 }
 if(offset!==grid.runs.length/2)throw Error('Unreferenced original runs');
 return{rows:grid.size,runs:offset,owned_cells:cells,decoded_bytes:grid.rows.byteLength+grid.runs.byteLength};
}
export function differences(a,b,bbox){
 const changes=[];let count=0;
 for(let row=0;row<bbox.height;row++)for(let x=0;x<bbox.width;){
  let n=row*bbox.width+x;
  if(a[n]===b[n]){x++;continue;}
  const left=a[n],right=b[n],start=x; x++;
  while(x<bbox.width&&a[row*bbox.width+x]===left&&b[row*bbox.width+x]===right)x++;
  changes.push({y:bbox.y+row,start:bbox.x+start,end:bbox.x+x,original_owner:left,reconstructed_owner:right});count+=x-start;
 }
 return{cells:count,runs:changes};
}
async function main(){
 const options={},args=process.argv.slice(2);
 for(let n=0;n<args.length;n+=2){if(!['--repo','--commit','--registry','--registry-sha256','--out'].includes(args[n])||!args[n+1]||options[args[n]])throw Error('Require explicit immutable inputs/fresh output');options[args[n]]=args[n+1];}
 if(!/^[a-f0-9]{40}$/.test(options['--commit']??''))throw Error('Immutable evaluation commit required');
 if(!options['--out']||fs.existsSync(options['--out']))throw Error('Refuse output overwrite');
 const gitRead=(commit,p)=>{if(!p||p.startsWith('/')||p.split('/').some(v=>!v||v==='.'||v==='..'))throw Error('Unsafe input path');return execFileSync('git',['-C',options['--repo'],'show',commit+':'+p],{maxBuffer:32*1024*1024});};
 const descriptor=JSON.parse(options['--registry']),registryRaw=gitRead(options['--commit'],descriptor.path);
 if(hash(registryRaw)!==descriptor.sha256||descriptor.sha256!==options['--registry-sha256']||registryRaw.length!==descriptor.bytes)throw Error('Registry pin mismatch');
 const registry=JSON.parse(registryRaw),pins=new Map(registry.baseline_files.map(p=>[p.path,p]));
 if(pins.size!==registry.baseline_files.length)throw Error('Duplicate baseline descriptor');
 const read=p=>{const pin=pins.get(p);if(!pin)throw Error('Undeclared baseline input');const raw=gitRead(registry.baseline_commit,p);if(raw.length!==pin.bytes||hash(raw)!==pin.sha256)throw Error('Baseline byte pin mismatch');return raw;};
 for(const p of ['src/pixel-grid.js','src/pixel-ownership.js','src/ownership-codec.js','src/ownership-assets.js',registry.prior_packet+'/compile.mjs'])if(!fs.readFileSync(path.join(root,p)).equals(read(p)))throw Error('Imported helper differs from pinned baseline');
 const manifest=JSON.parse(read('data/canonical-grid/manifest.json'));
 if(manifest.version!==2||manifest.size!==262166||manifest.coordinateBits!==19)throw Error('Unexpected original canonical grid context');
 const hierarchy=read('data/hierarchy.json');if(hash(hierarchy)!==manifest.hierarchy_sha256)throw Error('Original hierarchy pin differs');
 const boundsRaw=read('data/canonical-grid/bounds.json.gz');if(hash(boundsRaw)!==manifest.bounds.sha256)throw Error('Original bounds pin differs');
 const bounds=JSON.parse(gunzipSync(boundsRaw)),owners=new Map(bounds.map((r,n)=>{if(r.index!==n+1)throw Error('Noncontiguous owner inventory');return[r.id,r];}));
 if(owners.size!==bounds.length||bounds.length!==manifest.stats.locations)throw Error('Incomplete original owner inventory');
 const staged=JSON.parse(read(registry.prior_packet+'/results-v1/staged-neighbors.json'));
 for(const f of staged.baseline){const r=owners.get(f.id);if(!r||r.index!==staged.owner_indices[f.id]||r.province_id!==f.properties.parent_id)throw Error('Original owner/parent crosswalk differs');}
 const membershipRaw=read('data/canonical-grid/province-membership.bin.gz');if(hash(membershipRaw)!==manifest.province_membership.sha256)throw Error('Original membership pin differs');
 const membershipBytes=gunzipSync(membershipRaw),membership=new Uint32Array(membershipBytes.buffer.slice(membershipBytes.byteOffset,membershipBytes.byteOffset+membershipBytes.length));
 if(membership.length!==bounds.length+1||membership[0]!==0)throw Error('Incomplete membership');
 for(const r of bounds)if(membership[r.index]!==r.province_index||manifest.provinces[r.province_index-1]!==r.province_id)throw Error('Original province membership differs');
 const current=JSON.parse(read('data/geographic-releases/current-manifest.json')),releaseRaw=read('data/geographic-releases/'+current.path);if(hash(releaseRaw)!==current.sha256)throw Error('Release byte pin mismatch');
 const releaseManifest=JSON.parse(gunzipSync(releaseRaw)),release=releaseManifest.releases.at(-1);
 if(release.footprints_sha256!==manifest.footprints_sha256||release.hierarchy_sha256!==manifest.hierarchy_sha256||release.expected_counts.location!==bounds.length)throw Error('Immutable release/grid context differs');
 const loaded=[];
 const original=await loadOwnershipAssets(manifest,async url=>{const p='data/canonical-grid/'+url.replace(/^\.\//,'');const raw=read(p);loaded.push(p);return new Response(raw,{status:200});});
 if(new Set(loaded).size!==manifest.parts.length||loaded.length!==manifest.parts.length)throw Error('Original partition load inventory differs');
 const accounting=validateRuns(original,bounds.length),bbox=staged.bbox;
 const native=samplePackedOwnership(original,bbox),baseline=rasterize(caseIndex(staged.baseline,staged.owner_indices),bbox),candidate=rasterize(caseIndex(staged.candidate,staged.owner_indices),bbox);
 const baselineParity=differences(native,baseline,bbox),candidateChanges=differences(native,candidate,bbox);
 const prior=JSON.parse(read(registry.prior_packet+'/results-v2/compiled.json'));
 const reference=differences(baseline,candidate,bbox);
 if(reference.cells!==prior.change_counts.changed_cells||JSON.stringify(reference.runs.map(r=>({y:r.y,start:r.start,end:r.end,baseline_owner:r.original_owner,candidate_owner:r.reconstructed_owner})))!==JSON.stringify(prior.changes.map(({component_mask,...r})=>r)))throw Error('Prior complete changed-cell inventory differs');
 const out={version:1,method_id:'original-encoded-baseline-parity',evaluation_commit:options['--commit'],baseline_commit:registry.baseline_commit,registry_sha256:descriptor.sha256,partition_count:loaded.length,owner_count:bounds.length,geographic_release:release.id,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,accounting,bbox,inspected_cells:native.length,baseline_parity:baselineParity,candidate_changes:candidateChanges,installation_ready:false,limits:['All original encoded partitions and their decoded digests/row-run ordering/owner range checked. Original stored ID/parent/province inventory checked; full-world geometry proof is inherited from PR990, not recomputed here.','Original versus reconstructed ownership compared exhaustively only in the full affected rectangle. No world-wide raster comparison, source/geographic approval, core integration or deployment.','Positive native/baseline discrepancies, if any, remain explicit. Nine geometric residuals and factual/source/projection uncertainty remain unresolved.']};
 fs.writeFileSync(options['--out'],JSON.stringify(out)+'\n',{flag:'wx'});
 console.log(JSON.stringify({partitions:loaded.length,accounting,bbox_cells:native.length,baseline_discrepancies:baselineParity.cells,candidate_changes:candidateChanges.cells}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))await main();
