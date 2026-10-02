import os,json,gzip,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from shapely import STRtree,to_wkb,from_wkb
from shapely.geometry import Polygon,shape,box,Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from pyproj import Geod
P=Path(__file__).parent;repo=Path(os.environ.get('WORLDATLAS_REPO','/workspace/WorldAtlas'));geod=Geod(ellps='WGS84');(P/'modern-candidates').mkdir(exist_ok=True)
def area(g):
 if g.is_empty:return 0.
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient(g,1))[0])/1e6
 if g.geom_type in ('MultiPolygon','GeometryCollection'):return sum(area(x) for x in g.geoms)
 return 0.
loc=[];lg=[]
for part in json.load(open(repo/'data/world-index.json'))['parts']:
 data=json.load(open(repo/'data'/part))
 for f in data['features']:
  loc.append(f['properties']);lg.append(shape(f['geometry']))
tree=STRtree(lg);modern=json.load(open(P/'modern-coastline-index.json'));report=[]
REG={'RoWide':'framework:region:anatolia:eec70f5bbea8','Comino':'framework:region:italy:0397946dc154','Channel':'framework:region:france:d7a707436e62','FugloyWide':'framework:region:northern-europe:fdff5f0d4d80','CocosSouth':'framework:region:malesia:041eea1ae1b4','CocosNorth':'framework:region:malesia:041eea1ae1b4','DiegoGarcia':'atlas:macro-foundation:region:south-asian-oceanic-islands','SalomonWide':'atlas:macro-foundation:region:south-asian-oceanic-islands','Minamitorishima':None}
entries=json.load(open(P/'result.json'))['entries'];by={e['name']:e for e in entries};REG['RoWide']=by['Kastellorizo']['region_id'];REG['Comino']=by['Malta']['region_id'];REG['Channel']=by['Channel Islands']['region_id'];REG['FugloyWide']=by['Faroe Islands']['region_id']
parent={g['id']:g['parent_id'] for g in json.load(open(repo/'data/hierarchy.json'))};parent.update({p['id']:p['parent_id'] for p in loc})
def ancestors(i):
 a=[]
 while i in parent and parent[i]:i=parent[i];a.append(i)
 return a
for q in modern:
 if q.get('http_status')!=200:report.append(dict(query=q['name'],status='source-unavailable',error=q.get('error')));continue
 rings=[(r,Polygon(r['coordinates'])) for r in q['closed_rings'] if r['valid'] and r['area_km2']>0];water=[g for r,g in rings if r['land_on_left_signed_area_km2']<0]
 # Closed natural-water ways also subtract known inland water. Relational-water completeness is explicitly retained below.
 xml=ET.fromstring(gzip.decompress((P/q['original_path']).read_bytes()));nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in xml.findall('node')};waterways=[];incomplete=[]
 for w in xml.findall('way'):
  tags={t.attrib['k']:t.attrib['v'] for t in w.findall('tag')};refs=[t.attrib['ref'] for t in w.findall('nd')]
  if tags.get('natural')!='water' and tags.get('landuse')!='reservoir':continue
  if len(refs)<4 or refs[0]!=refs[-1] or any(n not in nodes for n in refs):incomplete.append(w.attrib['id']);continue
  wg=Polygon([nodes[n] for n in refs])
  if wg.is_valid:waterways.append((w.attrib['id'],wg));water.append(wg)
 unresolved_relations=[];resolved_relations=[]
 allways={w.attrib['id']:w for w in xml.findall('way')}
 def assemble(role,rel):
  pending=[]
  for m in rel.findall('member'):
   if m.attrib.get('type')!='way' or m.attrib.get('role','outer')!=role:continue
   w=allways.get(m.attrib['ref'])
   if w is None:return None
   refs=[n.attrib['ref'] for n in w.findall('nd')]
   if any(n not in nodes for n in refs):return None
   pending.append(refs)
  closed=[]
  while pending:
   chain=pending.pop()
   while chain[0]!=chain[-1]:
    found=False
    for ii,zz in enumerate(pending):
     if chain[-1]==zz[0]:chain.extend(zz[1:])
     elif chain[-1]==zz[-1]:chain.extend(zz[-2::-1])
     elif chain[0]==zz[-1]:chain=zz[:-1]+chain
     elif chain[0]==zz[0]:chain=zz[:0:-1]+chain
     else:continue
     pending.pop(ii);found=True;break
    if not found:return None
   poly=Polygon([nodes[n] for n in chain])
   if not poly.is_valid:return None
   closed.append(poly)
  return closed
 for rel in xml.findall('relation'):
  tags={t.attrib['k']:t.attrib['v'] for t in rel.findall('tag')}
  if tags.get('natural')!='water' and tags.get('water') not in ('lake','pond','reservoir','lagoon'):continue
  outs=assemble('outer',rel);ins=assemble('inner',rel)
  if outs is None or ins is None or not outs:unresolved_relations.append(rel.attrib['id']);continue
  relation_water=unary_union(outs).difference(unary_union(ins));water.append(relation_water)
  resolved_relations.append({'relation_id':rel.attrib['id'],'version':rel.attrib.get('version'),'timestamp':rel.attrib.get('timestamp'),'outer_count':len(outs),'inner_count':len(ins),'water_area_km2':area(relation_water)})
 for r,g in rings:
  if r['land_on_left_signed_area_km2']<=0:continue
  holes=[h for h in water if g.covers(h)];dry=g.difference(unary_union(holes));ak=area(dry)
  if ak<.1:continue
  overlaps=[];neighbors=[]
  for i in tree.query(dry.buffer(.001)):
   i=int(i);inter=area(dry.intersection(lg[i]));dist=dry.distance(lg[i])
   if inter>0:overlaps.append(dict(location_id=loc[i]['id'],name=loc[i]['name'],intersection_km2=inter,share=min(1,inter/ak),current_ancestors=ancestors(loc[i]['id'])))
   if dist<=.001:neighbors.append(dict(location_id=loc[i]['id'],name=loc[i]['name'],distance_degrees=dist))
  share=min(1,sum(o['intersection_km2'] for o in overlaps)/ak);complete=box(*q['requested_bbox']).covers(dry);pr=REG[q['name']];missing=share<.01 and not neighbors and complete;status='source-candidate-missing-land; identity-and-migration-review-required' if missing else 'represented-or-nearby-existing-land; geometry-restoration-review-required'
  if not complete:status='query-boundary-incomplete; cannot-stage-whole-land'
  if pr is None:status='new-named-route-decision-required; no-parent-assignment-authorized'
  if incomplete or unresolved_relations:status+='; inland-water-completeness-open'
  raw=to_wkb(dry);fn=hashlib.sha256(raw).hexdigest()[:24]+'.wkb.gz';(P/'modern-candidates'/fn).write_bytes(gzip.compress(raw,mtime=0));report.append(dict(query=q['name'],source_url=q['url'],source_xml_sha256=q['original_sha256'],source_way_versions=r['way_versions'],source_node_count=r['node_count'],query_whole_polygon=True,polygon_inside_query_bbox=complete,area_km2=ak,bounds=list(dry.bounds),subtracted_closed_water_rings=len(holes),incomplete_water_way_ids=incomplete,unresolved_water_relation_ids=unresolved_relations,resolved_water_relations=resolved_relations,all_current_location_overlaps=overlaps,current_location_union_overlap_share=share,all_current_locations_within_0_001_degree=neighbors,whole_location_predecessor_candidates=[o['location_id'] for o in overlaps],approved_region_id=pr,verified_geographic_association=pr is not None,geometry_path='modern-candidates/'+fn,geometry_wkb_sha256=hashlib.sha256(raw).hexdigest(),status=status,installation_authorized=False,migration_requirements='Retain any predecessor location footprints/history and source assets. Source-territory evidence must justify append versus new stable location identity and adjacent-tier parents; absencealone doesnotjustify an arbitrary nearestlocation attachment. Any acceptedgeometry change requires releasecrosswalk/newfixedgridrepresentation and revalidationofderivedownership/environmentproducts/claims.' ))
result=dict(version=1,modern_sources=len(modern),source_license='OpenStreetMap contributors, ODbL1.0; sourcearea/nativewater-hole evidence separately licensed.',geometry_validation='Directed coastway endpoint chains only, allreferencednodes present; completeclosedpositive landonleft rings minus containednegativewater and closedtaggedwaterway masks; boundsinsidequery required. Opennearby coastways/waterrelations retainedas gaps.',candidate_domain='>=0.1km² drycoastal polygons inside completequery windows; smaller OSMinferredislets remain originalsourceonly. Larger-than200m GSHHG offsets are not proof ofmissinggeometry.',current_location_footprints=49589,query_results=modern,candidates=report,summary={'compared_dryland_polygons':len(report),'missing_candidates':sum('source-candidate-missing-land' in r.get('status','') for r in report),'unresolved_named_route_candidates':sum('new-named-route' in r.get('status','') for r in report),'inland_water_open_candidates':sum('inland-water-completeness-open' in r.get('status','') for r in report)},installed_changes=0)
(P/'modern-candidate-review.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print(result['summary']);print([(r['query'],round(r.get('area_km2',0),3),round(r.get('current_location_union_overlap_share',0),4),r.get('status')) for r in report])
