#!/usr/bin/env /usr/bin/python3
"""Cross-vintage BC location-area, Census Division and role-layer union screen."""
import gzip,json,hashlib
from pathlib import Path
from osgeo import ogr,osr
P=Path(__file__).resolve().parent;S=P/'sources';ogr.UseExceptions();crs=osr.SpatialReference();crs.ImportFromEPSG(3347);crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
def read(p):
 with gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8') as f:return json.load(f)
def g(f):
 x=ogr.CreateGeometryFromJson(json.dumps(f['geometry'],separators=(',',':')));x.AssignSpatialReference(crs4326);x.TransformTo(crs)
 if not x.IsValid():x=x.MakeValid()
 return x
def u(xs):
 x=None
 for z in xs:x=z.Clone() if x is None else x.Union(z)
 return x
def km2(x):return round(x.GetArea()/1e6,6)
def cover(a,b):return round(a.Intersection(b).GetArea()/max(b.GetArea(),1)*100,6)
crs4326=osr.SpatialReference();crs4326.ImportFromEPSG(4326);crs4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
scope=read(P/'scope.json');current=read(S/'current-scope-and-parents.geojson.gz');ids=set(scope['member_location_ids'])
assert len(ids)==222
bcarea=next(x['id'] for x in scope['area_scopes'] if x['name']=='British Columbia')
chain={x['id']:x['parent_chain'] for x in read(S/'current-parent-chains.json.gz')}
features={f['properties']['id']:f for f in current['features']};assert set(features)==ids
bcids=[i for i in ids if any(x.get('id')==bcarea for x in chain[i])];assert len(bcids)==61
admin=[i for i in bcids if i.startswith('atlas:district:CAN-') or i.startswith('gb:CAN:ADM3:')];eco=[i for i in bcids if i.startswith('atlas:physical:CAN-')]
assert (len(admin),len(eco))==(23,38)
cur={i:g(features[i]) for i in bcids};admin_union=u(cur[i] for i in admin);eco_union=u(cur[i] for i in eco);bc_union=u(cur.values())
cd=read(S/'statistics-canada-bc-census-divisions-2021.geojson.gz')['features'];assert len(cd)==29
cdg={str(f['properties']['CDUID']):g(f) for f in cd};cd_union=u(cdg.values())
report={'scope':{'british_columbia_area_id':bcarea,'assigned_location_count':len(bcids),'administrative_aggregation_and_city_count':len(admin),'ecoregion_count':len(eco),'statistics_canada_2021_census_division_count':len(cd)},'union_metrics':{'assigned_area_km2':km2(bc_union),'official_2021_cd_union_km2':km2(cd_union),'assigned_area_coverage_of_2021_cd_union_pct':cover(bc_union,cd_union),'2021_cd_union_coverage_of_assigned_area_pct':cover(cd_union,bc_union),'symmetric_difference_km2':km2(bc_union.SymDifference(cd_union)),'admin_city_union_km2':km2(admin_union),'ecoregion_union_km2':km2(eco_union),'admin_ecoregion_intersection_km2':km2(admin_union.Intersection(eco_union)),'admin_ecoregion_symmetric_difference_km2':km2(admin_union.SymDifference(eco_union))},'per_cd_assigned_area_coverage_pct':{k:cover(bc_union,v) for k,v in sorted(cdg.items())},'method':'Project all 61 current British Columbia-assigned location geometries and all 29 official Statistics Canada 2021 Census Division geometries into EPSG:3347; temporarily repair invalid projected shapes for overlay; union within each cohort; compute area ratios and symmetric differences. No output geometry is proposed.','interpretation':'Independent, cross-vintage coverage screen only. Statistical Census Division extents are not legal provincial boundaries. The 23 administrative/grouped-city and 38 physical ecoregion roles are preserved separately; overlap and symmetric difference are not political ownership or an instruction to alter the shared baseline.','limitations':['Some Canadian input polygons are invalid or nested as released; only temporary projected overlay geometries are repaired.','Census Division and assigned location products use distinct source families, vintages and feature purposes; no difference alone demonstrates an error.','This cohort is British Columbia only; Canada–US neighbor lines require a separately documented mapping-source screen and coordinated follow-up if implicated.']}
(P/'bc-area-union-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report['union_metrics'],indent=2))
