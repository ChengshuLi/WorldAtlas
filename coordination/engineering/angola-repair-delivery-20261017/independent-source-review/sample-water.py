import pathlib,json,subprocess,hashlib,collections,time,resource
from osgeo import gdal
gdal.UseExceptions();gdal.SetCacheMax(64*1024*1024)
D=pathlib.Path(__file__).resolve().parent;W=(D/'workspace.txt').read_text();H='ffb3b4595367baa8dab5f16a0880410b2cb21532';P='research/geography/gap-source-namibia-angola-20261006/sources/jrc-gsw-2024/';start=time.monotonic()
def raw(p):return subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',H+':'+p])
m=json.loads(raw(P+'manifest.json'));rows=json.loads((D/'water-probe-centres.json').read_text());out=[]
for tile in m['tiles']:
 dest=D/(tile['layer']+'-'+tile['tile']+'.tif');whole=hashlib.sha256()
 with dest.open('xb') as f:
  for part in tile['parts']:
   b=raw(P+part['path']);assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];whole.update(b);f.write(b)
 assert dest.stat().st_size==tile['original_bytes'] and whole.hexdigest()==tile['original_sha256'];ds=gdal.Open(str(dest));band=ds.GetRasterBand(1);gt=ds.GetGeoTransform();counts=collections.Counter();per=collections.defaultdict(collections.Counter)
 for r in rows:
  x=int((r['lon']-gt[0])/gt[1]);y=int((r['lat']-gt[3])/gt[5]);
  if not 0<=x<ds.RasterXSize or not 0<=y<ds.RasterYSize:continue
  v=int(band.ReadRaster(x,y,1,1)[0]);r[tile['layer']]=v;counts[v]+=1;per[r['component']][v]+=1
 out.append(dict(layer=tile['layer'],tile=tile['tile'],sha256=tile['original_sha256'],counts=dict(counts),per_component={k:dict(v) for k,v in per.items()}));ds=None
summary={layer:dict(collections.Counter(r[layer] for r in rows)) for layer in ['occurrence','seasonality']};result=dict(head=H,centres=rows,tiles=out,summary=summary,elapsed_seconds=time.monotonic()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,method='Containing retained JRC v1.5 pixel at the exact original native centre, no interpolation/resampling; independent observation, not bank, legal-line or ownership adjudication.');(D/'water-probe-results.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['summary','elapsed_seconds','maxrss_kib']}))
