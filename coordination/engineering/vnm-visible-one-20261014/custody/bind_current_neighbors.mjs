// Rebind the unchanged complete-coordinate certificate to actual selected inputs.
// Boxes exclude only disjoint features; whole possible-neighbor geometries remain.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const here=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(here,'../../../..');
const own=path.relative(repo,path.dirname(here));
const baseline='a35ba193cfe5c84424a4952ca752593ebf9d7102';
const [head,vintage]=process.argv.slice(2);
const git=(...args)=>execFileSync('git',['-c','user.name=WorldAtlas Agent','-c','user.email=agent@invalid','-C',repo,...args],{maxBuffer:32*1024**2});
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const bytes=value=>Buffer.from(JSON.stringify(canonical(value))+'\n');
const digest=value=>sha(bytes(value));
const demand=(condition,message)=>{if(!condition)throw Error(message);};
demand(/^[a-f0-9]{40}$/.test(head??'')&&git('rev-parse','HEAD').toString().trim()===head,'Exact execution HEAD required');
demand(/^[a-z0-9][a-z0-9-]{0,63}$/.test(vintage??''),'Fresh named vintage required');
const script=path.relative(repo,fileURLToPath(import.meta.url));
const scriptBytes=fs.readFileSync(fileURLToPath(import.meta.url));
demand(scriptBytes.equals(git('show',head+':'+script)),'Unfrozen executing code');
const output=path.join(repo,own,'vintages',vintage);
function absentOutput(){
  for(let p=output;p!==path.dirname(repo);p=path.dirname(p)){
    const stat=fs.lstatSync(p,{throwIfNoEntry:false});
    demand(!stat?.isSymbolicLink(),'Symlink output path');
    if(p===output)demand(!stat,'Occupied output destination');
  }
}
absentOutput();
const inputs=new Map(),decodedInputs=new Map();
const charge=()=>demand([...inputs.values()].reduce((s,p)=>s+p.bytes,0)+[...decodedInputs.values()].reduce((s,n)=>s+n,0)+scriptBytes.length+16*1024**2<128*1024**2,'Complete metadata input/output reservation exceeded');
function read(name,expected={},commit=baseline){
  demand(typeof name==='string'&&!name.startsWith('/')&&!name.split('/').some(x=>!x||x==='.'||x==='..'),'Unsafe input path');
  const tree=git('ls-tree','-z',commit,'--',name).toString();
  const m=/^(100644) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(tree);
  demand(m&&m[3]===name,'Ordinary immutable source required');
  const size=Number(git('cat-file','-s',m[2]));
  demand(size<=32*1024**2,'Ordinary input too large');
  const raw=git('cat-file','blob',m[2]);
  const pin={commit,path:name,mode:m[1],git_blob_oid:m[2],bytes:raw.length,sha256:sha(raw)};
  for(const key of ['mode','git_blob_oid','bytes','sha256'])if(expected[key]!==undefined)demand(pin[key]===expected[key],'Input drift: '+name+' '+key);
  inputs.set(commit+':'+name,pin);charge();return raw;
}
function decoded(raw,pin,name){
  const result=gunzipSync(raw,{maxOutputLength:32*1024**2});
  demand(result.length===pin.bytes&&sha(result)===pin.sha256,'Decoded input drift: '+name);
  decodedInputs.set(name,result.length);charge();return result;
}
function bounds(geometry){
  const box=[Infinity,Infinity,-Infinity,-Infinity];
  function point(p){demand(p.length>=2&&p.every(Number.isFinite),'Nonfinite coordinate');box[0]=Math.min(box[0],p[0]);box[1]=Math.min(box[1],p[1]);box[2]=Math.max(box[2],p[0]);box[3]=Math.max(box[3],p[1]);}
  function visit(v){if(Array.isArray(v)&&v.length&&typeof v[0]==='number')point(v);else if(Array.isArray(v))v.forEach(visit);}
  if(geometry.type==='GeometryCollection')for(const g of geometry.geometries){const b=bounds(g);if(b){point(b.slice(0,2));point(b.slice(2));}}else visit(geometry.coordinates);
  return box.every(Number.isFinite)?box:null;
}
const intersects=(a,b)=>a&&b&&a[0]<=b[2]&&a[2]>=b[0]&&a[1]<=b[3]&&a[3]>=b[1];
const configPath=own+'/custody/inputs.json';
const config=JSON.parse(read(configPath,{},head));
const ids=config.components.map(row=>row.component_id);
const fit=JSON.parse(read('research/geography/southeast-asia-gap-batch-0393f64c-20261009/vintages/source-rule-fit-005/administrative-source-rule-fit.json'));
const candidates=ids.map(id=>{const rows=fit.cases.filter(r=>r.component_id===id);demand(rows.length===1,'Unique original source-fit candidate required');return rows[0].current_component_candidate.feature;});
demand(ids.length===1&&new Set(ids).size===1,'Exact one-case scope required');
const certificatePath='coordination/engineering/melanesia363-additive-delivery-20261010/selected-integration/current-f02-coordinate/certificate.json.gz';
const certificate=JSON.parse(decoded(read(certificatePath,{bytes:7515239,sha256:'23aef083ceeabff7d76e7da2a6d047e9dc30b40a3e9b03e122492c4d41c9cd7e'}),{bytes:18414409,sha256:'60cc10692d3133b8141e659b932fe1f1d6c14286a6b80009c47b324c6bcaaf23'},certificatePath));
const selection=JSON.parse(read('data/ownership-selection.json'));
const bank=JSON.parse(read(selection.selected_geography.path,selection.selected_geography));
const index=JSON.parse(read(bank.world_index.path,bank.world_index));
const selectedSources=[...bank.unchanged_files,...bank.overrides.map(row=>row.after??row)];
demand(certificate.inputs.length===index.parts.length&&certificate.entries.length===49625,'Incomplete selected certificate');
demand(JSON.stringify(certificate.inputs.map(x=>x.path).sort())===JSON.stringify(index.parts.map(x=>'data/'+x).sort()),'Certificate omits indexed paths');
demand(certificate.binding.release.id===selection.release_id&&certificate.binding.release.footprints_sha256===bank.footprints_sha256,'Certificate release differs');
for(const input of certificate.inputs){
  const p=input.source;
  demand(git('ls-tree','-z',baseline,'--',p.path).toString()===p.mode+' blob '+p.git_blob_oid+'\t'+p.path+'\0','Certificate source changed: '+input.path);
  const selected=selectedSources.filter(r=>(r.logical_path??r.path)===input.path);
  demand(selected.length===1&&selected[0].git_blob_oid===p.git_blob_oid&&(selected[0].decoded_sha256??selected[0].sha256)===input.whole_body_sha256,'Certificate is not actual selected source');
}
const ownerIds=new Set();
for(const row of certificate.entries){demand(row.length===certificate.entry_fields.length&&!ownerIds.has(row[0]),'Duplicate or malformed owner row');ownerIds.add(row[0]);}
const parts=new Map();
function actualFeature(row){
  if(!parts.has(row[4])){
    const input=certificate.inputs.find(x=>x.path===row[4]);
    const selected=selectedSources.find(r=>(r.logical_path??r.path)===row[4]);
    let raw=read(input.source.path,input.source);
    if(selected.encoding==='gzip')raw=decoded(raw,{bytes:selected.decoded_bytes,sha256:selected.decoded_sha256},input.source.path);
    demand(sha(raw)===input.whole_body_sha256,'Selected whole decoded body differs');
    const data=JSON.parse(raw);parts.set(row[4],data.features??data);
  }
  const feature=parts.get(row[4])[row[5]];
  demand(feature.id===row[0]&&feature.properties.parent_id===row[2]&&digest(feature)===row[6]&&digest(feature.geometry)===row[7],'Actual whole neighbor differs');
  return feature;
}
const sidecar=JSON.parse(read(selection.additive_release.path,selection.additive_release));
const base=structuredClone(selection);delete base.additive_release;
demand(digest(base)===digest(sidecar.base_selection),'Additive selection base differs');
const ledger=JSON.parse(read(sidecar.logical_asset_map.ledger.path,sidecar.logical_asset_map.ledger));
const envelope=JSON.parse(read(sidecar.runtime_envelope.path,sidecar.runtime_envelope));
const geometryRows=[];
function scan(v,locator){if(!v||typeof v!=='object')return;if(['Polygon','MultiPolygon','GeometryCollection','LineString','MultiLineString','Point','MultiPoint'].includes(v.type)){geometryRows.push({locator,bounds:bounds(v),geometry_sha256:digest(v)});return;}for(const[k,x]of Object.entries(v))scan(x,locator+'/'+k);}
scan(ledger.rows,'/rows');scan(ledger.current_targets,'/current_targets');
demand(geometryRows.length>0,'Missing current additive geometries');
const rows=candidates.map(candidate=>{
  const box=bounds(candidate.geometry);
  const hits=certificate.entries.filter(row=>row[9].some(b=>intersects(box,b)));
  const neighbors=hits.map(row=>({certificate_entry:row,feature:actualFeature(row)}));
  const additive=geometryRows.map(r=>({...r,candidate_bbox_intersects:intersects(box,r.bounds)}));
  demand(additive.every(r=>!r.candidate_bbox_intersects),'Current additive geometry needs actual predicate');
  return{component_id:candidate.id,candidate_bounds:box,derived_js_feature_sha256:digest(candidate),derived_js_geometry_sha256:digest(candidate.geometry),candidate_neighbors:neighbors,additive_geometry_screen:additive};
});
const result={baseline,execution_commit:head,runtime:{node:process.version,platform:process.platform,architecture:process.arch},scopeIds:ids,rows,actual_selection:selection,actual_runtime_envelope:envelope,
  complete_owner_rows:certificate.entries.length,complete_source_parts:certificate.inputs.length,complete_additive_geometry_records:geometryRows.length,
  inputs:[...inputs.values()],decoded_inputs:[...decodedInputs].map(([name,bytes])=>({name,bytes})),
  method:'Unchanged complete-coordinate certificate rebound to all actual selected source identities; decode actual overrides and authenticate whole possible-neighbor features; screen every current additive geometry.',
  limits:['Boxes exclude disjoint envelopes only. Actual whole possible-neighbor predicates must be reused only after their input identities match, or recomputed.', 'No native or selected continuous integration is established.']};
const raw=bytes(result);
const phase=[...inputs.values()].reduce((s,p)=>s+p.bytes,0)+[...decodedInputs.values()].reduce((s,n)=>s+n,0)+scriptBytes.length+raw.length+4096;
demand(phase<128*1024**2&&process.resourceUsage().maxRSS*1024<512*1024**2,'Metadata phase exceeds reservation');
absentOutput();fs.mkdirSync(path.dirname(output),{recursive:true});fs.mkdirSync(output);
fs.writeFileSync(path.join(output,'result.json'),raw,{flag:'wx'});
fs.writeFileSync(path.join(output,'.publication-incomplete'),bytes({version:1,status:'complete',outputs:[{path:path.relative(repo,path.join(output,'result.json')),bytes:raw.length,sha256:sha(raw),hash_kind:'file-bytes'}]}),{flag:'wx'});
fs.linkSync(path.join(output,'.publication-incomplete'),path.join(output,'publication.json'));
fs.unlinkSync(path.join(output,'.publication-incomplete'));
console.log(JSON.stringify({complete_owner_rows:result.complete_owner_rows,source_parts:result.complete_source_parts,additive_geometries:geometryRows.length,neighbors:rows.map(r=>({component:r.component_id,ids:r.candidate_neighbors.map(n=>n.feature.id)})),phase_bytes:phase,peak_rss_bytes:process.resourceUsage().maxRSS*1024}));
