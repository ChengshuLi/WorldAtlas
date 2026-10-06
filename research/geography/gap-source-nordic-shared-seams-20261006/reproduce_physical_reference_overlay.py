import json,gzip,hashlib,subprocess,pathlib
from shapely.geometry import shape,mapping
from shapely import union_all
W=pathlib.Path(__file__).resolve().parents[3]; R=str(W); M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'; D=W/'research/geography/gap-source-nordic-shared-seams-20261006'
def get(p):return subprocess.check_output(['git','-C',R,'show',M+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
# source water inputs and custody as present at pinned detector vintage
landpath='data/macro-foundation/retained-inspections/retained-geographic-sources/namibia/natural-earth-land.geojson.gz.gz'; lr=get(landpath); l1=gzip.decompress(lr); lb=gzip.decompress(l1)
lakespath='coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz'; kr=get(lakespath); kb=gzip.decompress(kr)
land=json.loads(lb); lakes=json.loads(kb)
components=json.load(open(D/'scoped-original-components.geojson'))['features']
lu=union_all([shape(f['geometry']) for f in land['features']]); ku=union_all([shape(f['geometry']) for f in lakes['features']])
rows=[]
for f in components:
 g=shape(f['geometry']);li=g.intersection(lu);ld=g.difference(lu);ki=g.intersection(ku);kd=g.difference(ku)
 rows.append({'component_id':f['id'],'candidate_planar_area':g.area,'natural_earth_land_intersection_area':li.area,'natural_earth_land_difference_area':ld.area,'natural_earth_land_intersection_geometry':mapping(li),'natural_earth_land_difference_geometry':mapping(ld),'natural_earth_lakes_intersection_area':ki.area,'natural_earth_lakes_difference_area':kd.area,'natural_earth_lakes_intersection_geometry':mapping(ki),'natural_earth_lakes_difference_geometry':mapping(kd)})
obj={'source_bindings':{'land':{'commit':M,'path':landpath,'stored_outer_bytes':len(lr),'stored_outer_sha256':sha(lr),'intermediate_gzip_bytes':len(l1),'decompressed_bytes':len(lb),'decompressed_sha256':sha(lb),'feature_count':len(land['features'])},'lakes':{'commit':M,'path':lakespath,'stored_bytes':len(kr),'stored_sha256':sha(kr),'decompressed_bytes':len(kb),'decompressed_sha256':sha(kb),'feature_count':len(lakes['features'])}},'results':rows,'limits':['Natural Earth land and lakes are generalized physical reference layers; neither establishes authoritative hydrology, ice, coastline, boundary assignment, or source vintage truth.','Planar square degree intersections only; a nonzero land overlap does not prove the remaining candidate portion is land.']}
(D/'physical-reference-overlays.json').write_text(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'land':obj['source_bindings']['land'],'lakes':obj['source_bindings']['lakes'],'results':[{k:r[k] for k in ['component_id','candidate_planar_area','natural_earth_land_intersection_area','natural_earth_land_difference_area','natural_earth_lakes_intersection_area']}for r in rows]},indent=2))
