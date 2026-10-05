#!/usr/bin/env python3
"""Screen the 2010 Greek island-source polygons against ELSTAT's 2021 census units."""
import csv,gzip,hashlib,io,json,pathlib,zipfile
import shapefile
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
ROOT=pathlib.Path(__file__).parent;SRC=ROOT/'sources'
raw=json.load(gzip.open(SRC/'geoBoundaries-GRC-ADM3.geojson.gz','rt'))['features']
issue=json.load(open(ROOT/'issue-71-api.json'))
body=issue['body']; scope=json.loads(body[body.index('{"area_scopes"'):body.index('\n```',body.index('{"area_scopes"'))])
ids=[x for x in scope['member_location_ids'] if x.startswith('gb:GRC:ADM3:')]
base=[]
for p in pathlib.Path('data/geography').glob('part-*.json'):
 for f in json.load(open(p))['features']:
  if f['properties']['id'] in ids: base.append(f)
base_by={f['properties']['id'].rsplit(':',1)[-1]:f for f in base}
# ELSTAT pages and archives are official but the files are not retained: terms for these census-use shapes were not clear in their metadata.
files=[('/tmp/DHMOI_2021.zip','https://www.statistics.gr/digital-cartographical-data','municipality'),('/tmp/PERIF_ENOT_2021.zip','https://www.statistics.gr/digital-cartographical-data','regional_unit')]
# EPSG:2100 Greek Grid to WGS84; compare after transforming both layers back to EPSG:2100.
to_gr=Transformer.from_crs('EPSG:4326','EPSG:2100',always_xy=True).transform
records=[]
for zip_path,url,kind in files:
 z=zipfile.ZipFile(zip_path); shpname=next(n for n in z.namelist() if n.lower().endswith('.shp')); stem=shpname[:-4]
 r=shapefile.Reader(shp=io.BytesIO(z.read(shpname)),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')))
 fields=[x[0] for x in r.fields[1:]]
 candidates=[]
 for rec,sh in zip(r.records(),r.shapes()):
  props=dict(zip(fields,rec)); candidates.append((props,shape(sh.__geo_interface__)))
 for ident,f in base_by.items():
  props=f['properties']; gf=next(x for x in raw if str(x.get('properties',{}).get('shapeID'))==ident)
  geom=transform(to_gr,shape(gf['geometry']))
  # Candidate intersection percentages show crosswalk/split patterns only.
  hits=[]
  for attrs,cg in candidates:
   intersection=geom.intersection(cg).area
   if intersection>geom.area*0.01:
    name=attrs.get('NAME_ENG') or attrs.get('PERIF_EN') or attrs.get('NAME_GR') or ''
    hits.append((name,attrs.get('CODE',''),intersection/geom.area,intersection/cg.area if cg.area else 0))
  for name,candidate_code,source_share,candidate_share in sorted(hits,key=lambda x:-x[2]):
   records.append({'legacy_id':props['id'],'legacy_name':props['name'],'legacy_reference_year':props.get('metadata',{}).get('reference_year'),'official_2021_level':kind,'candidate_2021_code':candidate_code,'candidate_2021_name':name,'legacy_area_fraction_intersecting_candidate':round(source_share,6),'candidate_area_fraction_intersecting_legacy':round(candidate_share,6),'method':'positive planar area intersection in EPSG:2100; >1% of legacy shape area','interpretation':'census/statistical source comparison only; ELSTAT expressly says it is not proof of administrative boundary'})
with open(ROOT/'greece-2021-crosswalk-screen.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator="\n");w.writeheader();w.writerows(records)
manifest=[]
for p,url,kind in files:
 b=pathlib.Path(p).read_bytes();manifest.append({'dataset':kind,'page':url,'retrieval_date':'2026-10-04','local_source_file_not_retained':'Terms for these census-use shapefiles were not clear; restore from official page and compare the pinned SHA-256 before relying on this screen.','sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
json.dump({'sources':manifest,'transform':'EPSG:4326 baseline/source GeoJSON -> EPSG:2100; ELSTAT supplied .prj is EPSG:2100','threshold':'Record every 2021 unit covering >1% of legacy subject planar area. Shares use area in each geometry as denominator.','warning':'ELSTAT states its 2021 Kallikratis/census boundaries are for statistical use and do not certify legal administrative limits. No intersection score chooses a parent or transfers an identity.','output_rows':len(records)},open(ROOT/'greece-2021-crosswalk-provenance.json','w'),indent=2)
print('crosswalk rows',len(records))
