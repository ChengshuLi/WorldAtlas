#!/usr/bin/env python3
"""Build source-vintage, full-parent and settlement accounting for issue #485."""
import gzip,hashlib,json,math,zipfile,tempfile,shutil,unicodedata,re
from collections import Counter,defaultdict
from pathlib import Path
from osgeo import ogr,osr
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=HERE/'sources';REF486=ROOT/'data/regional-review/regional-review-93f8f3bee8e205be/sources'
ogr.UseExceptions()
def read(p):
 p=Path(p);return json.load(gzip.open(p,'rt',encoding='utf-8')) if p.suffix=='.gz' else json.loads(p.read_text(encoding='utf-8'))
def check(v,m):
 if not v:raise SystemExit('FAIL: '+m)
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().casefold())
scope=read(HERE/'scope.json');ids=scope['member_location_ids']; idset=set(ids);curfc=read(SRC/'current-scope-and-parents.geojson.gz');current={f['properties']['id']:f for f in curfc['features']}
check(len(ids)==222 and set(current)==idset and len(current)==222,'exact 222 current scope')
chains={r['id']:r['parent_chain'] for r in read(SRC/'current-parent-chains.json.gz')};check(set(chains)==idset,'all complete parent chains')
# Read exact evidence files and independent current source metadata.
old_us={f['properties']['shapeID']:f for f in read(SRC/'geoboundaries-USA-ADM2-assigned-5-states.geojson.gz')['features']}
old_adm1={f['properties']['shapeName'].casefold():f for f in read(SRC/'geoboundaries-USA-ADM1-assigned-5-states.geojson.gz')['features']}
tigerfc=read(SRC/'tigerline-2024-mountain-counties.geojson.gz');tiger=tigerfc['features'];tiger_by_state=defaultdict(list)
for f in tiger:tiger_by_state[f['properties']['STATEFP']].append(f)
can_adm3=read(SRC/'geoboundaries-CAN-ADM3-2016.geojson');can3={f['properties']['shapeID']:f for f in can_adm3['features']}
cd_data=read(SRC/'statistics-canada-bc-census-divisions-2021.geojson.gz')['features'];cd={str(f['properties']['CDUID']):f for f in cd_data}
csd_data=read(SRC/'statistics-canada-bc-census-subdivisions-2021.geojson.gz')['features']
csd_bycd=defaultdict(list);csd_byname=defaultdict(list)
for f in csd_data:
 p=f['properties'];csdcd=str(p['CSDUID'])[:4];csd_bycd[csdcd].append(f);csd_byname[(csdcd,norm(p['CSDNAME']))].append(f)
pc_data=read(SRC/'statistics-canada-bc-population-centres-2021.geojson.gz')['features']
eco_data=read(SRC/'aafc-bc-scope-ecoregions.geojson.gz')['features'];eco_by_id=defaultdict(list)
for f in eco_data:eco_by_id[int(f['properties']['ECOREGION_ID'])].append(f)
gnis=read(SRC/'usgs-gnis-populated-places-AZ-ID-MT-NV-UT.geojson.gz')['features']
canadian_geonames=read(SRC/'canadian-geographical-names-populated-places-BC.geojson.gz')['features']
gshhg_report=read(HERE/'gshhg-scope-screen.json')
# Spatial reference: USA Albers for five full state cohorts; Canada Atlas Lambert for all BC source/eco overlays.
crs_cache={}
def crs(code):
 if code not in crs_cache:
  s=osr.SpatialReference();s.ImportFromEPSG(int(code.split(':')[1]));s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);crs_cache[code]=s
 return crs_cache[code]
def geom(obj):
 g=ogr.CreateGeometryFromJson(json.dumps(obj,separators=(',',':')))
 if g is None:raise ValueError('cannot parse geometry')
 g.AssignSpatialReference(crs('EPSG:4326'));return g
def proj(g,epsg):
 q=g.Clone();q.TransformTo(crs(epsg));fix=not bool(q.IsValid())
 if fix:q=q.MakeValid()
 if q is None or q.IsEmpty() or not q.IsValid():raise ValueError('invalid temporary projected geometry')
 return q,fix
def union(gs):
 out=None
 for g in gs:
  if g is None:continue
  out=g.Clone() if out is None else out.Union(g)
 return out
def ratio(a,b):return round(a.Intersection(b).GetArea()/max(b.GetArea(),1)*100,6)
def area(g):return round(g.GetArea()/1e6,6)
def polycount(g):
 if g.GetGeometryName()=='MULTIPOLYGON':return g.GetGeometryCount()
 if g.GetGeometryName()=='POLYGON':return 1
 return sum(polycount(g.GetGeometryRef(i)) for i in range(g.GetGeometryCount()))
def holes(g):
 name=g.GetGeometryName()
 if name=='POLYGON':return max(0,g.GetGeometryCount()-1)
 return sum(holes(g.GetGeometryRef(i)) for i in range(g.GetGeometryCount()))
US={'04':('Arizona','framework:province:arizona:d5c692ca0249'),'16':('Idaho','framework:province:idaho:c58f1d2ffab2'),'30':('Montana','framework:province:montana:3eff20c3960e'),'32':('Nevada','framework:province:nevada:5adbc1137282'),'49':('Utah','framework:province:utah:9a287fc042c2')}
US_BY_PARENT={v[1]:('EPSG:5070',k,v[0]) for k,v in US.items()}
US_ALPHA={v[0]:k for k,(v2,v3) in []} # explicit below
ALPHA={'04':'AZ','16':'ID','30':'MT','32':'NV','49':'UT'}
# Materialize source geometries in study projections.
current_projected={};repairs={}
for lid,f in current.items():
 parent=f['properties']['parent_id'];
 if parent in US_BY_PARENT:epsg=US_BY_PARENT[parent][0]
 else:epsg='EPSG:3347'
 current_projected[lid],repairs[lid]=proj(geom(f['geometry']),epsg)
old_us_proj={sid:proj(geom(f['geometry']),'EPSG:5070')[0] for sid,f in old_us.items()}
tiger_proj={str(f['properties']['GEOID']):proj(geom(f['geometry']),'EPSG:5070')[0] for f in tiger}
required_can3={mid.rsplit(':',1)[1] for f in current.values() for mid in f['properties'].get('metadata',{}).get('source_member_ids',[]) if mid.startswith('gb:CAN:ADM3:')}
required_can3|={lid.rsplit(':',1)[1] for lid in ids if lid.startswith('gb:CAN:ADM3:')}
can3_proj={sid:proj(geom(can3[sid]['geometry']),'EPSG:3347')[0] for sid in required_can3}
cd_proj={code:proj(geom(f['geometry']),'EPSG:3347')[0] for code,f in cd.items()}
csd_proj_cache={}
def csd_geom(f):
 key=str(f['properties']['CSDUID'])
 if key not in csd_proj_cache:csd_proj_cache[key]=proj(geom(f['geometry']),'EPSG:3347')[0]
 return csd_proj_cache[key]
pc_proj=[(f,proj(geom(f['geometry']),'EPSG:3347')[0]) for f in pc_data]
canadian_geonames_proj=[]
for f in canadian_geonames:
 g=geom(f['geometry']);g.TransformTo(crs('EPSG:3347'));canadian_geonames_proj.append((f,g))
# Municipal/county source-member groups are checked for every ID, not a sample.
admin_members={};member_owner={};all_members=[]
for lid,f in current.items():
 p=f['properties'];m=p.get('metadata',{})
 if lid.startswith('atlas:district:CAN-'):
  ms=m.get('source_member_ids',[]);admin_members[lid]=ms;all_members.extend(ms)
  for mid in ms:
   if mid in member_owner:raise SystemExit(f'duplicate Canadian source member {mid}')
   member_owner[mid]=lid
check(len(all_members)==376 and len(set(all_members))==376,'all 376 distinct BC group source members')
miss_can=[mid for mid in all_members+[i for i in ids if i.startswith('gb:CAN:ADM3:')] if mid.rsplit(':',1)[1] not in can3]
check(not miss_can,f'2016 geoBoundaries Canada ADM3 source ids missing: {miss_can[:5]}')
# Build 2018-to-2024 direct county identity and complete five-state roster audit.
old_by_id={f['properties']['shapeID']:f for f in old_us.values()};county_crosswalk={};state_audit={}
for lid in ids:
 if not lid.startswith('gb:USA:ADM2:'):continue
 sid=lid.rsplit(':',1)[1]; old=old_us[sid];op=old['properties'];state_name=op['shapeGroup'] # USA; parent determines actual state
 parent=current[lid]['properties']['parent_id'];epsg,st,state=US_BY_PARENT[parent]
 candidates=[f for f in tiger_by_state[st] if norm(f['properties']['NAME'])==norm(op['shapeName'])]
 if not candidates:
  oldg=old_us_proj[sid]; ranks=[]
  for tf in tiger_by_state[st]:
   tg=tiger_proj[str(tf['properties']['GEOID'])];intersection=oldg.Intersection(tg).GetArea()
   if intersection>1:ranks.append((intersection,tf))
  candidates=[f for a,f in ranks if a>max(oldg.GetArea()*0.00001,1)]
 oldg=old_us_proj[sid];cg=current_projected[lid]
 links=[]
 for tf in candidates:
  tp=tf['properties'];tg=tiger_proj[str(tp['GEOID'])]
  links.append({'geoid':tp['GEOID'],'name':tp['NAME'],'namelsad':tp.get('NAMELSAD'),'classfp':tp.get('CLASSFP'),'aland_m2':int(tp['ALAND']),'awater_m2':int(tp['AWATER']),'old2018_overlap_pct':ratio(tg,oldg),'current_overlap_pct':ratio(tg,cg)})
 county_crosswalk[lid]=links
for st,(state,parent) in US.items():
 assigned=[i for i in ids if current[i]['properties']['parent_id']==parent]
 src=[f for f in old_us.values() if norm(f['properties']['shapeName']) in {norm(current[i]['properties']['name']) for i in assigned}]
 linked={x['geoid'] for i in assigned for x in county_crosswalk[i]}
 census=tiger_by_state[st];unmatched=[{'geoid':f['properties']['GEOID'],'name':f['properties']['NAME']} for f in census if f['properties']['GEOID'] not in linked]
 state_audit[state]={'state_fips':st,'expected_2018_counties':len(assigned),'tiger_2024_counties':len(census),'assigned_ids':sorted(assigned),'unmatched_2024_counties':unmatched,'current_parent_location_count':len(assigned),'crosswalk_complete':len(assigned)==len(census) and not unmatched and all(len(county_crosswalk[i])==1 for i in assigned)}
# Complete US Census Places; GNIS and Canada census settlement evidence screens.
places=[];place_counts={}
for st in US:
 path=SRC/f'tl_2024_{st}_place.zip';tmp=Path(tempfile.mkdtemp(prefix='places485-'))
 with zipfile.ZipFile(path) as z:z.extractall(tmp)
 shp=next(tmp.rglob('*.shp'));ds=ogr.Open(str(shp));ly=ds.GetLayer();this=[]
 for of in ly:
  g=of.GetGeometryRef().Clone();g.AssignSpatialReference(ly.GetSpatialRef());g.TransformTo(crs('EPSG:5070'))
  pr=of.items();this.append({'state_fips':st,'geoid':pr.get('GEOID'),'name':pr.get('NAME'),'classfp':pr.get('CLASSFP'),'geometry':g})
 ds=None;shutil.rmtree(tmp,ignore_errors=True);place_counts[st]=len(this);places.extend(this)
gnis_records=[];unknown_gnis=0
for f in gnis:
 p=f.get('properties',{});st=next((k for k,v in ALPHA.items() if v==p.get('state_alpha')),None)
 if not st:continue
 coords=(f.get('geometry') or {}).get('coordinates') or []
 points=coords if coords and isinstance(coords[0],(list,tuple)) else [coords]
 if not any(len(x)>=2 and not(float(x[0])==0 and float(x[1])==0) for x in points):unknown_gnis+=1;continue
 g=geom(f['geometry']);g.TransformTo(crs('EPSG:5070'))
 gnis_records.append({'state_fips':st,'gaz_id':p.get('gaz_id'),'name':p.get('gaz_name'),'feature_class':p.get('gaz_featureclass'),'county_name':p.get('county_name'),'fcode':p.get('fcode'),'unknown_coords_flag':p.get('isunknowncoords'),'geometry':g})
# Exact EcoID footprints; current 38 rows vs 41 source polygons (some ECO IDs are discontiguous).
eco_metrics={};eco_loc_by_id={}
for lid in ids:
 m=current[lid]['properties'].get('metadata',{});srcid=m.get('source_id','')
 if srcid.startswith('aafc:ecoregion:'):
  ecoid=int(srcid.rsplit(':',1)[1]);eco_loc_by_id[ecoid]=lid;source=eco_by_id[ecoid];expected=union([proj(geom(f['geometry']),'EPSG:3347')[0] for f in source]);cur=current_projected[lid]
  eco_metrics[lid]={'eco_id':ecoid,'source_feature_count':len(source),'source_name':source[0]['properties'].get('ECOREGION_NAME_EN'),'current_overlap_over_source_pct':ratio(cur,expected),'source_overlap_over_current_pct':ratio(expected,cur),'symdiff_km2':area(expected.SymDifference(cur)),'current_area_km2':area(cur),'source_area_km2':area(expected),'geometry_repaired_temporarily':repairs[lid]}
check(set(eco_loc_by_id)=={int(f['properties']['ECOREGION_ID']) for f in eco_data},'exact complete AAFC EcoRegion roster')
# Match 4 direct cities and 376 2016 source members to 2021 CSDs by code/name and complete shape overlay.
can_admin_rows={};cd_loc_by_code={int(i.split(':')[2].split('-')[1]):i for i in ids if i.startswith('atlas:district:CAN-')}
city_by_cd=defaultdict(list)
# Intersections between all 19 source member groups and official 2021 CD/CSD sources.
cd_coverage={};unrepresented_cd=[]
for code,cf in cd.items():
 code_s=str(cf['properties']['CDUID']);cdname=cf['properties']['CDNAME'];assigned=cd_loc_by_code.get(int(code_s[-4:]))
 if assigned:
  locs=[assigned]+[i for i in ids if i.startswith('gb:CAN:ADM3:') and int(current[i]['properties']['metadata'].get('source_member_cd_uid',0) or 0)==int(code_s)]
  # City-to-CD relationship by official 2021 CSDNAME/code with name match.
  for lid in ids:
   if lid.startswith('gb:CAN:ADM3:') and norm(current[lid]['properties']['name']) in [norm(f['properties']['CSDNAME']) for f in csd_bycd[code_s]]:
    for c in csd_bycd[code_s]:
     if norm(c['properties']['CSDNAME'])==norm(current[lid]['properties']['name']):city_by_cd[code_s].append(lid);break
  locs=[assigned]+sorted(set(city_by_cd[code_s]))
  curr_union=union([current_projected[i] for i in locs]); full=cd_proj[code_s]
  cd_coverage[code_s]={'name':cdname,'assigned_district_id':assigned,'separately_mapped_cities':city_by_cd[code_s],'matched_admin_location_count':len(locs),'census_division_area_km2':area(full),'current_admin_union_area_km2':area(curr_union),'current_union_coverage_pct':ratio(curr_union,full),'symdiff_km2':area(curr_union.SymDifference(full)),'decision':'direct 2021 CD code location plus separately represented 2021 city members; statistical geography, not legal cadastral certification'}
 else:
  # Ecological physical units screened against this administrative remainder for containment.
  egs=[current_projected[lid] for lid in eco_loc_by_id.values()];egunion=union(egs);full=cd_proj[code_s]
  pct=ratio(egunion,full);cd_coverage[code_s]={'name':cdname,'assigned_district_id':None,'separately_mapped_cities':[],'matched_admin_location_count':0,'census_division_area_km2':area(full),'ecoregion_union_coverage_pct':pct,'ecoregion_intersection_area_km2':area(egunion.Intersection(full)),'symdiff_km2':area(egunion.SymDifference(full)),'decision':'no one-to-one administrative location in this packet; AAFC natural ecoregion coverage screen only; do not infer administrative membership from physical overlap'};unrepresented_cd.append(code_s)
# Compare the complete assigned British Columbia footprint to independent
# provincial statistical coverage; keep administrative and physical cohorts distinct.
bc_area_id=next(x['id'] for x in scope['area_scopes'] if x['name']=='British Columbia')
bc_ids=[i for i in ids if any(x.get('id')==bc_area_id for x in chains[i])]
bc_admin_ids=[i for i in ids if i.startswith('atlas:district:CAN-') or i.startswith('gb:CAN:ADM3:')]
bc_eco_ids=list(eco_loc_by_id.values())
bc_area_union=union([current_projected[i] for i in bc_ids]);bc_admin_union=union([current_projected[i] for i in bc_admin_ids]);bc_eco_union=union([current_projected[i] for i in bc_eco_ids]);bc_census_union=union(list(cd_proj.values()))
bc_area_screen={'assigned_area_id':bc_area_id,'assigned_location_count':len(bc_ids),'admin_and_city_location_count':len(bc_admin_ids),'physical_ecoregion_location_count':len(bc_eco_ids),'statistics_canada_2021_census_division_count':len(cd_proj),'assigned_union_area_km2':area(bc_area_union),'statistics_canada_cd_union_area_km2':area(bc_census_union),'assigned_union_coverage_of_2021_cd_union_pct':ratio(bc_area_union,bc_census_union),'2021_cd_union_coverage_of_assigned_union_pct':ratio(bc_census_union,bc_area_union),'assigned_vs_2021_cd_union_symdiff_km2':area(bc_area_union.SymDifference(bc_census_union)),'admin_and_city_union_area_km2':area(bc_admin_union),'physical_ecoregion_union_area_km2':area(bc_eco_union),'admin_physical_intersection_area_km2':area(bc_admin_union.Intersection(bc_eco_union)),'admin_physical_symdiff_km2':area(bc_admin_union.SymDifference(bc_eco_union)),'per_census_division_assigned_coverage_pct':{code:ratio(bc_area_union,cd_proj[code]) for code in sorted(cd_proj)},'interpretation':'A cross-vintage provincial completeness screen only; Census Division extent is statistical geography, not a legal/province-border adjudication. Administrative and AAFC physical cohorts may partition by different roles; their intersections are not ownership claims.'}
# Full location accounting.
rows=[];place_hit_counts={};gnis_hit_counts={};pc_hit_counts={};csd_hit_counts={}
for lid in ids:
 f=current[lid];p=f['properties'];m=p.get('metadata',{});parent=p.get('parent_id');chain=chains[lid];source_members=m.get('source_member_ids',[])
 if lid.startswith('gb:USA:ADM2:'):
  state=US_BY_PARENT[parent][2];st=US_BY_PARENT[parent][1];epsg='EPSG:5070';fam='USA 2018 ADM2 county';decision='justified' if len(county_crosswalk[lid])==1 else 'insufficient_evidence';source=old_us[lid.rsplit(':',1)[1]]['properties'];identity={'source_entity_id':source['shapeID'],'source_name':source['shapeName'],'source_tier':source['shapeType'],'source_vintage':'2018','current_2024_matches':county_crosswalk[lid]}
 elif lid.startswith('atlas:district:CAN-'):
  state='Canada / British Columbia';st='CA';epsg='EPSG:3347';fam='Statistics Canada census division group';code=lid.split(':')[2].split('-')[1];si=sorted(set(x.rsplit(':',1)[1] for x in source_members));src=[can3[x] for x in si];g=union([can3_proj[x] for x in si]);cur=current_projected[lid]
  # Crosswalk each source member to the right 2021 CD plus matching CSD identities by normalized name.
  mismatch=[];name_hit=0;overlap_match=0;member_xw=[]
  cands=csd_bycd.get(code,[])
  for mid,sf in zip(si,src):
   sp=sf['properties'];n=norm(sp['shapeName']);name_matches=[x for x in cands if norm(x['properties']['CSDNAME'])==n]
   if name_matches:name_hit+=1
   sg=can3_proj[mid]
   best=None;bestpct=0;candidates=name_matches if name_matches else cands
   for cf in candidates:
    if str(cf['properties']['CSDUID'])[:4]!=code:continue
    cg=csd_geom(cf);e=sg.GetEnvelope();ce=cg.GetEnvelope()
    if e[1]<ce[0] or ce[1]<e[0] or e[3]<ce[2] or ce[3]<e[2]:continue
    a=sg.Intersection(cg).GetArea();pct=a/max(sg.GetArea(),1)*100
    if pct>bestpct:bestpct=pct;best=cf
   if best and bestpct>95:overlap_match+=1
   else:mismatch.append({'shapeID':sp['shapeID'],'name':sp['shapeName'],'best_2021_CSDUID':best['properties']['CSDUID'] if best else None,'best_overlap_pct':round(bestpct,6)})
   member_xw.append({'source_shape_id':sp['shapeID'],'source_name':sp['shapeName'],'name_matches_2021_csd_within_cd':len(name_matches),'best_2021_csd_id':best['properties']['CSDUID'] if best else None,'best_2021_csd_name':best['properties']['CSDNAME'] if best else None,'overlap_pct':round(bestpct,6)})
  src_cover=ratio(g,cd_proj[code]);cur_cover=ratio(cur,cd_proj[code]);decision='justified' if code in cd and len(si)==len(source_members) else 'insufficient_evidence'
  identity={'official_2021_cd_id':code,'official_2021_cd_name':cd.get(code,{}).get('properties',{}).get('CDNAME'),'2016_geoBoundaries_adm3_member_count':len(si),'member_ids_present':len(si)==len(source_members),'source_union_area_km2':area(g),'current_location_area_km2':area(cur),'source_overlap_over_current_location_pct':ratio(g,cur),'current_location_overlap_over_source_union_pct':ratio(cur,g),'source_member_union_symdiff_km2':area(g.SymDifference(cur)),'source_union_coverage_of_2021_cd_pct':src_cover,'current_location_coverage_of_2021_cd_pct':cur_cover,'source_member_name_matches_2021_csd':name_hit,'source_member_geometry_matches_2021_csd_over_95pct':overlap_match,'source_member_unmatched_or_changed':mismatch,'members':member_xw}
 elif lid.startswith('gb:CAN:ADM3:'):
  state='Canada / British Columbia';st='CA';epsg='EPSG:3347';fam='geoBoundaries Canada ADM3 / city';sid=lid.rsplit(':',1)[1];source=can3[sid]['properties'];oldg=can3_proj[sid];name=p['name'];csd_matches=[x for x in csd_data if norm(x['properties']['CSDNAME'])==norm(name)];cds=sorted({str(x['properties']['CSDUID'])[:4] for x in csd_matches});hits=[]
  for cf in csd_matches:
   cg=csd_geom(cf);e=oldg.GetEnvelope();ce=cg.GetEnvelope()
   if e[1]<ce[0] or ce[1]<e[0] or e[3]<ce[2] or ce[3]<e[2]:continue
   a=oldg.Intersection(cg).GetArea();pct=a/max(oldg.GetArea(),1)*100
   if pct>1:hits.append({'csduid':cf['properties']['CSDUID'],'name':cf['properties']['CSDNAME'],'type':cf['properties']['CSDTYPE'],'cd_uid':str(cf['properties']['CSDUID'])[:4],'overlap_pct':round(pct,6)})
  decision='justified' if any(h['overlap_pct']>95 for h in hits) else 'insufficient_evidence'
  identity={'source_entity_id':sid,'source_name':source['shapeName'],'source_tier':source['shapeType'],'source_vintage':'2016','current_2021_census_subdivision_name_matches':[{**{k:x['properties'].get(k) for k in ('CSDUID','CSDNAME','CSDTYPE')},'CDUID':str(x['properties']['CSDUID'])[:4]} for x in csd_matches],'spatial_crosswalk_2016_to_2021':hits,'unambiguous_current_parent_cd_ids':cds}
 else:
  state='Canada / physical geography';st='CA';epsg='EPSG:3347';fam='AAFC Canadian ecoregion'; ecoid=int(m['source_id'].rsplit(':',1)[1]);source=eco_by_id[ecoid][0]['properties'];identity=eco_metrics[lid];decision='justified'
 g=current_projected[lid];env=g.GetEnvelope();pc_hits=[];canadian_name_hits=[]
 if st=='CA':
  for cf,cg in pc_proj:
   e=cg.GetEnvelope()
   if env[1]<e[0] or e[1]<env[0] or env[3]<e[2] or e[3]<env[2]:continue
   if g.Intersects(cg):pc_hits.append({k:cf['properties'].get(k) for k in ('PCUID','PCNAME','PCTYPE','PCCLASS','PRUID')})
  for cf,cg in canadian_geonames_proj:
   e=cg.GetEnvelope()
   if env[1]<e[0] or e[1]<env[0] or env[3]<e[2] or e[3]<env[2]:continue
   if g.Intersects(cg):canadian_name_hits.append({k:cf['properties'].get(k) for k in ('CGNDB_ID','GEONAME','GENERIC','CONCISE','CATEGORY','DECISION')})
 us_places=[];us_gnis=[]
 if st in US:
  for pl in places:
   if pl['state_fips']!=st:continue
   e=pl['geometry'].GetEnvelope()
   if env[1]<e[0] or e[1]<env[0] or env[3]<e[2] or e[3]<env[2]:continue
   if g.Intersects(pl['geometry']):us_places.append({k:pl[k] for k in ('geoid','name','classfp')})
  for pp in gnis_records:
   if pp['state_fips']!=st:continue
   e=pp['geometry'].GetEnvelope()
   if env[1]<e[0] or e[1]<env[0] or env[3]<e[2] or e[3]<env[2]:continue
   if g.Intersects(pp['geometry']):us_gnis.append({k:pp[k] for k in ('gaz_id','name','feature_class','county_name','fcode','unknown_coords_flag')})
  place_hit_counts[lid]=len(us_places);gnis_hit_counts[lid]=len(us_gnis)
 else:place_hit_counts[lid]=None;gnis_hit_counts[lid]=None
 pc_hit_counts[lid]=len(pc_hits)
 # Full current parent chain: location/province/area/region/subcontinent/continent records were independently extracted.
 hierarchy_levels=[x.get('level') for x in chain]
 row={'location_id':lid,'name':p['name'],'current_parent_id':parent,'full_parent_chain':chain,'chain_levels':hierarchy_levels,'source_family':fam,'decision':decision,'source_identity_and_vintage':identity,'current_geometry_screen':{'projected_crs':epsg,'area_km2':area(g),'polygon_component_count':polycount(g),'interior_ring_count':holes(g),'temporary_repair_after_projection':repairs[lid],'land_water_or_disconnected_review':'component and ring counts are retained; GSHHG comparison follows in physical_land_screen; these metrics alone do not determine islands or completeness'},'settlement_screen':{'us_census_places_2024_polygon_count':len(us_places) if st in US else None,'us_census_places_2024':us_places if st in US else [],'usgs_gnis_populated_place_point_count':len(us_gnis) if st in US else None,'usgs_gnis_populated_place_points':us_gnis if st in US else [],'canada_statistics_canada_population_centres_2021_polygon_count':len(pc_hits) if st=='CA' else None,'canada_population_centres_2021':pc_hits if st=='CA' else [],'canada_geographical_names_populated_place_point_count':len(canadian_name_hits) if st=='CA' else None,'canada_geographical_names_populated_places':canadian_name_hits if st=='CA' else [],'canada_statistics_canada_csd_2021_source_count':len(csd_data) if st=='CA' else None,'interpretation':'Census population-centre polygons cover census-defined dense urban centres. GNBC/NRCan populated-place points add approved Canadian geographic names; Census Places/CDPs and GNIS use separate inclusion rules. These sources are not a complete settlement census; a no-hit never establishes settlement absence.'}}
 if lid.startswith('atlas:district:CAN-'):row['settlement_screen']['canada_ecoregion_group']={'district_id':lid.split(':')[2],'source_member_count':len(source_members),'current_admin_members_within_official_cd':len(identity['members'])}
 row['physical_land_screen']=gshhg_report['per_location'][lid]
 questions=[]
 if not row['physical_land_screen']['representative_point_in_level1_land']:questions.append('GSHHG 2017 level-1 representative-point no-hit; investigate source extent/point only; no land absence inference')
 if st=='CA' and not pc_hits and not canadian_name_hits:questions.append('No hit in either retained Canadian settlement screen; additional authoritative local/settlement evidence needed')
 if 'members' in identity and (identity.get('source_member_name_matches_2021_csd',0)<len(identity['members']) or identity.get('source_member_geometry_matches_2021_csd_over_95pct',0)<len(identity['members'])):questions.append('At least one 2016 grouped source member has an unresolved 2021 CSD name/geometry vintage crosswalk; see exact member rows')
 row['evidence_status']='unresolved_follow_up' if questions else 'assessed_with_available_sources';row['outstanding_questions']=questions
 if questions:row['decision']='insufficient_evidence'
 rows.append(row)
# Cohort-wide complete parent checks and official StatsCan CD comparison.
province_cohorts={}
for item in scope['province_scopes']:
 own=[i for i in ids if current[i]['properties']['parent_id']==item['id']]
 province_cohorts[item['id']]={'name':item['name'],'assigned_member_count':len(own),'full_province_member_count':item['full_province_locations'],'complete':len(own)==item['full_province_locations'],'location_ids':sorted(own)}
# Overall accounting and settlement gap IDs.
counts=Counter(r['decision'] for r in rows)
summary={'issue':485,'snapshot_date_utc':'2026-10-03','scope':{'count':len(ids),'ids_sha256':sha(('\n'.join(sorted(ids))+'\n').encode()),'area_scopes':scope['area_scopes'],'province_scopes':scope['province_scopes']},'source_accounting':{'us_2018_adm2_counties':sum(i.startswith('gb:USA:ADM2:') for i in ids),'canada_2016_adm3_grouped_local_sources':len(all_members),'canada_2016_adm3_direct_cities':sum(i.startswith('gb:CAN:ADM3:') for i in ids),'aafc_eco_location_ids':len(eco_loc_by_id),'aafc_source_feature_count':len(eco_data),'distinct_aafc_ecoregion_ids':len(eco_by_id),'statistics_canada_2021_bc_census_divisions':len(cd_data),'statistics_canada_2021_bc_census_subdivisions':len(csd_data),'statistics_canada_2021_bc_population_centres':len(pc_data),'canada_geographical_names_bc_populated_places':len(canadian_geonames),'us_census_places_2024_by_state':place_counts,'us_census_places_2024_total':len(places),'usgs_gnis_populated_place_count':len(gnis),'usgs_gnis_no_coordinate_count':unknown_gnis},'complete_state_parent_cohorts':state_audit,'complete_province_parent_cohorts':province_cohorts,'british_columbia_admin_source_crosswalk_by_census_division':cd_coverage,'british_columbia_census_divisions_without_assigned_direct_admin_location':unrepresented_cd,'british_columbia_area_union_screen':bc_area_screen,'decision_counts':dict(counts),'locations':rows,'limitations':['The published v5 region reference is an outer baseline, not approval of its interior. The exact Mountain area is partially owned; issue #486 covers the complementary 120 IDs.','US county and city identity checks concern source-vintage, names, roster and map overlays; neither licensed legal ownership nor cadastral accuracy is inferred.','Statistics Canada CD/CSD/population-centre layers are 2021 census geography and have different purposes; population-centre no-hits do not prove no rural settlement.','Natural AAFC ecoregions are physical-geography evidence and do not establish political ownership or current administrative successor membership.','All current shared hierarchy and geometry are read-only in this packet; source-role and parent-cohort findings are proposals for integration only.']}
all_xwalk_members=[m for r in rows for m in r['source_identity_and_vintage'].get('members',[])]
summary['british_columbia_2016_to_2021_member_crosswalk_summary']={'member_count':len(all_xwalk_members),'name_match_zero_count':sum(m['name_matches_2021_csd_within_cd']==0 for m in all_xwalk_members),'name_match_multiple_count':sum(m['name_matches_2021_csd_within_cd']>1 for m in all_xwalk_members),'best_overlap_below_95pct_count':sum(m['overlap_pct']<95 for m in all_xwalk_members),'best_overlap_below_50pct_count':sum(m['overlap_pct']<50 for m in all_xwalk_members),'interpretation':'Thresholds are triage screens only; cross-vintage differences do not establish a boundary correction. Each member and its best current candidate remain in the applicable parent row.'}
summary['physical_land_screen']={'source':gshhg_report['source'],'method':gshhg_report['method'],'scope_count':gshhg_report['scope_count'],'source_level1_record_count':gshhg_report['source_level1_record_count'],'matched_source_record_count':gshhg_report['retained']['record_count'],'locations_with_land_polygon_centroid_hits':sum(x['level1_centroid_hits']>0 for x in gshhg_report['per_location'].values()),'locations_with_representative_point_in_source_land':sum(x['representative_point_in_level1_land'] for x in gshhg_report['per_location'].values()),'per_location':gshhg_report['per_location'],'limitations':gshhg_report['limitations']}
summary['evidence_status_counts']=dict(Counter(r['evidence_status'] for r in rows))
summary['decision_semantics']='Each row is classified as justified or insufficient_evidence using source identity/role, direct parent mapping and material source coverage gaps. The decision is not certification or regional approval. evidence_status and outstanding_questions retain coverage limits and unresolved member/settlement follow-ups; no correction_needed finding was established by this source-only packet.'
(HERE/'assessment.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'locations':len(rows),'decision_counts':dict(counts),'county_by_state':{k:{'assigned':v['expected_2018_counties'],'tiger2024':v['tiger_2024_counties'],'crosswalk_complete':v['crosswalk_complete'],'unmatched':len(v['unmatched_2024_counties'])} for k,v in state_audit.items()},'BC_CDs':len(cd_data),'BC_CDs_without_admin_location':unrepresented_cd,'BC_CSDs':len(csd_data),'BC_pop_centres':len(pc_data),'AAFC features/IDs':f'{len(eco_data)}/{len(eco_by_id)}','USPlaces':place_counts,'GNIS':len(gnis),'parent_cohorts_complete':all(x['complete'] for x in province_cohorts.values())},indent=2))
