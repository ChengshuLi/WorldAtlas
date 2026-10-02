import os,json,gzip,struct,hashlib,math,time
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box,Point
from shapely.geometry.polygon import orient
from shapely.ops import transform,unary_union
from shapely import from_wkb,make_valid,STRtree,to_wkb
from pyproj import Geod,CRS,Transformer
from config import DOMAINS,ALIASES,ADDITIONAL,MAINLAND,LARGE
P=Path(__file__).parent;repo=Path(os.environ.get('WORLDATLAS_REPO','/workspace/WorldAtlas')); geod=Geod(ellps='WGS84');SOURCE=Path(os.environ.get('WORLDATLAS_GSHHG_BINARY','/tmp/worldatlas-macro-coverage-africa-americas/gshhs_f.b'));(P/'candidate-components').mkdir(exist_ok=True)
def area(g):
 if g.is_empty:return 0.
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient(g,sign=1))[0])/1e6
 if g.geom_type in ('MultiPolygon','GeometryCollection'):return sum(area(a) for a in g.geoms)
 return 0.
rows=json.load(open(repo/'data/macro-foundation/envelopes-v3/envelope-index.json'))['groups'];regions=[x for x in rows if x['level']=='region'];rg=[from_wkb(gzip.decompress((repo/'data/macro-foundation/envelopes-v3'/x['path']).read_bytes())) for x in regions];tree=STRtree(rg);ri={x['id']:i for i,x in enumerate(regions)}
entries=json.load(open(P/'scoped-entries.json'));em={e['name']:e for e in entries};gzsrc=json.load(open(P/'gazetteer-source-inventory.json'));gaz={r['name']:r for r in gzsrc};components=json.load(open(P/'components.json'))['components'] if (P/'components.json').exists() else [];seen={(x['family'],x['gshhg_id']) for x in components};total=0
while True:
 with SOURCE.open('rb') as reader:
  while hdr:=reader.read(44):
   vals=struct.unpack('>11i',hdr);identity,n,flag,west,east,south,north,akm,fulla,container,ancestor=vals;raw=reader.read(n*8);total+=1
   if flag&255!=1 or north/1e6< -13 or south/1e6>82:continue
   coords=np.frombuffer(raw,dtype='>i4').reshape(n,2).astype('float64')/1e6
   xs=np.rad2deg(np.unwrap(np.deg2rad(coords[:,0])));xs-=360*math.floor((float(xs.mean())+180)/360);coords[:,0]=xs
   bounds=(float(coords[:,0].min()),float(coords[:,1].min()),float(coords[:,0].max()),float(coords[:,1].max()))
   relevant=[name for name,bs in DOMAINS.items() if any(bounds[0]<=b[2] and bounds[2]>=b[0] and bounds[1]<=b[3] and bounds[3]>=b[1] for b in bs)]
   if not relevant:continue
   relevant=[name for name in relevant if (akm/(10**((flag>>26)&63))<=300000 if name in LARGE else akm/(10**((flag>>26)&63))<=10000) or name in MAINLAND]
   if not relevant:continue
   geom=Polygon(coords);valid=geom.is_valid
   if not valid:geom=make_valid(geom)
   for name in relevant:
    if (name,identity) in seen:continue
    hits=[b for b in DOMAINS[name] if geom.intersects(box(*b))]
    if not hits:continue
    g=geom.intersection(unary_union([box(*b) for b in hits])) if name in MAINLAND else geom
    ak=area(g)
    if ak<=0:continue
    overlaps=[]
    for i in tree.query(g):
     ai=area(g.intersection(rg[int(i)]))
     if ai>1e-9:overlaps.append(dict(region_id=regions[int(i)]['id'],region=regions[int(i)]['name'],intersection_km2=ai,share=min(1,ai/ak)))
    overlaps.sort(key=lambda x:x['intersection_km2'],reverse=True);best=overlaps[0] if overlaps else None;target=rg[ri[em[name]['region_id']]];target_ai=next((x['intersection_km2'] for x in overlaps if x['region_id']==em[name]['region_id']),0);share=min(1,target_ai/ak)
    shifted_share=None;distance_km=None
    # Metric local AEQD on source component, only a narrow clipped atlas neighborhood; 200m comparison is diagnostic, never migration geometry.
    if ak>=.1 and share<.98:
     p=g.representative_point();crs=CRS.from_proj4(f'+proj=aeqd +lat_0={p.y} +lon_0={p.x} +datum=WGS84 +units=m');f=Transformer.from_crs('EPSG:4326',crs,always_xy=True).transform;back=Transformer.from_crs(crs,'EPSG:4326',always_xy=True).transform
     bb=g.bounds;pad=max(.03,.003/max(.01,math.cos(math.radians(p.y))));near=target.intersection(box(bb[0]-pad,bb[1]-.03,bb[2]+pad,bb[3]+.03))
     if near.is_empty:shifted_share=0.
     else:
      ng=transform(f,near);pg=transform(f,g);inter=pg.intersection(ng.buffer(200));shifted_share=min(1,area(transform(back,inter))/ak);distance_km=pg.distance(ng)/1000
    qnames=[ALIASES.get(name,name.replace(' ','_'))]+ADDITIONAL.get(name,[]);matches=[]
    for q in qnames:
     for co in gaz.get(q,{}).get('coordinates',[])[:1]:
      pt=Point(co)
      if g.covers(pt) or g.distance(pt)<.005:matches.append({'name':q,'coordinate':co,'relation':'inside' if g.covers(pt) else 'within_0.005_degree_diagnostic','source_url':gaz[q]['url']})
    canonical=to_wkb(g);sha=hashlib.sha256(canonical).hexdigest();asset=f'{identity}-{hashlib.sha256(name.encode()).hexdigest()[:8]}.wkb.gz';(P/'candidate-components'/asset).write_bytes(gzip.compress(canonical,mtime=0))
    components.append(dict(family=name,gshhg_id=identity,native_points=n,header_area_km2=akm/(10**((flag>>26)&63)),source_polygon_valid=valid,audit_normalization='longitude unwrap; repair invalid source audit geometry only' if not valid else 'longitude unwrap only',area_km2=ak,bounds=list(g.bounds),source_window_clipped=name in MAINLAND,majority_region=best,all_region_overlaps=overlaps,target_region_share=share,target_region_200m_buffer_diagnostic_share=shifted_share,nearest_target_distance_km=distance_km,gazetteer_named_matches=matches,whole_polygon_within_declared_windows=any(box(*b).covers(g) for b in DOMAINS[name]),geometry_wkb_sha256=sha,candidate_geometry_path='candidate-components/'+asset))
   if len(components)%500==0:print('read',total,'components',len(components),flush=True)
 break
(P/'components.json').write_text(json.dumps(dict(gshhg_polygons_read=total,component_area_method='WGS84 geodesic polygon integration; rings oriented, holes subtracted; GeometryCollections land parts summed.',components=components),separators=(',',':'))+'\n')
ledger=[]
for e in entries:
 cs=[x for x in components if x['family']==e['name']];scope=[x for x in cs if x['area_km2']>=.1];pres=[x for x in scope if x['target_region_share']>.5];missing=[x for x in scope if x['target_region_share']<=.5];buffer_only=[x for x in missing if (x['target_region_200m_buffer_diagnostic_share'] or 0)>.5];absent=[x for x in missing if (x['target_region_200m_buffer_diagnostic_share'] or 0)<=.5];wrong=[x for x in scope if x['majority_region'] and x['majority_region']['share']>.5 and x['majority_region']['region_id']!=e['region_id']];named=[x for x in scope if x['gazetteer_named_matches']];qs=[ALIASES.get(e['name'],e['name'].replace(' ','_'))]+ADDITIONAL.get(e['name'],[])
 row={**e,'source_domain_boxes':DOMAINS[e['name']],'shoreline_source':'GSHHG2.3.7-full-level1','minimum_quantified_component_area_km2':.1,'source_components_all_sizes':len(cs),'source_components_gte_0_1km2':len(scope),'target_region_majority_components':len(pres),'source_window_components_without_target_majority':len(missing),'coastline_offset_diagnostic_candidates':len(buffer_only),'source_window_missing_or_wrong_region_candidates':len(absent),'majority_wrong_region_components':len(wrong),'named_components_identified':len(named),'source_window_area_km2':sum(x['area_km2'] for x in scope),'target_intersection_area_km2':sum(x['area_km2']*x['target_region_share'] for x in scope),'missing_candidate_ids':[x['gshhg_id'] for x in absent],'wrong_region_candidate_ids':[x['gshhg_id'] for x in wrong],'named_sources':[gaz[q] for q in qs if q in gaz],'coverage_status':'independent-component-comparison-completed; named-family-membership-review-open','association_precision':'Gazetteer coordinate only names a component; complete geometry comparison uses its polygon. Broad windows do not establish every component belongs to the family. Mainland windows explicitly clipped and not certified whole-peninsula coverage.','component_details_path':'components.json'}
 ledger.append(row);print(e['name'],'components',len(cs),'scope',len(scope),'target',len(pres),'missing',len(absent),'offset',len(buffer_only),'wrong',len(wrong),'named',len(named),flush=True)
(P/'ledger-initial.json').write_text(json.dumps(ledger,separators=(',',':'))+'\n');print('DONE',total,len(components))
