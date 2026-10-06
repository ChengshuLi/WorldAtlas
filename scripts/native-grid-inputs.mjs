import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {ownershipRun} from '../src/pixel-ownership.js';

export const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function loadNativeAuditInputs(repo,commit){
  if(!/^[a-f0-9]{40}$/.test(commit??''))throw Error('Require immutable data commit');
  const files=new Map();
  function read(name){
    if(!/^(data|src)\/[a-zA-Z0-9_./-]+$/.test(name)||name.includes('..'))throw Error('Unsafe source path');
    const raw=execFileSync('git',['-C',repo,'show',commit+':'+name],{maxBuffer:32*1024*1024});
    files.set(name,{path:name,bytes:raw.length,sha256:sha256(raw)});return raw;
  }
  const decode=raw=>JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
  for(const name of ['src/pixel-grid.js','src/pixel-ownership.js','src/ownership-assets.js','src/ownership-codec.js'])read(name);
  const manifest=decode(read('data/canonical-grid/manifest.json'));
  if(manifest.size!==262166||manifest.version!==2||manifest.coordinateBits!==19)
    throw Error('Unsupported original canonical convention');
  const hierarchy=read('data/hierarchy.json');
  if(sha256(hierarchy)!==manifest.hierarchy_sha256)throw Error('Original hierarchy pin differs');
  const boundsRaw=read('data/canonical-grid/'+manifest.bounds.path);
  if(sha256(boundsRaw)!==manifest.bounds.sha256)throw Error('Original bounds pin differs');
  const bounds=decode(boundsRaw),owners=new Map(bounds.map(r=>[r.id,r]));
  if(owners.size!==bounds.length||bounds.some((r,i)=>r.index!==i+1))throw Error('Incomplete original owner registry');
  const pointer=decode(read('data/geographic-releases/current-manifest.json'));
  const releaseRaw=read('data/geographic-releases/'+pointer.path);
  if(sha256(releaseRaw)!==pointer.sha256)throw Error('Original release pointer differs');
  const release=decode(releaseRaw).releases.at(-1);
  if(release.footprints_sha256!==manifest.footprints_sha256||release.hierarchy_sha256!==manifest.hierarchy_sha256||
    release.expected_counts.location!==bounds.length)throw Error('Original release and roster differ');
  const loaded=[];
  const stored=await loadOwnershipAssets(manifest,async url=>{
    const name='data/canonical-grid/'+url.replace(/^\.\//,'');loaded.push(name);
    return new Response(read(name),{status:200});
  });
  if(loaded.length!==manifest.parts.length||new Set(loaded).size!==loaded.length)
    throw Error('Original ownership partition accounting differs');
  let totalStoredRuns=0,totalStoredOwned=0;
  for(let y=0;y<stored.size;y++){
    let previous=0;
    for(let n=stored.rows[y*2];n<stored.rows[y*2]+stored.rows[y*2+1];n++){
      const r=ownershipRun(stored,n);
      if(r.start<previous||r.end<=r.start||r.end>stored.size||r.id<1||r.id>bounds.length)
        throw Error('Invalid original row/run');
      previous=r.end;totalStoredOwned+=r.end-r.start;totalStoredRuns++;
    }
  }
  const world=decode(read('data/world-index.json'));
  if(!Array.isArray(world.parts)||new Set(world.parts).size!==world.parts.length)throw Error('Invalid original world inventory');
  const seen=new Set(),index=[],roster=[],serialized=[];
  let vertices=0;
  for(const part of world.parts){
    const path='data/'+part,collection=decode(read(path));
    if(collection.type!=='FeatureCollection'||!Array.isArray(collection.features))throw Error('Invalid original world part');
    for(const f of collection.features){
      const owner=owners.get(f.id);
      if(!owner||seen.has(f.id)||f.properties?.parent_id!==owner.province_id)
        throw Error('Original location/parent crosswalk differs');
      seen.add(f.id);
      if(!['Polygon','MultiPolygon'].includes(f.geometry?.type))throw Error('Unsupported original native geometry');
      serialized.push({id:f.id,json:JSON.stringify([f.id,f.geometry])});
      let minLat=Infinity,maxLat=-Infinity;
      const raw=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;
      if(!Array.isArray(raw)||!raw.length)throw Error('Missing original polygons');
      const polygons=raw.map(p=>{
        if(!Array.isArray(p)||!p.length)throw Error('Missing original rings');
        return p.map(r=>{
          if(!Array.isArray(r)||r.length<4)throw Error('Malformed original ring');
          const ring=new Float64Array(r.length*2);
          r.forEach((point,i)=>{
            if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||
               Math.abs(point[0])>180||Math.abs(point[1])>90)throw Error('Invalid original native coordinate');
            ring[i*2]=point[0];ring[i*2+1]=point[1];
            minLat=Math.min(minLat,point[1]);maxLat=Math.max(maxLat,point[1]);vertices++;
          });
          if(ring[0]!==ring.at(-2)||ring[1]!==ring.at(-1))throw Error('Unclosed original native ring');
          return ring;
        });
      });
      index.push({index:owner.index,polygons,minLat,maxLat});
      roster.push({index:owner.index,id:f.id,parent_id:owner.province_id,name:f.properties.name,path});
    }
  }
  if(seen.size!==bounds.length||[...owners.keys()].some(id=>!seen.has(id)))throw Error('Incomplete original native roster');
  // Same canonical footprint hash as footprintHash(), streamed feature by
  // feature instead of constructing a second world-sized JSON string.
  serialized.sort((a,b)=>a.id.localeCompare(b.id));
  const footprint=createHash('sha256').update('[');
  for(let i=0;i<serialized.length;i++){if(i)footprint.update(',');footprint.update(serialized[i].json);}
  if(footprint.update(']').digest('hex')!==manifest.footprints_sha256)throw Error('Original actual footprint hash differs');
  serialized.length=0;
  index.sort((a,b)=>a.index-b.index);roster.sort((a,b)=>a.index-b.index);
  return {stored,index,roster,release,manifest,vertices,totalStoredRuns,totalStoredOwned,
    sourceFiles:[...files.values()].sort((a,b)=>a.path.localeCompare(b.path))};
}
