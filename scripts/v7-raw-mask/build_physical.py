#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

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
    processing_started = time.perf_counter()
    manifest_path = Path(manifest_path).resolve(); data = manifest_path.read_bytes(); cfg = json.loads(data)
    if cfg.get('schema') != 'raw-physical-pipeline-v1' or not cfg.get('selection_notes'):
        raise ValueError('explicit pipeline schema and selection notes required')
    reserve = cfg.get('minimum_free_bytes', 2 * (1 << 30))
    # Keep the worker count configurable; use complete-source profiles to
    # balance CPU throughput against disk headroom for on-demand shard staging.
    workers = cfg.get('max_parallel_shards', 2)
    if type(workers) is not int or workers < 1:
        raise ValueError('max_parallel_shards must be a positive integer')
    staging = cfg.get('source_staging')
    if staging is not None:
        if (not isinstance(staging, dict) or set(staging) != {'mode','wrangler_path','wrangler_config'}
            or staging['mode'] != 'wrangler-r2' or workers != 1):
            raise ValueError('R2 staging requires a wrangler path, config and one shard worker')
        for key in ('wrangler_path','wrangler_config'):
            if not isinstance(staging[key],str) or not Path(staging[key]).is_file():
                raise ValueError(f'invalid R2 staging {key}')
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    land_path, land_bytes, land_cfg = read_pin(cfg['land_config'])
    water_path, water_bytes, water_cfg = read_pin(cfg['water_config'])
    source_path, source_bytes, source = read_pin(cfg['source_manifest'])
    grid = land_cfg['grid']
    if grid != water_cfg['grid']:
        raise ValueError('land and water grids differ')
    batch_size = water_cfg.get('batch_size', 8192)
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError('water batch_size must be a positive integer')
    union_rows_per_block = cfg.get('union_rows_per_block', 128)
    physical_rows_per_block = cfg.get('physical_rows_per_block', 128)
    for value in (union_rows_per_block, physical_rows_per_block):
        if type(value) is not int or value < 1:
            raise ValueError('rows_per_block must be a positive integer')
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
        if staging is not None and not path.is_file():
            if (not isinstance(entry.get('r2_bucket'),str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}',entry['r2_bucket'])
                or not isinstance(entry.get('r2_key'),str) or not entry['r2_key']
                or type(entry.get('size')) is not int or entry['size'] < 0):
                raise ValueError('missing or invalid pinned R2 source metadata')
        raw.append((path, digest, entry))
    if len({x[0] for x in raw}) != len(raw) or len({x[1] for x in raw}) != len(raw):
        raise ValueError('raw source paths and hashes must be unique')
    scripts = {name:sha(HERE / name) for name in ('build_physical.py','build.py','rasterize_land.py','overture/rasterize_water_shard.py','overture/aggregate_compare.py','compose_physical.py')}
    output = Path(output).resolve()
    inputs = [manifest_path, land_path, water_path, source_path] + [x[0] for x in raw]
    if staging is not None:
        inputs += [Path(staging[k]).resolve() for k in ('wrangler_path','wrangler_config')]
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
    download_elapsed = 0.0
    staged_count = 0
    def build_shard(item):
        nonlocal download_elapsed, staged_count
        i, (path, digest, entry) = item
        destination = output / 'shards' / f'{i:05d}'
        owned = False
        if not path.is_file() and staging is not None:
            stage_dir=output/'source-staging';stage_dir.mkdir(mode=0o700,exist_ok=True)
            for name in ('cache','state','runtime'):(stage_dir/name).mkdir(mode=0o700,exist_ok=True)
            staged=stage_dir/f'{i:05d}.parquet'
            if staged.exists():raise ValueError('staging target already exists')
            env=os.environ.copy()
            env.update({key:str(stage_dir) for key in ('TMPDIR','TMP','TEMP','CPL_TMPDIR','SQLITE_TMPDIR')})
            env.update({'XDG_CACHE_HOME':str(stage_dir/'cache'),'XDG_STATE_HOME':str(stage_dir/'state'),'XDG_RUNTIME_DIR':str(stage_dir/'runtime')})
            started=time.perf_counter()
            try:
                subprocess.run([staging['wrangler_path'],'r2','object','get',entry['r2_bucket']+'/'+entry['r2_key'],
                                '--file',str(staged),'--remote','--config',staging['wrangler_config']],check=True,env=env)
            finally:
                download_elapsed += time.perf_counter()-started
            if not staged.is_file() or staged.stat().st_size != entry['size'] or sha(staged) != digest:
                raise ValueError(f'staged source size/hash mismatch: {path}')
            path=staged;owned=True;staged_count+=1
        run_stage('overture/rasterize_water_shard.py', path, digest, water_path, destination, '--batch-size', str(batch_size))
        report_path = destination / 'report.json'; report = json.loads(report_path.read_bytes())
        if report.get('status') != 'candidate-only':
            raise ValueError(f'incomplete water shard: {path}')
        if owned:path.unlink()
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
                 'minimum_free_bytes':reserve,'source_manifest':cfg['source_manifest'],'shard_count':len(shards),
                 'rows_per_block':union_rows_per_block,'shards':shards}
    if cfg.get('water_reference'): union_cfg['reference'] = cfg['water_reference']
    union_config = output / 'configs/union.json'; write_json(union_config, union_cfg)
    run_stage('overture/aggregate_compare.py', union_config, output / 'union')
    union_report = json.loads((output / 'union/report.json').read_bytes())
    compose_cfg = {'schema':'candidate-physical-composition-v1','grid':grid,'selection_notes':cfg['selection_notes'],
                   'minimum_free_bytes':reserve,'rows_per_block':physical_rows_per_block,
                   'land':{'path':str(output / 'land/land.tif'),'sha256':land_report['land_sha256']},
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
              'water_config':cfg['water_config'],'water_batch_size':batch_size,
              'union_rows_per_block':union_rows_per_block,'physical_rows_per_block':physical_rows_per_block,
              'shard_count':len(shards),'max_parallel_shards':workers,'script_sha256':scripts,
              'stage_reports':{key:{'path':str(output / key / 'report.json'),'sha256':sha(output / key / 'report.json')}
                               for key in ('land','union','physical')},
              'physical_output_sha256':physical['output_sha256'],
              'limitations':'Candidate physical land/water only; not historical source reproduction or continent labels.'}
    with (output / 'pipeline-config.json').open('xb') as f: f.write(data)
    report['source_download_elapsed_seconds'] = download_elapsed
    report['staged_shard_count'] = staged_count
    report['processing_elapsed_seconds'] = time.perf_counter() - processing_started - download_elapsed
    write_json(output / 'report.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit('usage: build_physical.py PIPELINE_CONFIG.json NEW_OUTPUT_DIRECTORY')
    try: run(sys.argv[1], sys.argv[2])
    except (ValueError, OSError, subprocess.CalledProcessError) as e: sys.exit(f'failed: {e}')
