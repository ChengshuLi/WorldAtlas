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
    features = [f for f in features if str(f.get('properties', {}).get('mrgid_sr')) == str(feature_id)]
    if len(features) != 1:
        raise ValueError('expected exactly one selected SeaVoX feature')
    feature = features[0]
    geom = feature.get('geometry')
    if not isinstance(geom, dict) or geom.get('type') not in ('Polygon', 'MultiPolygon'):
        raise ValueError('invalid Gulf source geometry')
    actual = hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if actual != geometry_sha:
        raise ValueError('canonical geometry hash mismatch')
    return feature



def selected_basin(snapshot, decision_id):
    basin = find_basin(snapshot, decision_id)
    if basin.get('assignment_method') != 'single_continent_named_basin':
        raise ValueError('this stage supports only direct single-participant basin decisions')
    codes = participant_water_codes(snapshot, basin)
    if len(codes) != 1:
        raise ValueError('direct basin must have one participant')
    if not basin.get('source_feature_id') or not basin.get('geometry_sha256'):
        raise ValueError('basin feature and canonical geometry hashes are required')
    return basin, find_source(snapshot, basin), codes[0]


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
    ap.add_argument('--policy', type=Path, required=True); ap.add_argument('--policy-sha256', required=True)
    ap.add_argument('--rows', type=Path, required=True); ap.add_argument('--rows-sha256', required=True)
    ap.add_argument('--runs', type=Path, required=True); ap.add_argument('--runs-sha256', required=True)
    ap.add_argument('--allow-unverified-snapshot', action='store_true', help='test only: Neon acceptance cannot yet be authenticated by this tool')
    ap.add_argument('--out', type=Path, required=True, help='new output directory outside input root')
    args = ap.parse_args()
    if not args.allow_unverified_snapshot:
        raise ValueError('authenticated Neon revision verification is not implemented; explicit test-only flag required')
    root = args.input_root.resolve(); out = args.out.resolve()
    geometry, rows_path, runs_path, policy_path = args.geometry.resolve(), args.rows.resolve(), args.runs.resolve(), args.policy.resolve()
    if not root.is_dir() or any(not p.is_relative_to(root) for p in (geometry, rows_path, runs_path, policy_path)):
        raise ValueError('all inputs must be inside an existing input root')
    if out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError('output must be outside input root')
    snapshot = read_snapshot(policy_path, args.policy_sha256)
    basin, source, water_code = selected_basin(snapshot, args.decision_id)
    feature = validate_source(geometry, source['sha256'], basin['geometry_sha256'], basin['source_feature_id'])
    decision_revision = snapshot['decision_revision']['id']; entity_revision = snapshot['decision_revision']['entity_revision']
    member_id = str(basin['id'])
    if digest(rows_path) != args.rows_sha256 or digest(runs_path) != args.runs_sha256:
        raise ValueError('physical grid hash mismatch')
    rows = np.memmap(rows_path, dtype='<u4', mode='r'); runs = np.memmap(runs_path, dtype='<u4', mode='r')
    if len(rows) != H+1 or len(runs)%2 or int(rows[0]) != 0 or int(rows[-1]) != len(runs)//2 or np.any(rows[1:] <= rows[:-1]):
        raise ValueError('invalid physical RLE offsets')
    x0, x1, y0, y1 = grid_bounds(feature)
    create_directory_exclusive(out)
    feature_path = out/'source.geojson'; raster_path = out/'source-mask.dat'
    with create_text_exclusive(feature_path) as f:
        json.dump({'type':'FeatureCollection','features':[feature]}, f, separators=(',', ':'))
    bounds = [format(-180+x0*STEP, '.15g'), format(90-y1*STEP, '.15g'),
              format(-180+x1*STEP, '.15g'), format(90-y0*STEP, '.15g')]
    cmd = ['gdal_rasterize','-q','-burn','1','-init','0','-ot','Byte','-of','ENVI',
           '-te',*bounds,'-ts',str(x1-x0),str(y1-y0),'-a_srs','EPSG:4326',str(feature_path),str(raster_path)]
    subprocess.run(cmd, check=True)
    raster = np.memmap(raster_path, dtype='u1', mode='r', shape=(y1-y0,x1-x0))
    assignment = out/'basin-assignment.jsonl.gz'; cells = spans_count = row_count = 0
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
            records = [{'start':a,'end':b,'code':water_code,'rule_id':'approved-named-basin-direct-continent-v1','member_id':member_id} for a,b in intervals]
            stream.write(json.dumps({'row':y,'spans':records},separators=(',', ':'))+'\n')
            cells += sum(b-a for a,b in intervals); spans_count += len(intervals); row_count += 1
    manifest = {'schema':'worldatlas-full-water-assignment-tiles-v1', 'status':'completed_unverified_candidate_not_published',
                'grid':{'width':W,'height':H,'angular_step_deg':STEP,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
                'coverage':{'complete':True,'meaning':'all physical-water centers inside the selected SeaVoX Gulf polygon'},
                'source':{'decision_id':args.decision_id,'assignment_method':basin['assignment_method'],'source_id':basin['source_id'],'source_version':basin['source_version'],'source_feature_id':str(basin['source_feature_id']),'source_file_sha256':source['sha256'],'canonical_geometry_sha256':basin['geometry_sha256'],
                          'physical_rows_sha256':args.rows_sha256,'physical_runs_sha256':args.runs_sha256,'policy_sha256':args.policy_sha256,'decision_revision':decision_revision,'entity_revision':entity_revision},
                'physical_water_cells':cells,'span_count':spans_count,'row_count':row_count,
                'tiles':[{'core_rows':[0,H],'core_cols':[0,W],'span_file':{'path':assignment.name,'sha256':digest(assignment)}}]}
    write_json_exclusive(out/'manifest.json', manifest, indent=2)
    print(json.dumps({'cells':cells,'spans':spans_count,'rows':row_count,'assignment_sha256':digest(assignment)}))


if __name__ == '__main__':
    main()
