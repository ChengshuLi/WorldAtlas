"""Named ISTAT local labour systems as geographic locations, staged for review.
Whole functional territories are retained; upper atlas groups follow their members.
No population/rank/history is inferred from the commuting geography.
"""
import collections,hashlib,json,pathlib,math
from shapely import STRtree,make_valid,union_all
from shapely.geometry import shape,mapping,Polygon
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache/framework'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(x) for x in getattr(g,'geoms',[])])
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']]
old=[f for f in fs if f['properties']['metadata'].get('source_id')=='gb:ITA:ADM3'];assert len(old)>90
oldg=[shape(f['geometry']) for f in old];oldtree=STRtree(oldg);mask=union_all(oldg)
source=read(C/'italy-sll2018.geojson')['features'];source.sort(key=lambda f:f['properties']['sll_2011'])
assert len(source)==610
geoms=[];clean=[];overlaps=[]
for f in source:
 g=poly(make_valid(shape(f['geometry']))).intersection(mask)
 if not g.is_empty:geoms.append(g);clean.append(f)
tree=STRtree(geoms)
for i,g in enumerate(geoms):
 for j in tree.query(g,predicate='intersects'):
  j=int(j)
  if j>=i:continue
  overlap=g.intersection(geoms[j]).area
  if overlap>0:
   overlaps.append({'id':clean[i]['properties']['sll_2011_t'],'degrees2':overlap})
   g=poly(make_valid(g.difference(geoms[j])))
 geoms[i]=g
claimed=union_all(geoms)
print('Italy: source systems clipped and shared edges reconciled',flush=True)
remaining=poly(mask.difference(claimed));pieces=list(remaining.geoms) if remaining.geom_type=='MultiPolygon' else [remaining]
tree=STRtree(geoms);adjustments=[]
for g in pieces:
 if g.is_empty:continue
 candidates=list(map(int,tree.query(g.buffer(.00001))))
 if candidates:i=max(candidates,key=lambda j:g.boundary.intersection(geoms[j].buffer(.000001)).length)
 else:i=int(tree.nearest(g))
 distance=g.distance(geoms[i]);assert distance<.02,(g.area,distance,g.bounds)
 adjustments.append({'system':clean[i]['properties']['sll_2011_t'],'degrees2':g.area,'distance_degrees':distance})
 geoms[i]=poly(make_valid(union_all([geoms[i],g])))
units={u['id']:u for u in read(D/'hierarchy.json')};result=[];matches=[]
for f,g in zip(clean,geoms):
 scores=[(g.intersection(oldg[int(j)]).area,int(j)) for j in oldtree.query(g)]
 overlap,j=max(scores);parent=old[j];p=f['properties'];name=p['den_sl2011'].title();code=p['sll_2011_t'];id=f'atlas:location:ITA:SLL:{code}'
 area=units[parent['properties']['parent_id']]['name'];ratio=overlap/g.area
 matches.append({'id':id,'province':parent['properties']['name'],'overlap':round(ratio,6),'source_multi_province':p['multi_prov'],'source_multi_region':p['multi_reg']})
 meta={'source_name':'Atlas source aggregation','source_id':f'ISTAT:SLL2011-2018:{code}','source_url':read(C/'sll-item.json')['url'],'license':'CC BY 3.0 (Regione Umbria D.G.R. 1389/2014); ISTAT local labour systems','reference_year':'2011 geography, 2018 update','administrative_level':'Local labour system (functional geography)','location_basis':'Published named commuting territory; multiple contiguous municipalities. Atlas parent grouping follows whole systems, not exact administrative province borders.','representative_point':list(g.representative_point().coords)[0],'search_aliases':[name]+(['Rome'] if name=='Roma' else []),'reference_version':3,'hierarchy_version':4,'semantic_version':2,'framework_province':parent['properties']['name'],'framework_province_key':parent['id'],'framework_area':area,'framework_overlap':round(ratio,6),'framework_source':'ISTAT SLL / Regione Umbria SIAT; geoBoundaries Italian province crosswalk','framework_status':'sourced-geographic-group','source_geography_sha256':hashlib.sha256((C/'italy-sll2018.geojson').read_bytes()).hexdigest()}
 result.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':parent['properties']['parent_id'],'reference_owner':parent['properties']['reference_owner'],'metadata':meta},'geometry':mapping(g)})
assert mask.symmetric_difference(union_all(geoms)).area<1e-7
report={'source_locations':len(source),'new_locations':len(result),'retired_ids':[f['id'] for f in old],'matches':matches,'coastline_adjustments':adjustments,'source_overlap_repairs':overlaps,'coverage_difference_degrees2':mask.symmetric_difference(union_all(geoms)).area}
write(C/'italy-locations.json',result);write(C/'italy-refinement-report.json',report)
print(json.dumps({'new':len(result),'old':len(old),'adjustment_area_degrees2':sum(x['degrees2'] for x in adjustments),'overlap_area_degrees2':sum(x['degrees2'] for x in overlaps),'low_parent_overlap':sum(x['overlap']<.8 for x in matches),'coverage_difference':report['coverage_difference_degrees2']}),flush=True)
