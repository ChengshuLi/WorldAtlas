"""Refine source-verified local roles, preserving coherent cities and display land."""
import collections,gzip,hashlib,json,pathlib,shutil
from shapely import STRtree,union_all,make_valid
from shapely.geometry import shape,mapping,Polygon
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';S=D/'global-sources'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(x) for x in getattr(g,'geoms',[])])
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];u={x['id']:x for x in read(D/'hierarchy.json')};semantic=read(D/'semantic-report.json');changes=[];reports=read(D/'global-refinement-report.json')['profiles'] if (D/'global-refinement-report.json').exists() else []
for iso,level,oldlevel,role in [('IND','ADM3','ADM2','Sub-district / taluka / tehsil'),('PAK','ADM3','ADM2','Tehsil'),('BTN','ADM2','ADM1','Gewog')]:
 if any(f['id'].startswith(f'atlas:local:{iso}:') for f in fs):continue
 reports=[r for r in reports if r['iso']!=iso]
 all_old=[f for f in fs if f['id'].startswith(f'gb:{iso}:{oldlevel}:')]
 metadata=read(S/f'{iso}-{level}-metadata.json');source=json.loads(gzip.decompress((S/f'{iso}-{level}.geojson.gz').read_bytes()))['features'];source_geoms=[poly(make_valid(shape(x['geometry']))) for x in source];source_union=union_all(source_geoms);old=[];retained=[]
 for f in all_old:
  g=shape(f['geometry']);missing=g.difference(source_union);pieces=list(missing.geoms) if missing.geom_type=='MultiPolygon' else [missing]
  # Retain a complete named district whenever local source coverage cannot support a bounded seam correction.
  if missing.area/g.area>.005 or any(not q.is_empty and q.representative_point().distance(source_union)>.02 for q in pieces):retained.append({'id':f['id'],'name':f['properties']['name'],'missing_share':missing.area/g.area,'reason':'Finer source omits land beyond bounded source-edge adjustments; retain the named original territory'})
  else:old.append(f)
 if not old:reports.append({'iso':iso,'status':'blocked-incomplete-coverage','retained':retained});continue
 # Excluding an incomplete neighboring district must not create a tiny sliver carrying an entire local-unit name.
 for iteration in range(8):
  current_mask=union_all([shape(f['geometry']) for f in old]);eligible=[g for g in source_geoms if g.area and g.intersection(current_mask).area/g.area>=.9];available=union_all(eligible);kept=[]
  for f in old:
   g=shape(f['geometry']);missing=g.difference(available);pieces=list(missing.geoms) if missing.geom_type=='MultiPolygon' else [missing]
   if missing.area/g.area>.005 or any(not q.is_empty and q.representative_point().distance(available)>.02 for q in pieces):retained.append({'id':f['id'],'name':f['properties']['name'],'missing_share':missing.area/g.area,'reason':'Retain original district to avoid naming a clipped sliver as a complete local territory'})
   else:kept.append(f)
  if len(kept)==len(old):break
  old=kept
  if not old:break
 if not old:reports.append({'iso':iso,'status':'blocked-incomplete-coverage','retained':retained});continue
 oldg=[shape(f['geometry']) for f in old];mask=union_all(oldg);ot=STRtree(oldg);geoms=[];items=[]
 for x in sorted(source,key=lambda f:f['properties']['shapeID']):
  g=poly(poly(make_valid(shape(x['geometry']))).intersection(mask))
  if not g.is_empty and g.area/max(shape(x['geometry']).area,1e-20)>=.9 and x['properties'].get('shapeName','').strip():items.append(x);geoms.append(g)
 tree=STRtree(geoms);repair=0
 for i,g in enumerate(geoms):
  for j in tree.query(g,predicate='intersects'):
   if int(j)>=i:continue
   repair+=g.intersection(geoms[int(j)]).area;g=poly(make_valid(g.difference(geoms[int(j)])))
  geoms[i]=g
 missing=poly(mask.difference(union_all(geoms)));gap_ratio=missing.area/mask.area;report={'iso':iso,'role':role,'source_locations':len(source),'old_locations':len(old),'gap_ratio':gap_ratio,'seam_repairs_degrees2':repair,'source_url':metadata['download_url'],'license':metadata['boundaryLicense'],'retained':retained}
 if gap_ratio>.005:report['status']='blocked-incomplete-coverage';reports.append(report);print(report,flush=True);continue
 gaps=list(missing.geoms) if missing.geom_type=='MultiPolygon' else [missing];tree=STRtree(geoms);adjust=[];blocked=False
 for g in gaps:
  if g.is_empty:continue
  candidates=list(map(int,tree.query(g.buffer(.00001))));j=max(candidates,key=lambda j:g.boundary.intersection(geoms[j].buffer(.000001)).length) if candidates else int(tree.nearest(g))
  distance=g.distance(geoms[j])
  if distance>.02:blocked=True;break
  geoms[j]=poly(make_valid(union_all([geoms[j],g])));adjust.append({'id':items[j]['properties']['shapeID'],'area_degrees2':g.area,'distance_degrees':distance})
 if blocked:report['status']='blocked-source-gap';reports.append(report);print(report,flush=True);continue
 new=[];matches=[]
 for x,g in zip(items,geoms):
  if g.is_empty:continue
  overlap,j=max((g.intersection(oldg[int(j)]).area,int(j)) for j in ot.query(g));parent=old[j];oldprovince=u[parent['properties']['parent_id']];region=u[u[oldprovince['parent_id']]['parent_id']]
  # ADM1 districts in Bhutan retain the existing broad area; ADM2 districts become provinces under states.
  if oldlevel=='ADM1':area=u[oldprovince['parent_id']]
  else:
   aid='atlas:area:'+iso+':'+hashlib.sha256(oldprovince['id'].encode()).hexdigest()[:12];area={'id':aid,'name':oldprovince['name'],'level':'area','parent_id':region['id'],'metadata':{'source':'geoBoundaries named ADM1 reference','source_url':metadata['boundarySourceURL'],'basis':'Published state/province geographic area above district clusters','kind':'geographic','framework_status':'source-backed','review_reasons':[]}};u[aid]=area
  pid='atlas:province:'+iso+':'+hashlib.sha256(parent['id'].encode()).hexdigest()[:12];u[pid]={'id':pid,'name':parent['properties']['name'],'level':'province','parent_id':area['id'],'metadata':{'source':'geoBoundaries named district reference','source_url':metadata['boundarySourceURL'],'basis':'Named district group of whole sourced local territories; follows member footprints','kind':'geographic','framework_status':'source-backed','review_reasons':[]}}
  p=x['properties'];id=f'atlas:local:{iso}:'+p['shapeID'];name=p['shapeName'].rstrip('*').strip();ratio=overlap/g.area
  meta={'source_name':'Atlas source aggregation','source_id':f'gb:{iso}:{level}','source_url':metadata['download_url'],'license':metadata['boundaryLicense'],'reference_year':metadata['boundaryYearRepresented'],'administrative_level':role,'location_basis':f'Published named {role} local territory; coherent source city unions preserved','representative_point':list(g.representative_point().coords)[0],'reference_version':3,'hierarchy_version':4,'semantic_version':3,'source_footprint_share':round(g.area/max(shape(x['geometry']).area,1e-20),6),'framework_overlap':round(ratio,6),'parent_match':f'Greatest overlap with named district {parent["properties"]["name"]}: {ratio:.2%}','source_geography_sha256':metadata['sha256'],'source_member_ids':[p['shapeID']],'source_name_with_footnote':p['shapeName']}
  new.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':pid,'reference_owner':parent['properties']['reference_owner'],'metadata':meta},'geometry':mapping(g)});matches.append({'id':id,'source_id':p['shapeID'],'province_id':pid,'reference_parent_id':parent['id'],'overlap':round(ratio,6)})
 assert mask.symmetric_difference(union_all([shape(f['geometry']) for f in new])).area<1e-7
 retired={f['id'] for f in old};fs=[f for f in fs if f['id'] not in retired]+new
 semantic['retired'] += [{'id':f['id'],'name':f['properties']['name'],'reason':f'Replaced by sourced {role} local territories; original geometry and historical records retained'} for f in old]
 semantic['changes'] += [{'id':f['id'],'name':f['properties']['name'],'basis':f'Published named {role}','source_url':metadata['download_url']} for f in new]
 report.update(status='adopted',new_locations=len(new),matches=matches,coastline_adjustments=adjust,coverage_difference_degrees2=0);reports.append(report);print({k:v for k,v in report.items() if k not in ['matches','coastline_adjustments','retained']},flush=True)
 # Protected city unions remain locations and receive a named metropolitan group under their state area.
 for f in fs:
  if f['properties']['reference_owner']!=old[0]['properties']['reference_owner'] or not f['id'].startswith('atlas:city:'):continue
  oldp=u[f['properties']['parent_id']];aid=next((a['id'] for a in u.values() if a['level']=='area' and a['name']==oldp['name'] and a['id'].startswith('atlas:area:'+iso)),None)
  if aid:
   pid='atlas:province:'+f['id'];u[pid]={'id':pid,'name':f['properties']['name']+' metropolitan territory','level':'province','parent_id':aid,'metadata':{'source':f['properties']['metadata']['source_url'],'basis':'Coherent published metropolitan union; coextensive location/province exception','source_url':f['properties']['metadata']['source_url'],'kind':'geographic','framework_status':'source-backed','review_reasons':[]}};f['properties']['parent_id']=pid
# Only active ancestors count.
used=set()
for f in fs:
 p=f['properties']['parent_id']
 while p:used.add(p);p=u[p]['parent_id']
u={id:x for id,x in u.items() if id in used};children=collections.Counter(f['properties']['parent_id'] for f in fs);children.update(x['parent_id'] for x in u.values() if x['parent_id'])
for x in u.values():x['metadata']['child_count']=children[x['id']]
parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]});parts.append(p)
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(u.values()));semantic['locations']=len(fs);write(D/'semantic-report.json',semantic);write(D/'global-refinement-report.json',{'version':1,'profiles':reports,'locations':len(fs)})
h=read(D/'hierarchy-report.json');h['locations']=len(fs);h['counts']=dict(collections.Counter(x['level'] for x in u.values()));h['global_refinement_report']='global-refinement-report.json';write(D/'hierarchy-report.json',h)
