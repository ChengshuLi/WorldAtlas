import json,gzip,glob,os,hashlib
from shapely.geometry import shape
from shapely.strtree import STRtree
base='coordination/engineering/physical-gap-components-1005-20261005-local19'
idx=json.load(open(base+'/custody-v1/index.json'))
byorig={a['original']['path']:a['payload'] for a in idx['aliases']}
def read_alias(path):
 b=open(byorig[path],'rb').read()
 return json.loads(gzip.decompress(b))
selected=[]
for p in sorted(glob.glob('coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/investigations-*.json.gz')):
 d=json.load(gzip.open(p,'rb'))
 for r in d:
  if r.get('partition','').startswith('interior') and sorted(r.get('positive_length_neighbor_ids',[]))==['atlas:physical:a2735e777a9d1037bd3a','atlas:physical:cbea9d242259efda3120']:
   selected.append(r['component'])
selected=set(selected)
assert len(selected)==134
roster_bytes=(json.dumps(sorted(selected),separators=(',',':'))+'\n').encode()
assert hashlib.sha256(roster_bytes).hexdigest()=='b7af8568f5972dd935d8cc85d16c19f349938ea6810b6b2b391c92d4a1b9df94'
comps=[]
for n in range(11):
 d=read_alias(f'{base}/components-v2/components-{n:03}.json.gz')
 comps += [f for f in d['features'] if f['id'] in selected]
assert len(selected)==134 and len(comps)==134
eco=json.load(open('research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson'))
assert len(eco['features'])==5
eco_by_id={f['properties'].get('ECO_ID'):f for f in eco['features']}
control_component=shape(comps[0]['geometry'])
assert control_component.intersects(shape(eco_by_id[811]['geometry']))
assert not control_component.intersects(shape(eco_by_id[320]['geometry']))
# longitude/latitude geometries; exact topological tests at source coordinate precision
geos=[shape(f['geometry']) for f in eco['features']]; tree=STRtree(geos)
results=[]
for f in comps:
 g=shape(f['geometry']); matches=[]
 for i in tree.query(g):
  e=eco['features'][int(i)]; eg=geos[int(i)]
  if g.intersects(eg):
   ix=g.intersection(eg)
   matches.append({'eco_id':e['properties'].get('ECO_ID'),'eco_name':e['properties'].get('ECO_NAME'),'objectid':e.get('id'),'intersection_type':ix.geom_type,'intersection_area_degrees2':ix.area,'intersection_length_degrees':ix.length,'component_area_degrees2':g.area})
 results.append({'component':f['id'],'bbox':list(g.bounds),'matches':matches})
print('matches count',sum(bool(x['matches']) for x in results),'positive-area',sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'exact contacts only',sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results))
print('ecoregions',sorted({(m['eco_id'],m['eco_name']) for x in results for m in x['matches']}))
print('sample no match',next((x for x in results if not x['matches']),None))
out={'version':'abudhabi-physical-seam-source-overlay-v1','source_note':'Exact source-coordinate topological intersections only; EPSG:4326; no buffering or snapping. Ecoregion source is not verified as intended historical source because service ObjectID conflicts with original Atlas IDs.','component_count':len(comps),'subject_roster_sha256':hashlib.sha256(roster_bytes).hexdigest(),'ecoregion_feature_count':len(eco['features']),'positive_area_overlap_count':sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'zero_area_intersection_count':sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'no_intersection_count':sum(not x['matches'] for x in results),'controls':{'positive_selected_component_intersects_ECO_ID_811':True,'negative_selected_component_does_not_intersect_ECO_ID_320':True},'components':results}
p='research/geography/gap-source-abudhabi-physical-seam-20261006/overlay-v1.json';open(p,'w').write(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n')
