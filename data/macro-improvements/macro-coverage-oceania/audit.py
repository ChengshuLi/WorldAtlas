import json,gzip,zipfile,struct,hashlib,pathlib,re,math,os
import numpy as np
from shapely import from_wkb,make_valid
from shapely.geometry import Polygon,box,mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Geod
root=pathlib.Path(__file__).resolve().parent;repo=pathlib.Path(os.environ.get('WORLDATLAS_REPO','/workspace/WorldAtlas')); routes=json.load(open(root/'routes.json'));gaz={x['name']:x for x in json.load(open(root/'gazetteers.json'))}; geod=Geod(ellps='WGS84')
def coord(s):
 v=[float(x) for x in re.findall(r'[\d.]+',s)];a=sum(x/60**i for i,x in enumerate(v));return -a if 'S' in s or 'W' in s else a
special={'Hawaii':[-179.5,18,-154.5,29.6],'Main Hawaiian Islands':[-161,18,-154.5,22.8],'Northwestern Hawaiian Islands':[-179.5,22.8,-161,29.6],'Gilbert Islands':[172,-3,177.5,4.5],'Kermadec':[-179,-32,-177,-28.5],'Chatham':[-177,-44.8,-175,-43.3],'Auckland':[165.7,-51,166.5,-50.4],'Campbell':[168.8,-52.8,169.4,-52.3],'Aru archipelago (including Tanahbesar/Wokam, Wamar, Kola, Kobroor, Maikoor, Koba, Trangan)':[133.8,-8,135.5,-5.2],'Amsterdam and Saint-Paul':[77.3,-39,77.9,-37.5],'Norfolk/Phillip/Nepean island group':[167.8,-29.2,168.1,-28.9]}
centers={'Palmyra':[-162.083333,5.883333],'Palmerston':[-163.166667,-18.05]}
domains={}
for r in routes:
 name=r['name'];g=gaz[name]
 if name in special:b=special[name]
 else:
  if name in centers:lon,lat=centers[name]
  else:lat,lon=[coord(c) for c in g['coordinate_html']]
  rad=.25 if name=='Rapa Nui' else .7 if name=='Kiritimati/Christmas (Pacific)' else .35 if name=='Penrhyn/Tongareva' else .12
  b=[lon-rad,lat-rad,lon+rad,lat+rad]
 domains[name]=b
(root/'selection-domains.json').write_text(json.dumps(domains,separators=(',',':')))
if (root/'gshhg-selected-full-records.bin.gz').exists():data=gzip.decompress((root/'gshhg-selected-full-records.bin.gz').read_bytes())
else:
 with zipfile.ZipFile(os.environ.get('WORLDATLAS_GSHHG_ZIP','/tmp/worldatlas-macro-coverage-africa-americas/gshhg-bin-2.3.7.zip')) as z:data=z.read('gshhs_f.b')
print('gshhg full',len(data),hashlib.sha256(data).hexdigest(),flush=True); pos=0;polys={};headers={};allcounts={};selected_records=[]
while pos<len(data):
 lid,num,flag,w,e,s,north,ar,arf,cont,anc=struct.unpack_from('>IIIiiiiIIii',data,pos);pos+=44;offset=pos;pos+=num*8;level=flag&255;allcounts[level]=allcounts.get(level,0)+1
 if level>4:continue
 # Header coordinates can be 0..360; select whole geometry only if envelope intersects any named domain.
 west=w/1e6;east=e/1e6;south=s/1e6;north=north/1e6
 if west>=180:west-=360;east-=360
 if east>180:continue # No requested domain crosses 180; skip unrelated dateline-straddling shells explicitly.
 if not any(west<b[2] and east>b[0] and south<b[3] and north>b[1] for b in domains.values()):continue
 selected_records.append(data[offset-44:pos])
 xy=np.frombuffer(data,dtype='>i4',count=num*2,offset=offset).reshape(-1,2)/1e6;xy=xy.copy();xy[:,0]=np.where(xy[:,0]>180,xy[:,0]-360,xy[:,0]);p=Polygon(xy)
 input_valid=p.is_valid
 if not input_valid:p=make_valid(p)
 polys[lid]=p;headers[lid]={'id':lid,'level':level,'container':cont,'n':num,'header_area_km2':ar/10**(flag>>26),'bounds':list(p.bounds),'source_flag':(flag>>24)&1,'valid':p.is_valid,'input_valid':input_valid}
print('selected',len(polys),flush=True)
selected_native=b''.join(selected_records);(root/'gshhg-selected-full-records.bin.gz').write_bytes(gzip.compress(selected_native,mtime=0));(root/'gshhg-extraction.json').write_text(json.dumps({'parent_archive_sha256':'28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc','parent_member':'gshhs_f.b','parent_member_sha256':'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6','selected_native_sha256':hashlib.sha256(selected_native).hexdigest(),'selected_native_bytes':len(selected_native),'selected_record_count':len(selected_records),'method':'Byte-for-byte complete native headers+coordinate records, source order retained, records selected by declared named-land domains; not source polygon editing','license':'LGPLv3 or later'},separators=(',',':'))) 
# Subtract direct lake/lagoon polygons from each L1 ocean-land shell; L3 islands are retained separately.
land={}
for lid,p in polys.items():
 h=headers[lid]
 if h['level'] not in [1,3]:continue
 holes=[polys[k] for k in polys if headers[k]['container']==lid and headers[k]['level']==h['level']+1]
 land[lid]=p.difference(unary_union(holes)) if holes else p
# Actual applicable footprints from immutable, bottom-up approved regional envelope, with complete global location spatial index to detect wrong routing.
hier={g['id']:g for g in json.load(open(repo/'data/hierarchy.json'))};featuregeo=[];featureprops=[]
for part in json.load(open(repo/'data/world-index.json'))['parts']:
 for f in json.load(open(repo/'data'/part))['features']:
  p=f['properties'];parent=p['parent_id']
  while parent in hier and hier[parent]['level']!='region':parent=hier[parent]['parent_id']
  # Oceania only plus near named domains outside it; global detection selection by envelope.
  geom=f['geometry'] # preserve exact geographic footprint
  from shapely.geometry import shape
  q=shape(geom);b=q.bounds
  if not any(b[0]<d[2] and b[2]>d[0] and b[1]<d[3] and b[3]>d[1] for d in domains.values()):continue
  featuregeo.append(make_valid(q) if not q.is_valid else q);featureprops.append({'id':p['id'],'name':p['name'],'region_id':parent})
print('source locations',len(featuregeo),flush=True);tree=STRtree(featuregeo)
def area(g):
 if g.is_empty:return 0
 if g.geom_type in ['Polygon','MultiPolygon']:return abs(geod.geometry_area_perimeter(g)[0])/1e6
 if hasattr(g,'geoms'):return sum(area(x) for x in g.geoms)
 return 0
rows=[];candidatefeatures=[];seen={};allcomponents=[]
for route in routes:
 name=route['name'];domain=box(*domains[name]);components=[]
 for lid,p in land.items():
  # Intersection selects full source polygons, never clipping island geometry into arbitrary bbox.
  if not p.intersects(domain):continue
  indices=list(tree.query(p));applicable=[i for i in indices if featureprops[i]['region_id']==route['region_id']];other=[i for i in indices if featureprops[i]['region_id']!=route['region_id']]
  existing=unary_union([featuregeo[i] for i in applicable]);all_existing=unary_union([featuregeo[i] for i in indices]);a=area(p);ov=area(p.intersection(existing));allov=area(p.intersection(all_existing));min_dist=min([p.distance(featuregeo[i]) for i in tree.query(p.buffer(.003))],default=None)
  status='absent-from-all-current-footprints' if allov/max(a,1e-12)<.01 and min_dist is None else 'wrong-region-overlap' if allov/max(a,1e-12)>.5 and ov/max(a,1e-12)<.01 else 'existing-land-partially-matches-independent-shoreline' if ov/max(a,1e-12)<.95 else 'existing-land-overlaps-independent-shoreline'
  c={'gshhg_id':lid,'source_level':headers[lid]['level'],'source_land_area_km2':a,'same_region_covered_area_km2':ov,'all_regions_covered_area_km2':allov,'same_region_covered_fraction':ov/a if a else None,'all_regions_covered_fraction':allov/a if a else None,'source_bounds':list(p.bounds),'source_vertex_count':headers[lid]['n'],'overlap_locations':[featureprops[i] for i in indices if p.intersects(featuregeo[i])],'status':status,'near_current_land_0_003_degrees':min_dist is not None}
  components.append(c);allcomponents.append(c)
  if status=='absent-from-all-current-footprints':
   if lid not in seen:
    seen[lid]={'type':'Feature','geometry':mapping(p),'properties':{'gshhg_id':lid,'source_id':'gshhg-full-2.3.7','named_routes':[name],'region_id':route['region_id'],'source_land_area_km2':a,'status':'candidate-needs-named-gazetteer-identity-and-migration-review','source_level':headers[lid]['level']}}
   else:seen[lid]['properties']['named_routes'].append(name)
 total=sum(c['source_land_area_km2'] for c in components);covered=sum(c['same_region_covered_area_km2'] for c in components)
 rows.append({'name':name,'region_id':route['region_id'],'old_represented':route['represented'],'selection_domain':domains[name],'domain_method':'Declared named-island/archipelago search envelope, gazetteer coordinate selects full GSHHG polygons; selection envelope is not approved territory and polygon is not clipped','gazetteer':gaz[name],'independent_land_components':components,'source_component_count':len(components),'source_domain_land_area_km2':total,'same_region_covered_fraction':covered/total if total else None,'status':'source-has-no-land-polygon-in-domain' if not components else 'confirmed-source-omission' if all(c['status']=='absent-from-all-current-footprints' for c in components) else 'partial-component-omission' if any(c['status']=='absent-from-all-current-footprints' for c in components) else 'represented-geometry-compared; full-modern-shoreline-not-certified','whole_source_domain_test_performed':True,'modern_complete_coverage_certified':False})
 print(name,len(components),round(total,3),round(covered/total,3) if total else None,sum(c['status']=='absent-from-all-current-footprints' for c in components),flush=True)
report={'scope':'All 64 named-land routes assigned to Oceania at approved geographic version3; no regional interior audit','input':{'geographic_version':3,'hierarchy_sha256':hashlib.sha256((repo/'data/hierarchy.json').read_bytes()).hexdigest(),'routing_sha256':hashlib.sha256((repo/'data/macro-foundation/approved-boundary-decisions.json').read_bytes()).hexdigest()},'method':{'source':'GSHHG2.3.7 full native binary','source_archive_sha256':'28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc','source_full_binary_sha256':'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6','source_parsed_binary_sha256':hashlib.sha256(data).hexdigest(),'source_vintage':'2017-06-15 release; underlying WVS/WDBII various older source surveys','source_license':'LGPLv3 or later; underlying public-domain inputs do not make this release public-domain','area':'WGS84 ellipsoidal geodesic area of polygon intersections, not square degrees; no antimeridian domain crossing in these declared searches','lagoon_handling':'Subtract direct level2 lagoon/lake children of Level1, and direct Level4 children of Level3; include Level3 island-in-lagoon when selected','parsed_source_polygon_counts':allcounts,'full_archive_source_polygon_counts':{1:179832,2:6659,3:1437,4:11,5:329,6:344},'selected_source_polygons':len(polys),'invalid_source_polygons_for_comparison_repaired':sum(not h['input_valid']for h in headers.values()),'invalid_source_policy':'Exact native bytes retained; make_valid only enables comparison and cannot authorize import','actual_locations_tested':len(featuregeo),'centroid_only_test':False,'candidate_minimum_overlap':'<1% of independent polygon against every existing footprint, and no existing footprint within0.003degree corridor','coverage_limits':['Comparison certifies only declared source-domain polygons in GSHHG2017, not all modern shoals/islets or2026reclaimed land.','GSHHG atoll source geometry can include generalized lagoon/reef extents where no lake child exists; named-route candidates require modern coast/gazetteer cross-check before import.','All entire polygons are retained. Coordinate search domains are discovery selectors, not territorial subdivisions.','No values or identities imported; no existing footprints replaced or clipped.','No historical attributes inferred from current or2017geography.']},'routes':rows,'missing_component_candidates':len(seen),'candidate_file':'missing-land-candidates.geojson.gz','followup':'root integrates only independently corroborated dry-land named candidates; leaves source-indeterminate tiny-islet gaps explicit and certified scope bounded'}
(root/'report.json').write_text(json.dumps(report,separators=(',',':')))
(root/'missing-land-candidates.geojson.gz').write_bytes(gzip.compress(json.dumps({'type':'FeatureCollection','features':list(seen.values())},separators=(',',':')).encode(),mtime=0))
