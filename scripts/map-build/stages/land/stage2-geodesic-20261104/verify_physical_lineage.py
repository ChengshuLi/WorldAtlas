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

def _validate_legacy_combined(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard=lambda:None):
 chain=validate(request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard)
 selected=validate_neon_sources(snapshot,snapshot_sha256,request_path,guard)
 need(chain['request_sha256']==selected['lineage_request_sha256'],'lineage request changed during source binding')
 return {'schema':'stage1-lineage-and-selection-validation-v1','status':'selected-sources-match-reported-lineage','report_chain':chain,'neon_selection':selected,'limitations':['Report-chain and selected-record consistency only; no raw sources were rehashed or rerasterized.','The snapshot and provider/R2 custody require independent authentication.']}

def _events(pin, guard):
 need(isinstance(pin,dict) and set(pin)=={'path','sha256'} and HEX.fullmatch(pin['sha256']),'invalid event pin')
 p=Path(pin['path']).resolve(strict=True);need(p.is_file() and digest(p,guard)==pin['sha256'],'event hash mismatch')
 with p.open() as f: rows=[json.loads(line) for line in f if line.strip()]
 need(digest(p,guard)==pin['sha256'],'events changed during read')
 return rows


def _validate_orchestrated(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard):
 """Check current orchestrator reports and captured receipts, not provider authenticity."""
 need(all(isinstance(x,str) and HEX.fullmatch(x) for x in (snapshot_sha256,physical_report_sha256,rows_sha256,runs_sha256)),'invalid expected hashes')
 need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and grid['width']>1 and type(grid['height']) is int and grid['height']>0 and grid['west']==-180 and grid['north']==90 and grid['step']==360/grid['width'] and 90-grid['height']*grid['step']>=-90-1e-8,'invalid expected grid')
 path=Path(request_path).resolve(strict=True);raw=path.read_bytes();req=json.loads(raw)
 need(set(req)=={'schema','inputs','code_root'} and req['schema'] in ('stage1-orchestrated-lineage-request-v1','stage1-raw-physical-lineage-request-v1'),'invalid orchestrated lineage request')
 fresh=req['schema']=='stage1-raw-physical-lineage-request-v1'
 expected={'pipeline_report','osm_receipt','neon_selection'}
 if not fresh:expected|={'initial_events','resume_events','part18_receipt'}
 inp=req['inputs'];need(isinstance(inp,dict) and set(inp)==expected,'invalid orchestrated input set')
 pipe,pp=read_pin(inp['pipeline_report'],guard);osm,_=read_pin(inp['osm_receipt'],guard);neon,_=read_pin(inp['neon_selection'],guard)
 if not fresh:
  part18,_=read_pin(inp['part18_receipt'],guard);initial=_events(inp['initial_events'],guard);resumed=_events(inp['resume_events'],guard)
 need(pipe.get('status')=='candidate-only' and pipe.get('grid')==grid and pipe.get('shard_count')==32,'pipeline report mismatch')
 code_root=Path(req['code_root']).resolve(strict=True);need(code_root.is_dir(),'invalid code root')
 code=pipe.get('script_sha256');names={'build_physical.py','build.py','rasterize_land.py','overture/rasterize_water_shard.py','overture/aggregate_compare.py','compose_physical.py'}
 native_names={'overture/water_native.py','overture/water_native.cpp'}
 batch_name='overture/water_batch.py'
 need(isinstance(code,dict) and set(code) in (names,names|native_names,names|{batch_name}),'invalid pipeline code pins')
 names=set(code)
 for name in sorted(names):
  cp=(code_root/name).resolve(strict=True);need(cp.is_relative_to(code_root) and cp.is_file() and digest(cp,guard)==code[name],'pipeline code mismatch: '+name)
 pipeline_config,_=read_pin({'path':str(pp.parent/'pipeline-config.json'),'sha256':pipe['configuration_sha256']},guard)
 for k in ('land_config','water_config','source_manifest'):need(pipe.get(k)==pipeline_config.get(k),'pipeline config pin mismatch: '+k)
 landcfg,_=read_pin(pipe['land_config'],guard);watercfg,_=read_pin(pipe['water_config'],guard);manifest,_=read_pin(pipe['source_manifest'],guard)
 need(landcfg.get('grid')==watercfg.get('grid')==grid,'input grid mismatch')
 stages=pipe.get('stage_reports');need(isinstance(stages,dict) and set(stages)=={'land','union','physical'},'invalid stage report pins')
 land,lp=read_pin(stages['land'],guard);union,up=read_pin(stages['union'],guard);physical,fp=read_pin(stages['physical'],guard)
 need(stages['physical']['sha256']==physical_report_sha256 and all(x.get('status')=='candidate-only' and x.get('grid')==grid for x in (land,union,physical)),'stage report mismatch')
 need(land.get('configuration_sha256')==pipe['land_config']['sha256'] and digest(lp.parent/'config.json',guard)==pipe['land_config']['sha256'] and digest(lp.parent/'land.tif',guard)==land.get('land_sha256'),'land output/config mismatch')
 unioncfg,_=read_pin({'path':str(up.parent/'config.json'),'sha256':union['configuration_sha256']},guard)
 physcfg,_=read_pin({'path':str(fp.parent/'config.json'),'sha256':physical['configuration_sha256']},guard)
 need(union.get('source_manifest')==unioncfg.get('source_manifest')==pipe['source_manifest'] and union.get('shard_count')==unioncfg.get('shard_count')==32 and union.get('shards')==unioncfg.get('shards'),'union configuration mismatch')
 need(digest(up.parent/'water-union.tif',guard)==union.get('union_sha256') and physcfg.get('land')==physical.get('inputs',{}).get('land') and physcfg.get('water')==physical.get('inputs',{}).get('water') and physcfg['land']['sha256']==land['land_sha256'] and physcfg['water']['sha256']==union['union_sha256'],'physical input mismatch')
 outputs=physical.get('output_sha256');need(isinstance(outputs,dict) and outputs==pipe.get('physical_output_sha256') and outputs.get('rows.u32le')==rows_sha256 and outputs.get('runs.u32le')==runs_sha256,'physical output pins mismatch')
 for name in ('physical-dry.tif','rows.u32le','runs.u32le'):need(digest(fp.parent/name,guard)==outputs.get(name),'physical output hash mismatch: '+name)
 files=manifest.get('files');need(manifest.get('source')=='Overture Maps Foundation' and manifest.get('theme')=='base' and manifest.get('type')=='water' and manifest.get('file_count')==32 and isinstance(files,list) and len(files)==32 and len(union['shards'])==32,'invalid shard manifest')
 need(sum(x.get('size',0) for x in files)==manifest.get('total_bytes'),'manifest byte total mismatch')
 srcs={(x['source_id'],x['version']):x for x in snapshot.get('sources',[])};assets={(x['source_id'],x['version']):x for x in snapshot.get('source_lineage_assets',[])};deps=snapshot.get('source_lineage_dependencies');sel=snapshot.get('stage1_source_inputs');need(isinstance(sel,list) and len(sel)==33 and len(srcs)==len(snapshot.get('sources',[])) and len(assets)==len(snapshot.get('source_lineage_assets',[])) and isinstance(deps,list),'invalid snapshot selection')
 need(all(isinstance(x,dict) and isinstance(x.get('source_id'),str) and isinstance(x.get('version'),str) for x in deps),'invalid source lineage dependencies');derived={(x['source_id'],x['version']) for x in deps}
 selected={};selected_assets=set()
 for x in sel:
  key=(x.get('role'),x.get('ordinal'));asset=(x.get('source_id'),x.get('source_version'));need(key not in selected and asset not in selected_assets and x.get('execution_status')=='selected_for_research','invalid selected source');selected[key]=x;selected_assets.add(asset)
 need(set(selected)=={('physical_land',0)}|{('inland_water',i) for i in range(32)},'incomplete selected source set')
 live=neon.get('rows');need(neon.get('schema')=='worldatlas-neon-stage1-selection-readback-v1' and isinstance(live,list) and len(live)==33,'invalid Neon capture')
 liveby={}
 for x in live:
  key=(x.get('role'),x.get('ordinal'));need(key not in liveby and x.get('revision')==neon.get('revision') and x.get('execution_status')=='selected_for_research','invalid Neon selection row');liveby[key]=x
 need(set(liveby)==set(selected) and snapshot.get('decision_revision',{}).get('id')==neon.get('revision'),'Neon revision mismatch')
 for key,selrow in selected.items():
  live_row=liveby[key];assetkey=(selrow.get('source_id'),selrow.get('source_version'));source=srcs.get(assetkey);asset=assets.get(assetkey)
  need(selrow.get('decision_revision')==neon.get('revision') and isinstance(source,dict) and isinstance(asset,dict) and assetkey not in derived and asset.get('kind')=='raw' and isinstance(asset.get('source_uri'),str) and bool(asset['source_uri']) and isinstance(asset.get('provenance'),dict) and (live_row.get('source_id'),live_row.get('version'))==assetkey and all(str(live_row.get(k))==str(source.get(k))==str(asset.get(k)) for k in ('sha256','size_bytes','r2_bucket','r2_key')),'Neon source differs from snapshot or raw lineage')
 landrow=liveby[('physical_land',0)];need(osm.get('status')=='matched' and osm.get('r2_bucket')==landrow['r2_bucket'] and osm.get('r2_key')==landrow['r2_key'] and osm.get('r2_stream',{}).get('sha256')==landrow['sha256'] and str(osm.get('r2_stream',{}).get('bytes'))==str(landrow['size_bytes']) and osm.get('local_archive',{}).get('sha256')==landrow['sha256'] and str(osm.get('local_archive',{}).get('bytes'))==str(landrow['size_bytes']),'OSM custody mismatch')
 members=osm.get('members');need(isinstance(members,list) and len(members)==5,'OSM member receipt incomplete')
 byname={Path(x['member']).name:x for x in members};pins={Path(x['path']).name:x for layer in landcfg['land'] for x in layer['files']};need(len(byname)==len(pins)==5 and set(byname)==set(pins),'OSM sidecar set mismatch')
 for name,pin in pins.items():
  m=byname[name];need(m.get('match') is True and m.get('archive_sha256')==m.get('local_sha256')==m.get('config_sha256')==pin['sha256'] and digest(pin['path'],guard)==pin['sha256'],'OSM sidecar mismatch: '+name)
 if not fresh:
  oldrows=[x for x in initial if x.get('event')=='shard_complete'];reusedrows=[x for x in resumed if x.get('event')=='reused_shard_checkpoint'];freshrows=[x for x in resumed if 'downloaded' in x]
  old={x.get('source_id'):x for x in oldrows};reused={x.get('source_id'):x for x in reusedrows};freshrows_by_id={x.get('source_id'):x for x in freshrows}
  need(len(oldrows)==len(old)==18 and len(reusedrows)==len(reused)==18 and len(freshrows)==len(freshrows_by_id)==14,'incomplete or duplicated event set')
 reportpins=[]
 for i,(item,sp) in enumerate(zip(files,union['shards'])):
  guard();source_id=item.get('source_id');live_row=liveby[('inland_water',i)];need(source_id==live_row['source_id'] and item.get('sha256')==live_row['sha256'] and str(item.get('size'))==str(live_row['size_bytes']) and item.get('r2_bucket')==live_row['r2_bucket'] and item.get('r2_key')==live_row['r2_key'],'source manifest/Neon mismatch')
  sr,_=read_pin(sp['report'],guard);need(sp.get('status')=='candidate-only' and sr.get('status')=='candidate-only' and sr.get('source_sha256')==item['sha256'] and Path(sr.get('source','')).name==Path(item['path']).name and sr.get('configuration_sha256')==pipe['water_config']['sha256'] and sr.get('script_sha256')==code['overture/rasterize_water_shard.py'] and sr.get('grid')==grid and sr.get('policy')==watercfg.get('policy') and sr.get('batch_size')==pipe.get('water_batch_size') and sr.get('output_sha256')==sp.get('sha256') and digest(sp['path'],guard)==sp['sha256'],'shard report/output mismatch: '+str(i))
  if native_names<=names:need(sr.get('rasterizer')==watercfg.get('rasterizer','native'),'water rasterizer/config mismatch: '+str(i))
  if batch_name in names:
   engine=watercfg.get('rasterizer','gdal');kernel=sr.get('gdal_kernel')
   need(engine in ('gdal','python') and sr.get('rasterizer')==engine and sr.get('native_kernel') is None,'water rasterizer/config mismatch: '+str(i))
   if engine=='gdal':
    need(isinstance(kernel,dict) and kernel.get('implementation') in ('python-gdal-c-api-v1','python-gdal-api-v2') and kernel.get('method')==watercfg.get('batch_method','hybrid') and kernel.get('binding_sha256')==code[batch_name],'GDAL water kernel mismatch: '+str(i))
   else:
    need(kernel is None,'unexpected GDAL water kernel: '+str(i))
  if sr.get('rasterizer')=='native':
   kernel=sr.get('native_kernel',{});need(native_names<=names and kernel.get('method')==watercfg.get('native_method','hybrid') and kernel.get('source_sha256')==code['overture/water_native.cpp'] and kernel.get('binding_sha256')==code['overture/water_native.py'] and digest(Path(sp['path']).parent/'water-native.so',guard)==kernel.get('binary_sha256'),'native water kernel mismatch: '+str(i))
  elif native_names<=names:need(sr.get('rasterizer')=='python' and sr.get('native_kernel') is None,'invalid water rasterizer: '+str(i))
  if not fresh and i<18:
   e=old.get(source_id,{});re=reused.get(source_id,{});need(e.get('sha256')==item['sha256'] and e.get('size')==item['size'] and Path(e.get('source','')).name==Path(item['path']).name and e.get('output_sha256')==sp['sha256'] and re.get('source_sha256')==item['sha256'] and re.get('output_sha256')==sp['sha256'] and re.get('report_sha256')==sp['report']['sha256'],'checkpoint event mismatch')
  elif not fresh:
   e=freshrows_by_id.get(source_id,{});need(e.get('sha256')==item['sha256'] and e.get('size')==item['size'],'fresh staging event mismatch')
   if i==18:need(e.get('downloaded') is False and part18.get('source_id')==source_id and part18.get('source_sha256')==item['sha256'] and part18.get('bytes')==item['size'] and part18.get('r2_key')==item['r2_key'] and part18.get('r2_bucket')==item['r2_bucket'] and part18.get('shard_report_sha256')==sp['report']['sha256'] and part18.get('output_sha256')==sp['sha256'] and part18.get('r2_readback')=='verified in this run','part18 receipt mismatch')
   else:need(e.get('downloaded') is True,'missing fresh R2 download assertion')
  reportpins.append(sp['report']['sha256'])
 for pin in inp.values():need(digest(pin['path'],guard)==pin['sha256'],'lineage input changed')
 for pin in stages.values():need(digest(pin['path'],guard)==pin['sha256'],'stage report changed')
 for sp in union['shards']:need(digest(sp['path'],guard)==sp['sha256'] and digest(sp['report']['path'],guard)==sp['report']['sha256'],'shard changed')
 for name in names:need(digest(code_root/name,guard)==code[name],'pipeline code changed')
 for pin in pins.values():need(digest(pin['path'],guard)==pin['sha256'],'OSM sidecar changed')
 need(digest(path,guard)==hashlib.sha256(raw).hexdigest(),'lineage request changed')
 limitations=['Report and receipt consistency, not independently authenticated provider claims or proof of geographic correctness.','The checker did not rerasterize raw sources; captured Neon and R2 observations are not cryptographic signatures.']
 if not fresh:limitations.insert(1,'The first 18 shards and land were reused from checked checkpoints; prior land producer code identity is an operator assertion, not an attestation.')
 return {'schema':'stage1-lineage-and-selection-validation-v1','status':'selected-sources-match-reported-lineage','method':'raw-physical-report-chain-v1' if fresh else 'orchestrated-report-chain-v1','request_sha256':hashlib.sha256(raw).hexdigest(),'snapshot_sha256':snapshot_sha256,'physical_report_sha256':physical_report_sha256,'physical_rows_sha256':rows_sha256,'physical_runs_sha256':runs_sha256,'shard_report_sha256':reportpins,'grid':grid,'limitations':limitations}


def validate_combined(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard=lambda:None):
 with open(request_path,'rb') as f: schema=json.load(f).get('schema')
 if schema in ('stage1-orchestrated-lineage-request-v1','stage1-raw-physical-lineage-request-v1'):
  return _validate_orchestrated(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard)
 return _validate_legacy_combined(snapshot,snapshot_sha256,request_path,physical_report_sha256,rows_sha256,runs_sha256,grid,guard)
