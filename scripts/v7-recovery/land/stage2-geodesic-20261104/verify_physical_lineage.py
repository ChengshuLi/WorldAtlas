"""Verify the pinned OSM/Overture-to-physical *reported* lineage.

No source rasterization or source-byte rehash occurs here. This checks that the
pinned reports form one internally consistent chain to the physical streams;
it is not independent proof that the raw source generated those streams.
"""
import hashlib,json,re
from pathlib import Path
HEX=re.compile(r'^[0-9a-f]{64}$')

def need(v,msg):
 if not v:raise ValueError(msg)
def digest(path,guard):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()
def read_pin(pin,guard):
 need(isinstance(pin,dict) and set(pin)=={'path','sha256'} and isinstance(pin['path'],str) and isinstance(pin['sha256'],str) and HEX.fullmatch(pin['sha256']),'invalid report pin')
 p=Path(pin['path']).resolve(strict=True);need(p.is_file() and digest(p,guard)==pin['sha256'],'report hash mismatch')
 with open(p,'rb') as f:data=json.load(f)
 need(digest(p,guard)==pin['sha256'],'report changed during read')
 return data,p

def read_overture_readback(pin,guard):
 need(isinstance(pin,dict) and set(pin)=={'path','sha256'} and isinstance(pin.get('sha256'),str) and HEX.fullmatch(pin['sha256']),'invalid R2 readback pin')
 p=Path(pin['path']).resolve(strict=True);need(p.is_file(),'R2 readback is not a file')
 with open(p,'rb') as f:data=f.read()
 need(hashlib.sha256(data).hexdigest()==pin['sha256'],'R2 readback hash mismatch');text=data.decode('utf-8').strip()
 if text.startswith('```json\n') and text.endswith('```'):text=text[8:-3].strip()
 return json.loads(text)

def validate(request_path,expected_physical_report_sha256,expected_rows_sha256,expected_runs_sha256,expected_grid,guard=lambda:None):
 need(all(isinstance(x,str) and HEX.fullmatch(x) for x in (expected_physical_report_sha256,expected_rows_sha256,expected_runs_sha256)),'invalid expected physical hashes')
 need(isinstance(expected_grid,dict) and set(expected_grid)=={'width','height','west','north','step'} and type(expected_grid['width']) is int and type(expected_grid['height']) is int and expected_grid['width']>1 and expected_grid['height']>0 and expected_grid['west']==-180 and expected_grid['north']==90 and type(expected_grid['step']) in (int,float) and expected_grid['step']==360/expected_grid['width'] and 90-expected_grid['height']*expected_grid['step']>=-90-1e-8,'invalid expected physical grid')
 path=Path(request_path).resolve(strict=True)
 with open(path,'rb') as f:raw=f.read()
 req=json.loads(raw)
 need(isinstance(req,dict) and set(req)=={'schema','inputs','shard_reports'} and req['schema']=='stage1-reported-lineage-request-v1','invalid lineage request')
 inp=req['inputs'];need(isinstance(inp,dict) and set(inp)=={'overture_manifest','overture_readback','osm_receipt','shard_summary','water_union','land_report','physical_report'},'invalid lineage input set')
 docs={};paths={}
 for k,pin in inp.items():
  guard()
  if k=='overture_readback':docs[k]=read_overture_readback(pin,guard);paths[k]=Path(pin['path']).resolve()
  else:docs[k],paths[k]=read_pin(pin,guard)
 shards=req['shard_reports'];need(isinstance(shards,list) and len(shards)==32 and all(isinstance(x,dict) and set(x)=={'index','path','sha256'} and type(x['index']) is int for x in shards),'32 shard report pins required')
 sby={x['index']:x for x in shards};need(set(sby)==set(range(32)),'duplicate or missing shard report indexes')
 reports={};report_paths=[]
 for i in range(32):
  r,p=read_pin({'path':sby[i]['path'],'sha256':sby[i]['sha256']},guard);reports[i]=r;report_paths.append(p)
 m=docs['overture_manifest'];summary=docs['shard_summary'];union=docs['water_union'];land=docs['land_report'];physical=docs['physical_report'];receipt=docs['osm_receipt']
 files=m.get('files');need(m.get('source')=='Overture Maps Foundation' and m.get('theme')=='base' and m.get('type')=='water' and m.get('file_count')==32 and isinstance(files,list) and len(files)==32,'invalid Overture manifest')
 by={}
 for f in files:
  need(isinstance(f,dict) and isinstance(f.get('path'),str) and isinstance(f.get('key'),str) and isinstance(f.get('sha256'),str) and HEX.fullmatch(f['sha256']) and type(f.get('size')) is int and f['size']>0 and f.get('provider_sha256_composite')==f.get('computed_sha256_composite') and bool(f.get('provider_sha256_composite')),'invalid Overture source record')
  match=re.fullmatch(r'part-(\d{5})-.+\.zstd\.parquet',Path(f['path']).name);need(match is not None,'invalid shard filename');i=int(match.group(1));need(i not in by and Path(f['key']).name==Path(f['path']).name,'duplicate shard or key mismatch');by[i]=f
 need(set(by)==set(range(32)) and sum(f['size'] for f in files)==m.get('total_bytes'),'incomplete source manifest')
 readback=docs['overture_readback'];need(isinstance(readback,list) and len(readback)==32 and all(isinstance(x,dict) and set(x)=={'key','size','sha256'} for x in readback),'invalid Overture readback listing');rb={}
 for x in readback:
  match=re.fullmatch(r'part-(\d{5})-.+\.zstd\.parquet',Path(x['key']).name) if isinstance(x.get('key'),str) else None;need(match is not None,'invalid readback key');idx=int(match.group(1));need(idx not in rb,'duplicate readback shard');rb[idx]=x
 need(set(rb)==set(range(32)) and all(rb[i]['sha256']==by[i]['sha256'] and rb[i]['size']==by[i]['size'] and Path(rb[i]['key']).name==Path(by[i]['path']).name for i in range(32)),'Overture readback differs from source manifest')
 entries=summary.get('shards');uh=union.get('shard_hashes');need(summary.get('status')=='candidate-only' and summary.get('manifest_sha256')==inp['overture_manifest']['sha256'] and isinstance(entries,list) and len(entries)==32 and union.get('status')=='candidate-only' and union.get('source_summary_sha256')==inp['shard_summary']['sha256'] and isinstance(uh,list) and len(uh)==32,'invalid shard summary/union')
 def keyed(xs):
  need(all(isinstance(x,dict) and type(x.get('index')) is int for x in xs),'bad shard entries');out={x['index']:x for x in xs};need(len(out)==32 and set(out)==set(range(32)),'duplicate or missing shard entries');return out
 ent=keyed(entries);u=keyed(uh);grid=physical.get('grid');need(grid==expected_grid,'physical grid mismatch');need(isinstance(summary.get('rasterizer_sha256'),str) and HEX.fullmatch(summary['rasterizer_sha256']),'missing rasterizer hash')
 for i in range(32):
  guard();r=reports[i];e=ent[i];need(isinstance(r.get('output_sha256'),str) and HEX.fullmatch(r['output_sha256']) and isinstance(r.get('counts'),dict) and bool(r['counts']) and all(isinstance(k,str) and type(v) is int and v>=0 for k,v in r['counts'].items()),'missing shard output hash or counts: '+str(i));need(r.get('status')=='candidate-only' and e.get('status')=='candidate-only' and r.get('grid')==grid and r.get('source_sha256')==by[i]['sha256'] and Path(r.get('source','')).name==Path(by[i]['path']).name and r.get('script_sha256')==summary.get('rasterizer_sha256') and r.get('output_sha256')==e.get('output_sha256')==u[i].get('sha256') and r.get('counts')==e.get('counts'),'shard report chain mismatch: '+str(i))
 need(isinstance(receipt.get('archive_sha256'),str) and HEX.fullmatch(receipt['archive_sha256']) and isinstance(receipt.get('files'),list) and isinstance(land.get('source_files'),list),'invalid OSM receipt or land report')
 members={Path(x.get('name','')).name:x.get('sha256') for x in receipt['files'] if isinstance(x,dict)};landfiles={Path(x.get('path','')).name:x.get('sha256') for x in land['source_files'] if isinstance(x,dict)}
 required={'README.txt','land_polygons.cpg','land_polygons.dbf','land_polygons.prj','land_polygons.shp','land_polygons.shx'}
 need(len(receipt['files'])==len(land['source_files'])==6 and set(members)==set(landfiles)==required and members==landfiles and all(isinstance(x,str) and HEX.fullmatch(x) for x in members.values()),'OSM member chain mismatch')
 need(isinstance(land.get('candidate_sha256'),str) and HEX.fullmatch(land['candidate_sha256']) and isinstance(union.get('union_sha256'),str) and HEX.fullmatch(union['union_sha256']),'missing land or water output hash')
 outputs=physical.get('physical_output_sha256',physical.get('output_sha256',{}))
 need(land.get('status')=='candidate-only' and physical.get('status') in ('candidate-only','stage1-complete') and inp['physical_report']['sha256']==expected_physical_report_sha256 and physical.get('inputs',{}).get('land',{}).get('sha256')==land.get('candidate_sha256') and physical.get('inputs',{}).get('water',{}).get('sha256')==union.get('union_sha256') and outputs.get('rows.u32le')==expected_rows_sha256 and outputs.get('runs.u32le')==expected_runs_sha256,'physical report chain mismatch')
 for pin in inp.values():need(digest(pin['path'],guard)==pin['sha256'],'lineage report changed')
 for x in shards:need(digest(x['path'],guard)==x['sha256'],'shard report changed')
 need(digest(path,guard)==hashlib.sha256(raw).hexdigest(),'lineage request changed')
 return {'schema':'stage1-reported-lineage-validation-v1','status':'reported-lineage-verified-not-rerasterized','request_sha256':hashlib.sha256(raw).hexdigest(),'inputs_sha256':{k:v['sha256'] for k,v in inp.items()},'shard_report_sha256':[sby[i]['sha256'] for i in range(32)],'physical_rows_sha256':expected_rows_sha256,'physical_runs_sha256':expected_runs_sha256,'grid':grid,'limitations':['Report-chain consistency only; no raw source bytes were rehashed and no source was rerasterized.','Matching hashes and receipts do not independently authenticate providers or prove source-to-mask computation.']}

def validate_neon_sources(snapshot,snapshot_sha256,request_path,guard=lambda:None):
 """Bind the selected Neon source records to the already checked report chain.

 Snapshot bytes must have been authenticated by the caller; this checks their
 internal records and hashes against the manifest/receipt, not provider custody.
 """
 need(isinstance(snapshot,dict) and isinstance(snapshot_sha256,str) and HEX.fullmatch(snapshot_sha256),'invalid source snapshot')
 revision=snapshot.get('decision_revision',{}).get('id');need(isinstance(revision,str) and revision,'missing source revision')
 with open(request_path,'rb') as f:raw=f.read()
 req=json.loads(raw);manifest,_=read_pin(req['inputs']['overture_manifest'],guard);receipt,_=read_pin(req['inputs']['osm_receipt'],guard);readback=read_overture_readback(req['inputs']['overture_readback'],guard)
 selected=snapshot.get('stage1_source_inputs');sources=snapshot.get('sources');assets=snapshot.get('source_lineage_assets');deps=snapshot.get('source_lineage_dependencies')
 need(isinstance(selected,list) and len(selected)==33 and isinstance(sources,list) and isinstance(assets,list) and isinstance(deps,list),'missing selected stage-1 source records')
 def catalog(rows):
  result={}
  for row in rows:
   need(isinstance(row,dict) and all(isinstance(row.get(k),str) and row[k] for k in ('source_id','version')),'invalid source catalog');key=(row['source_id'],row['version']);need(key not in result,'duplicate source catalog key');result[key]=row
  return result
 sc=catalog(sources);ac=catalog(assets);need(all(isinstance(x,dict) and isinstance(x.get('source_id'),str) and isinstance(x.get('version'),str) for x in deps),'invalid source dependency');derived={(x['source_id'],x['version']) for x in deps}
 selection={};used=set()
 for row in selected:
  need(isinstance(row,dict) and set(row)=={'decision_revision','role','ordinal','source_id','source_version','execution_status'} and row['decision_revision']==revision and row['execution_status']=='selected_for_research' and row['role'] in ('physical_land','inland_water') and type(row['ordinal']) is int and row['ordinal']>=0 and isinstance(row['source_id'],str) and bool(row['source_id']) and isinstance(row['source_version'],str) and bool(row['source_version']),'invalid selected stage-1 source')
  key=(row['role'],row['ordinal']);assetkey=(row['source_id'],row['source_version']);need(key not in selection and assetkey not in used,'duplicate selected stage-1 source');used.add(assetkey);selection[key]=assetkey
 need(set(selection)=={('physical_land',0)}|{('inland_water',i) for i in range(32)},'stage-1 source selection incomplete')
 files=manifest.get('files');need(isinstance(files,list) and len(files)==32,'source manifest incomplete');by={}
 for f in files:
  match=re.fullmatch(r'part-(\d{5})-.+\.zstd\.parquet',Path(f.get('path','')).name);need(match is not None,'invalid manifest shard');i=int(match.group(1));need(i not in by,'duplicate manifest shard');by[i]=f
 need(set(by)==set(range(32)),'source manifest indexes incomplete');rb={}
 for item in readback:
  match=re.fullmatch(r'part-(\d{5})-.+\.zstd\.parquet',Path(item.get('key','')).name);need(match is not None,'invalid readback key');idx=int(match.group(1));need(idx not in rb,'duplicate readback key');rb[idx]=item
 need(set(rb)==set(range(32)),'readback shard selection incomplete');results=[]
 for role,ordinal in sorted(selection):
  guard();key=selection[(role,ordinal)];src=sc.get(key);asset=ac.get(key);need(isinstance(src,dict) and isinstance(asset,dict) and key not in derived and asset.get('kind')=='raw' and all(src.get(k)==asset.get(k) for k in ('sha256','r2_bucket','r2_key','size_bytes')) and isinstance(src.get('sha256'),str) and HEX.fullmatch(src['sha256']) and isinstance(src.get('r2_bucket'),str) and src['r2_bucket'] and isinstance(src.get('r2_key'),str) and src['r2_key'] and type(src.get('size_bytes')) is int and src['size_bytes']>0 and isinstance(asset.get('source_uri'),str) and asset['source_uri'] and isinstance(asset.get('provenance'),dict),'selected source custody invalid')
  if role=='physical_land':expected_sha=receipt.get('archive_sha256');expected_size=receipt.get('archive_bytes');expected_name=Path(receipt.get('source_url','')).name
  else:expected_sha=by[ordinal].get('sha256');expected_size=by[ordinal].get('size');expected_name=Path(by[ordinal].get('path','')).name;need(src['r2_key']==rb[ordinal].get('key') and src['sha256']==rb[ordinal].get('sha256') and src['size_bytes']==rb[ordinal].get('size'),'selected Neon R2 key differs from readback')
  need(src['sha256']==expected_sha and src['size_bytes']==expected_size and Path(src['r2_key']).name==expected_name,'selected Neon source differs from report chain: '+role+'/'+str(ordinal))
  results.append({'role':role,'ordinal':ordinal,'source_id':key[0],'source_version':key[1],'sha256':src['sha256'],'size_bytes':src['size_bytes']})
 return {'schema':'stage1-neon-source-selection-validation-v1','status':'selected-source-records-match-reported-lineage','snapshot_sha256':snapshot_sha256,'decision_revision':revision,'lineage_request_sha256':hashlib.sha256(raw).hexdigest(),'selected_sources':results,'limitations':['Snapshot and provider/R2 custody must be independently authenticated.','The report chain is not a fresh raw-source rasterization.']}

def validate_combined(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard=lambda:None):
 chain=validate(request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard)
 selected=validate_neon_sources(snapshot,snapshot_sha256,request_path,guard)
 need(chain['request_sha256']==selected['lineage_request_sha256'],'lineage request changed during source binding')
 return {'schema':'stage1-lineage-and-selection-validation-v1','status':'selected-sources-match-reported-lineage','report_chain':chain,'neon_selection':selected,'limitations':['Report-chain and selected-record consistency only; no raw sources were rehashed or rerasterized.','The snapshot and provider/R2 custody require independent authentication.']}
