"""Extract hash-pinned OSM land archive feature geometries for component selection.

The ZIP is the source of truth. A separately materialized shapefile may be used
only after its members are compared byte-for-byte by SHA-256 with the ZIP.
Feature IDs are zero-based OGR FIDs and are stable only for the pinned archive.
"""
import hashlib,json,math,zipfile
from pathlib import Path
from osgeo import ogr,osr
ogr.UseExceptions()
MEMBERS=('land_polygons.shp','land_polygons.shx','land_polygons.dbf','land_polygons.prj')
def need(ok,message):
 if not ok:raise ValueError(message)
def digest(stream):
 h=hashlib.sha256()
 while True:
  b=stream.read(1<<20)
  if not b:break
  h.update(b)
 return h.hexdigest()
def path_hash(path):
 with path.open('rb') as f:return digest(f)
def canonical(g):return json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def extract(archive,shapefile,source_sha256,features):
 need(isinstance(source_sha256,str) and len(source_sha256)==64 and all(c in '0123456789abcdef' for c in source_sha256),'invalid source pin')
 archive=Path(archive).resolve(strict=True);shapefile=Path(shapefile).resolve(strict=True)
 need(archive.is_file() and shapefile.is_file() and shapefile.name=='land_polygons.shp','invalid source paths')
 need(isinstance(features,list) and 0<len(features)<=1000,'invalid feature list')
 ids=[]
 for f in features:
  need(isinstance(f,dict) and set(f)=={'source_feature_id','geometry_sha256'} and isinstance(f['source_feature_id'],str) and f['source_feature_id'].isascii() and f['source_feature_id'].isdigit() and (f['source_feature_id']=='0' or not f['source_feature_id'].startswith('0')) and isinstance(f['geometry_sha256'],str) and len(f['geometry_sha256'])==64 and all(c in '0123456789abcdef' for c in f['geometry_sha256']),'invalid feature pin')
  ids.append(int(f['source_feature_id']))
 need(len(set(ids))==len(ids),'duplicate feature IDs')
 need(path_hash(archive)==source_sha256,'archive hash mismatch')
 extracted={}
 with zipfile.ZipFile(archive) as z:
  for name in MEMBERS:
   match=[i for i in z.infolist() if i.filename=='land-polygons-split-4326/'+name]
   need(len(match)==1 and not match[0].is_dir() and 0<match[0].file_size<=3*(1<<30),'missing or oversized source member')
   path=shapefile.with_name(name);need(path.is_file() and path.stat().st_size==match[0].file_size,'source member size mismatch')
   with z.open(match[0]) as f:expected=digest(f)
   need(path_hash(path)==expected,'source member hash mismatch');extracted[name]=expected
 ds=ogr.Open(str(shapefile),0);need(ds is not None and ds.GetLayerCount()==1,'invalid shapefile');layer=ds.GetLayer(0);srs=layer.GetSpatialRef();expected=osr.SpatialReference();expected.ImportFromEPSG(4326);expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);need(srs is not None and bool(srs.IsSame(expected)),'source CRS is not WGS84')
 result=[]
 for fid,f in zip(ids,features):
  row=layer.GetFeature(fid);need(row is not None,'source feature missing');geometry=row.GetGeometryRef();need(geometry is not None and not geometry.IsEmpty() and bool(geometry.IsValid()) and geometry.GetGeometryName() in ('POLYGON','MULTIPOLYGON'),'invalid source polygon')
  g=json.loads(geometry.ExportToJson());need(set(g)=={'type','coordinates'} and g['type'] in ('Polygon','MultiPolygon'),'invalid source geometry')
  polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];vertices=0
  for poly in polygons:
   need(isinstance(poly,list) and bool(poly),'empty polygon')
   for ring in poly:
    need(isinstance(ring,list) and len(ring)>=4 and ring[0]==ring[-1],'invalid ring');prev=None
    for p in ring:
     need(isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p),'invalid vertex');lon,lat=p;need(-180<=lon<=180 and -90<=lat<=90 and (prev is None or abs(lon-prev)<=180),'invalid vertex or dateline wrap');prev=lon;vertices+=1;need(vertices<=1000000,'too many vertices')
  gh=hashlib.sha256(canonical(g)).hexdigest();need(gh==f['geometry_sha256'],'source geometry hash mismatch');result.append((g,{'source_sha256':source_sha256,'source_feature_id':str(fid),'geometry_sha256':gh,'vertices':vertices,'coordinate_reference':'EPSG:4326; longitude, latitude','limitation':'FID and geometry are specific to the exact archive bytes; source contact alone does not establish island membership.'}))
 ds=None
 for name,h in extracted.items():need(path_hash(shapefile.with_name(name))==h,'source member changed during extraction')
 need(path_hash(archive)==source_sha256,'archive changed during extraction')
 return result
