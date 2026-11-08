#!/usr/bin/env python3
"""Compare every selected raw water shard in-process, with serial pinned R2 reads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:sys.path.append(str(HERE.parent))
from build_physical import download_r2
import benchmark_water_shard as benchmark
from rasterize_water_shard import sha256


def run(selection,output,*,shards=None,repeats=1,keep_sources=False):
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
    output=Path(output).resolve();output.mkdir();(output/'runtime').mkdir();(output/'shards').mkdir();(output/'configs').mkdir()
    config=output/'configs/water-config.json';config.write_text(json.dumps(water,indent=2,sort_keys=True,allow_nan=False)+'\n')
    code={name:sha256(HERE/name) for name in
          ('benchmark_selected_water.py','benchmark_water_shard.py','rasterize_water_shard.py','water_batch.py')}
    report={'status':'in-progress','selection_sha256':hashlib.sha256(data).hexdigest(),
        'water_configuration_sha256':sha256(config),'script_sha256':code,'manifest_file_count':len(files),
        'selected_ordinals':indices,'scope':'complete-manifest' if len(indices)==len(files) else 'selected-complete-shards',
        'timing_protocol':'serial in-process production; alternate first backend by shard/repeat; downloads and pixel comparison excluded',
        'results':[]}
    previous={key:os.environ.get(key) for key in ('TMPDIR','TMP','TEMP','CPL_TMPDIR','SQLITE_TMPDIR')}
    os.environ.update({key:str(output/'runtime') for key in previous})
    try:
        for i in indices:
            entry=files[i];source=(selection.parent/entry['path']).resolve();owned=False;download_seconds=0.
            if not source.is_relative_to(selection.parent):raise ValueError('raw source escapes selected directory')
            if not source.is_file():
                staging=cfg.get('physical_controls',{}).get('source_staging',{})
                if staging.get('mode')!='r2-s3':raise ValueError('missing local shard requires selected R2 S3 staging')
                folder=output/'source-staging'/f'{i:05d}';folder.mkdir(parents=True)
                source=folder/Path(entry['path']).name;started=time.perf_counter()
                download_r2(staging['endpoint_url'],entry,source);download_seconds=time.perf_counter()-started;owned=True
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
            (output/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
        if selection.read_bytes()!=data or any(sha256(HERE/name)!=digest for name,digest in code.items()):
            raise ValueError('selection or benchmark code changed during processing')
        report['status']='all-selected-inputs-pixels-and-diagnostics-identical'
        report['processing_seconds']={engine:sum(pair['runs'][engine]['seconds']
            for item in report['results'] for pair in item['results']) for engine in ('python','gdal')}
        report['ratio_of_summed_processing_times']=report['processing_seconds']['python']/report['processing_seconds']['gdal']
        (output/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
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
    args=parser.parse_args(argv)
    if args.repeats<1:parser.error('repeats must be positive')
    return run(args.selected_pipeline_config,args.output,shards=args.shard,repeats=args.repeats,keep_sources=args.keep_downloaded_sources)


if __name__=='__main__':print(json.dumps(main(),indent=2))
