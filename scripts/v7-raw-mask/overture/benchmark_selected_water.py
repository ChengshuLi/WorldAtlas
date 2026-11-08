#!/usr/bin/env python3
"""Compare every selected raw water shard in-process, with serial pinned R2 reads."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:sys.path.append(str(HERE.parent))
from build_physical import download_r2
import benchmark_water_shard as benchmark
from rasterize_water_shard import sha256


def write_report(path,report):
    pending=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    with pending.open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(pending,path)


def verify_completed(item,entry,output,config,repeats):
    if item['source']!=entry or len(item['results'])!=repeats:
        raise ValueError('completed benchmark source or repeat mismatch')
    for repeat,pair in enumerate(item['results']):
        if pair.get('repeat')!=repeat or set(pair['runs'])!={'python','gdal'}:
            raise ValueError('completed paired benchmark identity mismatch')
        for engine,run in pair['runs'].items():
            folder=output/f'{repeat:02d}-{engine}';report=json.loads((folder/'report.json').read_bytes())
            if (Path(run['output']).resolve()!=folder or sha256(folder/'report.json')!=run['report_sha256'] or
                    report.get('status')!='candidate-only' or report.get('source_sha256')!=entry['sha256'] or
                    report.get('configuration_sha256')!=sha256(config) or report.get('rasterizer')!=engine or
                    report.get('counts')!=run['counts'] or report.get('rows_in_source')!=run['counts']['rows'] or
                    report.get('output_sha256')!=run['mask_sha256'] or sha256(folder/'water.tif')!=run['mask_sha256']):
                raise ValueError('completed benchmark report or mask changed')
        if (pair['runs']['python']['counts']!=pair['runs']['gdal']['counts'] or
                benchmark.compare(output/f'{repeat:02d}-python',output/f'{repeat:02d}-gdal')):
            raise ValueError('completed benchmark parity mismatch')


def run(selection,output,*,shards=None,repeats=1,keep_sources=False,resume=False):
    for name,module in (('benchmark_water_shard.py',benchmark),('rasterize_water_shard.py',benchmark.build)):
        if Path(module.__file__).resolve()!=HERE/name:
            raise ValueError('water benchmark module resolved outside selected checkout: '+name)
    selection=Path(selection).resolve();data=selection.read_bytes();cfg=json.loads(data)
    if cfg.get('schema')!='worldatlas-end-to-end-pipeline-v1':raise ValueError('selected pipeline configuration required')
    water=cfg['sources']['water_config']['json'];manifest=cfg['sources']['raw_manifest']['json']
    files=manifest['files']
    if (manifest.get('file_count')!=len(files) or not files or
            len({entry['sha256'] for entry in files})!=len(files)):
        raise ValueError('complete unique raw manifest required')
    indices=list(range(len(files))) if shards is None else sorted(set(shards))
    if not indices or any(type(i) is not int or not 0<=i<len(files) for i in indices):
        raise ValueError('invalid selected shard ordinals')
    for entry in files:
        path=Path(entry['path']);digest=entry['sha256']
        if path.is_absolute() or '..' in path.parts or not path.name:
            raise ValueError('raw shard path must be relative and remain inside its source directory')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('raw shard SHA-256 required')
    output=Path(output).resolve()
    if not resume:
        output.mkdir();(output/'runtime').mkdir();(output/'shards').mkdir();(output/'configs').mkdir()
    config=output/'configs/water-config.json';config_bytes=(json.dumps(water,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if resume:
        if config.read_bytes()!=config_bytes:raise ValueError('resumed water configuration changed')
    else:config.write_bytes(config_bytes)
    code_paths={name:HERE/name for name in
          ('benchmark_selected_water.py','benchmark_water_shard.py','rasterize_water_shard.py','water_batch.py')}
    code_paths['build_physical.py']=HERE.parent/'build_physical.py'
    code={name:sha256(path) for name,path in code_paths.items()}
    report={'status':'in-progress','selection_sha256':hashlib.sha256(data).hexdigest(),
        'water_configuration_sha256':sha256(config),'script_sha256':code,'manifest_file_count':len(files),
        'selected_ordinals':indices,'repeats':repeats,'scope':'complete-manifest' if len(indices)==len(files) else 'selected-complete-shards',
        'timing_protocol':'serial in-process production; alternate first backend by shard/repeat; downloads and pixel comparison excluded',
        'results':[]}
    if resume:
        previous=json.loads((output/'benchmark.json').read_bytes())
        if any(previous.get(key)!=report[key] for key in
               ('selection_sha256','water_configuration_sha256','script_sha256','manifest_file_count','selected_ordinals','repeats')):
            raise ValueError('resumed benchmark identity changed')
        report=previous
        if [item['ordinal'] for item in report['results']]!=indices[:len(report['results'])]:
            raise ValueError('resumed benchmark shard order changed')
    report['status']='in-progress'
    report.setdefault('attempts',[]).append({'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'reused_completed_ordinals':[item['ordinal'] for item in report['results']]})
    write_report(output/'benchmark.json',report)
    completed={item['ordinal']:item for item in report['results']}
    def quarantine(path):
        if path.exists():
            target=output/'interrupted';target.mkdir(exist_ok=True)
            path.rename(target/(path.name+'-'+uuid.uuid4().hex))
    previous={key:os.environ.get(key) for key in ('TMPDIR','TMP','TEMP','CPL_TMPDIR','SQLITE_TMPDIR')}
    os.environ.update({key:str(output/'runtime') for key in previous})
    try:
        for i in indices:
            entry=files[i];source=(selection.parent/entry['path']).resolve();owned=False;download_seconds=0.
            if not source.is_relative_to(selection.parent):raise ValueError('raw source escapes selected directory')
            if i in completed:
                verify_completed(completed[i],entry,output/'shards'/f'{i:05d}',config,repeats)
                if source.is_file() and sha256(source)!=entry['sha256']:raise ValueError('local benchmark source changed')
                continue
            if resume:quarantine(output/'shards'/f'{i:05d}')
            if not source.is_file():
                staging=cfg.get('physical_controls',{}).get('source_staging',{})
                if staging.get('mode')!='r2-s3':raise ValueError('missing local shard requires selected R2 S3 staging')
                folder=output/'source-staging'/f'{i:05d}';source=folder/Path(entry['path']).name
                if source.exists() and (not source.is_file() or source.stat().st_size!=entry['size'] or sha256(source)!=entry['sha256']):
                    quarantine(folder)
                folder.mkdir(parents=True,exist_ok=True)
                if not source.exists():
                    started=time.perf_counter();download_r2(staging['endpoint_url'],entry,source)
                    download_seconds=time.perf_counter()-started
                owned=True
                if source.stat().st_size!=entry['size'] or sha256(source)!=entry['sha256']:
                    raise ValueError('downloaded raw shard pin mismatch')
            results=benchmark.run(source,entry['sha256'],config,output/'shards'/f'{i:05d}',
                repeats=repeats,order_offset=i%2)
            item={'ordinal':i,'source':entry,'source_download_seconds':download_seconds,'results':results}
            if owned and not keep_sources:
                if source.is_symlink() or sha256(source)!=entry['sha256']:
                    raise ValueError('owned raw shard changed before cleanup')
                item['discarded_owned_source']={'sha256':entry['sha256'],'bytes':source.stat().st_size}
                source.unlink()
            report['results'].append(item)
            write_report(output/'benchmark.json',report)
        if selection.read_bytes()!=data or any(sha256(code_paths[name])!=digest for name,digest in code.items()):
            raise ValueError('selection or benchmark code changed during processing')
        report['status']='all-selected-inputs-pixels-and-diagnostics-identical'
        report['processing_seconds']={engine:sum(pair['runs'][engine]['seconds']
            for item in report['results'] for pair in item['results']) for engine in ('python','gdal')}
        report['ratio_of_summed_processing_times']=report['processing_seconds']['python']/report['processing_seconds']['gdal']
        report['attempts'][-1]['ended_at_utc']=datetime.now(timezone.utc).isoformat()
        write_report(output/'benchmark.json',report)
        return report
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selected_pipeline_config');parser.add_argument('output')
    parser.add_argument('--shard',type=int,action='append',help='complete selected shard ordinal; default: every manifest entry')
    parser.add_argument('--repeats',type=int,default=1);parser.add_argument('--keep-downloaded-sources',action='store_true')
    parser.add_argument('--resume',action='store_true',help='reverify completed paired masks/reports; preserve and retry incomplete work')
    args=parser.parse_args(argv)
    if args.repeats<1:parser.error('repeats must be positive')
    return run(args.selected_pipeline_config,args.output,shards=args.shard,repeats=args.repeats,
               keep_sources=args.keep_downloaded_sources,resume=args.resume)


if __name__=='__main__':print(json.dumps(main(),indent=2))
