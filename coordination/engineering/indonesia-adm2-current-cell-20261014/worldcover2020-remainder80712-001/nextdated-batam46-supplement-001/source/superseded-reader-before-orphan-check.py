"""Existing Rasterio native Window read/read_masks and atomic NPZ custody, raw only.
No normalization, display, indices, physical classifier or authority predicate.
"""
from pathlib import Path
import collections,contextlib,datetime,hashlib,json,os,resource,sys,time,urllib.request,shutil
import numpy as np
import rasterio
from rasterio.windows import Window
ROOT=Path(__file__).resolve().parent
PLAN=ROOT/'next-distinct-native-block-plan72.json'
PLAN_SHA='e3b1689644c1bd30f928e24f91b19e349984d54e368318784280d8cb9e01e098'
OUT=ROOT/'next-distinct-raw-native-observation-001'
OUT.mkdir(exist_ok=True)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return {'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':h.hexdigest()}
def atomic_json(path,value):
 b=(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode();temporary=path.with_suffix(path.suffix+'.partial')
 with temporary.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(temporary,path);return pin(path)
def identity(headers):return {k.lower():v for k,v in headers.items() if k.lower() in ('etag','content-length','last-modified','accept-ranges')}
raw=PLAN.read_bytes();assert hashlib.sha256(raw).hexdigest()==PLAN_SHA;plan=json.loads(raw)
assert plan['exact_original_scope']==72 and plan['total_asset_native_block_windows']==55 and len(plan['items'])==1
reader=pin(Path(__file__));start=time.monotonic();started=utc();remote_blocks=0;remote_data_calls=0;remote_mask_calls=0;reused_blocks=0;failures=[];complete_items=[]
atomic_json(OUT/'attempt-001.started.json',{'started_utc':started,'pid':os.getpid(),'plan_sha256':PLAN_SHA,'reader':reader,'phase':'rawDN+nativeMasks+SCL-only','Root_authorization':'Launch requires distinct complete whole72 plan review and explicit parent instruction; original first-date f9d57d96 review is historical method context only','normalization_display_indices':False})
def status(state):
 return atomic_json(OUT/'execution-status.json',{'state':state,'started_utc':started,'updated_utc':utc(),'elapsed_seconds':time.monotonic()-start,'pid':os.getpid(),'plan_sha256':PLAN_SHA,'reader':reader,'remote_value_block_calls':remote_data_calls,'remote_mask_block_calls':remote_mask_calls,'reused_complete_block_arrays':reused_blocks,'complete_items':complete_items,'failures':failures,'new_scientific_or_native_credit':0})
status('running')
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_CONNECTTIMEOUT='30',GDAL_HTTP_TIMEOUT='120'):
 for item in plan['items']:
  folder=OUT/item['item_id'];folder.mkdir(exist_ok=True);done=folder/'item-complete.json'
  if done.exists():
   previous=json.loads(done.read_text());assert previous['plan_sha256']==PLAN_SHA and previous['reader_sha256']==reader['sha256']
   for f in previous['products']:
    assert pin(ROOT/f['file'])==f
   complete_items.append(previous);reused_blocks+=previous['asset_block_count'];status('running');continue
  print(json.dumps({'event':'item-start','item':item['item_id'],'points':len(item['points'])}),flush=True)
  point_records={tuple(p['original_key'][k] for k in ('owner','y','x')):{'original_key':p['original_key'],'point_index':p['point_index'],'centre_unchanged':p['centre_unchanged'],'item_id':item['item_id'],'acquisition_datetime':item['acquisition_datetime'],'processing_generation_time':item['processing_generation_time'],'processing_baseline':item['processing_baseline'],'normalization_contract_unchanged':item['normalization_contract'],'original_source_association_inventory':plan['original778_inventory'],'planned_native_context':p['per_asset_native_plan'],'actual_polygon_clear_sky_body_validity':'not-established-by-raw-data-or-mask-alone','assets':{},'new_physical_interpretation_or_native_credit':0} for p in item['points']}
  products=[];asset_failed=False;item_blocks=0
  for asset_name,asset in item['assets'].items():
   af=folder/asset_name;af.mkdir(exist_ok=True);cached={};arrays={};missing=[];metadata_pins=[]
   try:
    for block in asset['native_blocks']:
     br,bc=block['block'];meta=af/('block-%02d-%02d.json'%(br,bc));array=af/('block-%02d-%02d.npz'%(br,bc))
     if meta.exists():
      m=json.loads(meta.read_text());assert m['plan_sha256']==PLAN_SHA and m['reader_sha256']==reader['sha256'] and m['item_id']==item['item_id'] and m['asset']==asset_name and m['native_window']==block['native_window'] and m['source_url']==asset['source_url'] and m['source_object_identity']==asset['HEAD_identity'];assert pin(array)==m['array'];cached[(br,bc)]=m;reused_blocks+=1
     else:missing.append((block,meta,array))
    if missing:
     with urllib.request.urlopen(urllib.request.Request(asset['source_url'],method='HEAD'),timeout=60) as response:
      actual_identity=identity(dict(response.headers));assert response.status==200 and actual_identity==asset['HEAD_identity']
     with rasterio.open(asset['source_url']) as ds:
      h=asset['actual_header'];assert str(ds.crs)==h['crs'] and list(ds.transform)==h['transform'] and ds.width==h['width'] and ds.height==h['height'] and ds.count==1 and list(ds.dtypes)==h['dtypes'] and ds.nodata==h['nodata'] and [list(x) for x in ds.block_shapes]==h['block_shapes'] and list(ds.scales)==h['scales'] and list(ds.offsets)==h['offsets']
      for block,meta,array in missing:
       left,top,width,height=block['native_window'];window=Window(left,top,width,height)
       if shutil.disk_usage(ROOT).free < 10*1024**3+6*1024**2:raise RuntimeError('Insufficient actual disk for next whole block plus metadata safety above10GiB floor; stop entire item.')
       values=ds.read(1,window=window);remote_data_calls+=1
       mask=ds.read_masks(1,window=window);remote_mask_calls+=1
       assert values.shape==mask.shape==(height,width) and str(values.dtype)==h['dtypes'][0] and str(mask.dtype)=='uint8'
       temporary=array.with_suffix('.npz.partial')
       with temporary.open('wb') as f:np.savez_compressed(f,values=values,mask=mask);f.flush();os.fsync(f.fileno())
       os.replace(temporary,array)
       m={'plan_sha256':PLAN_SHA,'reader_sha256':reader['sha256'],'item_id':item['item_id'],'asset':asset_name,'source_url':asset['source_url'],'source_object_identity':actual_identity,'native_window':block['native_window'],'native_block':block['block'],'source_header':h,'array':pin(array),'saved_utc':utc(),'operation':'Raw native integer fullblock and literal native source mask, no normalization/resampling/indices/display','whole_remote_object_authenticated':False}
       atomic_json(meta,m);cached[tuple(block['block'])]=m;remote_blocks+=1;status('running')
       if remote_blocks%25==0:print(json.dumps({'event':'blocks-complete','item':item['item_id'],'asset':asset_name,'remote_blocks':remote_blocks,'reused_blocks':reused_blocks}),flush=True)
    for block in asset['native_blocks']:
     br,bc=block['block'];m=cached[(br,bc)];meta=af/('block-%02d-%02d.json'%(br,bc));metadata_pins.append(pin(meta))
     with np.load(ROOT/m['array']['file'],allow_pickle=False) as npz:values=npz['values'];mask=npz['mask']
     left,top,width,height=m['native_window'];assert values.shape==mask.shape==(height,width) and str(values.dtype)==asset['actual_header']['dtypes'][0] and str(mask.dtype)=='uint8';arrays[(br,bc)]=(values,mask,m)
    h=asset['actual_header'];bh,bw=h['block_shapes'][0]
    def pixel(row,col):
     if not (0<=row<h['height'] and 0<=col<h['width']):return None,None,None
     values,mask,m=arrays[(row//bh,col//bw)];left,top,_,_=m['native_window'];return int(values[row-top,col-left]),int(mask[row-top,col-left]),m['array']
    for p in item['points']:
     key=tuple(p['original_key'][k] for k in ('owner','y','x'));row,col=p['per_asset_native_plan'][asset_name]['containing_pixel'];value,mask,array=pixel(row,col);near=[];near_masks=[]
     for rr in range(row-1,row+2):
      nv=[];nm=[]
      for cc in range(col-1,col+2):v,ma,_=pixel(rr,cc);nv.append(v);nm.append(ma)
      near.append(nv);near_masks.append(nm)
     point_records[key]['assets'][asset_name]={'raw_value':value,'native_valid_mask':mask,'nodata_match':value==h['nodata'],'native_containing_pixel':[row,col],'native_fractional_pixel':p['per_asset_native_plan'][asset_name]['fractional_pixel'],'actual_raw3x3':near,'actual_mask3x3':near_masks,'raw3x3_complete':all(v is not None for line in near for v in line),'containing_array':array,'native_context_window_plan':p['per_asset_native_plan'][asset_name],'source_url':asset['source_url'],'source_object_identity':asset['HEAD_identity'],'actual_header':h,'declared_raster_bands':asset['declared_raster_bands']}
    item_blocks+=len(asset['native_blocks']);products.extend(metadata_pins);products.extend(m['array'] for m in cached.values());arrays.clear();cached.clear()
    products.append(atomic_json(af/'asset-complete.json',{'plan_sha256':PLAN_SHA,'reader_sha256':reader['sha256'],'item_id':item['item_id'],'asset':asset_name,'native_blocks':metadata_pins,'complete_point_records':len(item['points']),'source_object_identity':asset['HEAD_identity'],'status':'raw-native-blocks-complete'}))
   except Exception as error:
    failure={'item_id':item['item_id'],'asset':asset_name,'type':type(error).__name__,'error':str(error),'at_utc':utc()};failures.append(failure);atomic_json(af/'failure.json',failure);asset_failed=True;print(json.dumps({'event':'asset-failed',**failure}),flush=True);status('running')
    break  # Any failure stops the complete natural item; no later asset reads.
  if not asset_failed:
   observations=folder/'point-observations.jsonl';temporary=observations.with_suffix('.jsonl.partial')
   with temporary.open('wb') as f:
    for key,r in sorted(point_records.items()):
     assert len(r['assets'])==5;f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    f.flush();os.fsync(f.fileno())
   os.replace(temporary,observations);products.append(pin(observations));receipt={'plan_sha256':PLAN_SHA,'reader_sha256':reader['sha256'],'item_id':item['item_id'],'point_count':len(point_records),'asset_block_count':item_blocks,'products':products,'acquisition_datetime':item['acquisition_datetime'],'completed_utc':utc(),'physical_or_native_credit':0};atomic_json(done,receipt);complete_items.append(receipt);status('running');print(json.dumps({'event':'item-complete','item':item['item_id'],'points':len(point_records),'asset_blocks':item_blocks}),flush=True)
status('complete' if not failures else 'partial-with-actual-failures')
atomic_json(OUT/'attempt-001.execution.json',{'started_utc':started,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-start,'plan_sha256':PLAN_SHA,'reader':reader,'complete_item_count':len(complete_items),'complete_points':sum(x['point_count'] for x in complete_items),'remote_data_block_calls':remote_data_calls,'remote_mask_block_calls':remote_mask_calls,'reused_blocks':reused_blocks,'failures':failures,'process_lifetime_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),'runtime':{'platform':sys.platform,'python':sys.version,'numpy':np.__version__,'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__},'normalization_or_display_or_indices':False,'scientific_or_native_credit':0,'actual_saved_npz_encoded_bytes':sum(p.stat().st_size for p in OUT.rglob('*.npz')),'complete_item_resource_declaration':plan['complete_item_resource_declaration']})
print(json.dumps({'status':'complete' if not failures else 'partial','items':len(complete_items),'points':sum(x['point_count'] for x in complete_items),'remote_blocks':remote_blocks,'reused_blocks':reused_blocks,'failures':len(failures),'elapsed_seconds':time.monotonic()-start}),flush=True)
sys.exit(0 if not failures else 1)
