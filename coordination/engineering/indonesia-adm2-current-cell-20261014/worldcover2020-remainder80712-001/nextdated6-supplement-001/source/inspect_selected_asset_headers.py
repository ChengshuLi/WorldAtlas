"""Metadata/header-only cohort use of existing Rasterio; no read/read_masks/sample call."""
from pathlib import Path
import json,hashlib,datetime,urllib.request,time
import rasterio
ROOT=Path(__file__).resolve().parent
PLAN=ROOT/'metadata-coverage-plan.json'
source=PLAN.read_bytes();plan=json.loads(source)
OUT=ROOT/'asset-headers-001';OUT.mkdir(exist_ok=False)
start=time.monotonic();products=[]
def write(path,obj):
 path.write_text(json.dumps(obj,indent=2)+'\n')
 return {'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_CONNECTTIMEOUT='30',GDAL_HTTP_TIMEOUT='120'):
 for selected in plan['selected_items']:
  item=selected['item']
  cached=ROOT/'previous-compatible-headers-not-present'/(item['id']+'.json')
  if cached.exists():
   old=json.loads(cached.read_text())
   assert all(old['assets'][key]['status']=='actual-header-matches-declared-grid' and old['assets'][key]['url']==item['assets'][key]['href'] for key in ('red','green','blue','nir','scl'))
   products.append({'file':str(cached.relative_to(ROOT)),'bytes':cached.stat().st_size,'sha256':hashlib.sha256(cached.read_bytes()).hexdigest(),'reused_without_remote_reopen':True})
   print(json.dumps({'item':item['id'],'status':'reuse-complete-actual-header-no-HTTP'}),flush=True)
   continue
  record={'item_id':item['id'],'owner':selected['owner'],'acquisition':item['properties']['datetime'],'properties':item['properties'],'geometry':item['geometry'],'bbox':item['bbox'],'license_links':[x for x in item['links'] if x['rel']=='license'],'assets':{},'value_or_mask_reads':0}
  for key in ('red','green','blue','nir','scl'):
   asset=item['assets'][key];url=asset['href'];observed={'url':url,'declared_asset':asset,'inspected_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
   try:
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60) as h:observed['HEAD']={'status':h.status,'headers':dict(h.headers)}
    with rasterio.open(url) as ds:
     observed['actual_header']={'driver':ds.driver,'crs':str(ds.crs),'epsg':ds.crs.to_epsg(),'width':ds.width,'height':ds.height,'transform':list(ds.transform),'count':ds.count,'dtypes':list(ds.dtypes),'nodata':ds.nodata,'block_shapes':[list(x) for x in ds.block_shapes],'scales':list(ds.scales),'offsets':list(ds.offsets),'tags':ds.tags(),'band1_tags':ds.tags(1),'mask_flag_enums':[[x.name for x in y] for y in ds.mask_flag_enums]}
     expected=20 if key=='scl' else 10
     assert ds.crs.to_epsg()==item['properties']['proj:epsg'] and ds.count==1
     assert [ds.height,ds.width]==asset['proj:shape'] and list(ds.transform)[:6]==asset['proj:transform']
     assert ds.res==(expected,expected) and ds.nodata==asset['raster:bands'][0]['nodata']
    observed['status']='actual-header-matches-declared-grid'
   except Exception as e:observed['status']='header-inspection-failed';observed['error_type']=type(e).__name__;observed['error']=str(e)
   record['assets'][key]=observed
   print(json.dumps({'item':item['id'],'asset':key,'status':observed['status']}),flush=True)
  products.append(write(OUT/(item['id']+'.json'),record))
write(OUT/'execution-summary.json',{'kind':'actual-source-header-only-no-value-window-execution','input_plan_sha256':hashlib.sha256(source).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'products':products,'item_count':len(products),'value_or_mask_reads':0,'rasterio_version':rasterio.__version__,'gdal_version':rasterio.__gdal_version__,'elapsed_seconds':time.monotonic()-start})
