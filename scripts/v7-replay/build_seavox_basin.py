#!/usr/bin/env python3
"""Rasterize a selected direct-assignment SeaVoX basin at physical-water centers.

The input geometry and physical grid are pinned, and every output is written in a
fresh directory. This stage does not read or inherit old water assignment labels.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path
import sys

import numpy as np
import scipy
import pyproj
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from osgeo import gdal
from exclusive_outputs import create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, write_json_exclusive, validate_fresh_output
import exclusive_outputs, decision_snapshot, seavox_properties
from decision_snapshot import read_snapshot, participant_water_codes, find_basin, find_source
from seavox_properties import feature_id as read_feature_id
import shared_nearest as shared
import interval_nearest
import rectangle_nearest

W, H = 131072, 54614
STEP = 360.0 / W


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_source(path, source_sha, geometry_sha, feature_id):
    if digest(path) != source_sha:
        raise ValueError('source file hash mismatch')
    doc = json.loads(path.read_text())
    features = doc.get('features', []) if doc.get('type') == 'FeatureCollection' else []
    if len(features) != 1 or read_feature_id(features[0].get('properties')) != str(feature_id):
        raise ValueError('expected exactly one selected SeaVoX feature')
    feature = features[0]
    geom = feature.get('geometry')
    if not isinstance(geom, dict) or geom.get('type') not in ('Polygon', 'MultiPolygon'):
        raise ValueError('invalid Gulf source geometry')
    actual = hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if actual != geometry_sha:
        raise ValueError('canonical geometry hash mismatch')
    return feature



def validate_extraction(manifest_path, expected_manifest_sha, archive, geometry, snapshot, basin, source, policy_sha):
    if digest(manifest_path) != expected_manifest_sha:
        raise ValueError('extraction manifest hash mismatch')
    manifest = json.loads(manifest_path.read_text())
    rev = snapshot['decision_revision']
    if (manifest.get('schema') != 'worldatlas-seavox-archive-extraction-v1'
            or manifest.get('decision_id') != basin['id']
            or manifest.get('decision_snapshot_sha256') != policy_sha
            or manifest.get('decision_revision') != rev['id']
            or manifest.get('entity_revision') != rev['entity_revision']
            or manifest.get('source_id') != basin['source_id']
            or manifest.get('source_version') != basin['source_version']
            or str(manifest.get('source_feature_id')) != str(basin['source_feature_id'])
            or manifest.get('archive_sha256') != source['sha256']
            or manifest.get('geometry_sha256') != basin['geometry_sha256']):
        raise ValueError('extraction manifest does not match selected decision')
    name = manifest.get('feature_file')
    if not isinstance(name, str) or (manifest_path.parent / name).resolve() != geometry:
        raise ValueError('extraction manifest feature path mismatch')
    if digest(archive) != source['sha256']:
        raise ValueError('source archive hash mismatch')
    if digest(geometry) != manifest.get('feature_file_sha256'):
        raise ValueError('extracted feature file hash mismatch')
    return manifest


def validate_geometry_ogr(path):
    """Fail closed on empty or invalid polygon geometries; never repair source bytes."""
    with gdal.ExceptionMgr():
        with gdal.OpenEx(str(path), gdal.OF_VECTOR) as dataset:
            layer = dataset.ExecuteSQL(
                'SELECT ST_IsValid(geometry) AS valid, ST_IsEmpty(geometry) AS empty FROM source',
                dialect='SQLite')
            if layer is None:
                raise ValueError('source geometry could not be verified')
            try:
                feature = layer.GetNextFeature()
                if (feature is None or feature.GetField('valid') != 1
                        or feature.GetField('empty') != 0 or layer.GetNextFeature() is not None):
                    raise ValueError('source geometry is empty, invalid, or could not be verified')
            finally:
                feature = None
                dataset.ReleaseResultSet(layer)


def rasterize_source(feature_path, raster_path, bounds, width, height):
    # Preserve the CLI's coordinate precision and separate update-mode burn.
    options = ['-q', '-burn', '1', '-init', '0', '-ot', 'Byte', '-of', 'ENVI',
               '-te', *bounds, '-ts', str(width), str(height), '-a_srs', 'EPSG:4326']
    with gdal.ExceptionMgr():
        with gdal.Rasterize(str(raster_path), str(feature_path), options=options):
            pass
        with gdal.Open(str(raster_path), gdal.GA_Update) as raster:
            if gdal.Rasterize(raster, str(feature_path), options=['-q', '-burn', '1']) != 1:
                raise ValueError('source geometry rasterization failed')


def selected_basin(snapshot, decision_id):
    basin = find_basin(snapshot, decision_id)
    method = basin.get('assignment_method')
    codes = participant_water_codes(snapshot, basin)
    if method == 'single_continent_named_basin':
        if len(codes) != 1: raise ValueError('direct basin must have one participant')
        selection = codes[0]
    elif method == 'shared_nearest_assigned_shore':
        selection = shared.selected_rules(snapshot, basin)
    else:
        raise ValueError('unsupported basin assignment method')
    if not basin.get('source_feature_id') or not basin.get('geometry_sha256'):
        raise ValueError('basin feature and canonical geometry hashes are required')
    return basin, find_source(snapshot, basin), selection


def coordinate_pairs(coordinates):
    if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2 and all(isinstance(n, (int, float)) for n in coordinates[:2]):
        lon, lat = coordinates[:2]
        # SeaVoX/OGR serialization can overshoot the antimeridian by a few
        # floating-point ulps. Clamp only a sub-nanodegree overshoot for
        # computing grid bounds; source geometry bytes passed to GDAL remain
        # exactly as pinned. Larger or non-finite coordinates still fail.
        eps = 1e-10
        if not (math.isfinite(lon) and math.isfinite(lat) and -180-eps <= lon <= 180+eps and -90-eps <= lat <= 90+eps):
            raise ValueError('invalid longitude or latitude')
        yield max(-180.0, min(180.0, lon)), max(-90.0, min(90.0, lat))
    elif isinstance(coordinates, (list, tuple)):
        for child in coordinates:
            yield from coordinate_pairs(child)
    else:
        raise ValueError('invalid geometry coordinates')


def grid_bounds(feature):
    coords = list(coordinate_pairs(feature['geometry']['coordinates']))
    if not coords:
        raise ValueError('empty source geometry')
    minlon = min(lon for lon, _ in coords); maxlon = max(lon for lon, _ in coords)
    minlat = min(lat for _, lat in coords); maxlat = max(lat for _, lat in coords)
    x0 = max(0, math.floor((minlon + 180) / STEP))
    x1 = min(W, math.ceil((maxlon + 180) / STEP))
    y0 = max(0, math.floor((90 - maxlat) / STEP))
    y1 = min(H, math.ceil((90 - minlat) / STEP))
    if not (x0 < x1 and y0 < y1):
        raise ValueError('invalid source bounds')
    return x0, x1, y0, y1


def contiguous_spans(selected, x_offset=0):
    indices = np.flatnonzero(selected)
    if not len(indices):
        return []
    groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
    return [(int(g[0]) + x_offset, int(g[-1]) + x_offset + 1) for g in groups]



def source_water_spans(mask, x_offset, ends, values):
    """Intersect selected source cells with physical water without scanning RLE for empty cells."""
    selected = np.flatnonzero(mask)
    if not len(selected): return []
    selected = selected[values[np.searchsorted(ends, selected+x_offset, side='right')] == 1]
    if not len(selected): return []
    cuts = np.r_[0, np.flatnonzero(np.diff(selected)>1)+1, len(selected)]
    return [(int(selected[a])+x_offset, int(selected[b-1])+x_offset+1)
            for a,b in zip(cuts[:-1], cuts[1:])]

def main(argv=None, *, emit=print, shared_inputs=None):
    processing_started=time.perf_counter()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input-root', type=Path, required=True)
    ap.add_argument('--geometry', type=Path, required=True); ap.add_argument('--decision-id', required=True)
    ap.add_argument('--archive', type=Path); ap.add_argument('--extraction-manifest', type=Path)
    ap.add_argument('--extraction-manifest-sha256')
    ap.add_argument('--policy', type=Path, required=True); ap.add_argument('--policy-sha256', required=True)
    ap.add_argument('--rows', type=Path, required=True); ap.add_argument('--rows-sha256', required=True)
    ap.add_argument('--runs', type=Path, required=True); ap.add_argument('--runs-sha256', required=True)
    ap.add_argument('--land-rows', type=Path); ap.add_argument('--land-rows-sha256')
    ap.add_argument('--land-runs', type=Path); ap.add_argument('--land-runs-sha256')
    ap.add_argument('--shore-pad-degrees', type=float, default=8.0)
    engine = ap.add_mutually_exclusive_group()
    engine.add_argument('--research-interval', action='store_true', help='reference engine: use exact row certificates rather than two-dimensional rectangles')
    engine.add_argument('--research-rectangles', action='store_true', help='compatibility option: exact rectangle certificates are now the shared-basin default')
    engine.add_argument('--pointwise-nearest', action='store_true', help='reference engine: classify every shared-basin water center independently')
    ap.add_argument('--research-shore-method', choices=['wgs84-coastal-4neighbor-center-v2'],
                    help='draft research only: use the WGS84 ellipsoidal four-neighbor coastal land-cell-center method')
    ap.add_argument('--allow-draft-snapshot', action='store_true', help='research only: allow a correctly labeled draft decision and entity revision')
    ap.add_argument('--allow-unverified-snapshot', action='store_true', help='test only: Neon acceptance cannot yet be authenticated by this tool')
    ap.add_argument('--out', type=Path, required=True, help='fresh output directory that does not contain inputs')
    args = ap.parse_args(argv)
    builder_code_sha = digest(Path(__file__))
    shared_code_sha = digest(Path(shared.__file__))
    interval_code_sha = digest(Path(interval_nearest.__file__))
    helpers = {'exclusive_outputs':exclusive_outputs,'decision_snapshot':decision_snapshot,'seavox_properties':seavox_properties}
    if not args.allow_unverified_snapshot:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    root = args.input_root.resolve(); out = args.out.resolve()
    geometry, rows_path, runs_path, policy_path = args.geometry.resolve(), args.rows.resolve(), args.runs.resolve(), args.policy.resolve()
    extraction_args = (args.archive, args.extraction_manifest, args.extraction_manifest_sha256)
    if any(extraction_args) and not all(extraction_args):
        raise ValueError('archive, extraction manifest and its hash must be provided together')
    archive = args.archive.resolve() if args.archive else None
    extraction_path = args.extraction_manifest.resolve() if args.extraction_manifest else None
    land_args = (args.land_rows, args.land_rows_sha256, args.land_runs, args.land_runs_sha256)
    if any(land_args) and not all(land_args): raise ValueError('all land paths and hashes must be supplied together')
    land_rows_path = args.land_rows.resolve() if args.land_rows else None
    land_runs_path = args.land_runs.resolve() if args.land_runs else None
    input_paths = [geometry, rows_path, runs_path, policy_path] + ([archive, extraction_path] if archive else []) + ([land_rows_path, land_runs_path] if land_rows_path else [])
    if not root.is_dir() or any(not p.is_relative_to(root) for p in input_paths):
        raise ValueError('all inputs must be inside an existing input root')
    out=validate_fresh_output(root,args.out,tuple(input_paths))
    snapshot = read_snapshot(policy_path, args.policy_sha256, allow_draft=args.allow_draft_snapshot)
    basin, source, selection = selected_basin(snapshot, args.decision_id)
    is_shared = basin['assignment_method'] == 'shared_nearest_assigned_shore'
    if (args.research_interval or args.research_rectangles) and not is_shared: raise ValueError('interval research mode requires a shared basin')
    use_interval = is_shared and not args.pointwise_nearest
    use_rectangles = use_interval and not args.research_interval
    if use_rectangles: helpers['rectangle_nearest'] = rectangle_nearest
    helper_code_shas = {name:digest(Path(module.__file__)) for name,module in helpers.items()} if use_interval else {}
    interval_software = {'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                         'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str} if use_interval else None
    if is_shared and not land_rows_path: raise ValueError('shared basin requires pinned final-land RLEs')
    if is_shared and (not args.allow_draft_snapshot or snapshot['decision_revision']['status'] != 'draft'
                      or args.research_shore_method != 'wgs84-coastal-4neighbor-center-v2'):
        raise ValueError('shared shoreline distance method is not a versioned decision; explicit draft research method is required')
    if archive:
        extraction = validate_extraction(extraction_path, args.extraction_manifest_sha256, archive, geometry, snapshot, basin, source, args.policy_sha256)
        feature_sha = extraction['feature_file_sha256']
    else:
        feature_sha = source['sha256']  # The selected source itself is GeoJSON.
    feature = validate_source(geometry, feature_sha, basin['geometry_sha256'], basin['source_feature_id'])
    decision_revision = snapshot['decision_revision']['id']; entity_revision = snapshot['decision_revision']['entity_revision']
    member_id = str(basin['id'])
    if shared_inputs is None:
        if digest(rows_path) != args.rows_sha256 or digest(runs_path) != args.runs_sha256:
            raise ValueError('physical grid hash mismatch')
        rows = np.memmap(rows_path, dtype='<u4', mode='r'); runs = np.memmap(runs_path, dtype='<u4', mode='r')
    else:
        from verified_water_inputs import VerifiedWaterInputs
        if not isinstance(shared_inputs, VerifiedWaterInputs):
            raise TypeError('a verified shared water input context is required')
        rows, runs = shared_inputs.grid('physical', rows_path, args.rows_sha256,
                                       runs_path, args.runs_sha256, W, H)
        if land_rows_path is not None:
            shared_land = shared_inputs.grid('land', land_rows_path, args.land_rows_sha256,
                                            land_runs_path, args.land_runs_sha256, W, H)
    if len(rows) != H+1 or len(runs)%2 or int(rows[0]) != 0 or int(rows[-1]) != len(runs)//2 or np.any(rows[1:] <= rows[:-1]):
        raise ValueError('invalid physical RLE offsets')
    x0, x1, y0, y1 = grid_bounds(feature)
    if is_shared:
        if shared_inputs is None:
            if digest(land_rows_path) != args.land_rows_sha256 or digest(land_runs_path) != args.land_runs_sha256:
                raise ValueError('land grid hash mismatch')
            lr = np.memmap(land_rows_path, dtype='<u4', mode='r'); lu = np.memmap(land_runs_path, dtype='<u4', mode='r')
        else:
            lr, lu = shared_land
        if len(lr) != H+1 or len(lu)%2 or int(lr[0]) != 0 or int(lr[-1]) != len(lu)//2 or np.any(lr[1:] <= lr[:-1]):
            raise ValueError('invalid land RLE offsets')
        pairs, tolerance = selection
        import wrapped_bounds, streamed_shore_fallback
        wrapped_code_sha = digest(Path(wrapped_bounds.__file__))
        fallback_code_sha = digest(Path(streamed_shore_fallback.__file__))
        full_shore_bounds = shared.crop_bounds((x0,x1,y0,y1), W, H, STEP, args.shore_pad_degrees)
        wrapped_source, windows = wrapped_bounds.wrapped_grid_bounds(feature,W,H,STEP)
        shore_bounds = (shared.crop_bounds(wrapped_source,W,H,STEP,args.shore_pad_degrees)
                        if len(windows)==2 and wrapped_source[1]-wrapped_source[0] < x1-x0 else full_shore_bounds)
    create_directory_exclusive(out)
    feature_path = out/'source.geojson'; raster_path = out/'source-mask.dat'
    with create_text_exclusive(feature_path) as f:
        json.dump({'type':'FeatureCollection','features':[feature]}, f, separators=(',', ':'))
    validate_geometry_ogr(feature_path)
    bounds = [format(-180+x0*STEP, '.15g'), format(90-y1*STEP, '.15g'),
              format(-180+x1*STEP, '.15g'), format(90-y0*STEP, '.15g')]
    rasterize_source(feature_path, raster_path, bounds, x1-x0, y1-y0)
    raster = np.memmap(raster_path, dtype='u1', mode='r', shape=(y1-y0,x1-x0))
    if is_shared:
        try:
            edges = (shared.centers_for_crop((rows,runs), (lr,lu), shore_bounds, W, H, STEP, [p[1] for p in pairs])
                     if shared_inputs is None else shared_inputs.shore_index.centers_for_crop(shore_bounds, STEP, [p[1] for p in pairs]))
            if shore_bounds!=full_shore_bounds:
                edges=wrapped_bounds.baseline_shore_order(edges,full_shore_bounds,W,STEP)
            indexes = shared.make_indexes(edges, pairs)
        except ValueError as exc:
            if shore_bounds==full_shore_bounds or not (str(exc)=='no participant shorelines in crop' or str(exc).startswith('crop has no shoreline for participant land code ')):
                raise
            edges={'mids':[]};indexes={}
        def full_blocks(code):
            return wrapped_bounds.shore_blocks(shared,(rows,runs),(lr,lu),full_shore_bounds,W,H,STEP,code)
        classifier=wrapped_bounds.StreamedWrappedClassifier(shared.classify,streamed_shore_fallback.classify_one,shore_bounds,full_shore_bounds,W,H,STEP,pairs,tolerance,indexes,full_blocks)
    assignment = out/'basin-assignment.jsonl.gz'; cells = spans_count = row_count = 0
    certified = exact = interval_certified = exact_interval_probes = exact_rectangle_probes = interval_leaf_cells = 0
    with create_gzip_text_exclusive(assignment, encoding='utf8') as stream:
        for y in range(y0, y1):
            a, b = int(rows[y]), int(rows[y+1]); ends = runs[2*a:2*b:2]; values = runs[2*a+1:2*b:2]
            if not len(ends) or int(ends[0]) == 0 or int(ends[-1]) != W or np.any(ends[1:] <= ends[:-1]) or np.any(~np.isin(values,[1,17])):
                raise ValueError(f'invalid physical grid row {y}')
            if is_shared and use_rectangles:
                if (y-y0)%64 == 0:
                    selected_rows = {}
                    for yy in range(y, min(y+64, y1)):
                        ff,ll = int(rows[yy]),int(rows[yy+1]); ee=runs[2*ff:2*ll:2]; vv=runs[2*ff+1:2*ll:2]
                        if not len(ee) or int(ee[0])<=0 or int(ee[-1])!=W or np.any(ee[1:]<=ee[:-1]) or np.any(~np.isin(vv,[1,17])):
                            raise ValueError(f'invalid physical grid row {yy}')
                        selected_rows[yy] = source_water_spans(raster[yy-y0], x0, ee, vv)
                    rectangle_rows, stats = rectangle_nearest.classify_rows(
                        selected_rows, windows, shore_bounds, W, H, STEP, pairs,
                        tolerance, indexes, classifier.classify)
                    certified += stats['bounded_cells']; exact += stats['exact_cells']
                    interval_certified += stats['certified_cells']; interval_leaf_cells += stats['leaf_cells']
                    exact_rectangle_probes += stats['exact_rectangle_probes']
                intervals = selected_rows[y]
            elif is_shared and use_interval:
                intervals = source_water_spans(raster[y-y0], x0, ends, values)
            else:
                x = np.arange(x0,x1,dtype='u4')
                chosen = (raster[y-y0] != 0) & (values[np.searchsorted(ends,x,side='right')] == 1)
                intervals = contiguous_spans(chosen, x0)
            if not intervals:
                continue
            if is_shared and use_rectangles:
                records = [{'start':a,'end':b,'code':code,
                            'rule_id':'research-named-basin-nearest-final-center-v2',
                            'member_id':member_id} for a,b,code in rectangle_rows[y]]
            elif is_shared and use_interval:
                assigned, stats = interval_nearest.classify_row(
                    y, intervals, shore_bounds, W, H, STEP, pairs, tolerance, indexes,
                    point_classifier=classifier.classify)
                certified += stats['bounded_cells']; exact += stats['exact_cells']
                interval_certified += stats['certified_cells']
                exact_interval_probes += stats['exact_interval_probes']
                interval_leaf_cells += stats['leaf_cells']
                records = [{'start':a,'end':b,'code':code,
                            'rule_id':'research-named-basin-nearest-final-center-v2',
                            'member_id':member_id} for a,b,code in assigned]
            elif is_shared:
                records = []
                for a,b in intervals:
                    for start in range(a,b,5000):
                        end=min(start+5000,b); xs=np.arange(start,end,dtype=np.float64)
                        lat=np.full(len(xs),90-(y+.5)*STEP); lon=-180+(xs+.5)*STEP
                        codes, ncert, nexact=classifier.classify(lat,lon)
                        certified+=ncert; exact+=nexact
                        cuts=np.r_[0,np.flatnonzero(np.diff(codes)!=0)+1,len(codes)]
                        for i,j in zip(cuts[:-1],cuts[1:]):
                            q={'start':start+int(i),'end':start+int(j),'code':int(codes[i]),
                               'rule_id':'research-named-basin-nearest-final-center-v2','member_id':member_id}
                            if records and records[-1]['end']==q['start'] and records[-1]['code']==q['code']:
                                records[-1]['end']=q['end']
                            else: records.append(q)
            else:
                records = [{'start':a,'end':b,'code':selection,
                            'rule_id':'research-named-basin-direct-continent-v1',
                            'member_id':member_id} for a,b in intervals]
            stream.write(json.dumps({'row':y,'spans':records},separators=(',', ':'))+'\n')
            cells += sum(b-a for a,b in intervals); spans_count += len(records); row_count += 1
    if is_shared and (certified+exact != cells or interval_certified+classifier.narrow_cells+classifier.fallback_cells != cells):
        raise ValueError('shared basin classification accounting mismatch')
    # A run that observed changing inputs is not a usable result.
    checked_paths = [(policy_path,args.policy_sha256),(geometry,feature_sha)]
    if shared_inputs is None:
        checked_paths.extend(((rows_path,args.rows_sha256),(runs_path,args.runs_sha256)))
    for path, expected in checked_paths:
        if digest(path) != expected: raise ValueError(f'input changed during run: {path}')
    if archive and (digest(archive) != source['sha256'] or digest(extraction_path) != args.extraction_manifest_sha256):
        raise ValueError('archive or extraction manifest changed during run')
    if shared_inputs is None and is_shared and (digest(land_rows_path) != args.land_rows_sha256 or digest(land_runs_path) != args.land_runs_sha256):
        raise ValueError('land input changed during run')
    if (digest(Path(__file__))!=builder_code_sha or digest(Path(shared.__file__))!=shared_code_sha
            or digest(Path(interval_nearest.__file__))!=interval_code_sha):
        raise ValueError('builder or classifier code changed during run')
    if any(digest(Path(helpers[name].__file__)) != pin for name,pin in helper_code_shas.items()):
        raise ValueError('interval builder helper code changed during run')
    if is_shared and (digest(Path(wrapped_bounds.__file__))!=wrapped_code_sha or digest(Path(streamed_shore_fallback.__file__))!=fallback_code_sha):
        raise ValueError('wrapped classifier code changed during run')
    gdal_version = gdal.VersionInfo('--version')
    manifest = {'schema':'worldatlas-full-water-assignment-tiles-v1', 'status':'completed_unverified_candidate_not_published',
                'grid':{'width':W,'height':H,'angular_step_deg':STEP,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
                'coverage':{'complete':True,'meaning':'all physical-water centers inside the selected SeaVoX polygon',
                            'verification':'generator assertion; independent completeness and geometry semantics not yet verified'},
                'source':{'decision_id':args.decision_id,'assignment_method':basin['assignment_method'],'source_id':basin['source_id'],'source_version':basin['source_version'],'source_feature_id':str(basin['source_feature_id']),'source_file_sha256':source['sha256'],'extraction_manifest_sha256':args.extraction_manifest_sha256,
                          'extracted_feature_sha256':feature_sha,'canonical_geometry_sha256':basin['geometry_sha256'],
                          'physical_rows_sha256':args.rows_sha256,'physical_runs_sha256':args.runs_sha256,
                          'land_rows_sha256':args.land_rows_sha256,'land_runs_sha256':args.land_runs_sha256,
                          'tie_rules':basin.get('tie_rules') if is_shared else None, 'policy_sha256':args.policy_sha256,'decision_revision':decision_revision,'entity_revision':entity_revision,
                          'decision_status':snapshot['decision_revision']['status']},
                'physical_water_cells':cells,'span_count':spans_count,'row_count':row_count,
                'rasterization':{'source_mask_sha256':digest(raster_path),'gdal_version':gdal_version,
                                 'method':'GDAL polygon center raster, ENVI create and update burn',
                                 'geometry_validity':'OGR/GEOS ST_IsValid and ST_IsEmpty checked',
                                 'bounds_columns_rows':[x0,x1,y0,y1]},
                'algorithm_sha256':builder_code_sha,
                'nearest_assignment_audit': {'shore_method':(('wgs84-wrapped-center-interval-v1 (research, not an approved decision)' if shore_bounds!=full_shore_bounds else 'wgs84-coastal-center-interval-v1 (research, not an approved decision)') if use_interval else ('wgs84-wrapped-certified-with-streamed-full-fallback-v1 (research, not an approved decision)' if shore_bounds!=full_shore_bounds else 'wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)')), 'shore_crop':shore_bounds,'coastal_center_count':len(edges['mids']),'coastal_center_count_scope':'indexed-shore-crop',
                    **({'full_shore_crop':full_shore_bounds,'full_streamed_shore_count':'not-precomputed','index_optimization':'certified-wrapped-crop-with-streamed-full-shore-fallback','shore_order':'original-full-crop-row-column-order','wrapped_narrow_cells':classifier.narrow_cells,'wrapped_fallback_cells':classifier.fallback_cells,'wrapped_bounds_sha256':wrapped_code_sha,'streamed_fallback_sha256':fallback_code_sha} if shore_bounds!=full_shore_bounds else {}),
                    **({'execution_method':('wgs84-center-rectangle-v1' if use_rectangles else 'wgs84-center-row-interval-v1'),'interval_certified_cells':interval_certified,'exact_interval_probe_count':exact_interval_probes,'interval_leaf_cells':interval_leaf_cells,'interval_nearest_sha256':interval_code_sha,**({'rectangle_nearest_sha256':helper_code_shas['rectangle_nearest'],'exact_rectangle_probe_count':exact_rectangle_probes} if use_rectangles else {}),'helper_code_sha256':helper_code_shas,'software':interval_software} if use_interval else {}),
                    'certified_bound_cells':certified,'exact_distance_cells':exact,
                    'shared_nearest_sha256':shared_code_sha,
                    'shore_geometry_sha256':shared_code_sha} if is_shared else None,
                'tiles':[{'core_rows':[0,H],'core_cols':[0,W],'span_file':{'path':assignment.name,'sha256':digest(assignment)}}]}
    if shared_inputs is not None:
        manifest['shared_input_generation'] = shared_inputs.provenance()
    manifest['processing_elapsed_seconds']=time.perf_counter()-processing_started
    write_json_exclusive(out/'manifest.json', manifest, indent=2)
    emit(json.dumps({'cells':cells,'spans':spans_count,'rows':row_count,'assignment_sha256':digest(assignment)}))


if __name__ == '__main__':
    main()
