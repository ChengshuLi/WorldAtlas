#!/usr/bin/env python3
"""Wire pinned raw land and water sources into a candidate physical grid."""
import hashlib
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from contextvars import copy_context
import fcntl
import json
import math
import os
import re
from pathlib import Path
import shutil
import sys
import threading
import time
import uuid

from map_build.execution import control
from map_build.physical import land, water, union as water_union, composition

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


def run_stage(function, *args):
    return function(*args, emit=control.emit)


def validate_r2_endpoint(endpoint):
    if (not isinstance(endpoint, str) or not re.fullmatch(
            r'https://[0-9a-f]{32}(?:\.(?:eu|us|fedramp))?\.r2\.cloudflarestorage\.com', endpoint)):
        raise ValueError('R2 endpoint must be an HTTPS Cloudflare R2 S3 account endpoint')


def make_r2_client(endpoint):
    validate_r2_endpoint(endpoint)
    try:
        import boto3
    except ImportError as exc:
        raise ValueError('R2 staging requires boto3 in the pipeline Python environment') from exc
    return boto3.client('s3', endpoint_url=endpoint, region_name='auto')


def download_r2(endpoint, entry, destination):
    """Write a streamed response exclusively. Keep partial files for inspection."""
    from atlas_sources.catalog import stream_source

    control.check_cancelled()
    with closing(make_r2_client(endpoint)) as client, destination.open('xb') as stream:
        try:
            stream_source(client, dict(entry, size_bytes=entry['size']), stream,
                          check_cancelled=control.check_cancelled)
        except ValueError as exc:
            raise ValueError('staged source size/hash mismatch: ' + str(destination)) from exc



def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def write_bytes_atomic(path, data):
    """Publish exclusively after fsync; leave interrupted pending data intact."""
    path=Path(path);pending=path.parent/('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    with pending.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.link(pending,path)
    sync_directory(path.parent)
    pending.unlink();sync_directory(path.parent)


def write_json(path, value):
    write_bytes_atomic(path,(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())


class ProcessingJournal:
    """Durable attempt/unit records; never infer duration across a crash."""
    def __init__(self, output, started, resume):
        self.path=output/'processing-events.jsonl';self.started=started
        self.attempt=uuid.uuid4().hex;self.lock=threading.Lock();self.download=0.0;self.finished=False
        self.events=[]
        if resume:
            raw=self.path.read_bytes();end=raw.rfind(b'\n')+1
            if end<len(raw):
                interrupted=output/'interrupted';interrupted.mkdir(mode=0o700,exist_ok=True)
                sync_directory(output)
                tail=interrupted/('journal-tail-'+uuid.uuid4().hex)
                with tail.open('xb') as f:f.write(raw[end:]);f.flush();os.fsync(f.fileno())
                fd=os.open(interrupted,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(fd)
                finally:os.close(fd)
                with self.path.open('r+b') as f:f.truncate(end);f.flush();os.fsync(f.fileno())
            self.events=[json.loads(line) for line in raw[:end].splitlines()]
        else:
            with self.path.open('x') as f:f.flush();os.fsync(f.fileno())
            sync_directory(output)
        self.add({'event':'attempt_start','attempt':self.attempt})
    def add(self,event):
        with self.lock:
            with self.path.open('a') as f:
                f.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
            self.events.append(event)
    def unit(self,name,started,report,output):
        ended=time.perf_counter()
        self.add({'event':'unit_complete','attempt':self.attempt,'unit':name,
                  'start_monotonic_seconds':started,'end_monotonic_seconds':ended,
                  'processing_elapsed_seconds':ended-started,
                  'report_sha256':sha(report),'output_sha256':sha(output)})
    def download_done(self,started):
        elapsed=time.perf_counter()-started;self.download+=elapsed
        self.add({'event':'download_complete','attempt':self.attempt,'seconds':elapsed})
    def finish(self,status):
        if self.finished:raise ValueError('attempt already ended')
        elapsed=time.perf_counter()-self.started
        if not math.isfinite(elapsed) or elapsed<self.download:raise ValueError('invalid attempt timing')
        self.add({'event':'attempt_end','attempt':self.attempt,'status':status,
                  'processing_elapsed_seconds':elapsed-self.download,'source_download_elapsed_seconds':self.download})
        self.finished=True
    def summary(self):
        if any(e.get('event') not in ('attempt_start','attempt_end','unit_complete','download_complete') for e in self.events):raise ValueError('unknown processing journal event')
        starts={e['attempt'] for e in self.events if e.get('event')=='attempt_start'}
        ends={e['attempt']:e for e in self.events if e.get('event')=='attempt_end'}
        if len(starts)!=sum(e.get('event')=='attempt_start' for e in self.events) or len(ends)!=sum(e.get('event')=='attempt_end' for e in self.events) or not set(ends)<=starts:
            raise ValueError('invalid processing journal attempts')
        if any(e.get('status') not in ('complete','failed') for e in ends.values()):raise ValueError('invalid processing journal status')
        if any(e.get('attempt') not in starts for e in self.events):raise ValueError('processing journal event without attempt')
        if any(type(e.get(k)) not in (int,float) or not math.isfinite(e[k]) or e[k]<0 for e in ends.values() for k in ('processing_elapsed_seconds','source_download_elapsed_seconds')):
            raise ValueError('invalid processing journal duration')
        if any(type(e.get('seconds')) not in (int,float) or not math.isfinite(e['seconds']) or e['seconds']<0 for e in self.events if e.get('event')=='download_complete'):
            raise ValueError('invalid processing journal download duration')
        missing=starts-set(ends)
        lower=sum(e['processing_elapsed_seconds'] for e in ends.values())
        for attempt in missing:
            intervals=sorted((e['start_monotonic_seconds'],e['end_monotonic_seconds']) for e in self.events if e.get('event')=='unit_complete' and e['attempt']==attempt)
            merged=[]
            for start,end in intervals:
                if not (math.isfinite(start) and math.isfinite(end) and end>=start):raise ValueError('invalid processing journal interval')
                if merged and start<=merged[-1][1]:merged[-1][1]=max(end,merged[-1][1])
                else:merged.append([start,end])
            lower+=sum(end-start for start,end in merged)
        download=sum(e['source_download_elapsed_seconds'] for e in ends.values())
        download+=sum(e['seconds'] for e in self.events if e.get('event')=='download_complete' and e['attempt'] in missing)
        return {'timing_complete':not missing,'processing_elapsed_seconds':lower if not missing else None,
                'recorded_processing_elapsed_seconds':lower,'source_download_elapsed_seconds':download,
                'source_download_elapsed_scope':'complete' if not missing else 'recorded-lower-bound',
                'invocation_processing_elapsed_seconds':ends[self.attempt]['processing_elapsed_seconds'],
                'invocation_source_download_elapsed_seconds':ends[self.attempt]['source_download_elapsed_seconds']}


def run(manifest_path, output, *, resume=False):
    started=time.perf_counter();output=Path(output).resolve()
    if not output.parent.is_dir():raise ValueError('output parent must exist')
    lock_path=output.parent/(output.name+'.lock')
    with lock_path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('physical pipeline already running') from None
        journal=[None]
        try:return _run(manifest_path,output,started,resume,journal)
        except BaseException:
            if journal[0] is not None and not journal[0].finished:journal[0].finish('failed')
            raise


def _run(manifest_path, output, processing_started, resume, journal_slot):
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
        if (not isinstance(staging, dict) or set(staging) != {'mode', 'endpoint_url'}
                or staging['mode'] != 'r2-s3' or workers != 1):
            raise ValueError('R2 staging requires r2-s3 mode, endpoint_url and one shard worker')
        validate_r2_endpoint(staging['endpoint_url'])
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < 0:
        raise ValueError('invalid free-space reserve')
    land_path, land_bytes, land_cfg = read_pin(cfg['land_config'])
    water_path, water_bytes, water_cfg = read_pin(cfg['water_config'])
    if water_cfg.get('rasterizer','gdal') not in ('gdal','python'):
        raise ValueError('water rasterizer must be gdal or python; runtime native compilation is retired')
    if 'native_method' in water_cfg:
        raise ValueError('retired native_method; use batch_method')
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
    scripts = {name:sha(HERE / name) for name in ('build.py','sources.py','land.py','water.py','water_batch.py','union.py','composition.py')}
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
    source_pins=[item for spec in land_cfg['land'] for item in spec['files']]
    if any(sha(p['path'])!=p['sha256'] for p in source_pins):raise ValueError('land source hash mismatch')
    identity={'schema':'raw-physical-resume-identity-v1','configuration_sha256':hashlib.sha256(data).hexdigest(),
              'land_config':cfg['land_config'],'water_config':cfg['water_config'],'source_manifest':cfg['source_manifest'],
              'script_sha256':scripts,'land_source_pins':source_pins}
    identity_path=output/'pipeline-identity.json'
    if resume:
        previous = json.loads(identity_path.read_bytes()) if identity_path.is_file() else {}
        data_identity = lambda value: {k:v for k,v in value.items() if k!='script_sha256'}
        if not output.is_dir() or data_identity(previous)!=data_identity(identity):
            raise ValueError('physical resume identity mismatch')
        if (output/'report.json').exists():
            report=json.loads((output/'report.json').read_bytes());stages=report.get('stage_reports',{})
            if (report.get('status')!='candidate-only' or report.get('configuration_sha256')!=identity['configuration_sha256']
                or report.get('pipeline_identity_sha256')!=sha(identity_path)
                or report.get('processing_journal_sha256')!=sha(output/'processing-events.jsonl') or set(stages)!={'land','union','physical'}
                or any(Path(stages[k]['path']).resolve()!=output/k/'report.json' or sha(stages[k]['path'])!=stages[k]['sha256'] for k in stages)):
                raise ValueError('completed physical report mismatch')
            for key,name in (('land','land.tif'),('union','water-union.tif')):
                stage=json.loads((output/key/'report.json').read_bytes());digest=stage['land_sha256' if key=='land' else 'union_sha256']
                if sha(output/key/name)!=digest:raise ValueError('completed stage output mismatch: '+key)
            union=json.loads((output/'union/report.json').read_bytes());shards=union.get('shards')
            if not isinstance(shards,list) or len(shards)!=len(raw):raise ValueError('completed shard inventory mismatch')
            for i,(entry,(source,digest,_)) in enumerate(zip(shards,raw)):
                directory=output/'shards'/f'{i:05d}';rp=directory/'report.json';tif=directory/'water.tif';sp=entry.get('report',{})
                if (Path(entry.get('path','')).resolve()!=tif or Path(sp.get('path','')).resolve()!=rp
                    or sha(rp)!=sp.get('sha256') or sha(tif)!=entry.get('sha256') or entry.get('status')!='candidate-only'):
                    raise ValueError(f'completed shard checkpoint mismatch: {i}')
                item=json.loads(rp.read_bytes())
                if (item.get('source_sha256')!=digest or Path(item.get('source','')).name!=source.name
                    or item.get('configuration_sha256')!=cfg['water_config']['sha256'] or item.get('grid')!=grid
                    or item.get('policy')!=water_cfg.get('policy')
                    or item.get('batch_size')!=batch_size or item.get('output_sha256')!=entry['sha256']):
                    raise ValueError(f'completed shard report mismatch: {i}')
            physical=json.loads((output/'physical/report.json').read_bytes());outputs=physical.get('output_sha256',{})
            if outputs!=report.get('physical_output_sha256') or any(sha(output/'physical'/name)!=outputs.get(name) for name in ('physical-dry.tif','rows.u32le','runs.u32le')):
                raise ValueError('completed physical output mismatch')
            return report
    else:
        os.mkdir(output);sync_directory(output.parent);(output/'configs').mkdir();(output/'shards').mkdir();write_json(identity_path,identity)
    journal_exists=(output/'processing-events.jsonl').exists()
    if resume and not journal_exists:
        if ((output/'land').exists() or (output/'union').exists() or (output/'physical').exists()
            or any((output/'shards').iterdir()) or any((output/'configs').iterdir())):
            raise ValueError('missing processing journal for existing checkpoints')
    journal=ProcessingJournal(output,processing_started,resume and journal_exists);journal_slot[0]=journal
    if resume and not journal_exists:
        journal.add({'event':'attempt_start','attempt':'unrecorded-before-journal-'+uuid.uuid4().hex})
    def prior(name):
        matches=[e for e in journal.events if e.get('event')=='unit_complete' and e.get('unit')==name]
        return matches[-1] if matches else None
    def quarantine(path):
        if path.exists():
            target=output/'interrupted';target.mkdir(mode=0o700,exist_ok=True)
            sync_directory(output)
            os.rename(path,target/(path.name+'-'+uuid.uuid4().hex))
            sync_directory(path.parent);sync_directory(target)
    land_dir=output/'land';land_checkpoint=prior('land') if resume else None
    if land_checkpoint:
        land_report=json.loads((land_dir/'report.json').read_bytes())
        if (sha(land_dir/'report.json')!=land_checkpoint['report_sha256'] or sha(land_dir/'land.tif')!=land_checkpoint['output_sha256']
            or land_report.get('status')!='candidate-only' or land_report.get('configuration_sha256')!=cfg['land_config']['sha256']
            or land_report.get('grid')!=grid or land_report.get('land_sha256')!=land_checkpoint['output_sha256']):
            raise ValueError('land checkpoint mismatch')
    else:
        if resume:quarantine(land_dir)
        unit_start=time.perf_counter();run_stage(land.run, land_path, land_dir)
        land_report=json.loads((land_dir/'report.json').read_bytes())
        if land_report.get('status')!='candidate-only' or land_report.get('land_sha256')!=sha(land_dir/'land.tif'):raise ValueError('land raster is incomplete')
        journal.unit('land',unit_start,land_dir/'report.json',land_dir/'land.tif')
    staged_count = 0
    def build_shard(item):
        control.check_cancelled()
        nonlocal staged_count
        i, (path, digest, entry) = item
        destination = output / 'shards' / f'{i:05d}'
        checkpoint=prior(f'shard-{i:05d}') if resume else None
        if checkpoint:
            report_path=destination/'report.json';report=json.loads(report_path.read_bytes())
            if (sha(report_path)!=checkpoint['report_sha256'] or sha(destination/'water.tif')!=checkpoint['output_sha256']
                or report.get('status')!='candidate-only' or report.get('source_sha256')!=digest
                or Path(report.get('source','')).name!=path.name or report.get('configuration_sha256')!=cfg['water_config']['sha256']
                or report.get('grid')!=grid
                or report.get('policy')!=water_cfg.get('policy') or report.get('batch_size')!=batch_size
                or report.get('output_sha256')!=checkpoint['output_sha256']):raise ValueError(f'shard checkpoint mismatch: {i}')
            staged=output/'source-staging'/path.name
            if staged.is_file() and staged.stat().st_size==entry.get('size') and sha(staged)==digest:staged.unlink()
            return {'path':str(destination/'water.tif'),'sha256':checkpoint['output_sha256'],
                    'status':'candidate-only','report':{'path':str(report_path),'sha256':checkpoint['report_sha256']}}
        if resume:quarantine(destination)
        owned = False
        if not path.is_file() and staging is not None:
            stage_dir=output/'source-staging';stage_dir.mkdir(mode=0o700,exist_ok=True)
            staged=stage_dir/path.name
            if staged.exists() and (not staged.is_file() or staged.stat().st_size!=entry['size'] or sha(staged)!=digest):quarantine(staged)
            if not staged.exists():
                started=time.perf_counter()
                try:
                    download_r2(staging['endpoint_url'], entry, staged)
                finally:
                    journal.download_done(started)
                staged_count+=1
            if not staged.is_file() or staged.stat().st_size != entry['size'] or sha(staged) != digest:
                raise ValueError(f'staged source size/hash mismatch: {path}')
            path=staged;owned=True
        unit_start=time.perf_counter()
        run_stage(water.run, path, digest, destination, water_path, batch_size)
        report_path = destination / 'report.json'; report = json.loads(report_path.read_bytes())
        if (report.get('status')!='candidate-only' or report.get('source_sha256')!=digest
            or report.get('configuration_sha256')!=cfg['water_config']['sha256']
            or report.get('output_sha256')!=sha(destination/'water.tif')):
            raise ValueError(f'incomplete water shard: {path}')
        journal.unit(f'shard-{i:05d}',unit_start,report_path,destination/'water.tif')
        if owned:path.unlink()
        return {'path':str(destination / 'water.tif'), 'sha256':report['output_sha256'],
                'status':report['status'], 'report':{'path':str(report_path), 'sha256':sha(report_path)}}
    # Independent child outputs are kept in manifest order. On failure,
    # cancel work not yet started; running children finish and remain auditable.
    shards = [None] * len(raw)
    with ThreadPoolExecutor(max_workers=min(workers, len(raw))) as pool:
        futures = {pool.submit(copy_context().run, build_shard, item): item[0] for item in enumerate(raw)}
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
    def bind_config(path,value):
        if path.exists():
            if not resume or json.loads(path.read_bytes())!=value:raise ValueError('resumed stage config mismatch')
        else:write_json(path,value)
    union_config = output / 'configs/union.json';bind_config(union_config,union_cfg)
    union_dir=output/'union';union_checkpoint=prior('union') if resume else None
    if union_checkpoint:
        union_report=json.loads((union_dir/'report.json').read_bytes())
        if (sha(union_dir/'report.json')!=union_checkpoint['report_sha256'] or sha(union_dir/'water-union.tif')!=union_checkpoint['output_sha256']
            or union_report.get('status')!='candidate-only' or union_report.get('configuration_sha256')!=sha(union_config)
            or union_report.get('grid')!=grid or union_report.get('union_sha256')!=union_checkpoint['output_sha256']):raise ValueError('union checkpoint mismatch')
    else:
        if resume:quarantine(union_dir)
        unit_start=time.perf_counter();run_stage(water_union.run,union_config,union_dir)
        union_report=json.loads((union_dir/'report.json').read_bytes())
        if union_report.get('status')!='candidate-only' or union_report.get('union_sha256')!=sha(union_dir/'water-union.tif'):raise ValueError('water union is incomplete')
        journal.unit('union',unit_start,union_dir/'report.json',union_dir/'water-union.tif')
    compose_cfg = {'schema':'candidate-physical-composition-v1','grid':grid,'selection_notes':cfg['selection_notes'],
                   'minimum_free_bytes':reserve,'rows_per_block':physical_rows_per_block,
                   'land':{'path':str(output / 'land/land.tif'),'sha256':land_report['land_sha256']},
                   'water':{'path':str(output / 'union/water-union.tif'),'sha256':union_report['union_sha256']}}
    if cfg.get('physical_reference_mask'):
        compose_cfg['reference_mask'] = cfg['physical_reference_mask']
        compose_cfg['reference_streams'] = cfg['physical_reference_streams']
    compose_config = output / 'configs/compose.json';bind_config(compose_config,compose_cfg)
    physical_dir=output/'physical';physical_checkpoint=prior('physical') if resume else None
    if physical_checkpoint:
        physical=json.loads((physical_dir/'report.json').read_bytes());outputs=physical.get('output_sha256',{})
        if (sha(physical_dir/'report.json')!=physical_checkpoint['report_sha256'] or sha(physical_dir/'rows.u32le')!=physical_checkpoint['output_sha256']
            or physical.get('status')!='candidate-only' or physical.get('configuration_sha256')!=sha(compose_config)
            or physical.get('grid')!=grid or any(sha(physical_dir/name)!=outputs.get(name) for name in ('physical-dry.tif','rows.u32le','runs.u32le'))):raise ValueError('physical checkpoint mismatch')
    else:
        if resume:quarantine(physical_dir)
        unit_start=time.perf_counter();run_stage(composition.main,compose_config,physical_dir)
        physical=json.loads((physical_dir/'report.json').read_bytes())
        if physical.get('status')!='candidate-only' or any(sha(physical_dir/name)!=physical.get('output_sha256',{}).get(name) for name in ('physical-dry.tif','rows.u32le','runs.u32le')):raise ValueError('physical composition is incomplete')
        journal.unit('physical',unit_start,physical_dir/'report.json',physical_dir/'rows.u32le')
    for p, original in ((manifest_path,data),(land_path,land_bytes),(water_path,water_bytes),(source_path,source_bytes)):
        if p.read_bytes() != original:
            raise ValueError(f'pipeline input changed during processing: {p}')
    if any(sha(p['path'])!=p['sha256'] for p in source_pins):raise ValueError('land source changed during processing')
    report = {'status':'candidate-only','configuration_sha256':hashlib.sha256(data).hexdigest(),
              'grid':grid,'source_manifest':cfg['source_manifest'],'land_config':cfg['land_config'],
              'water_config':cfg['water_config'],'water_batch_size':batch_size,
              'union_rows_per_block':union_rows_per_block,'physical_rows_per_block':physical_rows_per_block,
              'shard_count':len(shards),'max_parallel_shards':workers,'script_sha256':scripts,
              'stage_reports':{key:{'path':str(output / key / 'report.json'),'sha256':sha(output / key / 'report.json')}
                               for key in ('land','union','physical')},
              'physical_output_sha256':physical['output_sha256'],
              'limitations':'Candidate physical land/water only; not historical source reproduction or continent labels.'}
    pipeline_config=output/'pipeline-config.json'
    if pipeline_config.exists():
        if not resume or pipeline_config.read_bytes()!=data:raise ValueError('resumed pipeline config mismatch')
    else:write_bytes_atomic(pipeline_config,data)
    report['staged_shard_count'] = staged_count
    report['staged_shard_count_scope'] = 'current invocation'
    journal.finish('complete');report.update(journal.summary())
    report['pipeline_identity_sha256']=sha(identity_path);report['processing_journal_sha256']=sha(journal.path)
    write_json(output / 'report.json', report)
    return report


def main(argv=None, *, emit=print):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline_config');parser.add_argument('output');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv)
    emit(json.dumps(run(args.pipeline_config, args.output, resume=args.resume), indent=2), flush=True)


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as e: sys.exit(f'failed: {e}')
