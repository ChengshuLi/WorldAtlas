// Immutable native-only inputs; original ownership run assets are not loaded.
import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const digest=raw=>createHash('sha256').update(raw).digest('hex');
export async function loadNativeSourceInputs(repo,commit,{readFile}={}){
 if(!/^[a-f0-9]{40}$/.test(commit??''))throw Error('Immutable data commit required');
 const files=new Map();
 function read(name){
  if(!/^data\/[a-zA-Z0-9_./-]+$/.test(name)||name.split('/').some(p=>!p||p==='.'||p==='..'))
   throw Error('Unsafe native input path');
  if(readFile){
   const raw=Buffer.from(readFile(name,commit));
   if(raw.length>32*1024*1024)throw Error('Original exceeds per-file byte budget');
   files.set(name,{path:name,bytes:raw.length,sha256:digest(raw)});return raw;
  }
  const tree=execFileSync('git',['-C',repo,'ls-tree','-z',commit,'--',name],{encoding:'utf8'});
  if(!tree.startsWith('100644 ')&&!tree.startsWith('100755 '))throw Error('Original must be an ordinary blob');
  if(tree.slice(tree.indexOf('\t')+1)!==name+'\0')throw Error('Original path differs');
  const blob=tree.split(' ')[2].split('\t')[0];
  const length=Number(execFileSync('git',['-C',repo,'cat-file','-s',blob],{encoding:'utf8'}));
  if(!Number.isSafeInteger(length)||length<0||length>32*1024*1024)throw Error('Original exceeds per-file byte budget');
  const raw=execFileSync('git',['-C',repo,'cat-file','blob',blob],{maxBuffer:32*1024*1024});
  if(raw.length!==length)throw Error('Original read incomplete');
  files.set(name,{path:name,bytes:raw.length,sha256:digest(raw)});return raw;
 }
 const json=raw=>JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
 const manifestRaw=read('data/canonical-grid/manifest.json'),manifest=json(manifestRaw);
 if(manifest.version!==2||manifest.size!==262166||manifest.coordinateBits!==19)
  throw Error('Unsupported original canonical convention');
 const hierarchy=read('data/hierarchy.json');
 if(digest(hierarchy)!==manifest.hierarchy_sha256)throw Error('Original hierarchy differs');
 const boundsRaw=read('data/canonical-grid/'+manifest.bounds.path);
 if(digest(boundsRaw)!==manifest.bounds.sha256)throw Error('Original bounds differ');
 const bounds=json(boundsRaw),owners=new Map(bounds.map(r=>[r.id,r]));
 if(owners.size!==bounds.length||bounds.some((r,i)=>r.index!==i+1))throw Error('Incomplete stable owner registry');
 const provinces=manifest.provinces;
 if(!Array.isArray(provinces)||new Set(provinces).size!==provinces.length)
  throw Error('Invalid original province registry');
 const membershipRaw=read('data/canonical-grid/'+manifest.province_membership.path);
 if(digest(membershipRaw)!==manifest.province_membership.sha256)throw Error('Original province bytes differ');
 const membership=gunzipSync(membershipRaw,{maxOutputLength:32*1024*1024});
 if(membership.length!==(bounds.length+1)*4||membership.readUInt32LE(0)!==0)
  throw Error('Original province membership accounting differs');
 for(const owner of bounds)if(!Number.isInteger(owner.province_index)||owner.province_index<1||
   owner.province_index>provinces.length||provinces[owner.province_index-1]!==owner.province_id||
   membership.readUInt32LE(owner.index*4)!==owner.province_index)
  throw Error('Original complete province/parent crosswalk differs');
 const pointer=json(read('data/geographic-releases/current-manifest.json'));
 const releaseRaw=read('data/geographic-releases/'+pointer.path);
 if(digest(releaseRaw)!==pointer.sha256)throw Error('Original release pointer differs');
 const release=json(releaseRaw).releases.at(-1);
 if(release.footprints_sha256!==manifest.footprints_sha256||release.hierarchy_sha256!==manifest.hierarchy_sha256||
  release.expected_counts.location!==bounds.length)throw Error('Original release and roster differ');
 const world=json(read('data/world-index.json'));
 if(!Array.isArray(world.parts)||new Set(world.parts).size!==world.parts.length)throw Error('Invalid original world inventory');
 const seen=new Set(),index=[],roster=[],serialized=[],partitions=[];let vertices=0;
 for(const part of world.parts){
  const name='data/'+part,collection=json(read(name));
  if(collection.type!=='FeatureCollection'||!Array.isArray(collection.features))throw Error('Invalid native world part');
  const beforeVertices=vertices;
  for(const feature of collection.features){
   const owner=owners.get(feature.id);
   if(!owner||seen.has(feature.id)||feature.properties?.parent_id!==owner.province_id)
    throw Error('Original stable identity/parent crosswalk differs');
   seen.add(feature.id);
   if(!['Polygon','MultiPolygon'].includes(feature.geometry?.type))throw Error('Unsupported original native geometry');
   serialized.push({id:feature.id,json:JSON.stringify([feature.id,feature.geometry])});
   const raw=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
   if(!Array.isArray(raw)||!raw.length)throw Error('Missing original polygons');
   let minLat=Infinity,maxLat=-Infinity;
   const polygons=raw.map(p=>{
    if(!Array.isArray(p)||!p.length)throw Error('Missing original rings');
    return p.map(r=>{
     if(!Array.isArray(r)||r.length<4)throw Error('Malformed original ring');
     const ring=new Float64Array(r.length*2);
     r.forEach((point,i)=>{
      if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||
       Math.abs(point[0])>180||Math.abs(point[1])>90)throw Error('Invalid original native coordinate');
      ring[i*2]=point[0];ring[i*2+1]=point[1];vertices++;
      minLat=Math.min(minLat,point[1]);maxLat=Math.max(maxLat,point[1]);
     });
     if(ring[0]!==ring.at(-2)||ring[1]!==ring.at(-1))throw Error('Unclosed original ring');
     return ring;
    });
   });
   index.push({index:owner.index,polygons,minLat,maxLat});
   roster.push({index:owner.index,id:feature.id,parent_id:owner.province_id,name:feature.properties.name,path:name});
  }
  partitions.push({path:name,features:collection.features.length,vertices:vertices-beforeVertices});
 }
 if(seen.size!==bounds.length||[...owners.keys()].some(id=>!seen.has(id)))throw Error('Incomplete native original roster');
 serialized.sort((a,b)=>a.id.localeCompare(b.id));
 const footprint=createHash('sha256').update('[');
 for(let n=0;n<serialized.length;n++){if(n)footprint.update(',');footprint.update(serialized[n].json);}
 if(footprint.update(']').digest('hex')!==manifest.footprints_sha256)throw Error('Original actual footprint differs');
 index.sort((a,b)=>a.index-b.index);roster.sort((a,b)=>a.index-b.index);
 return {baselineCommit:commit,partitions,manifest,manifestRaw,bounds,boundsRaw,membershipRaw,release,index,roster,vertices,
  sourceFiles:[...files.values()].sort((a,b)=>a.path.localeCompare(b.path))};
}
