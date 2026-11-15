#!/usr/bin/env python3
"""Fill residual water from source-backed barriers and registry-bound ocean seeds."""

from __future__ import annotations
import hashlib, json, math, re, struct, time
from pathlib import Path
from worldatlas.map_build.water.ocean.partition_core import rasterize_barriers, floodfill_run_graph
from worldatlas.map_build.water.ocean.rle_inputs import RunRasterU32LE, make_prefill_adapters
from worldatlas.map_build.execution.outputs import (
    create_directory_exclusive,
    create_text_exclusive,
    write_json_exclusive,
)
from worldatlas.map_build.execution import outputs

HEX = re.compile(r'^[0-9a-f]{64}$')
RULE = 'fresh-ocean-seed-floodfill-v1'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def unique_by(rows, key):
    if not isinstance(rows, list):
        raise ValueError(f'{key}: expected list')
    result = {}
    for row in rows:
        ident = row.get(key)
        if not isinstance(ident, str) or not ident or ident in result:
            raise ValueError(f'duplicate or invalid {key}')
        result[ident] = row
    return result


def num(x):
    if isinstance(x, bool) or not isinstance(x, (str, int, float)):
        raise ValueError('invalid coordinate')
    n = float(x)
    if not math.isfinite(n):
        raise ValueError('invalid coordinate')
    return n


def load_config(snapshot, width, height):
    """Rasterize imported divider geometry and validate source-backed ocean witnesses."""
    from shapely.geometry import Point, shape
    from worldatlas.map_build.inputs.features import feature_geometry

    policies = [p for p in snapshot.get('policies', []) if p.get('kind') == 'ocean_fill']
    if len(policies) != 1:
        raise ValueError('one ocean_fill policy is required')
    policy = policies[0]['definition']
    if (policy.get('connectivity') != 4 or type(policy.get('wrap_longitude')) is not bool
            or policy.get('barrier_tie_rule') != 'left-of-oriented-route'
            or policy.get('unseeded_policy') != 'report-only'):
        raise ValueError('unsupported ocean-fill policy')
    features = unique_by(snapshot.get('features', []), 'feature_id')
    partitions = unique_by([p for p in snapshot.get('partitions', [])
                            if p['method'] == 'ocean_barrier'], 'id')
    seed_rows = snapshot.get('ocean_seeds', [])
    if not seed_rows:
        raise ValueError('ocean fill needs source-backed seeds')
    step = 360.0 / width
    south = 90 - height * step
    paths = []
    for record in partitions.values():
        feature = features.get(record['feature_id'])
        if feature is None:
            raise ValueError('ocean partition refers to a missing source feature')
        ll = [list(p) for p in feature_geometry(feature, ('LineString',))['coordinates']]
        if record.get('extend_to_south_grid_edge', False):
            i = 0 if ll[0][1] < ll[-1][1] else -1
            if not south <= ll[i][1] < south + step:
                raise ValueError('south-grid endpoint must lie in the final grid row')
            if any(p[0] != ll[0][0] for p in ll):
                raise ValueError('south-grid extension requires a meridian')
            ll[i][1] = south
        path = []
        for (lon0, lat0), (lon1, lat1) in zip(ll, ll[1:]):
            if (abs(lon1-lon0) > 180 or not south <= lat0 <= 90
                    or not south <= lat1 <= 90):
                raise ValueError('ocean divider leaves the supported grid')
            x0, y0 = (lon0+180)/step, (90-lat0)/step
            x1, y1 = (lon1+180)/step, (90-lat1)/step
            n = max(1, math.ceil(max(abs(x1-x0), abs(y1-y0))))
            path.extend((x0+(x1-x0)*i/n,y0+(y1-y0)*i/n) for i in range(n))
        path.append(((ll[-1][0]+180)/step,(90-ll[-1][1])/step))
        paths.append(path)
    bindings = snapshot.get('category_bindings', [])
    seeds, metadata, entities = {}, {}, set()
    for seed in seed_rows:
        entity = seed['entity_id']
        found = [b['code'] for b in bindings
                 if b['entity_id'] == entity and b['physical_class'] == 'water']
        if len(found) != 1 or type(found[0]) is not int or not 0 < found[0] < 2**32:
            raise ValueError('seed must bind uniquely to a water code')
        feature = features.get(seed['feature_id'])
        if feature is None:
            raise ValueError('ocean seed refers to a missing source area')
        area = feature_geometry(feature, ('Polygon','MultiPolygon'))
        lon, lat = map(num,seed['witness'])
        if not shape(area).contains(Point(lon,lat)):
            raise ValueError('ocean seed must be inside its selected source area')
        x,y = math.floor((lon+180)/step), math.floor((90-lat)/step)
        code = found[0]
        if not (0 <= x < width and 0 <= y < height) or code in seeds or entity in entities:
            raise ValueError('duplicate code or seed outside grid')
        seeds[code] = (x,y)
        entities.add(entity)
        metadata[code] = dict(seed_id=str(entity), entity_id=entity,
                              feature_id=seed['feature_id'],
                              nominal_longitude_deg=lon,nominal_latitude_deg=lat)
    for record in partitions.values():
        pair = {record['side_a_entity_id'],record['side_b_entity_id']}
        if len(pair) != 2 or not pair <= entities:
            raise ValueError('ocean partition must separate two seeded entities')
    return policy,paths,seeds,metadata


def export_layer(partition, out, width, height, metadata, inputs, tile_height=256):
    offsets = struct.unpack('<%dQ' % (height + 1), (partition / 'ocean_rows.u64le').read_bytes())
    tiles = []
    with (partition / 'ocean_assignment_spans.u32le').open('rb') as stream:
        for y0 in range(0, height, tile_height):
            y1 = min(height, y0 + tile_height)
            p = out / f'ocean-{y0:06d}-{y1:06d}.jsonl'
            with create_text_exclusive(p, encoding='utf8', newline='\n') as f:
                for y in range(y0, y1):
                    stream.seek(offsets[y] * 12)
                    spans = []
                    for _ in range(offsets[y + 1] - offsets[y]):
                        raw = stream.read(12)
                        if len(raw) != 12:
                            raise ValueError('truncated ocean spans')
                        a, b, code = struct.unpack('<III', raw)
                        if not (0 <= a < b <= width) or code not in metadata:
                            raise ValueError('invalid ocean output span')
                        spans.append(
                            {
                                'start': a,
                                'end': b,
                                'code': code,
                                'rule_id': RULE,
                                'member_id': metadata[code]['seed_id'],
                            }
                        )
                    f.write(json.dumps({'row': y, 'spans': spans}, separators=(',', ':')) + '\n')
            tiles.append(
                {
                    'core_rows': [y0, y1],
                    'core_cols': [0, width],
                    'span_file': {'path': p.name, 'sha256': sha(p)},
                }
            )
    manifest = {
        'schema': 'worldatlas-full-water-assignment-tiles-v1',
        'status': 'completed_unverified_candidate_not_published',
        'grid': {
            'width': width,
            'height': height,
            'angular_step_deg': 360.0 / width,
            'row_convention': 'north-to-south; cell centers; half-open [start,end) x spans',
        },
        'coverage': {
            'complete': True,
            'meaning': 'seeded residual marine components only; unseeded components require separate review',
        },
        'source': inputs,
        'tiles': tiles,
    }
    write_json_exclusive(out / 'ocean-layer-manifest.json', manifest, indent=2)
    return manifest


def run(
    snapshot,
    snapshot_hash,
    physical_rows,
    physical_runs,
    prefill_rows,
    prefill_runs,
    out,
    width,
    height,
    inputs,
    tile_height=256,
    pre_finalize=None,
    pre_summary=None,
    processing_started=None,
):
    if processing_started is None:
        processing_started = time.perf_counter()
    policy, paths, seeds, metadata = load_config(snapshot, width, height)
    if tile_height <= 0:
        raise ValueError('tile height must be positive')
    create_directory_exclusive(out)
    cuts = rasterize_barriers(paths, width, height)
    if not policy['wrap_longitude']:
        cuts.wrap.update(range(height))
    cut_path = out / 'barrier_edges.u32le'
    cuts.write_u32le(cut_path)
    here = Path(__file__).resolve().parent
    code_pins = {
        name: sha(here / name) for name in ('engine.py', 'partition_core.py', 'rle_inputs.py')
    }
    code_pins['outputs.py'] = sha(Path(outputs.__file__))
    pins = {
        **inputs,
        'decision_snapshot_sha256': snapshot_hash,
        'source_cut_edges_sha256': sha(cut_path),
        'partition_ids': [p['id'] for p in snapshot['partitions'] if p['method']=='ocean_barrier'],
        'seed_entity_ids': [s['entity_id'] for s in snapshot['ocean_seeds']],
        'candidate_code_sha256': code_pins,
    }
    with RunRasterU32LE(physical_rows, physical_runs, width, height) as physical, RunRasterU32LE(
        prefill_rows, prefill_runs, width, height
    ) as prefill:
        land_codes = {
            b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'
        }
        land_entities = {
            b['entity_id'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'
        }
        water_codes = {
            b['code']
            for b in snapshot['category_bindings']
            if b['physical_class'] == 'water' and b['entity_id'] in land_entities
        }
        eligible, classes = make_prefill_adapters(
            physical, prefill, width, height, land_codes, water_codes
        )
        part = floodfill_run_graph(
            eligible,
            width,
            height,
            cuts,
            seeds,
            out / 'partition',
            manifest_inputs=pins,
            unassigned_policy='report-only',
            classification_rows=classes,
            seed_metadata=metadata,
            required_seed_codes=set(seeds),
            class_labels={
                b['code']: str(b['entity_id']) + ' ' + b['physical_class']
                for b in snapshot['category_bindings']
            },
        )
    if pre_finalize:
        pre_finalize()
    export_layer(out / 'partition', out, width, height, metadata, pins, tile_height)
    if pre_summary:
        pre_summary()
    write_json_exclusive(
        out / 'run-summary.json',
        {
            'status': 'unverified-candidate-not-published',
            'snapshot_sha256': snapshot_hash,
            'unseeded_cell_count': part['unseeded_cell_count'],
            'assigned_cells_total': part['assigned_cells_total'],
            'barrier_sha256': pins['source_cut_edges_sha256'],
            'layer_manifest_sha256': sha(out / 'ocean-layer-manifest.json'),
            'processing_elapsed_seconds': time.perf_counter() - processing_started,
        },
        indent=2,
    )
