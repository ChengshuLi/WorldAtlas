#!/usr/bin/env python3
"""Reproduce issue #494 geometry diagnostics with GeoJSON longitude-first EPSG:4326 axes.

Reads a fixed published baseline commit, exact original retained geoBoundaries bytes,
and the pinned 265-ID issue scope. Updates only this evidence packet's audit and
geometry report. Invalid shapes are retained; MakeValid is used only on clones in
aggregate diagnostics.
"""
import collections, gzip, hashlib, json, pathlib, subprocess
from osgeo import gdal, ogr, osr
from pyproj import Geod, Transformer, __version__ as pyproj_version

P = pathlib.Path(__file__).resolve().parent
ROOT = P.parents[2]
S = P / 'sources'
BASELINE = '6c6271af6b0dac49b82eaafb2db4de8b9c4611f2'

def sha(data): return hashlib.sha256(data).hexdigest()
def check(ok, message):
    if not ok: raise AssertionError(message)
def git_bytes(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASELINE}:{path}'])

def norm_poly_area(geom, geod):
    """Absolute geodesic polygon area in m2, subtracting holes; Polygon only."""
    check(geom.GetGeometryName().upper() == 'POLYGON', 'Independent geodesic sample must be Polygon')
    rings=[]
    for i in range(geom.GetGeometryCount()):
        ring=geom.GetGeometryRef(i)
        pts=[ring.GetPoint_2D(j) for j in range(ring.GetPointCount())]
        rings.append(abs(geod.polygon_area_perimeter([p[0] for p in pts], [p[1] for p in pts])[0]))
    return max(0.0, rings[0] - sum(rings[1:]))

def ogr_geom(feature, src_srs, transform):
    geom=ogr.CreateGeometryFromJson(json.dumps(feature['geometry'], ensure_ascii=False))
    check(geom is not None, 'Could not parse input GeoJSON geometry')
    geom.AssignSpatialReference(src_srs)
    check(geom.Transform(transform) == 0, 'Coordinate transformation failed')
    return geom

ogr.UseExceptions()

scope=json.loads((P/'issue-scope.json').read_text())
ids=sorted(scope['member_location_ids'])
check(len(ids)==265==scope['location_count'], 'Exact assigned scope must contain 265 locations')
check(sha('\n'.join(ids).encode()) == scope['member_location_ids_sha256'], 'Issue scope fingerprint mismatch')

# Read only the assigned published baseline snapshot; later main advances cannot
# silently change the geometry being measured.
index_bytes=git_bytes('data/world-index.json')
index=json.loads(index_bytes)
hierarchy_bytes=git_bytes('data/hierarchy.json')
check(sha(hierarchy_bytes)==scope['release']['hierarchy_sha256'], 'Assigned v5 hierarchy pin mismatch')
current={}; part_bytes={}
for rel in index['parts']:
    data=git_bytes('data/'+rel)
    found=[f for f in json.loads(data).get('features',[]) if f.get('id') in set(ids)]
    if found:
        part_bytes['data/'+rel]=data
        for f in found:
            check(f['id'] not in current, 'Duplicate subject feature in baseline parts')
            current[f['id']]=f
check(set(current)==set(ids), 'Published baseline does not contain all 265 scoped features')

source_gz=(S/'geoboundaries-COL-ADM2-geojson.json.gz').read_bytes()
source_bytes=gzip.decompress(source_gz)
source_data=json.loads(source_bytes)
source={f['properties']['shapeID']:f for f in source_data['features']}
audit_path=P/'audit.jsonl'
rows=[json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
check(len(rows)==265 and {r['location_id'] for r in rows}==set(ids), 'Audit must cover exactly the pinned 265 IDs')
old_path=P/'superseded/axis-order-v1/audit.jsonl'
old_rows={r['location_id']:r for r in (json.loads(line) for line in old_path.read_text().splitlines() if line.strip())}
check(set(old_rows)==set(ids), 'Superseded audit lacks exact scope')

src_srs=osr.SpatialReference(); src_srs.ImportFromEPSG(4326)
tgt_srs=osr.SpatialReference(); tgt_srs.ImportFromEPSG(6933)
# GeoJSON is x=longitude,y=latitude. Explicitly prevent EPSG authority axis order
# from treating those tuples as latitude,longitude.
src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
tgt_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
transform=osr.CoordinateTransformation(src_srs,tgt_srs)

# Independent coordinate control: compare OGR's explicit mapping to pyproj's
# always_xy transformer. Also calculate the known-bad authority-order result and
# assert that the test detects it rather than passing either result blindly.
control_lonlat=(-73.0,5.0)
point=ogr.Geometry(ogr.wkbPoint); point.AddPoint(*control_lonlat); point.AssignSpatialReference(src_srs)
check(point.Transform(transform)==0, 'OGR known-point transform failed')
ogr_xy=point.GetPoint_2D(0)
pyproj_xy=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform(*control_lonlat)
control_error=(ogr_xy[0]-pyproj_xy[0],ogr_xy[1]-pyproj_xy[1])
check(max(abs(x) for x in control_error)<0.001, 'OGR transform disagrees with independent always_xy coordinate control')
authority_src=osr.SpatialReference(); authority_src.ImportFromEPSG(4326)
authority_tgt=osr.SpatialReference(); authority_tgt.ImportFromEPSG(6933)
authority_pt=ogr.Geometry(ogr.wkbPoint); authority_pt.AddPoint(*control_lonlat); authority_pt.AssignSpatialReference(authority_src)
authority_pt.Transform(osr.CoordinateTransformation(authority_src,authority_tgt))
wrong_axis_xy=authority_pt.GetPoint_2D(0)
wrong_axis_error_m=((wrong_axis_xy[0]-pyproj_xy[0])**2+(wrong_axis_xy[1]-pyproj_xy[1])**2)**0.5
check(wrong_axis_error_m>1_000_000, 'Negative control failed to detect authority-axis ordering')

# Independent geodesic area control over a one-degree cell near the data's
# latitude. EPSG:6933 is equal-area on its authalic sphere; WGS84 geodesic area
# differs slightly because it uses the ellipsoid. The documented tolerance is
# deliberately broad enough for that model difference but catches axis swaps.
ring=[(-74.0,4.0),(-73.0,4.0),(-73.0,5.0),(-74.0,5.0),(-74.0,4.0)]
control_json={'type':'Polygon','coordinates':[[list(x) for x in ring]]}
control_feature={'geometry':control_json}
control_poly=ogr_geom(control_feature,src_srs,transform)
geod=Geod(ellps='WGS84')
control_geodesic_area=abs(geod.polygon_area_perimeter([x[0] for x in ring],[x[1] for x in ring])[0])
control_equal_area=control_poly.GetArea()
control_area_delta=abs(control_equal_area-control_geodesic_area)/control_geodesic_area
check(control_area_delta<0.002, 'Known-cell EPSG:6933 area disagrees with independent WGS84 geodesic calculation')

# Recompute every measurement. Keep invalid geometry status and classifications;
# area diagnostics are still recalculated from the raw invalid rings, while no
# symmetric-difference overlay is claimed for those subjects.
by_department={}; result_rows=[]; valid_rows=[]; invalid_rows=[]; geodesic_samples=[]; geodesic_raw_areas={}
for row in rows:
    ident=row['location_id']; src_feature=source[row['geoBoundaries_shape_id']]
    curr_geom=ogr_geom(current[ident],src_srs,transform)
    src_geom=ogr_geom(src_feature,src_srs,transform)
    invalid_current=not curr_geom.IsValid(); invalid_source=not src_geom.IsValid()
    current_area=curr_geom.GetArea(); source_area=src_geom.GetArea()
    area_fraction=abs(current_area-source_area)/source_area if source_area else None
    old=old_rows[ident]['geometry_comparison']
    old_assessment=row['assessment']
    geom_result=row['geometry_comparison']
    geom_result['area_fraction_difference']=area_fraction
    if invalid_current or invalid_source:
        # Invalid after correct longitude-first projection means this row's
        # overlay-based disposition must remain explicitly insufficient.
        row['assessment']='insufficient-evidence'
        row['administrative_unit_classification']='insufficient-evidence'
        geom_result['status']='invalid overlay'
        geom_result.pop('symmetric_difference_fraction',None)
        geom_result['error']=f'invalid_current={invalid_current}, invalid_source={invalid_source}'
        invalid_rows.append({'id':ident,'name':row['name'],'department':row['department'],'invalid_current':invalid_current,'invalid_source':invalid_source,'new_area_fraction_difference':area_fraction,'old_area_fraction_difference':old.get('area_fraction_difference')})
        marker=' Current or source shapes remain invalid for symmetric-difference overlay after the axis correction'
        if marker in row['finding']: base_finding=row['finding'].split(marker,1)[0]
        elif ' Current or source shapes are not valid for the attempted overlay;' in row['finding']: base_finding=row['finding'].split(' Current or source shapes are not valid for the attempted overlay;',1)[0]
        else: base_finding=row['finding'].split(' Source/current geometry overlay measured ',1)[0]
        row['finding']=base_finding+f' Current or source shapes remain invalid for symmetric-difference overlay after the axis correction (invalid_current={invalid_current}, invalid_source={invalid_source}); exact alignment remains insufficiently evidenced. Corrected planar area-difference diagnostic: {area_fraction:.8f}.'
        result_rows.append({'id':ident,'name':row['name'],'department':row['department'],'status':'invalid overlay','old_area_fraction_difference':old.get('area_fraction_difference'),'new_area_fraction_difference':area_fraction,'old_symmetric_difference_fraction':old.get('symmetric_difference_fraction'),'new_symmetric_difference_fraction':None,'assessment_before':old_assessment,'assessment_after':row['assessment']})
        group=by_department.setdefault(row['department'],{'current':[],'source':[],'invalid_current':0,'invalid_source':0,'locations':0})
        group['current'].append(curr_geom.Clone()); group['source'].append(src_geom.Clone()); group['invalid_current']+=int(invalid_current); group['invalid_source']+=int(invalid_source); group['locations']+=1
        continue
    symmetric=curr_geom.SymDifference(src_geom).GetArea()/source_area if source_area else None
    old_sym=old.get('symmetric_difference_fraction')
    geom_result['status']='symmetric-difference overlay; exact alignment remains unverified'
    geom_result['symmetric_difference_fraction']=symmetric
    geom_result.pop('error',None)
    marker=' Corrected longitude-first EPSG:6933 source/current overlay:'
    if marker in row['finding']: base_finding=row['finding'].split(marker,1)[0]
    elif ' Source/current geometry overlay measured ' in row['finding']: base_finding=row['finding'].split(' Source/current geometry overlay measured ',1)[0]
    else: base_finding=row['finding']
    row['finding']=base_finding+f' Corrected longitude-first EPSG:6933 source/current overlay: symmetric-difference fraction {symmetric:.8f}; relative area difference {area_fraction:.8f}. Exact alignment remains unverified.'
    valid_rows.append({'id':ident,'name':row['name'],'department':row['department'],'area_fraction_difference':area_fraction,'symmetric_difference_fraction':symmetric,'old_area_fraction_difference':old.get('area_fraction_difference'),'old_symmetric_difference_fraction':old_sym})
    result_rows.append({'id':ident,'name':row['name'],'department':row['department'],'status':'overlay','old_area_fraction_difference':old.get('area_fraction_difference'),'new_area_fraction_difference':area_fraction,'old_symmetric_difference_fraction':old_sym,'new_symmetric_difference_fraction':symmetric,'assessment_before':old_assessment,'assessment_after':row['assessment']})
    group=by_department.setdefault(row['department'],{'current':[],'source':[],'invalid_current':0,'invalid_source':0,'locations':0})
    group['current'].append(curr_geom.Clone()); group['source'].append(src_geom.Clone()); group['locations']+=1
    # Independently measure a deterministic sample of source/current raw shapes
    # selected below after all projected feature areas are known.
    geodesic_raw_areas[ident]={'source':norm_poly_area(ogr.CreateGeometryFromJson(json.dumps(src_feature['geometry'])),geod),'current':norm_poly_area(ogr.CreateGeometryFromJson(json.dumps(current[ident]['geometry'])),geod)}

# Independent geodesic-area sample: top five scoped sources by corrected planar
# equal-area footprint; compare raw-coordinate WGS84 Geod with corrected EPSG:6933.
with_geod=[r for r in rows if r['location_id'] in geodesic_raw_areas]
for row in sorted(with_geod,key=lambda x:geodesic_raw_areas[x['location_id']]['source'],reverse=True)[:5]:
    ident=row['location_id']; src_feature=source[row['geoBoundaries_shape_id']]
    sg=ogr_geom(src_feature,src_srs,transform); cg=ogr_geom(current[ident],src_srs,transform)
    gsrc=geodesic_raw_areas[ident]['source']; gcurr=geodesic_raw_areas[ident]['current']
    geodesic_samples.append({'id':ident,'name':row['name'],'department':row['department'],'source_geodesic_area_km2':gsrc/1e6,'source_equal_area_km2':sg.GetArea()/1e6,'source_area_relative_difference':abs(gsrc-sg.GetArea())/gsrc,'current_geodesic_area_km2':gcurr/1e6,'current_equal_area_km2':cg.GetArea()/1e6,'current_area_relative_difference':abs(gcurr-cg.GetArea())/gcurr})
    check(geodesic_samples[-1]['source_area_relative_difference']<0.003 and geodesic_samples[-1]['current_area_relative_difference']<0.003,'Independent geodesic and equal-area measures diverge beyond 0.3% on sample')

# Deterministic all-265 audit rewrite. No input geometry, source bytes or current
# release file is modified.
audit_path.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))

def add_polygons(out,g):
    name=g.GetGeometryName().upper()
    if name=='POLYGON': out.AddGeometry(g)
    elif name=='MULTIPOLYGON':
        for i in range(g.GetGeometryCount()): out.AddGeometry(g.GetGeometryRef(i))
    elif name=='GEOMETRYCOLLECTION':
        for i in range(g.GetGeometryCount()): add_polygons(out,g.GetGeometryRef(i))

def valid_polygon_union(items):
    multi=ogr.Geometry(ogr.wkbMultiPolygon)
    for geom in items:
        candidate=geom.Clone() if geom.IsValid() else geom.MakeValid()
        check(candidate is not None,'MakeValid failed on local diagnostic clone')
        add_polygons(multi,candidate)
    return multi.UnionCascaded()

summary=[]
for department,g in sorted(by_department.items()):
    current_union=valid_polygon_union(g['current']); source_union=valid_polygon_union(g['source'])
    diff=current_union.SymDifference(source_union); source_union_area=source_union.GetArea(); current_union_area=current_union.GetArea()
    summary.append({'department':department,'locations':g['locations'],'current_union_area_km2':current_union_area/1e6,'source_union_area_km2':source_union_area/1e6,'relative_area_delta':(current_union_area-source_union_area)/source_union_area,'union_symmetric_difference_fraction':diff.GetArea()/source_union_area,'invalid_current_inputs_made_valid_for_union':g['invalid_current'],'invalid_source_inputs_made_valid_for_union':g['invalid_source']})
union_report={'method':'Corrected OGR EPSG:6933 with EPSG:4326 OAMS_TRADITIONAL_GIS_ORDER (GeoJSON longitude,latitude). Parent aggregates use the exact 265 assigned current baseline and original source records. Invalid geometries are cloned and MakeValid is applied only for diagnostic union calculations; no published/source shape is mutated. These union metrics do not establish external parent-envelope completeness or omitted physical land.','baseline_commit':BASELINE,'source_sha256_compressed':sha(source_gz),'source_sha256_uncompressed':sha(source_bytes),'departments':summary}
(P/'department-union-comparison.json').write_text(json.dumps(union_report,ensure_ascii=False,indent=2)+'\n')

# Baseline feature file descriptors ensure each scoped feature was read from the
# immutable evaluation snapshot, not inferred from properties or current main.
baseline_part_descriptors=[{'path':path,'bytes':len(data),'sha256':sha(data)} for path,data in sorted(part_bytes.items())]
old_valid=[r for r in old_rows.values() if r['geometry_comparison']['status']!='invalid overlay']
old_top=sorted(old_valid,key=lambda r:r['geometry_comparison']['symmetric_difference_fraction'],reverse=True)[:5]
new_top=sorted(valid_rows,key=lambda r:r['symmetric_difference_fraction'],reverse=True)[:5]
assessment_changes=[r['location_id'] for r in rows if r['assessment']!=old_rows[r['location_id']]['assessment']]
correction={
 'issue':580,'packet_issue':494,'as_of':'2026-10-03','baseline_commit':BASELINE,
 'scope':{'count':len(ids),'member_ids_sha256':scope['member_location_ids_sha256'],'source_feature_count':len(source_data['features']),'current_features_resolved':len(current),'baseline_files':[{'path':'data/world-index.json','bytes':len(index_bytes),'sha256':sha(index_bytes)},{'path':'data/hierarchy.json','bytes':len(hierarchy_bytes),'sha256':sha(hierarchy_bytes)},*baseline_part_descriptors]},
 'axis_policy':{'source_crs':'EPSG:4326','source_axis_mapping':'OAMS_TRADITIONAL_GIS_ORDER; GeoJSON x=longitude,y=latitude','target_crs':'EPSG:6933','target_axis_mapping':'OAMS_TRADITIONAL_GIS_ORDER','gdal_version':gdal.VersionInfo('--version'),'proj_version':f'{osr.GetPROJVersionMajor()}.{osr.GetPROJVersionMinor()}.{osr.GetPROJVersionMicro()}','pyproj_version':pyproj_version},
 'method_sources':[{'title':'GDAL OSR API Tutorial: CRS and axis order','url':'https://gdal.org/en/stable/tutorials/osr_api_tut.html#crs-and-axis-order','retrieved_at':'2026-10-03','http_last_modified':'2026-08-18T10:07:15Z','response_bytes':92028,'response_sha256':'db51c0711380e1a36188bd9857ffe1c3e9201e6f765796a264c7b75648623b14','role':'Authoritative GDAL guidance for authority-compliant and traditional GIS axis strategies','retention':'restoration-only','reuse_terms':'No page bytes retained; confirm license before redistributing.'},{'title':'GDAL Python SpatialReference API','url':'https://gdal.org/en/stable/api/python/spatial_ref_api.html','retrieved_at':'2026-10-03','http_last_modified':'2026-08-18T10:07:16Z','response_bytes':205519,'response_sha256':'3e4f92f64a971d32d753cf8955837809fba70b42d419d76e1edf324f05bc4b94','role':'Python binding API reference for SetAxisMappingStrategy','retention':'restoration-only','reuse_terms':'No page bytes retained; confirm license before redistributing.'},{'title':'pyproj Transformer API','url':'https://pyproj4.github.io/pyproj/stable/api/transformer.html#pyproj.transformer.Transformer','retrieved_at':'2026-10-03','http_last_modified':'2026-09-16T12:28:06Z','response_bytes':176949,'response_sha256':'86ca34e1956d0a431a5b47814ba3440885a62252c56c1cd2db02c2045304a2a8','role':'Independent always_xy coordinate transform reference/control','retention':'restoration-only','reuse_terms':'No page bytes retained; verify current upstream terms when restoring.'},{'title':'pyproj Geod API','url':'https://pyproj4.github.io/pyproj/stable/api/geod.html#pyproj.Geod','retrieved_at':'2026-10-03','http_last_modified':'2026-09-16T12:28:06Z','response_bytes':145390,'response_sha256':'0660037df5d4c9f26af22f915a750b1da8b4f4f7a4203efeabd0980be88383fe','role':'Independent WGS84 geodesic area/perimeter check','retention':'restoration-only','reuse_terms':'No page bytes retained; verify current upstream terms when restoring.'}],
 'known_point_control':{'input_longitude_latitude':list(control_lonlat),'ogr_epsg6933_x_y':list(ogr_xy),'pyproj_always_xy_epsg6933_x_y':list(pyproj_xy),'difference_metres':list(control_error),'authority_default_wrong_axis_x_y':list(wrong_axis_xy),'wrong_axis_control_separation_metres':wrong_axis_error_m,'tolerance_metres':0.001,'negative_control_threshold_metres':1000000},
 'known_area_control':{'geometry':'one-degree cell -74..-73 longitude, 4..5 latitude','epsg6933_equal_area_m2':control_equal_area,'wgs84_geodesic_m2':control_geodesic_area,'relative_difference':control_area_delta,'tolerance':0.002,'independent_geodesic_samples':geodesic_samples},
 'result_counts':{'assigned':len(rows),'valid_overlays':len(valid_rows),'invalid_overlays':len(invalid_rows),'classification_changes':len(assessment_changes),'classification_changes_ids':assessment_changes,'invalid_overlay_ids':[r['id'] for r in invalid_rows]},
 'old_vs_corrected_summary':{'old_top5_symmetric_difference':[{'id':r['location_id'],'name':r['name'],'department':r['department'],'fraction':r['geometry_comparison']['symmetric_difference_fraction']} for r in old_top],'corrected_top5_symmetric_difference':[{'id':r['id'],'name':r['name'],'department':r['department'],'fraction':r['symmetric_difference_fraction']} for r in new_top],'corrected_max_area_fraction_difference':max(r['area_fraction_difference'] for r in valid_rows),'corrected_max_symmetric_difference_fraction':max(r['symmetric_difference_fraction'] for r in valid_rows),'corrected_maximum_absolute_area_fraction_difference_all_265':max(r['geometry_comparison']['area_fraction_difference'] for r in rows)},
 'invalid_overlays':invalid_rows,'subjects':result_rows,
 'interpretation':'All 265 projected geometry diagnostics have been recomputed from the same pinned source and baseline with explicit longitude-first axis mapping. The two preexisting invalid current polygons remain insufficient-evidence for symmetric overlay; no classification changes were justified by this measurement correction. These generalized source/current comparisons are not legal boundaries, do not prove gap-free topology or land completeness, and do not support unilateral footprint edits.'
}
(P/'axis-order-correction.json').write_text(json.dumps(correction,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'assigned':len(rows),'valid_overlays':len(valid_rows),'invalid_overlays':len(invalid_rows),'classification_changes':len(assessment_changes),'corrected_top5':correction['old_vs_corrected_summary']['corrected_top5_symmetric_difference'],'area_control_relative_difference':control_area_delta,'known_point_wrong_axis_separation_m':wrong_axis_error_m},ensure_ascii=False,indent=2))
