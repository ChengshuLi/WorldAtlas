"""Refine oversized rural source units on published ecological boundaries.

No equal-area slicing: administrative edges and actual source ecoregion edges
form the new territories. Coastline mismatches remain explicit named source
remainders rather than being assigned to an arbitrarily distant polygon.
"""
import collections,hashlib,json,math,pathlib,re
from shapely import make_valid,union_all,STRtree
from shapely.geometry import shape,mapping,Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'data';C=ROOT/'.cache/semantic'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(x) for x in getattr(g,'geoms',[])])
def parts(g):return list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
def area(g):return sum(p.area*12364*math.cos(math.radians(p.representative_point().y)) for p in parts(g) if p.geom_type=='Polygon')
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']]
if all(f['properties']['metadata'].get('remote_version')==1 for f in fs):print('Remote audit already installed');raise SystemExit
units={u['id']:u for u in read(D/'hierarchy.json')};report=read(D/'semantic-report.json');new=[];outliers=[]
sets={}
for name,file,name_field,id_field in [('global','resolve-ecoregions.geojson','ECO_NAME','ECO_ID'),('australia','ibra-subregions.geojson','SUB_NAME_7','SUB_CODE_7')]:
 source=read(C/file)['features']
 if name=='global':
  source=source+[{'type':'Feature','properties':{'ECO_NAME':f['properties']['name'],'ECO_ID':'lake:'+str(f['properties'].get('ne_id',i)),'water':True},'geometry':f['geometry']} for i,f in enumerate(read(C/'lakes.geojson')['features']) if f['properties'].get('name')]
 geoms=[poly(make_valid(shape(f['geometry']))).simplify(.001,preserve_topology=True) for f in source];sets[name]=(source,geoms,STRtree(geoms),name_field,id_field)
for n,f in enumerate(fs):
 p=f['properties'];g=shape(f['geometry']);a=area(g);anonymous=bool(re.search(r'unincorporated|unorganized|unorganised',p['name'],re.I))
 if (a<50000 and not anonymous) or p['reference_owner']=='Canada' or p['metadata']['source_name']=='AAFC physical geography adaptation':new.append(f);continue
 source,sg,st,nf,kf=sets['australia' if p['reference_owner']=='Australia' else 'global'];remaining=g;pieces=[]
 for j in sorted(map(int,st.query(g,predicate='intersects'))):
  part=poly(make_valid(remaining.intersection(sg[j],grid_size=1e-8)))
  if part.is_empty or area(part)<5:continue
  pieces.append([j,part]);remaining=poly(make_valid(remaining.difference(part,grid_size=1e-8)))
 # Publish geographic subdivisions only where a source actually distinguishes them.
 significant=[(j,q) for j,q in pieces if area(q)>=500]
 if len(significant)<2 and not anonymous:
  p['metadata']['scale_review']={'area_km2':round(a),'decision':'Retain named rural district; source does not establish multiple substantial geographic subdivisions','geographic_context':[source[j]['properties'][nf] for j,q in significant]};new.append(f);outliers.append({'id':f['id'],**p['metadata']['scale_review']});continue
 # Coastline slivers abutting a source subdivision inherit that edge. The error
 # is recorded, and large/distant gaps are a build failure, not guessed coverage.
 adjustments=[]
 if remaining.area/max(g.area,1e-12)>=.05:
  assert not anonymous,('Anonymous physical source coverage',f['id'])
  p['metadata']['scale_review']={'area_km2':round(a),'decision':'Retain named source district: physical source does not provide sufficient verified coverage','uncovered_fraction':round(remaining.area/g.area,5)}
  new.append(f);outliers.append({'id':f['id'],**p['metadata']['scale_review']});continue
 anchors={j:q for j,q in pieces}
 for distance in [.001,.005,.01,.025,.05,.1]:
  if remaining.is_empty:break
  for item in pieces:
   extra=poly(make_valid(remaining.intersection(anchors[item[0]].buffer(distance))))
   if extra.is_empty:continue
   item[1]=poly(make_valid(union_all([item[1],extra])));remaining=poly(make_valid(remaining.difference(extra)))
   adjustments.append({'area_km2':round(area(extra),4),'distance_band_degrees':distance})
 if not remaining.is_empty and remaining.area>=1e-8:
  assert not anonymous,('Anonymous territory requires complete source coverage',f['id'])
  p['metadata']['scale_review']={'area_km2':round(a),'decision':'Retain named source territory: finer physical classification has offshore coverage gaps beyond the bounded coastline adjustment','uncovered_km2':round(area(remaining),2)}
  new.append(f);outliers.append({'id':f['id'],**p['metadata']['scale_review']});continue
 for j,q in pieces:
  props=source[j]['properties'];name=props[nf];token=str(props[kf]);identifier='atlas:physical:'+hashlib.sha256((f['id']+':'+token).encode()).hexdigest()[:20]
  # A source portion needs its containing district for an unambiguous name.
  label=name if anonymous else p['name']+' · '+name
  meta={**p['metadata'],'source_name':'Named physical region adaptation','source_id':('ibra:' if p['reference_owner']=='Australia' else 'resolve:')+token,'source_url':'https://www.arcgis.com/home/item.html?id='+('0e78c21ba12543019b92e10272f980fe' if p['reference_owner']=='Australia' else '37ea320eebb647c6838c23f72abae5ef'),'license':'CC BY 4.0; underlying administrative source license retained','location_basis':'Published geographic subdivision within a source rural district','administrative_level':'Named physical region portion','source_member_ids':[f['id']],'search_aliases':list(set(p['metadata'].get('search_aliases',[])+[p['name']])),'representative_point':list(q.representative_point().coords)[0],'remote_version':1,'reference_version':3,'coastline_adjustments':adjustments}
  if props.get('water'):meta.update(source_id='natural-earth:'+token,source_url='https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-lakes/',license='Natural Earth public domain; underlying administrative source license retained',location_basis='Named inland-water portion within a source district')
  new.append({'type':'Feature','id':identifier,'properties':{'id':identifier,'name':label,'parent_id':p['parent_id'],'reference_owner':p['reference_owner'],'metadata':meta},'geometry':mapping(q)})
  report['changes'].append({'id':identifier,'name':label,'basis':meta['location_basis'],'source':meta['source_url'],'replaces':[f['id']],'area_km2':round(area(q),2)})
 report['retired'].append({'id':f['id'],'name':p['name']});outliers.append({'id':f['id'],'area_km2':round(a),'decision':'Subdivided on published geographic boundaries','subdivisions':len(pieces)})
 if n%100==0:print('Remote refinement',n,len(fs),flush=True)
for f in new:f['properties']['metadata']['remote_version']=1
parts_out=[]
for i in range(0,len(new),1500):
 path=f'geography/part-{i//1500}.json';parts_out.append(path);write(D/path,{'type':'FeatureCollection','features':new[i:i+1500]})
write(D/'world-index.json',{'parts':parts_out});report['locations']=len(new);report['remote_scale_reviews']=outliers;report['retired_locations']=len(report['retired']);report['sources']['physical']={key:read(C/file) for key,file in [('australia','ibra-item.json'),('global','resolve-item.json')]};write(D/'semantic-report.json',report)
print('Remote refinement:',len(fs),'→',len(new),'locations;',len(outliers),'outliers reviewed')
