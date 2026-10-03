#!/usr/bin/env python3
"""Reproduce exact-source settlement screens for issue #606; see README.md."""
import csv, gzip, hashlib, io, json, zipfile
from pathlib import Path
from osgeo import ogr, osr

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
BASE=HERE.parents[0]/'regional-review-4254da254d94f450'
SRC=BASE/'sources'; LOCAL=HERE/'sources'
OUT=HERE/'settlement-assessment.json'
IDS=[f'atlas:physical:CAN-{n}:BRC' for n in (173,177,178,195,201,207)]
PINS={
 'assessment.json':'2ab2c0610e37d50f020d031538fa5a22aecf4c7389bd64f6ec17b79487b60499',
 'scope.json':'eeeba48c2ac959c2304b31f2008251b2dd8b34751d9aab1b9735d825532bf055',
 'sources/current-scope-and-parents.geojson.gz':'7ac3154985ef3bf5aae5b978481233e3a73c0ef6b2a753e1c7a15cef4c9302bb',
 'sources/current-parent-chains.json.gz':'aa0c1643d376baa9b7478d26886510718d3c0e242782df004e2defd028938290',
 'sources/aafc-bc-scope-ecoregions.geojson.gz':'915cdeb7dc028d7ce9a7e563ffecc5653121c2afd132abf24c7bb2ac59f2bb44',
 'sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz':'a16ca45708ab0ccd898994e5e792187d5a108741c2ff6f5f9f74e91242206ad4',
 'sources/statistics-canada-bc-population-centres-2021.geojson.gz':'511c74952f6a826503cbbee7907c749cceb2dd8ac0d2f8bf009f3f183fb3d86f',
 'sources/canadian-geographical-names-populated-places-BC.geojson.gz':'6863a835d8c599ec28bc81b587beb59540c7708835212ca9f1e637e3c7d1074b',
 'sources/aafc-ecoregions-layer-metadata.json':'59cf889bc9ebb717f1994a9b06b731768b25431fcfb3a0a611476a8be0bcba57',
 'sources/statistics-canada-census-subdivisions-layer-metadata.json':'2d134b376eeebcd8168aa8dc23bd04ab5e845b35e683c1875e40b7526fa189f9',
 'current-geography/part-29.json':'077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a',
}
TABLE=LOCAL/'statcan-2021-census-population-and-dwelling-counts-98-10-0002-01.zip'
TABLE_SHA='36ab6c8f3f6b82d70d9dea927cb5cf04f6fbf9b543a7ad543695e6ea70d22876'
MUNI_BBOXES={'173':[-139.0522,59.18482,-136.8095105272844,60.0],'177':[-133.63845,58.90547,-131.3323,60.00000699652852],'178':[-131.93811,59.78328,-129.85145,60.0001],'195':[-124.9231,49.0025,-123.5824,50.1471],'201':[-127.87051,54.03263,-126.95088851290241,55.04882],'207':[-120.59837,50.638401305513156,-115.28454510471033,54.59115]}
MUNI_COUNTS={'173':0,'177':0,'178':0,'195':9,'201':2,'207':14}
MUNI_HASHES={'173':'db246259b2fb2369fd471ad07c1f658fea9eb64739e189962e0fc749b0f14f64','177':'e17e2a92035c18f29304cb99396ebb2e6fbb9a5982ed700f16c33c8d3f1c21d0','178':'4e5e152b7b62efa0286919a61c22b57e2d044b4052e2a50848c961ce8af43cd5','195':'800890443774e266bac0d4b1fb9b44a14468a2dda80279893bc7b48c9425e3dd','201':'428cdd72ee4d511283815734e56f650701be01296dfb3dde0e0062ed5266c743','207':'1eccfed7e0c1b854f5f10d47130e568ffb5b67009dcbf578543c40ab9cf12d80'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    op=gzip.open if str(path).endswith('.gz') else open
    with op(path,'rt',encoding='utf-8') as f:return json.load(f)
def ref(epsg):
    s=osr.SpatialReference();s.ImportFromEPSG(epsg);s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);return s
S3347=ref(3347)
def project(geo,epsg=4326):
    g=ogr.CreateGeometryFromJson(json.dumps(geo,separators=(',',':')))
    g.AssignSpatialReference(ref(epsg));g.TransformTo(S3347)
    invalid=not bool(g.IsValid())
    if invalid:g=g.MakeValid()
    return g,invalid

def bbox_intersects(a,b):
    return not (a[1]<b[0] or a[0]>b[1] or a[3]<b[2] or a[2]>b[3])

for rel,expected in PINS.items():
    path=(REPO/'data/geography/part-29.json') if rel=='current-geography/part-29.json' else BASE/rel
    if not path.is_file() or sha(path)!=expected:raise SystemExit(f'baseline pin mismatch: {rel}')
if not TABLE.is_file() or sha(TABLE)!=TABLE_SHA:raise SystemExit('Statistics Canada census table size/hash changed')
assess=read(BASE/'assessment.json'); rows={r['location_id']:r for r in assess['locations']}
if not set(IDS)<=set(rows):raise SystemExit('Issue #606 subject list differs from #485 assessment')
scoped=read(SRC/'current-scope-and-parents.geojson.gz')['features']; features={f['properties']['id']:f for f in scoped}
if not set(IDS)<=set(features):raise SystemExit('Issue #606 subjects missing from pinned current scope')
parent_rows=read(SRC/'current-parent-chains.json.gz'); chains={x['id']:x['parent_chain'] for x in parent_rows}
# Full source table contains official 2021/2016 census population and land/dwelling counts for CDs/CSDs.
with zipfile.ZipFile(TABLE) as z:
    csvname=next(n for n in z.namelist() if n.endswith('.csv') and 'MetaData' not in n)
    table_rows=list(csv.DictReader(io.TextIOWrapper(z.open(csvname),encoding='utf-8-sig')))
    pc21='Population and dwelling counts (13): Population, 2021 [1]';pc16='Population and dwelling counts (13): Population, 2016 [2]';land='Population and dwelling counts (13): Land area in square kilometres, 2021 [10]'
pop_by_dguid={r['DGUID']:r for r in table_rows}
cd_features=read(SRC/'statistics-canada-bc-census-subdivisions-2021.geojson.gz')['features']
pc_features=read(SRC/'statistics-canada-bc-population-centres-2021.geojson.gz')['features']
gnbc_features=read(SRC/'canadian-geographical-names-populated-places-BC.geojson.gz')['features']
if len(cd_features)!=751 or len(pc_features)!=108 or len(gnbc_features)!=2228:raise SystemExit('Pinned source cohort count changed; inspect before reproducing')

out=[]
for id in IDS:
    subject=features[id]; raw=subject['geometry']; shape,bad=project(raw)
    wgs=ogr.CreateGeometryFromJson(json.dumps(raw)); env=wgs.GetEnvelope()
    muni_key=id.rsplit('-',1)[1].split(':')[0]
    observed_bbox=[env[0],env[2],env[1],env[3]]
    if any(abs(a-b)>1e-9 for a,b in zip(observed_bbox,MUNI_BBOXES[muni_key])):raise SystemExit(f'BC municipality bbox differs from frozen current geometry: {id}')
    source=rows[id];
    candidates=[]; cd_invalid=[]; cd_prefiltered=0
    for c in cd_features:
        geom=c['geometry']; cenv=ogr.CreateGeometryFromJson(json.dumps(geom)).GetEnvelope()
        if not bbox_intersects(env,cenv):continue
        cd_prefiltered+=1
        cg,c_bad=project(geom)
        if c_bad:cd_invalid.append(c['properties']['CSDUID'])
        if shape.Intersects(cg):
            inter=shape.Intersection(cg); area=inter.Area()/1e6
            if area>1e-5:
                p=c['properties']; dguid='2021A0005'+str(p['CSDUID']); pop=pop_by_dguid.get(dguid)
                if pop is None:raise SystemExit(f'2021 census population row missing for {dguid}')
                candidates.append({'csduid':str(p['CSDUID']),'dguid':dguid,'name':p['CSDNAME'],'csd_type':p['CSDTYPE'],'overlap_km2':round(area,6),'csd_landarea_km2':p.get('LANDAREA'),'population_2021':pop.get(pc21),'population_2016':pop.get(pc16),'source_geometry_invalid_before_temporary_repair':c_bad})
    muni_path=LOCAL/f'bc-municipalities-{muni_key}-bbox-20261003.geojson'
    if sha(muni_path)!=MUNI_HASHES[muni_key]:raise SystemExit(f'BC municipal WFS response hash mismatch: {muni_key}')
    muni_source=read(muni_path); muni_features=muni_source['features']
    if muni_source.get('numberMatched')!=MUNI_COUNTS[muni_key] or len(muni_features)!=MUNI_COUNTS[muni_key]:raise SystemExit(f'BC municipal WFS result count mismatch: {muni_key}')
    muni_hits=[]
    for f in muni_features:
        mg,m_bad=project(f['geometry'])
        if shape.Intersects(mg):
            overlap=shape.Intersection(mg).Area()/1e6
            muni_hits.append({'properties':f['properties'],'overlap_km2':round(overlap,6),'invalid_before_temporary_repair':m_bad})
    if muni_hits:raise SystemExit(f'Unexpected BC municipal boundary intersection for {id}; stop and re-review')
    pc_hits=[]
    for f in pc_features:
        pgeo=f['geometry']; p_raw=ogr.CreateGeometryFromJson(json.dumps(pgeo))
        if not bbox_intersects(env,p_raw.GetEnvelope()):continue
        pg,pbad=project(pgeo)
        if shape.Intersects(pg):pc_hits.append({'properties':f['properties'],'invalid_before_temporary_repair':pbad})
    gnbc_hits=[]
    for f in gnbc_features:
        pgeo=f['geometry']; p_raw=ogr.CreateGeometryFromJson(json.dumps(pgeo))
        if not bbox_intersects(env,p_raw.GetEnvelope()):continue
        pt,pbad=project(pgeo)
        if shape.Intersects(pt):gnbc_hits.append({'properties':f['properties']})
    ch=chains[id]
    chain=[{'id':x.get('id'),'name':x.get('name'),'parent_id':x.get('parent_id'),'administrative_level':x.get('metadata',{}).get('administrative_level'),'reference_year':x.get('metadata',{}).get('reference_year'),'source_name':x.get('metadata',{}).get('source_name'),'source_id':x.get('metadata',{}).get('source_id')} for x in ch]
    out.append({'location_id':id,'name':source['name'],'role_and_source':source['source_identity_and_vintage'],'current_parent_chain':chain,'current_geometry':source['current_geometry_screen'],'source_physical_screen':source['physical_land_screen'],'settlement_screen':{'bc_legal_municipality_boundaries_intersecting':muni_hits,'bc_municipal_wfs_bbox_candidate_count':len(muni_features),'bc_municipal_wfs_observation_time':muni_source.get('timeStamp'),'statistics_canada_population_centres_2021_intersections':pc_hits,'nrCan_gnbc_populated_place_points_inside_or_touching':gnbc_hits,'statscan_2021_csd_intersections_with_census_population':sorted(candidates,key=lambda x:(-x['overlap_km2'],x['csduid'])), 'csd_source_invalid_geometries_temporarily_repaired':sorted(cd_invalid),'csd_geometries_after_geographic_bbox_prefilter':cd_prefiltered,'interpretation':'CSD population is an aggregate for the whole census subdivision. A large regional district electoral area intersecting a physical unit does not locate its residents inside that physical unit; reserve counts of zero are 2021 usual-resident counts and do not prove settlement absence or historical absence.'},'finding':'Unresolved: no retained 2021 Population Centre polygon or GNBC Populated Place point locates a settlement in this unit. Official census subdivision overlap/population and current BC community-location metadata do not resolve where residents or communities lie within the physical footprint.'})
report={'issue':606,'retrieved_utc_date':'2026-10-03','assigned_ids':IDS,'assessed_subject_count':len(out),'baseline':{'source_main_commit':'05c6de936040d82e0e93cd82a83c2450aeb0b253','wna_region_id':'framework:region:western-north-america:d2a1c2775a57','frozen_region_geometry_sha256':'7697f7a1a388f6b3e289ef00795cdb5e86bf9138f89eb97ec8d19bcfa1c131a9','frozen_region_member_ids_sha256':'3e060c8e712c4955bdb2996d4edf3b9271aaa8d0120501171cc7327e10797aaf','macro_certificate_sha256':'979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e'},'method':'For each of exactly the six issue IDs, verify immutable #485 baseline hashes, project pinned current unit geometry and official 2021 Census Subdivision/Population Centre/NRCan GNBC source geometries to EPSG:3347, temporarily MakeValid when needed, and use envelope-prefiltered OGR exact intersection. Enumerate every intersecting 2021 Census Subdivision with area over 0.00001 km2 and join its DGUID to the exact official 2021 Census population and dwelling counts table. Test exact point-in-unit/intersection for all retained GNBC British Columbia Populated Place records. Report source geometries requiring temporary repair. Shared geometry/source objects are never modified.' ,'source_cohort_counts':{'assigned_ids':6,'bc_2021_census_subdivision_polygons':len(cd_features),'bc_2021_population_centre_polygons':len(pc_features),'bc_gnbc_populated_place_points':len(gnbc_features),'census_table_rows':len(table_rows),'bc_legal_municipality_bbox_queries':6,'bc_legal_municipality_bbox_candidate_features':sum(MUNI_COUNTS.values())},'municipal_wfs_query':{'canonical_layer':'https://openmaps.gov.bc.ca/geo/pub/WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_MUNICIPALITIES_SP/ows','wfs_version':'2.0.0','typeName':'pub:WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_MUNICIPALITIES_SP','bbox_crs':'urn:ogc:def:crs:OGC:1.3:CRS84','result_crs':'urn:ogc:def:crs:OGC:1.3:CRS84','outputFormat':'application/json','count':1000,'retrieval_date_utc':'2026-10-03','queries':[{'location_id':f'atlas:physical:CAN-{n}:BRC','bbox_wgs84':MUNI_BBOXES[str(n)],'candidate_features':MUNI_COUNTS[str(n)],'response_timestamp':read(LOCAL/f'bc-municipalities-{n}-bbox-20261003.geojson').get('timeStamp'),'response_file':f'sources/bc-municipalities-{n}-bbox-20261003.geojson','response_sha256':MUNI_HASHES[str(n)]} for n in (173,177,178,195,201,207)]},'results':out,'overall_conclusion':'All six subjects are individually assessed. The official local-area census boundaries overlap each area, but regional-district population totals cannot geolocate residents in the portions. Three Georgia-Puget Basin reserve Census Subdivisions intersect a very small assigned physical feature and each reports zero 2021 usual residents. The complete retained population-centre and GNBC populated-place screens have no hits for all six, and the current official BC legally-defined municipal boundary WFS has no polygon intersection with any assigned physical unit. BC First Nation Community Locations is catalogued Access Only and expressly approximate; its metadata is retained, its restricted coordinates are not. Settlement presence/absence within each physical unit remains unresolved. Do not infer empty land, political ownership, or settlement absence from the screening no-hits.'}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'wrote {OUT}: {len(out)}/6 subjects; PC hits={sum(len(r["settlement_screen"]["statistics_canada_population_centres_2021_intersections"]) for r in out)}; GNBC hits={sum(len(r["settlement_screen"]["nrCan_gnbc_populated_place_points_inside_or_touching"]) for r in out)}; CSD overlaps={sum(len(r["settlement_screen"]["statscan_2021_csd_intersections_with_census_population"]) for r in out)}')
