#!/usr/bin/env python3
"""Reproduce the 18-sample coastal edge comparison; see README.md."""
import gzip, hashlib, json, math, sys
from pathlib import Path
from osgeo import ogr, osr

ROOT = Path(__file__).resolve().parents[1] / 'regional-review-4254da254d94f450'
OUT = Path(__file__).resolve().parent / 'sample-assessment.json'
EXPECTED = (258764, 'eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1')

def read(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as f: return json.load(f)
def srs(epsg):
    s = osr.SpatialReference(); s.ImportFromEPSG(epsg); s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER); return s
S3347 = srs(3347)
def projected(geo, epsg=4326):
    g = ogr.CreateGeometryFromJson(json.dumps(geo, separators=(',', ':')))
    g.AssignSpatialReference(srs(epsg)); g.TransformTo(S3347)
    if not g.IsValid(): g = g.MakeValid()
    return g

if len(sys.argv) != 2: raise SystemExit('usage: analyze_section25.py /temporary/path/us-canada-boundary-v1-3.zip')
archive = Path(sys.argv[1]); raw = archive.read_bytes()
if (len(raw), hashlib.sha256(raw).hexdigest()) != EXPECTED: raise SystemExit('IBC archive does not match receipt')
ds = ogr.Open('/vsizip/' + str(archive.resolve())); layer = ds.GetLayer(0); line = None
for f in layer:
    if f.GetField('SectionNum') == 25:
        line = f.GetGeometryRef().Clone(); line.AssignSpatialReference(srs(4269)); line.TransformTo(S3347); break
if line is None: raise SystemExit('IBC section 25 missing')
scoped = read(ROOT / 'sources/current-scope-and-parents.geojson.gz')['features']
member_ids = set(read(ROOT / 'scope.json')['member_location_ids'])
chains = {x['id']:x['parent_chain'] for x in read(ROOT / 'sources/current-parent-chains.json.gz')}
bc_area = next(x['id'] for x in read(ROOT / 'scope.json')['area_scopes'] if x['name']=='British Columbia')
bc_ids = {i for i in member_ids if any(x.get('id')==bc_area for x in chains[i])}
scoped_by_id = {f['properties']['id']:f for f in scoped}
city_id = 'gb:CAN:ADM3:43193130B1191968375732'
if city_id not in scoped_by_id: raise SystemExit('assigned BC city candidate missing from pinned scope')
city_edge = projected(scoped_by_id[city_id]['geometry']).Boundary()
if len(bc_ids) != 61: raise SystemExit(f'expected complete assigned BC cohort, got {len(bc_ids)}')
bc = []; bc_no_area = []
for f in scoped:
    if f['properties']['id'] in bc_ids:
        edge = projected(f['geometry']).Boundary()
        if edge is not None and not edge.IsEmpty(): bc.append((f['properties']['id'], edge))
        else: bc_no_area.append(f['properties']['id'])
cd_features = read(ROOT / 'sources/statistics-canada-bc-census-divisions-2021.geojson.gz')['features']
cd = [(f['properties']['CDUID'], projected(f['geometry']).Boundary()) for f in cd_features]
wa_features = read(ROOT / 'sources/tigerline-2024-washington-counties.geojson.gz')['features']
wa = [(f['properties']['GEOID'], projected(f['geometry']).Boundary(), projected(f['geometry'])) for f in wa_features]
if len(cd) != 29 or len(wa) != 39 or len(bc) != 60 or bc_no_area != ['atlas:physical:CAN-185:BRC']: raise SystemExit(f'incomplete source cohort: BC={len(bc)}, CDs={len(cd)}, WA={len(wa)}')
steps = math.ceil(line.Length()/1000); rows=[]
for n in range(steps+1):
    p = line.Value(line.Length()*n/steps)
    nearest_bc = min((p.Distance(g), k) for k,g in bc)
    nearest_cd = min((p.Distance(g), k) for k,g in cd)
    nearest_wa = min((p.Distance(b), k) for k,b,_ in wa)
    inside = sorted(k for k,_,g in wa if g.Contains(p))
    if n in range(50,68): rows.append({'sample':n,'epsg3347_m':[round(p.GetX(),1),round(p.GetY(),1)],'nearest_current_bc_location_boundary_m':round(nearest_bc[0],2),'nearest_current_bc_location_id':nearest_bc[1],'abbotsford_current_bc_location_boundary_m':round(p.Distance(city_edge),2),'nearest_2021_statscan_cd_boundary_m':round(nearest_cd[0],2),'nearest_2021_statscan_cd_code':nearest_cd[1],'nearest_2024_tiger_wa_county_boundary_m':round(nearest_wa[0],3),'nearest_2024_tiger_wa_county_geoid':nearest_wa[1],'tiger_wa_county_polygons_containing_point':inside})
assert len(rows)==18 and rows[0]['sample']==50 and rows[-1]['sample']==67
assert all(r['nearest_current_bc_location_id']=='atlas:district:CAN-5915:BRC' for r in rows)
assert all(r['nearest_2024_tiger_wa_county_geoid']=='53073' and r['nearest_2024_tiger_wa_county_boundary_m']<0.2 for r in rows)
assert sum(not r['tiger_wa_county_polygons_containing_point'] for r in rows)==5
report={'source_line':'IBC US–Canada Boundary v1.3, section 25, “49th Parallel (Pacific to Columbia Valley)”, metadata date 2018-04-20','source_archive':{'canonical_url':'https://www.internationalboundarycommission.org/uploads/shapefile/us-canada-boundary-v1-3.zip','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'retained':False,'reason':'IBC page states ©2015 IBC, All Rights Reserved; mapping use only. No open redistribution license identified. Download temporarily, verify size/hash, use for mapping only, do not republish bytes; recheck terms before restoration.'},'baseline':{'wna_region_id':'framework:region:western-north-america:d2a1c2775a57','release':'geographic release 5 / Site 21','frozen_region_geometry_sha256':'7697f7a1a388f6b3e289ef00795cdb5e86bf9138f89eb97ec8d19bcfa1c131a9','frozen_region_member_ids_sha256':'3e060c8e712c4955bdb2996d4edf3b9271aaa8d0120501171cc7327e10797aaf','macro_certificate_sha256':'979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e','bc_location':'atlas:district:CAN-5915:BRC (Greater Vancouver), StatsCan 2021 Census Division-derived group','bc_city_candidate':'gb:CAN:ADM3:43193130B1191968375732 (Abbotsford), current assigned member; 23,320.81–40,232.57 m from scoped line points','washington_current_memberships':[{'id':'gb:USA:ADM2:52423323B9068998137459','name':'Whatcom','parent':'framework:province:washington:b01ae89096c9'},{'id':'gb:USA:ADM2:52423323B32782252789959','name':'San Juan','parent':'framework:province:washington:b01ae89096c9'}],'washington_parent_chain':['framework:province:washington:b01ae89096c9','framework:area:pacific:31aced66907e','framework:region:western-north-america:d2a1c2775a57','framework:subcontinent:northern-america:477e054b32f2','framework:continent:north-america:1ca27616f338'],'bc_census_division':'5915 Greater Vancouver, Statistics Canada 2021 Census Divisions','wa_counties':[{'geoid':'53073','name':'Whatcom','source':'2024 TIGER/Line','ALAND_m2':5459563210,'AWATER_m2':1028031788},{'geoid':'53055','name':'San Juan','source':'2024 TIGER/Line','ALAND_m2':450435997,'AWATER_m2':1157474748}]},'bc_boundary_input_accounting':{'assigned_bc_location_count':len(bc_ids),'usable_area_boundaries':len(bc),'no_area_boundary_after_temporary_make_valid':['atlas:physical:CAN-185:BRC'],'note':'This assigned physical ecoregion feature yields no area boundary after the same temporary projection/validity-repair and polygon-boundary method; it contributes no edge candidate. It is reported explicitly rather than silently counted as a geometric hit.'},'method':'Recreate section 25 from the hash-pinned IBC archive. Project line and retained official BC/Census/TIGER geometry to EPSG:3347; sample line at equal intervals no more than 1 km apart (74 points total), corresponding to the inherited #485 screen. Report all 18 consecutive points whose nearest assigned BC location boundary is over 1 km, with nearest boundaries and county polygon containment. Point-on-boundary behavior is reported separately; not interpreted as ownership. The IBC v1.3 line is expressly mapping-only.','assessment':'18/18 scoped samples are enumerated. Their nearest assigned BC location boundary is Greater Vancouver (CAN-5915); point distances range from 1,011.91 m to 5,888.53 m. Their nearest 2024 TIGER Washington county polygon edge is Whatcom (53073), all within 0.2 m; San Juan is not the nearest county for any. Four samples lie on/near county polygon edges and report no strict polygon containment; the others are contained in Whatcom. This is consistent with, but does not prove, a coast/water footprint representation difference between the BC source group and Washington county representation. Census CD 5915 also lacks a `WATERAREA` attribute in the retained 2021 layer response; source line and boundary vintages/scales differ. The two county `AWATER` values show substantial water area but do not identify which exact surfaces account for this line offset. Insufficient evidence to assign cause or recommend any boundary correction. No legal boundary or political ownership conclusion follows. Coordinate cross-region follow-up with Washington and British Columbia source owners if a future certified boundary/footprint comparison is desired.','samples':rows}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'wrote {OUT}: {len(rows)} points; max BC gap {max(r["nearest_current_bc_location_boundary_m"] for r in rows)} m')
