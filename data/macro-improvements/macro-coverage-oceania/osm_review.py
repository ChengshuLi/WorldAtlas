import json,gzip,pathlib,xml.etree.ElementTree as E,os
from shapely.geometry import shape,Polygon,mapping,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import make_valid
from pyproj import Geod
root=pathlib.Path(__file__).resolve().parent;repo=pathlib.Path(os.environ.get('WORLDATLAS_REPO','/workspace/WorldAtlas')); sources=json.load(open(root/'osm-sources.json'));routes={r['name']:r for r in json.load(open(root/'routes.json'))};geod=Geod(ellps='WGS84');
for extra in json.load(open(root/'supplement-gazetteers.json')): routes[extra['name']]={'region_id':routes['Northwestern Hawaiian Islands']['region_id']}
hier={g['id']:g for g in json.load(open(repo/'data/hierarchy.json'))};geos=[];props=[]
def area(p):
 if p.is_empty:return 0
 if p.geom_type in ['Polygon','MultiPolygon']:return abs(geod.geometry_area_perimeter(p)[0])/1e6
 return sum(area(g)for g in getattr(p,'geoms',[]))
for part in json.load(open(repo/'data/world-index.json'))['parts']:
 for f in json.load(open(repo/'data'/part))['features']:
  p=shape(f['geometry']);b=p.bounds
  if not any(b[0]<s['bbox'][2] and b[2]>s['bbox'][0] and b[1]<s['bbox'][3] and b[3]>s['bbox'][1]for s in sources if 'bbox'in s):continue
  q=f['properties'];parent=q['parent_id']
  while parent in hier and hier[parent]['level']!='region':parent=hier[parent]['parent_id']
  geos.append(make_valid(p)if not p.is_valid else p);props.append({'id':q['id'],'name':q['name'],'region_id':parent})
tree=STRtree(geos);rows=[];features=[];allfeatures=[]
for s in sources:
 name=s['name']
 if 'error'in s:rows.append(s);continue
 x=E.fromstring(gzip.decompress((root/s['path']).read_bytes()));nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat')))for n in x.findall('node')};ways=[w for w in x.findall('way')if any(t.get('k')=='natural' and t.get('v')=='coastline'for t in w.findall('tag'))];segments=[];missing=[]
 for w in ways:
  refs=[n.get('ref')for n in w.findall('nd')]
  if not all(n in nodes for n in refs):missing.append(w.get('id'));continue
  segments.append({'refs':refs,'ways':[w.get('id')],'source_versions':[{k:w.get(k)for k in ['id','version','timestamp']}]})
 rings=[];unclosed=[]
 while segments:
  z=segments.pop();refs=z['refs'];used=z['ways'];versions=z['source_versions']
  while refs[0]!=refs[-1]:
   matches=[i for i,q in enumerate(segments)if q['refs'][0]==refs[-1]]
   if len(matches)!=1:break
   q=segments.pop(matches[0]);refs+=q['refs'][1:];used+=q['ways'];versions+=q['source_versions']
  if refs[0]!=refs[-1]:unclosed.append({'ways':used,'first_node':refs[0],'last_node':refs[-1]});continue
  p=Polygon([nodes[n]for n in refs]);signed=geod.geometry_area_perimeter(p)[0]/1e6
  rings.append({'geometry':p,'signed_area_km2':signed,'ways':used,'versions':versions,'valid':p.is_valid})
 outer=[r for r in rings if r['signed_area_km2']>0];holes=[r for r in rings if r['signed_area_km2']<0];components=[]
 for ring in outer:
  p=ring['geometry'];p=p.difference(unary_union([r['geometry']for r in holes if p.contains(r['geometry'].representative_point())]));idx=list(tree.query(p));region=routes.get(name,{}).get('region_id');good=[i for i in idx if props[i]['region_id']==region];exist=unary_union([geos[i]for i in idx]);same=unary_union([geos[i]for i in good]);a=area(p);fraction=area(p.intersection(exist))/a if a else 0;near=list(tree.query(p.buffer(.001)));actualnear=[i for i in near if p.distance(geos[i])<=.001];inside_domain=box(*s['bbox']).covers(p);missingall=fraction<.01 and not actualnear and inside_domain
  c={'osm_way_ids':ring['ways'],'osm_source_versions':ring['versions'],'source_area_km2':a,'valid_source_ring':ring['valid'],'geometry_type':p.geom_type,'whole_source_polygon_inside_query_domain':inside_domain,'bbox':list(p.bounds),'all_location_overlap_fraction':fraction,'intended_region_overlap_fraction':area(p.intersection(same))/a if a else 0,'intersecting_locations':[props[i]for i in idx if p.intersects(geos[i])],'nearby_locations_0_001_degrees':[props[i]for i in actualnear],'status':'corroborated-current-source-land-absent-from-existing-footprints'if missingall else 'current-source-overlaps-or-adjoins-existing-land; do-not-duplicate'};components.append(c)
  allfeatures.append({'type':'Feature','geometry':mapping(p),'properties':{'named_route':name,'region_id':region,'source_id':'osm-api-2026-10-02','source_sha256':s['sha256'],'source_way_ids':ring['ways'],'source_versions':ring['versions'],'source_area_km2':a,'source_geometry_valid':p.is_valid,'status':c['status'],'existing_overlap_locations':c['intersecting_locations'],'license':'ODbL1.0; OpenStreetMapcontributors'}})
  if missingall:features.append({'type':'Feature','geometry':mapping(p),'properties':{'named_route':name,'region_id':region,'source_id':'osm-api-2026-10-02','source_hash':s['sha256'],'source_way_ids':ring['ways'],'source_versions':ring['versions'],'source_area_km2':a,'existing_source_identity':'No current intersecting or within~111m location; exact release3 comparison','migration_status':'staged-source-footprint; requiresidentityandcanonicalgridreview','license':'ODbL1.0; copyrightOpenStreetMapcontributors','geometry_valid':p.is_valid}})
 total=sum(c['source_area_km2']for c in components);coverage=sum(c['source_area_km2']*c['all_location_overlap_fraction']for c in components);r={'name':name,'source':s,'coastline_way_count':len(ways),'closed_land_rings':len(outer),'closed_water_rings':len(holes),'unclosed_chains':unclosed,'missing_node_ways':missing,'complete_ring_reconstruction':not missing and not unclosed,'current_source_components':components,'source_land_area_km2':total,'any_existing_location_covered_fraction':coverage/total if total else None,'absent_current_land_components':sum(c['status'].startswith('corroborated')for c in components),'status':'confirmed-whole-named-island-source-omission'if components and all(c['status'].startswith('corroborated')for c in components)else'partial-islet-coverage-or-source-shoreline-difference'};rows.append(r);print(name,len(outer),len(holes),len(unclosed),round(total,4),round(coverage/total,4)if total else None,r['absent_current_land_components'],flush=True)
report={'scope':'39 specifically suspect, Hawaiian chain, or old-source-offset named Pacific island domains','method':{'whole_polygon_area_comparison':True,'coordinate_search_is_not_completeness_proof':True,'coastline_topology':'DirectedOSMcoastline ways assembled through matchingendpoint IDs; CCWrings define land; CWringscontainedwithinland are water and subtracted; incomplete chains retained as unresolved','area':'WGS84 ellipsoidal','candidate_rule':'<1% landintersection with everylocation and no currentfootprintwithin0.001degrees(~111m maximum); precisioncorridoralone cannot approve migration','source':'OSMpublicAPI mapextract retrieved2026-10-02; perwayversion/timestampsretained','license':'ODbL1.0; database derivative/licensedextractsretainattributionandsource','modern_complete_coverage_certified':False},'routes':rows,'candidate_component_count':len(features),'candidate_path':'osm-missing-land-candidates.geojson.gz'}
(root/'osm-report.json').write_text(json.dumps(report,separators=(',',':')));(root/'osm-missing-land-candidates.geojson.gz').write_bytes(gzip.compress(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')).encode(),mtime=0))

(root/'osm-all-land-footprints.geojson.gz').write_bytes(gzip.compress(json.dumps({'type':'FeatureCollection','features':allfeatures},separators=(',',':')).encode(),mtime=0))
