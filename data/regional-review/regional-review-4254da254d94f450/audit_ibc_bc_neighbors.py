#!/usr/bin/env /usr/bin/python3
"""Sampled map-only IBC screen for BC and Idaho/Montana neighbor boundaries."""
import gzip,json,os,math,hashlib,sys
from pathlib import Path
from osgeo import ogr,osr
P=Path(__file__).resolve().parent;S=P/'sources';ogr.UseExceptions()
def read(p):
 with gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8') as f:return json.load(f)
def ref(code):
 s=osr.SpatialReference();s.ImportFromEPSG(code);s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);return s
src=ref(4326);dst=ref(3347)
def project(obj,sr=src,target=dst):
 g=ogr.CreateGeometryFromJson(json.dumps(obj,separators=(',',':')));g.AssignSpatialReference(sr);g.TransformTo(target)
 if not g.IsValid():g=g.MakeValid()
 def collect(x,out):
  if x.GetGeometryName()=='POLYGON':out.AddGeometry(x)
  elif x.GetGeometryName() in ('MULTIPOLYGON','GEOMETRYCOLLECTION'):
   for j in range(x.GetGeometryCount()):collect(x.GetGeometryRef(j),out)
 out=ogr.Geometry(ogr.wkbMultiPolygon);collect(g,out);g=out
 return g
def envelope_near(a,b,pad):return not(a[1]+pad<b[0] or b[1]+pad<a[0] or a[3]+pad<b[2] or b[3]+pad<a[2])
def sample_screen(line, boundary_geoms, step=1000):
 n=max(1,math.ceil(line.Length()/step));counts={m:0 for m in (25,100,250,500,1000)};env=line.GetEnvelope();cand=[(key,g) for key,g in boundary_geoms if envelope_near(env,g.GetEnvelope(),1100)]
 distances=[]
 for j in range(n+1):
  pt=line.Value(line.Length()*j/n)
  ranked=sorted((pt.Distance(b),key) for key,b in cand);dist=ranked[0][0] if ranked else float('inf');nearest=ranked[0][1] if ranked else None
  distances.append({'sample':j,'distance_m':round(dist,2) if math.isfinite(dist) else None,'nearest_boundary':nearest,'point_epsg3347':[round(pt.GetX(),1),round(pt.GetY(),1)]})
  for m in counts:
   if dist<=m:counts[m]+=1
 gaps=[];start=None
 for rec in distances+[{'distance_m':0}]:
  if rec['distance_m'] is not None and rec['distance_m']>1000 and start is None:start=rec
  elif (rec['distance_m'] is None or rec['distance_m']<=1000) and start is not None:
   gaps.append({'start_point_epsg3347':start['point_epsg3347'],'end_point_epsg3347':prev['point_epsg3347'],'sample_count':prev['sample']-start['sample']+1,'max_sample_gap_m':max(x['distance_m'] for x in distances[start['sample']:prev['sample']+1]),'nearest_boundary_examples':sorted({x['nearest_boundary'] for x in distances[start['sample']:prev['sample']+1] if x['nearest_boundary']})});start=None
  prev=rec
 return {str(m):round(v/(n+1)*100,5) for m,v in counts.items()},len(cand),n+1,gaps,[key for key,_ in cand]
sc=read(P/'scope.json');ids=set(sc['member_location_ids']);fc=read(S/'current-scope-and-parents.geojson.gz');fs={f['properties']['id']:f for f in fc['features']};assert set(fs)==ids
area_id=next(x['id'] for x in sc['area_scopes'] if x['name']=='British Columbia');ch={r['id']:r['parent_chain'] for r in read(S/'current-parent-chains.json.gz')};bcids=[i for i in ids if any(x.get('id')==area_id for x in ch[i])];assert len(bcids)==61
bc_bounds=[(i,project(fs[i]['geometry']).Boundary()) for i in bcids]
cd=read(S/'statistics-canada-bc-census-divisions-2021.geojson.gz')['features'];assert len(cd)==29
cd_bounds=[(str(f['properties'].get('CDUID')),project(f['geometry']).Boundary()) for f in cd]
tiger=read(S/'tigerline-2024-mountain-counties.geojson.gz')['features']
us_bounds=[(str(f['properties'].get('GEOID')),project(f['geometry'],target=ref(3347)).Boundary()) for f in tiger if f['properties']['STATEFP'] in ('16','30')]
wa=read(S/'tigerline-2024-washington-counties.geojson.gz')['features'];wa_bounds=[(str(f['properties'].get('GEOID')),project(f['geometry'],target=ref(3347)).Boundary()) for f in wa]
if len(sys.argv)!=2:raise SystemExit('usage: audit_ibc_bc_neighbors.py /path/to/lawfully-obtained-us-canada-boundary-v1-3.zip')
archive=Path(sys.argv[1]).resolve();raw=archive.read_bytes()
if len(raw)!=258764 or hashlib.sha256(raw).hexdigest()!='eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1':raise SystemExit('IBC v1.3 archive size/hash mismatch; see ibc-source-receipt.json')
ibc=ogr.Open('/vsizip/'+str(archive));ly=ibc.GetLayer(0);records=[]
for f in ly:
 no=f.GetField('SectionNum')
 if no not in (22,23,24,25,26):continue
 line=f.GetGeometryRef().Clone();line.AssignSpatialReference(ref(4269));line.TransformTo(dst)
 bcv,bcn,bcs,bcgaps,bckeys=sample_screen(line,bc_bounds);cdv,cdn,cds,cdgaps,cdkeys=sample_screen(line,cd_bounds)
 rec={'section_num':no,'section_name':f.GetField('SectionEng'),'map_scale':f.GetField('MaxScale'),'length_km':round(line.Length()/1000,3),'samples_at_1km':bcs,'near_current_bc_location_boundary_sample_pct':bcv,'candidate_current_boundaries':bcn,'candidate_current_boundary_ids':bckeys,'current_bc_boundary_gaps_over_1km':bcgaps,'near_statistics_canada_2021_cd_boundary_sample_pct':cdv,'candidate_census_division_boundaries':cdn,'candidate_census_division_ids':cdkeys,'census_division_boundary_gaps_over_1km':cdgaps}
 if no in (22,24):
  rec['near_idaho_montana_2024_county_boundary_sample_pct'],rec['candidate_idaho_montana_county_boundaries'],_,rec['idaho_montana_boundary_gaps_over_1km'],rec['candidate_idaho_montana_county_ids']=sample_screen(line,us_bounds)
 if no==25:rec['near_washington_2024_county_boundary_sample_pct'],rec['candidate_washington_county_boundaries'],_,rec['washington_county_boundary_gaps_over_1km'],rec['candidate_washington_county_ids']=sample_screen(line,wa_bounds)
 records.append(rec)
report={'source':'International Boundary Commission US–Canada boundary shapefile v1.3; metadata date 2018-04-20; source line NAD83 EPSG:4269 temporarily projected to Statistics Canada Lambert EPSG:3347; 2024 TIGER county geometries projected to EPSG:3347 for a same-plane distance screen.','source_archive_bytes':len(raw),'source_archive_sha256':hashlib.sha256(raw).hexdigest(),'source_feature_count':ly.GetFeatureCount(),'selected_bc_adjacent_sections':records,'method':'Select IBC section numbers 22–26 (49th parallel Columbia/Similkameen/West Kootenay/Southeast BC reaches plus Straits of Georgia/Juan de Fuca). At one-kilometre intervals along each line, compute minimum distance to bbox-near feature boundaries from the complete 61 assigned current BC location geometries and 29 official Statistics Canada 2021 Census Divisions. For land reaches 22/24 also screen all Idaho/Montana 2024 TIGER county boundaries; for section 25 screen 2024 Washington TIGER county boundaries. Report sample fractions within 25/100/250/500/1,000 m. This is a proximity screen; sample discretization and line/feature source scales apply.','interpretation':'The IBC service is a source cross-check only. It expressly limits use to mapping at its stated scales. Proximity does not determine the international boundary, political ownership or whether a difference is due to map scale, water, vintage, projection or current source geometry. Do not modify shared boundaries.','limitations':['IBC web metadata carries ©2015 International Boundary Commission, All Rights Reserved, and says the shapefile is for mapping use only and must not define the boundary. No open redistribution license was identified; the archive is therefore not included in this packet.','The BC comparison uses boundaries of assigned current locations and 2021 Census Divisions, neither a certified province border; the full shared-boundary union is deliberately not certified by this local screen.','Current administrative and physical unit boundaries within BC are both screened; sample points near an internal edge can also fall near a feature boundary.','Only sections 22–26 and selected Idaho/Montana/Washington county source edges are screened here; other neighbors require their own coordinated evidence.','Any potentially material cross-region mismatch requires coordinated follow-up with affected neighbors, release pins and certificate validation.']}
(P/'ibc-bc-neighbor-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(records,indent=2))
