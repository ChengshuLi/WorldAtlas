"""Two genuinely unsaved adjacent-frame contexts; same retained native ds.read/read_masks window kernel."""
import datetime,hashlib,json,resource,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,'configured-existing-runtime:worldcover-reader')
import numpy as np
import rasterio
from rasterio.windows import Window
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;N=ROOT/'worldcover-native-001';started=time.monotonic();facts=[];failures=[]
for tile,br,bc in [('N15E096',35,20),('N09E096',0,20)]:
 folder=OUT/tile;folder.mkdir(exist_ok=True);prior=json.loads((N/'tiles'/tile/'source.json').read_text());url=prior['url'];p=folder/('new-block-%02d-%02d.npz'%(br,bc));q=p.with_suffix('.json')
 assert not(N/'tiles'/tile/p.name).exists(),'Refuse reread of completed nativeblock'
 if q.exists():
  saved=json.loads(q.read_text());raw=p.read_bytes();assert len(raw)==saved['array']['bytes']and hashlib.sha256(raw).hexdigest()==saved['array']['sha256'];facts.append(saved);continue
 try:
  with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60)as response:http={'status':response.status,'headers':dict(response.headers.items())}
  identity={k.lower():v for k,v in http['headers'].items()if k.lower()in('etag','content-length','last-modified','accept-ranges')};assert http['status']==200 and identity==prior['source_identity']
  with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_CONNECTTIMEOUT='30',GDAL_HTTP_TIMEOUT='120'):
   with rasterio.open(url)as ds:
    assert ds.crs.to_epsg()==4326 and ds.width==ds.height==36000 and ds.count==1 and ds.dtypes==('uint8',)and list(ds.transform)==prior['transform']and ds.nodata==prior['nodata']and ds.block_shapes==[(1024,1024)]
    r0,c0=br*1024,bc*1024;h,w=min(1024,ds.height-r0),min(1024,ds.width-c0);window=Window(c0,r0,w,h);codes=ds.read(1,window=window);masks=ds.read_masks(1,window=window);assert codes.shape==masks.shape==(h,w)
    with p.open('wb')as f:np.savez_compressed(f,codes=codes,masks=masks)
  raw=p.read_bytes();saved={'kind':'new-bounded-adjacent-frame-native-block','tile':tile,'source_url':url,'source_identity':identity,'http':http,'transform':prior['transform'],'crs':prior['crs'],'native_block':[br,bc],'window':{'row_off':r0,'col_off':c0,'height':h,'width':w},'array':{'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'acquired_at':datetime.datetime.now(datetime.timezone.utc).isoformat()};q.write_text(json.dumps(saved,indent=2)+'\n');facts.append(saved);print(json.dumps({'event':'new-block-complete','tile':tile,'native_block':[br,bc],'bytes':len(raw)}),flush=True)
 except Exception as e:
  failures.append({'tile':tile,'native_block':[br,bc],'exception_type':type(e).__name__,'message':str(e)});print(json.dumps({'event':'failure',**failures[-1]}),flush=True)
result={'kind':'actual-two-new-native-context-block-read','new_requested_blocks':2,'completed_blocks':len(facts),'blocks':facts,'failures':failures,'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'completed_original_blocks_reread':0,'source_year':2020,'reader_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(OUT/'actual-two-block-read.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'event':'complete','new_native_blocks':len(facts),'failures':len(failures),'elapsed_seconds':result['elapsed_seconds']}),flush=True)
if failures:sys.exit(1)
