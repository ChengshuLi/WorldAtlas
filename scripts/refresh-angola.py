"""Replace the old Angola source (including a point-like Catumbela artifact) with
its independently published 2018 humanitarian municipality layer."""
import json,pathlib,hashlib,collections
from shapely import make_valid,union_all,STRtree
from shapely.geometry import shape,mapping,Polygon
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache/semantic'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(p) for p in getattr(g,'geoms',[])])
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];old=[f for f in fs if f['properties']['reference_owner']=='Angola'];source=read(C/'angola-humanitarian.geojson')['features'];ids={'gb:AGO:ADM2:'+f['properties']['shapeID'] for f in source}
if {f['id'] for f in old}==ids:print('Reviewed Angola municipalities already installed');raise SystemExit
og=[shape(f['geometry']) for f in old];envelope=union_all(og);remaining=envelope;new=[];parts_geo=[];meta=read(C/'angola-humanitarian-metadata.json');units=read(D/'hierarchy.json')
for f in source:
 g=poly(make_valid(shape(f['geometry'])));q=poly(make_valid(g.intersection(remaining)));remaining=poly(make_valid(remaining.difference(q)));parts_geo.append(q)
assert remaining.area/envelope.area<.02,('Angola source coverage',remaining.area/envelope.area)
adjustments=[];anchors=parts_geo.copy()
for dist in [.001,.005,.01,.025,.05,.1]:
 for j,g in enumerate(anchors):
  if remaining.is_empty:break
  extra=poly(make_valid(remaining.intersection(g.buffer(dist))))
  if extra.is_empty:continue
  parts_geo[j]=poly(make_valid(union_all([parts_geo[j],extra])));remaining=poly(make_valid(remaining.difference(extra)));adjustments.append({'distance_band_degrees':dist,'area_degrees2':extra.area})
assert remaining.area<1e-8,('Angola distant gap',remaining.area)
for f,g in zip(source,parts_geo):
 assert not g.is_empty and g.is_valid
 votes=collections.defaultdict(float)
 for oldf,oldg in zip(old,og):
  if g.intersects(oldg):votes[oldf['properties']['parent_id']]+=g.intersection(oldg).area
 parent=max(votes,key=votes.get);id='gb:AGO:ADM2:'+f['properties']['shapeID'];name=f['properties']['shapeName'];m={'source_name':'geoBoundaries gbHumanitarian','source_id':'gb:AGO:ADM2','original_id':f['properties']['shapeID'],'source_url':meta['gjDownloadURL'],'license':meta['boundaryLicense'],'reference_year':meta['boundaryYearRepresented'],'administrative_level':'ADM2','source_role':'Municipality','location_basis':'Published municipality territory, 2018 humanitarian source','representative_point':list(g.representative_point().coords)[0],'reference_version':3,'hierarchy_version':3,'topology_version':1,'semantic_version':1,'remote_version':1,'coverage_version':1,'source_revision_reason':'Replace old point-like and obsolete municipal polygons; preserve reconciled country coverage'}
 new.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':parent,'reference_owner':'Angola','metadata':m},'geometry':mapping(g)})
fs=[f for f in fs if f['properties']['reference_owner']!='Angola']+new;parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})
write(D/'world-index.json',{'parts':parts});report=read(D/'semantic-report.json');report['retired'].extend({'id':f['id'],'name':f['properties']['name']} for f in old);report['locations']=len(fs);report['retired_locations']=len(report['retired']);report['angola_source_revision']={'old_locations':len(old),'new_locations':len(new),'source':meta,'adjustments':adjustments};write(D/'semantic-report.json',report)
sources=read(D/'administrative-sources.json');sources['gb:AGO:ADM2']={**meta,'collection':'gbHumanitarian','sha256':hashlib.sha256((C/'angola-humanitarian.geojson').read_bytes()).hexdigest()};write(D/'administrative-sources.json',sources)
print('Angola source replacement:',len(old),'→',len(new),'municipalities',flush=True)
