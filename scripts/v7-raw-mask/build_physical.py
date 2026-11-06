#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_pin(spec):
    path = Path(spec['path']).resolve()
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise ValueError(f'input hash mismatch: {path}')
    return path, data, json.loads(data)


def run_stage(script, *args):
    subprocess.run([sys.executable, str(HERE / script), *map(str, args)], check=True)


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')


def run(manifest_path, output):
    manifest_path = Path(manifest_path).resolve(); data = manifest_path.read_bytes(); cfg = json.loads(data)
    if cfg.get('schema') != 'raw-physical-pipeline-v1' or not cfg.get('selection_notes'):
        raise ValueError('explicit pipeline schema and selection notes required')
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    # Two-way builds have exact parity on the PR4 real-shard sample. Keep the
    # worker count configurable and profile full-source host/disk load before
    # raising it further.
    workers = cfg.get('max_parallel_shards', 2)
    if type(workers) is not int or workers < 1:
        raise ValueError('max_parallel_shards must be a positive integer')
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    land_path, land_bytes, land_cfg = read_pin(cfg['land_config'])
    water_path, water_bytes, water_cfg = read_pin(cfg['water_config'])
    source_path, source_bytes, source = read_pin(cfg['source_manifest'])
    grid = land_cfg['grid']
    if grid != water_cfg['grid']:
        raise ValueError('land and water grids differ')
    for stage in (land_cfg, water_cfg):
        if stage.get('minimum_free_bytes', 2 * (1 << 30)) < reserve:
            raise ValueError('stage free-space reserve is below pipeline reserve')
    files = source.get('files')
    if not isinstance(files, list) or not files or source.get('file_count') != len(files):
        raise ValueError('source manifest must list every raw shard')
    raw = []
    for entry in files:
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('raw source paths must be relative to manifest directory')
        path = (source_path.parent / rel).resolve()
        if not path.is_relative_to(source_path.parent):
            raise ValueError('raw source escapes manifest directory')
        digest = entry['sha256']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('invalid raw source digest')
        raw.append((path, digest))
    if len({x[0] for x in raw}) != len(raw) or len({x[1] for x in raw}) != len(raw):
        raise ValueError('raw source paths and hashes must be unique')
    scripts = {name:sha(HERE / name) for name in ('build_physical.py','build.py','rasterize_land.py','overture/rasterize_water_shard.py','overture/aggregate_compare.py','compose_physical.py')}
    output = Path(output).resolve()
    inputs = [manifest_path, land_path, water_path, source_path] + [x[0] for x in raw]
    inputs += [Path(item['path']).resolve() for spec in land_cfg['land'] for item in spec['files']]
    for key in ('water_reference', 'physical_reference_mask'):
        if cfg.get(key): inputs.append(Path(cfg[key]['path']).resolve())
    if cfg.get('physical_reference_streams'):
        inputs += [Path(cfg['physical_reference_streams'][k]['path']).resolve() for k in ('rows', 'runs')]
    if bool(cfg.get('physical_reference_mask')) != bool(cfg.get('physical_reference_streams')):
        raise ValueError('physical reference mask and streams must be supplied together')
    if any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):
        raise ValueError('output must be outside all input directories and must not contain inputs')
    if shutil.disk_usage(output.parent).free < reserve:
        raise ValueError('free disk below pipeline reserve')
    os.mkdir(output)
    (output / 'configs').mkdir(); (output / 'shards').mkdir()
    run_stage('rasterize_land.py', land_path, output / 'land')
    land_report = json.loads((output / 'land/report.json').read_bytes())
    if land_report.get('status') != 'candidate-only':
        raise ValueError('land raster is incomplete')
    def build_shard(item):
        i, (path, digest) = item
        destination = output / 'shards' / f'{i:05d}'
        run_stage('overture/rasterize_water_shard.py', path, digest, water_path, destination)
        report_path = destination / 'report.json'; report = json.loads(report_path.read_bytes())
        if report.get('status') != 'candidate-only':
            raise ValueError(f'incomplete water shard: {path}')
        return {'path':str(destination / 'water.tif'), 'sha256':report['output_sha256'],
                'status':report['status'], 'report':{'path':str(report_path), 'sha256':sha(report_path)}}
    # Independent child outputs are kept in manifest order. On failure,
    # cancel work not yet started; running children finish and remain auditable.
    shards = [None] * len(raw)
    with ThreadPoolExecutor(max_workers=min(workers, len(raw))) as pool:
        futures = {pool.submit(build_shard, item): item[0] for item in enumerate(raw)}
        try:
            for future in as_completed(futures):
                shards[futures[future]] = future.result()
        except Exception:
            for future in futures: future.cancel()
            raise
    union_cfg = {'schema':'water-union-comparison-v1','grid':grid,'selection_notes':cfg['selection_notes'],
                 'minimum_free_bytes':reserve,'source_manifest':cfg['source_manifest'],'shard_count':len(shards),'shards':shards}
    if cfg.get('water_reference'): union_cfg['reference'] = cfg['water_reference']
    union_config = output / 'configs/union.json'; write_json(union_config, union_cfg)
    run_stage('overture/aggregate_compare.py', union_config, output / 'union')
    union_report = json.loads((output / 'union/report.json').read_bytes())
    compose_cfg = {'schema':'candidate-physical-composition-v1','grid':grid,'selection_notes':cfg['selection_notes'],
                   'minimum_free_bytes':reserve,'land':{'path':str(output / 'land/land.tif'),'sha256':land_report['land_sha256']},
                   'water':{'path':str(output / 'union/water-union.tif'),'sha256':union_report['union_sha256']}}
    if cfg.get('physical_reference_mask'):
        compose_cfg['reference_mask'] = cfg['physical_reference_mask']
        compose_cfg['reference_streams'] = cfg['physical_reference_streams']
    compose_config = output / 'configs/compose.json'; write_json(compose_config, compose_cfg)
    run_stage('compose_physical.py', compose_config, output / 'physical')
    for p, original in ((manifest_path,data),(land_path,land_bytes),(water_path,water_bytes),(source_path,source_bytes)):
        if p.read_bytes() != original:
            raise ValueError(f'pipeline input changed during processing: {p}')
    if any(sha(HERE / name) != digest for name,digest in scripts.items()):
        raise ValueError('pipeline code changed during processing')
    physical = json.loads((output / 'physical/report.json').read_bytes())
    report = {'status':'candidate-only','configuration_sha256':hashlib.sha256(data).hexdigest(),
              'grid':grid,'source_manifest':cfg['source_manifest'],'land_config':cfg['land_config'],
              'water_config':cfg['water_config'],'shard_count':len(shards),'max_parallel_shards':workers,'script_sha256':scripts,
              'stage_reports':{key:{'path':str(output / key / 'report.json'),'sha256':sha(output / key / 'report.json')}
                               for key in ('land','union','physical')},
              'physical_output_sha256':physical['output_sha256'],
              'limitations':'Candidate physical land/water only; not historical source reproduction or continent labels.'}
    with (output / 'pipeline-config.json').open('xb') as f: f.write(data)
    write_json(output / 'report.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit('usage: build_physical.py PIPELINE_CONFIG.json NEW_OUTPUT_DIRECTORY')
    try: run(sys.argv[1], sys.argv[2])
    except (ValueError, OSError, subprocess.CalledProcessError) as e: sys.exit(f'failed: {e}')
