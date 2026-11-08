#!/usr/bin/env python3
"""Compare complete raw-shard Python reference/GDAL batches in one process."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np
from osgeo import gdal

import rasterize_water_shard as build


def compare(first, second):
    if build.sha256(Path(first)/'water.tif')==build.sha256(Path(second)/'water.tif'):return 0
    a, b = (gdal.Open(str(Path(p)/'water.tif')) for p in (first, second))
    if (a.RasterXSize,a.RasterYSize,a.GetGeoTransform()) != (b.RasterXSize,b.RasterYSize,b.GetGeoTransform()):
        raise ValueError('benchmark grids differ')
    different = 0
    for y in range(0,a.RasterYSize,512):
        n=min(512,a.RasterYSize-y)
        different += int(np.count_nonzero(a.ReadAsArray(0,y,a.RasterXSize,n) !=
                                          b.ReadAsArray(0,y,b.RasterXSize,n)))
    return different


def run(source, expected, config, output, repeats=1, reference=None,discard=False,discard_source=False,gdal_only=False,order_offset=0):
    output=Path(output).resolve();output.mkdir()
    prior=None
    if gdal_only and not reference:raise ValueError('GDAL-only profiling requires a pinned prior shard reference')
    if reference:
        prior=json.loads((Path(reference)/'report.json').read_text())
        if (prior.get('status')!='candidate-only' or prior.get('source_sha256')!=expected or
                prior.get('configuration_sha256')!=build.sha256(config) or
                prior.get('output_sha256')!=build.sha256(Path(reference)/'water.tif')):
            raise ValueError('prior shard reference identity mismatch')
    results=[];document={'source_sha256':expected,'configuration_sha256':build.sha256(config),'results':results}
    for repeat in range(repeats):
        engines=('gdal',) if gdal_only else (('python','gdal') if (repeat+order_offset)%2==0 else ('gdal','python'))
        pair={}
        for engine in engines:
            destination=output/f'{repeat:02d}-{engine}'
            started_utc=datetime.now(timezone.utc).isoformat()
            started=time.perf_counter()
            build.run(source,expected,destination,config,engine=engine)
            elapsed=time.perf_counter()-started
            ended_utc=datetime.now(timezone.utc).isoformat()
            report=json.loads((destination/'report.json').read_text())
            if report.get('status')!='candidate-only':raise ValueError('benchmark shard is incomplete')
            pair[engine]={'output':str(destination),'seconds':elapsed,
                          'started_at_utc':started_utc,'ended_at_utc':ended_utc,
                          'counts':report['counts'],'mask_sha256':report['output_sha256'],
                          'report_sha256':build.sha256(destination/'report.json'),
                          'batch_timings':report.get('batch_timings'),'gdal_kernel':report.get('gdal_kernel')}
        if 'python' in pair and pair['python']['counts'] != pair['gdal']['counts']:
            raise ValueError('GDAL/reference feature counts differ')
        if prior and prior.get('counts')!=pair['gdal']['counts']:
            raise ValueError('GDAL/prior-reference feature counts differ')
        different=compare(pair['python']['output'] if 'python' in pair else reference,pair['gdal']['output'])
        result={'repeat':repeat,'runs':pair,'different_pixels':different,
                'speedup':pair['python']['seconds']/pair['gdal']['seconds'] if 'python' in pair else None}
        if reference:result['different_reference_pixels']=compare(reference,pair['gdal']['output'])
        results.append(result)
        (output/'benchmark.json').write_text(json.dumps(document,indent=2)+'\n')
        if different or result.get('different_reference_pixels',0):
            raise ValueError('GDAL/reference pixels differ')
        baseline_hash=pair['python']['mask_sha256'] if 'python' in pair else prior['output_sha256']
        if discard and baseline_hash==pair['gdal']['mask_sha256']:
            result['discarded_matching_outputs']=[]
            for run in pair.values():
                path=Path(run['output'])/'water.tif'
                if path.is_symlink() or build.sha256(path)!=run['mask_sha256']:raise ValueError('benchmark mask changed before cleanup')
                receipt={'path':str(path.relative_to(output)),'sha256':run['mask_sha256'],'bytes':path.stat().st_size}
                path.unlink();result['discarded_matching_outputs'].append(receipt)
            (output/'benchmark.json').write_text(json.dumps(document,indent=2)+'\n')
    if discard_source:
        source=Path(source)
        if source.is_symlink() or build.sha256(source)!=expected:raise ValueError('owned source changed before cleanup')
        receipt={'name':source.name,'sha256':expected,'bytes':source.stat().st_size}
        source.unlink();document['discarded_owned_source']=receipt
        (output/'benchmark.json').write_text(json.dumps(document,indent=2)+'\n')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('sha256');parser.add_argument('config');parser.add_argument('output')
    parser.add_argument('--repeats',type=int,default=1)
    parser.add_argument('--reference',help='optional prior complete shard output directory')
    parser.add_argument('--gdal-only',action='store_true',help='profile GDAL batches against a pinned prior mask; does not produce a fresh paired speedup')
    parser.add_argument('--discard-matching-outputs',action='store_true',help='remove only new byte-identical benchmark mask copies after verification')
    parser.add_argument('--discard-owned-source',action='store_true',help='after full success, remove only a regenerable source copy downloaded specifically for this benchmark')
    args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    print(json.dumps(run(args.source,args.sha256,args.config,args.output,args.repeats,args.reference,args.discard_matching_outputs,args.discard_owned_source,args.gdal_only),indent=2))
