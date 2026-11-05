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
from pathlib import Path
import subprocess
import sys

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, write_json_exclusive
from decision_snapshot import read_snapshot, participant_water_codes, find_basin, find_source
from seavox_properties import feature_id as read_feature_id
import shared_nearest as shared

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
    result = subprocess.run(['ogrinfo','-ro','-json','-features','-dialect','sqlite','-sql',
        'SELECT ST_IsValid(geometry) AS valid, ST_IsEmpty(geometry) AS empty FROM source',str(path)],
        check=True,capture_output=True,text=True)
    doc=json.loads(result.stdout); layers=doc.get('layers',[])
    features=layers[0].get('features',[]) if len(layers)==1 else []
    if len(features)!=1 or features[0].get('properties')!={'valid':1,'empty':0}:
        raise ValueError('source geometry is empty, invalid, or could not be verified')


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
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('invalid longitude or latitude')
        yield lon, lat
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


def main():
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
    ap.add_argument('--research-shore-method', choices=['wgs84-coastal-4neighbor-center-v2'],
                    help='draft research only: use the WGS84 ellipsoidal four-neighbor coastal land-cell-center method')
    ap.add_argument('--allow-draft-snapshot', action='store_true', help='research only: allow a correctly labeled draft decision and entity revision')
    ap.add_argument('--allow-unverified-snapshot', action='store_true', help='test only: Neon acceptance cannot yet be authenticated by this tool')
    ap.add_argument('--out', type=Path, required=True, help='new output directory outside input root')
    args = ap.parse_args()
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
    if out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('output must be outside input root')
    snapshot = read_snapshot(policy_path, args.policy_sha256, allow_draft=args.allow_draft_snapshot)
    basin, source, selection = selected_basin(snapshot, args.decision_id)
    is_shared = basin['assignment_method'] == 'shared_nearest_assigned_shore'
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
    if digest(rows_path) != args.rows_sha256 or digest(runs_path) != args.runs_sha256:
        raise ValueError('physical grid hash mismatch')
    rows = np.memmap(rows_path, dtype='<u4', mode='r'); runs = np.memmap(runs_path, dtype='<u4', mode='r')
    if len(rows) != H+1 or len(runs)%2 or int(rows[0]) != 0 or int(rows[-1]) != len(runs)//2 or np.any(rows[1:] <= rows[:-1]):
        raise ValueError('invalid physical RLE offsets')
    x0, x1, y0, y1 = grid_bounds(feature)
    if is_shared:
        if digest(land_rows_path) != args.land_rows_sha256 or digest(land_runs_path) != args.land_runs_sha256:
            raise ValueError('land grid hash mismatch')
        lr = np.memmap(land_rows_path, dtype='<u4', mode='r'); lu = np.memmap(land_runs_path, dtype='<u4', mode='r')
        if len(lr) != H+1 or len(lu)%2 or int(lr[0]) != 0 or int(lr[-1]) != len(lu)//2 or np.any(lr[1:] <= lr[:-1]):
            raise ValueError('invalid land RLE offsets')
        pairs, tolerance = selection
        shore_bounds = shared.crop_bounds((x0,x1,y0,y1), W, H, STEP, args.shore_pad_degrees)
        edges = shared.centers_for_crop((rows,runs), (lr,lu), shore_bounds, W, H, STEP, [p[1] for p in pairs])
        indexes = shared.make_indexes(edges, pairs)
    create_directory_exclusive(out)
    feature_path = out/'source.geojson'; raster_path = out/'source-mask.dat'
    with create_text_exclusive(feature_path) as f:
        json.dump({'type':'FeatureCollection','features':[feature]}, f, separators=(',', ':'))
    validate_geometry_ogr(feature_path)
    bounds = [format(-180+x0*STEP, '.15g'), format(90-y1*STEP, '.15g'),
              format(-180+x1*STEP, '.15g'), format(90-y0*STEP, '.15g')]
    cmd = ['gdal_rasterize','-q','-burn','1','-init','0','-ot','Byte','-of','ENVI',
           '-te',*bounds,'-ts',str(x1-x0),str(y1-y0),'-a_srs','EPSG:4326',str(feature_path),str(raster_path)]
    subprocess.run(cmd, check=True)
    # ENVI creation with -init can silently leave tiny rasters all zero on
    # some GDAL builds. A separate update-mode burn is idempotent and tested.
    subprocess.run(['gdal_rasterize','-q','-burn','1',str(feature_path),str(raster_path)], check=True)
    raster = np.memmap(raster_path, dtype='u1', mode='r', shape=(y1-y0,x1-x0))
    assignment = out/'basin-assignment.jsonl.gz'; cells = spans_count = row_count = 0
    certified = exact = 0
    with create_gzip_text_exclusive(assignment, encoding='utf8') as stream:
        for y in range(y0, y1):
            a, b = int(rows[y]), int(rows[y+1]); ends = runs[2*a:2*b:2]; values = runs[2*a+1:2*b:2]
            if not len(ends) or int(ends[0]) == 0 or int(ends[-1]) != W or np.any(ends[1:] <= ends[:-1]) or np.any(~np.isin(values,[1,17])):
                raise ValueError(f'invalid physical grid row {y}')
            x = np.arange(x0,x1,dtype='u4')
            chosen = (raster[y-y0] != 0) & (values[np.searchsorted(ends,x,side='right')] == 1)
            intervals = contiguous_spans(chosen, x0)
            if not intervals:
                continue
            records = []
            for a,b in intervals:
                if not is_shared:
                    records.append({'start':a,'end':b,'code':selection,'rule_id':'research-named-basin-direct-continent-v1','member_id':member_id})
                    continue
                # Bound memory even for a long source span.
                for start in range(a,b,5000):
                    end=min(start+5000,b); xs=np.arange(start,end,dtype=np.float64)
                    lat=np.full(len(xs),90-(y+.5)*STEP); lon=-180+(xs+.5)*STEP
                    codes, ncert, nexact=shared.classify(lat,lon,shore_bounds,W,H,STEP,pairs,tolerance,indexes)
                    certified+=ncert; exact+=nexact
                    cuts=np.r_[0,np.flatnonzero(np.diff(codes)!=0)+1,len(codes)]
                    for i,j in zip(cuts[:-1],cuts[1:]):
                        q={'start':start+int(i),'end':start+int(j),'code':int(codes[i]),
                           'rule_id':'research-named-basin-nearest-final-center-v2','member_id':member_id}
                        if records and records[-1]['end']==q['start'] and records[-1]['code']==q['code']:
                            records[-1]['end']=q['end']
                        else: records.append(q)
            stream.write(json.dumps({'row':y,'spans':records},separators=(',', ':'))+'\n')
            cells += sum(b-a for a,b in intervals); spans_count += len(records); row_count += 1
    # A run that observed changing inputs is not a usable result.
    for path, expected in ((policy_path,args.policy_sha256),(geometry,feature_sha),
                           (rows_path,args.rows_sha256),(runs_path,args.runs_sha256)):
        if digest(path) != expected: raise ValueError(f'input changed during run: {path}')
    if archive and (digest(archive) != source['sha256'] or digest(extraction_path) != args.extraction_manifest_sha256):
        raise ValueError('archive or extraction manifest changed during run')
    if is_shared and (digest(land_rows_path) != args.land_rows_sha256 or digest(land_runs_path) != args.land_runs_sha256):
        raise ValueError('land input changed during run')
    gdal_version = subprocess.run(['gdal_rasterize','--version'],check=True,capture_output=True,text=True).stdout.strip()
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
                'algorithm_sha256':digest(Path(__file__)),
                'nearest_assignment_audit': {'shore_method':'wgs84-coastal-4neighbor-center-v2 (research, not an approved decision)', 'shore_crop':shore_bounds,'coastal_center_count':len(edges['mids']),
                    'certified_bound_cells':certified,'exact_distance_cells':exact,
                    'shared_nearest_sha256':digest(Path(shared.__file__)),
                    'shore_geometry_sha256':digest(Path(shared.__file__))} if is_shared else None,
                'tiles':[{'core_rows':[0,H],'core_cols':[0,W],'span_file':{'path':assignment.name,'sha256':digest(assignment)}}]}
    write_json_exclusive(out/'manifest.json', manifest, indent=2)
    print(json.dumps({'cells':cells,'spans':spans_count,'rows':row_count,'assignment_sha256':digest(assignment)}))


if __name__ == '__main__':
    main()
