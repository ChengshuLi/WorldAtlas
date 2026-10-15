"""WorldCover cohort adaptation: exact unread original keys, saved native windows.

Same Vietnam/53134 Rasterio ds.index/read/read_masks source kernels.
New remote reads are exact missing native blocks without halos; completed
original blocks/halos supply their actual pixels locally. No classification.
"""
from pathlib import Path
import collections,datetime,hashlib,io,json,os,resource,sys,time,urllib.error,urllib.request
sys.path.insert(0, 'configured-existing-runtime:worldcover-reader')
import numpy as np
import rasterio
from rasterio.windows import Window
ROOT=Path(__file__).resolve().parent
PLAN=ROOT/'point-plan.jsonl';CACHE=ROOT/'cache-inputs.json'
PLAN_SHA='fb3db9d02a72c066f8908826eb143adefa1b566277f9ac51ed11e630089d5f52'
CACHE_SHA='e6662e31e4ac40c32034858d75713ee3d2704648c150d9a08db0bfd39d561396'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic_json(path,value):
 b=(json.dumps(value,separators=(',',':'))+'\n').encode();tmp=path.with_suffix(path.suffix+'.partial')
 with tmp.open('wb')as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 return {'path':str(path),'bytes':len(b),'sha256':sha(b)}
def filepin(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':sha(b)}
started=time.monotonic();began=utc();code_sha=sha(Path(__file__).read_bytes())
b=PLAN.read_bytes();assert sha(b)==PLAN_SHA;points=[json.loads(x) for x in b.splitlines()];del b
b=CACHE.read_bytes();assert sha(b)==CACHE_SHA;cache=json.loads(b);del b
assert len(points)==16222
by_tile=collections.defaultdict(list)
for p in points:by_tile[p['tile']].append(p)
oldblocks={(r['tile'],*r['native_block']):r for r in cache['arrays']}

def old_supplier(tile,r,c):
 br,bc=r//1024,c//1024
 rs=[br]+([br-1]if r%1024==0 else[])+([br+1]if r%1024==1023 else[])
 cs=[bc]+([bc-1]if c%1024==0 else[])+([bc+1]if c%1024==1023 else[])
 for rr in rs:
  for cc in cs:
   q=oldblocks.get((tile,rr,cc))
   if q:
    w=q['window']
    if w['row_off']<=r<w['row_off']+w['height'] and w['col_off']<=c<w['col_off']+w['width']:return q
 return None

sources=[];tile_products=[];failures=[];counts=collections.Counter();values=collections.Counter();newly_read_blocks=0;reused_new_blocks=0;old_arrays_used=set()
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_CONNECTTIMEOUT='30',GDAL_HTTP_TIMEOUT='120'):
 for tile,members in sorted(by_tile.items()):
  folder=ROOT/'tiles'/tile;folder.mkdir(parents=True,exist_ok=True)
  url=f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/ESA_WorldCover_10m_2020_v100_{tile}_Map.tif'
  needed=sorted({tuple(b)for p in members for b in p['missing_context_native_blocks']})
  print(json.dumps({'event':'tile-start','tile':tile,'keys':len(members),'missing_native_blocks':len(needed)}),flush=True)
  loaded={};newblocks={};used_arrays=set();prior=cache['sources'].get(tile)
  try:
   checkpoint=folder/'tile-complete.json'
   if checkpoint.exists():
    done=json.loads(checkpoint.read_text())
    assert done['plan_sha256']==PLAN_SHA and done['reader_sha256']==code_sha
    assert done['point_indices']==[p['point_index']for p in members]
    assert filepin(Path(done['product']['observations']['path']))==done['product']['observations']
    source=json.loads((folder/'source.json').read_text())
    if prior:assert source['source_identity']==prior['source_identity']
    sources.append({**source,'reused_completed_tile':True});tile_products.append(done['product'])
    counts.update(done['coverage_status_counts']);values.update(done['literal_class_counts'])
    old_arrays_used.update(done['prior_saved_arrays_used']);reused_new_blocks+=done['product'].get('new_native_blocks',0)
    print(json.dumps({'event':'tile-reused-complete','tile':tile,'keys':len(members),'completed_keys':sum(counts.values())}),flush=True)
    continue
   if needed:
    try:
     with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60)as response:http={'status':response.status,'headers':dict(response.headers.items())}
    except urllib.error.HTTPError as e:
     if e.code!=404 or prior:raise
     source={'tile':tile,'url':url,'status':'missing-tile','http':{'status':404,'headers':dict(e.headers.items())},'keys':len(members)}
     atomic_json(folder/'source.json',source);sources.append(source)
     absent={'coverage_status':'missing-tile','class_code':None,'valid_mask':None,'nodata_match':None,'neighbourhood_complete':False,'neighbourhood_codes':None,'neighbourhood_masks':None,'centre_array':None,'source_object_identity':None}
     missing=[{**p,'planned_neighbourhood_complete':p['neighbourhood_complete'],**absent,'source_class_observation':absent}for p in members]
     tmp=folder/'point-observations.jsonl.partial'
     with tmp.open('w')as f:
      for p in missing:f.write(json.dumps(p,separators=(',',':'))+'\n')
      f.flush();os.fsync(f.fileno())
     final=folder/'point-observations.jsonl';os.replace(tmp,final)
     product={'tile':tile,'keys':len(members),'observations':filepin(final),'new_native_blocks':0}
     atomic_json(checkpoint,{'plan_sha256':PLAN_SHA,'reader_sha256':code_sha,'point_indices':[p['point_index']for p in members],'product':product,'coverage_status_counts':{'missing-tile':len(members)},'literal_class_counts':{},'prior_saved_arrays_used':[]})
     tile_products.append(product);counts['missing-tile']+=len(members);continue
    identity={k.lower():v for k,v in http['headers'].items()if k.lower()in('etag','content-length','last-modified','accept-ranges')}
    assert http['status']==200 and identity.get('accept-ranges','').lower()=='bytes'
    if prior:assert identity==prior['source_identity'],'Remote source object identity changed; refusing cached/new combination'
    with rasterio.open(url)as ds:
     assert ds.crs.to_epsg()==4326 and ds.width==ds.height==36000 and ds.count==1 and ds.dtypes==('uint8',)
     assert ds.transform.a==1/12000 and ds.transform.e==-1/12000 and ds.transform.b==ds.transform.d==0 and ds.block_shapes==[(1024,1024)]
     south=(1 if tile[0]=='N'else-1)*int(tile[1:3]);west=(1 if tile[3]=='E'else-1)*int(tile[4:])
     assert ds.transform.c==west and ds.transform.f==south+3
     if prior:assert list(ds.transform)==prior['transform'] and ds.nodata==prior['nodata']
     for p in members:assert ds.index(p['longitude'],p['latitude'])==(p['native_row'],p['native_col'])
     source={'tile':tile,'url':url,'status':'opened-native-cog','http':http,'source_identity':identity,'crs':str(ds.crs),'transform':list(ds.transform),'shape':[ds.height,ds.width],'block_shapes':ds.block_shapes,'nodata':ds.nodata,'tags':ds.tags(),'mask_flags':str(ds.mask_flag_enums),'keys':len(members),'full_source_hash_claimed':False}
     atomic_json(folder/'source.json',source);sources.append(source)
     for br,bc in needed:
      assert (tile,br,bc)not in oldblocks,'Plan attempted remote reread of completed cached native block'
      ap=folder/f'new-block-{br:02d}-{bc:02d}.npz';jp=ap.with_suffix('.json')
      if jp.exists():
       q=json.loads(jp.read_text());assert q['plan_sha256']==PLAN_SHA and q['reader_sha256']==code_sha and q['source_identity']==identity
       a=ap.read_bytes();assert len(a)==q['array']['bytes'] and sha(a)==q['array']['sha256'];reused_new_blocks+=1
      else:
       r0,c0=br*1024,bc*1024;h,w=min(1024,ds.height-r0),min(1024,ds.width-c0)
       window=Window(c0,r0,w,h);codes=ds.read(1,window=window);masks=ds.read_masks(1,window=window)
       assert codes.shape==masks.shape==(h,w)
       tmp=ap.with_suffix('.npz.partial')
       with tmp.open('wb')as f:np.savez_compressed(f,codes=codes,masks=masks);f.flush();os.fsync(f.fileno())
       os.replace(tmp,ap);q={'kind':'native-source-block-without-halo','plan_sha256':PLAN_SHA,'reader_sha256':code_sha,'tile':tile,'native_block':[br,bc],'source_identity':identity,'window':{'row_off':r0,'col_off':c0,'height':h,'width':w},'array':filepin(ap)}
       atomic_json(jp,q);newly_read_blocks+=1
      newblocks[(br,bc)]=q
      print(json.dumps({'event':'new-block-complete','tile':tile,'block':[br,bc],'new_block_count':newly_read_blocks,'reused_new_block_count':reused_new_blocks}),flush=True)
   else:
    assert prior
    source={**prior,'status':'saved-native-source-only-no-http','keys':len(members)};sources.append(source);atomic_json(folder/'source.json',source)

   def pixel(r,c):
    q=old_supplier(tile,r,c)
    if q:
     path=Path(q['array']['path']);old_arrays_used.add(str(path));used_arrays.add(str(path))
    else:
     q=newblocks[(r//1024,c//1024)];path=Path(q['array']['path']);used_arrays.add(str(path))
    key=str(path)
    if key not in loaded:
     a=path.read_bytes();assert len(a)==q['array']['bytes'] and sha(a)==q['array']['sha256']
     with np.load(io.BytesIO(a),allow_pickle=False)as z:loaded[key]=(z['codes'],z['masks'])
    w=q['window'];rr,cc=r-w['row_off'],c-w['col_off'];codes,masks=loaded[key]
    assert 0<=rr<w['height'] and 0<=cc<w['width']
    return int(codes[rr,cc]),int(masks[rr,cc]),str(path)
   tp=folder/'point-observations.jsonl.partial'
   tile_counts=collections.Counter();tile_values=collections.Counter()
   with tp.open('w')as f:
    for p in members:
     r,c=p['native_row'],p['native_col'];value,mask,centre_array=pixel(r,c);nodata=source['nodata']is not None and value==source['nodata'];complete=0<r<35999 and 0<c<35999
     assert complete==p['neighbourhood_complete']
     neighbours=neighbour_masks=None
     if complete:
      cells=[[pixel(r+dy,c+dx)for dx in(-1,0,1)]for dy in(-1,0,1)]
      neighbours=[[x[0]for x in row]for row in cells];neighbour_masks=[[x[1]for x in row]for row in cells]
     status='nodata'if nodata else('mask-invalid'if mask==0 else'valid-native-value')
     actual={'coverage_status':status,'class_code':value,'valid_mask':mask,'nodata_match':nodata,'neighbourhood_complete':complete,'neighbourhood_codes':neighbours,'neighbourhood_masks':neighbour_masks,'centre_array':centre_array,'source_object_identity':source['source_identity']}
     f.write(json.dumps({**p,**actual,'source_class_observation':actual},separators=(',',':'))+'\n');counts[status]+=1;values[str(value)]+=1;tile_counts[status]+=1;tile_values[str(value)]+=1
    f.flush();os.fsync(f.fileno())
   final=folder/'point-observations.jsonl';os.replace(tp,final)
   product={'tile':tile,'keys':len(members),'observations':filepin(final),'actual_array_sources':sorted(used_arrays),'new_native_blocks':len(newblocks)}
   used_old=sorted({str(Path(q['array']['path']))for q in oldblocks.values()}.intersection(used_arrays))
   atomic_json(checkpoint,{'plan_sha256':PLAN_SHA,'reader_sha256':code_sha,'point_indices':[p['point_index']for p in members],'product':product,'coverage_status_counts':dict(tile_counts),'literal_class_counts':dict(tile_values),'prior_saved_arrays_used':used_old})
   tile_products.append(product)
   print(json.dumps({'event':'tile-complete','tile':tile,'keys':len(members),'completed_keys':sum(counts.values())}),flush=True)
  except Exception as e:
   failure={'tile':tile,'error_type':type(e).__name__,'error':str(e),'time_utc':utc()};atomic_json(folder/'attempt-failure.json',failure);failures.append(failure);print(json.dumps({'event':'tile-failed',**failure}),flush=True);break
report={'kind':'original-physical-source-unread-worldcover-observations-not-answers','source_year':2020,'source_version':'v100','license':'CC BY4.0','attribution':'ESA WorldCover project2020 / Contains modified Copernicus Sentinel data(2020) processed by ESA WorldCover consortium','plan':filepin(PLAN),'cache_inputs':filepin(CACHE),'reader_sha256':code_sha,'started_utc':began,'ended_utc':utc(),'elapsed_seconds':time.monotonic()-started,'observed_process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'runtime':{'python':sys.version,'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__,'numpy':np.__version__},'complete':not failures and sum(counts.values())==16222,'requested_keys':16222,'observed_keys':sum(counts.values()),'coverage_status_counts':dict(counts),'literal_class_counts':dict(values),'sources':sources,'tile_products':tile_products,'newly_read_native_blocks':newly_read_blocks,'reused_new_native_blocks':reused_new_blocks,'prior_saved_arrays_used':sorted(old_arrays_used),'failures':failures,'new_answers':0,'repair_credit':0,'limits':['Source predictions/validity only, not physical answers or territorial/nativeauthority/adoption.','No whole remoteTIFFhash or InputQuality claim.','Missing tile/nodata/invalid/outside are not ocean.','Actual source-tile-edge contexts are reported perkey; no cross-tile fabrication.','Old point observations/point_indices were not reused for new keys; new values came from actual saved/new native arrays.']}
pin=atomic_json(ROOT/'source-observations.json',report);print(json.dumps({'event':'complete'if report['complete']else'incomplete','report':pin,'count':report['observed_keys'],'coverage_status_counts':dict(counts),'newly_read_native_blocks':newly_read_blocks,'reused_new_native_blocks':reused_new_blocks,'failures':failures}),flush=True)
sys.exit(0 if report['complete']else 1)
