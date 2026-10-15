"""Cohort adaptation of existing Rasterio native read/read_masks + atomic NPZ kernels.
Annual2020 RGBNIR composite, not dated imagery, classification or tide evidence.
"""
from pathlib import Path
import collections,datetime,hashlib,io,json,os,resource,sys,time,urllib.request
import numpy as np
import rasterio
from rasterio.windows import Window
ROOT=Path(__file__).resolve().parent
PLAN=ROOT/'rgbnir-2020-native-block-plan.json';KEYS=ROOT/'exact-residual-keys.jsonl'
PLAN_SHA='0b60d822014271282a7d8a96cff9fd6ba7a06874f1467ae3fbd57e2983590934'
KEYS_SHA='a4efa518c9259747746766d8d517893aec4d56a71f3763e71451848c94595f0b'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def atomic_json(p,d):
 b=(json.dumps(d,separators=(',',':'))+'\n').encode();tmp=p.with_suffix(p.suffix+'.partial')
 with tmp.open('wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);return pin(p)
def identity(headers):return {k.lower():v for k,v in headers.items()if k.lower()in('etag','content-length','last-modified','accept-ranges')}
started=time.monotonic();began=utc();reader=pin(Path(__file__))
b=PLAN.read_bytes();assert sha(b)==PLAN_SHA;plan=json.loads(b);del b
b=KEYS.read_bytes();assert sha(b)==KEYS_SHA;original={d['point_index']:d for d in map(json.loads,b.splitlines())};del b
assert len(original)==plan['keys']==9332 and plan['tile_count']==14 and plan['native_blocks']==297
products=[];sources=[];counts=collections.Counter();failures=[];read_blocks=0;reused_blocks=0
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_CONNECTTIMEOUT='30',GDAL_HTTP_TIMEOUT='120'):
 for t in plan['tiles']:
  tile=t['tile'];folder=ROOT/'rgbnir-tiles'/tile;folder.mkdir(parents=True,exist_ok=True);done=folder/'tile-complete.json'
  try:
   if done.exists():
    d=json.loads(done.read_text());assert d['plan_sha256']==PLAN_SHA and d['reader_sha256']==reader['sha256']
    assert d['point_indices']==[p['point_index']for p in t['points']]
    assert pin(Path(d['product']['observations']['path']))==d['product']['observations']
    products.append(d['product']);sources.append(json.loads((folder/'source.json').read_text()));counts.update(d['counts']);reused_blocks+=len(t['native_blocks']);continue
   print(json.dumps({'event':'tile-start','tile':tile,'keys':len(t['points']),'blocks':len(t['native_blocks'])}),flush=True)
   with urllib.request.urlopen(urllib.request.Request(t['url'],method='HEAD'),timeout=60)as r:head={'status':r.status,'headers':dict(r.headers)}
   obj=identity(head['headers']);assert head['status']==200 and obj==identity(t['head_identity']) and obj.get('accept-ranges','').lower()=='bytes'
   arrays={}
   with rasterio.open(t['url'])as ds:
    assert str(ds.crs)==t['crs'] and list(ds.transform)==t['transform'] and ds.width==t['width'] and ds.height==t['height']
    assert ds.count==4 and list(ds.dtypes)==t['dtypes'] and ds.nodata==t['nodata'] and [list(b)for b in ds.block_shapes]==t['block_shapes']
    bh,bw=ds.block_shapes[0]
    for p in t['points']:
     k=original[p['point_index']];c=k['centre_unchanged'];assert k['original_key']==p['original_key'] and ds.index(c['longitude'],c['latitude'])==(p['row'],p['col'])
    source={'tile':tile,'url':t['url'],'source_object_identity':obj,'http':head,'crs':str(ds.crs),'transform':list(ds.transform),'shape':[ds.height,ds.width],'block_shapes':t['block_shapes'],'count':4,'dtypes':list(ds.dtypes),'nodata':ds.nodata,'band_descriptions':list(ds.descriptions),'tags':ds.tags(),'mask_flags':[[str(f)for f in fs]for fs in ds.mask_flag_enums],'product':'annual2020 S2RGBNIR composite','band_order':['red','green','blue','nir'],'scale':0.0001,'offset':0,'no_single_acquisition_or_tide':True,'whole_remote_tiff_hash_claimed':False}
    atomic_json(folder/'source.json',source);sources.append(source)
    for br,bc in t['native_blocks']:
     ap=folder/f'block-{br:02d}-{bc:02d}.npz';jp=ap.with_suffix('.json')
     if jp.exists():
      q=json.loads(jp.read_text());assert q['plan_sha256']==PLAN_SHA and q['reader_sha256']==reader['sha256'] and q['source_object_identity']==obj and pin(ap)==q['array'];reused_blocks+=1
     else:
      r0,c0=br*bh,bc*bw;h,w=min(bh,ds.height-r0),min(bw,ds.width-c0);window=Window(c0,r0,w,h)
      values=ds.read(window=window);masks=ds.read_masks(window=window);assert values.shape==masks.shape==(4,h,w)
      tmp=ap.with_suffix('.npz.partial')
      with tmp.open('wb')as f:np.savez_compressed(f,values=values,masks=masks);f.flush();os.fsync(f.fileno())
      os.replace(tmp,ap);q={'plan_sha256':PLAN_SHA,'reader_sha256':reader['sha256'],'source_object_identity':obj,'native_block':[br,bc],'window':{'row_off':r0,'col_off':c0,'height':h,'width':w},'array':pin(ap)};atomic_json(jp,q);read_blocks+=1
     arrays[(br,bc)]=q;print(json.dumps({'event':'block-complete','tile':tile,'block':[br,bc],'new_blocks':read_blocks,'reused_blocks':reused_blocks}),flush=True)
   grouped=collections.defaultdict(list)
   for p in t['points']:grouped[(p['row']//bh,p['col']//bw)].append(p)
   tp=folder/'point-observations.jsonl.partial';tilecounts=collections.Counter();incomplete=[]
   with tp.open('w')as f:
    for core,members in sorted(grouped.items()):
     loaded={}
     def pixel(r,c):
      q=arrays.get((r//bh,c//bw))
      if not q or not(0<=r<t['height']and 0<=c<t['width']):return None
      key=tuple(q['native_block'])
      if key not in loaded:
       b=Path(q['array']['path']).read_bytes();assert sha(b)==q['array']['sha256']
       with np.load(io.BytesIO(b),allow_pickle=False)as z:loaded[key]=(z['values'],z['masks'])
      v,m=loaded[key];w=q['window'];rr,cc=r-w['row_off'],c-w['col_off'];return v[:,rr,cc].astype(int).tolist(),m[:,rr,cc].astype(int).tolist(),q['array']['path']
     for p in members:
      r,c=p['row'],p['col'];value,masks,array=pixel(r,c);nodata=[v==t['nodata']for v in value]if t['nodata']is not None else[False]*4
      grid=[[pixel(r+dy,c+dx)for dx in(-1,0,1)]for dy in(-1,0,1)];complete=all(a is not None for row in grid for a in row)
      context_values=[[a[0]if a else None for a in row]for row in grid];context_masks=[[a[1]if a else None for a in row]for row in grid]
      status='nodata'if any(nodata)else('mask-invalid'if any(m==0 for m in masks)else'valid-native-bands')
      actual={'coverage_status':status,'band_values':value,'band_masks':masks,'nodata_matches':nodata,'band_order':['red','green','blue','nir'],'reflectance_scale':0.0001,'reflectance_offset':0,'native_row':r,'native_col':c,'neighbourhood_complete':complete,'neighbourhood_values':context_values,'neighbourhood_masks':context_masks,'centre_array':array,'source_object_identity':obj,'source_year':2020,'temporal_scope':'annual median composite, not dated scene','source_url':t['url']}
      original_row=original[p['point_index']]
      f.write(json.dumps({**original_row,'rgbnir_composite_observation':actual},separators=(',',':'))+'\n');tilecounts[status]+=1;counts[status]+=1
      if not complete:incomplete.append(p['point_index'])
    f.flush();os.fsync(f.fileno())
   dest=folder/'point-observations.jsonl';os.replace(tp,dest)
   product={'tile':tile,'keys':len(t['points']),'observations':pin(dest),'arrays':[q['array']for q in arrays.values()],'source_header':pin(folder/'source.json'),'incomplete_context_indices':incomplete}
   atomic_json(done,{'plan_sha256':PLAN_SHA,'reader_sha256':reader['sha256'],'point_indices':[p['point_index']for p in t['points']],'counts':dict(tilecounts),'product':product});products.append(product)
   print(json.dumps({'event':'tile-complete','tile':tile,'counts':dict(tilecounts),'completed_keys':sum(counts.values())}),flush=True)
  except Exception as e:
   failure={'tile':tile,'error_type':type(e).__name__,'error':str(e),'utc':utc()};atomic_json(folder/'failure.json',failure);failures.append(failure);print(json.dumps({'event':'failed',**failure}),flush=True);break
report={'kind':'unresolved-original-keys-annual2020-rgbnir-observations-not-answers','started_utc':began,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-started,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'reader':reader,'plan':pin(PLAN),'exact_residual_keys':pin(KEYS),'requested_keys':9332,'observed_keys':sum(counts.values()),'complete':not failures and sum(counts.values())==9332,'coverage_status_counts':dict(counts),'new_native_blocks_read':read_blocks,'reused_native_blocks':reused_blocks,'sources':sources,'tile_products':products,'failures':failures,'license':'CC BY4.0','attribution':'ESA WorldCover project2020 / Contains modified Copernicus Sentinel data(2020) processed by ESA WorldCover consortium','runtime':{'python':sys.version,'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__,'numpy':np.__version__},'limits':['Annualcomposite has no single date or tide.','Masks/nodata are literal source validity, not confidence or ocean.','Nativecontext incomplete where neighboring block is outside existing297blockplan; no added values.','No classification, physical answer, territory/owner change, adoption or repair credit.','No whole remoteTIFFhash claim.']}
print(json.dumps({'event':'complete'if report['complete']else'incomplete','report':atomic_json(ROOT/'rgbnir-source-observations.json',report),'observed_keys':report['observed_keys'],'counts':dict(counts),'failures':failures}),flush=True)
sys.exit(0 if report['complete']else 1)
