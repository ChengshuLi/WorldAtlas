"""Extract one uniquely named airport point from a pinned GeoNames country ZIP."""
import hashlib,io,json,math,re,zipfile
from decimal import Decimal,InvalidOperation
HEX=re.compile(r'^[a-f0-9]{64}$');ID=re.compile(r'^[1-9][0-9]{0,15}$');DEC=re.compile(r'^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$')
def need(v,m):
 if not v:raise ValueError(m)
def extract(raw,expected_sha256,record_id,expected_name,country_code,expected_point_sha256):
 need(type(raw) is bytes and 0<len(raw)<=4*1024*1024,'source size')
 need(isinstance(expected_sha256,str) and HEX.fullmatch(expected_sha256) and hashlib.sha256(raw).hexdigest()==expected_sha256,'source hash')
 need(isinstance(record_id,str) and ID.fullmatch(record_id) and isinstance(expected_name,str) and 0<len(expected_name)<=256 and isinstance(country_code,str) and re.fullmatch(r'[A-Z]{2}',country_code) and isinstance(expected_point_sha256,str) and HEX.fullmatch(expected_point_sha256),'selection')
 try:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   hits=[x for x in z.infolist() if x.filename==country_code+'.txt'];need(len(hits)==1 and hits[0].file_size<=16*1024*1024 and not hits[0].is_dir(),'country archive')
   data=z.read(hits[0]).decode('utf-8','strict')
 except (zipfile.BadZipFile,UnicodeDecodeError,RuntimeError) as e:raise ValueError('invalid archive') from e
 records=[r.split('\t') for r in data.splitlines() if r.split('\t',1)[0]==record_id];need(len(records)==1 and len(records[0])==19,'record not unique or malformed');r=records[0]
 need(r[1]==expected_name and r[6:9]==['S','AIRP',country_code],'airport identity mismatch')
 def coord(s,lo,hi):
  need(len(s)<=32 and DEC.fullmatch(s),'invalid coordinate')
  try:d=Decimal(s)
  except InvalidOperation:raise ValueError('invalid coordinate') from None
  need(d.is_finite() and lo<=d<=hi,'coordinate range');return float(d)
 lat=coord(r[4],-90,90);lon=coord(r[5],-180,180);need(lon<180 and math.isfinite(lat) and math.isfinite(lon),'ambiguous coordinate')
 geom={'type':'Point','coordinates':[lon,lat]};h=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();need(h==expected_point_sha256,'geometry hash')
 return {'schema':'geonames-airport-point-extraction-v1','source_sha256':expected_sha256,'record_id':record_id,'name':r[1],'feature_class':'S','feature_code':'AIRP','country_code':country_code,'geometry':geom,'geometry_sha256':h,'source_crs':'OGC:CRS84','limitations':['An airport point locates a current physical component; it does not identify an island by itself or prove offshore-islet membership or coastline accuracy. Independent source evidence must establish island identity.']}
