#!/usr/bin/env python3
"""Compare complete raw-shard reference/native runs with exact pixel checks."""
import argparse
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


def run(source, expected, config, output, repeats=1, reference=None,discard=False,discard_source=False,native_only=False):
    output=Path(output).resolve();output.mkdir()
    prior=None
    if native_only and not reference:raise ValueError('native-only profiling requires a pinned prior shard reference')
    if reference:
        prior=json.loads((Path(reference)/'report.json').read_text())
        if (prior.get('status')!='candidate-only' or prior.get('source_sha256')!=expected or
                prior.get('configuration_sha256')!=build.sha256(config) or
                prior.get('output_sha256')!=build.sha256(Path(reference)/'water.tif')):
            raise ValueError('prior shard reference identity mismatch')
    results=[];document={'source_sha256':expected,'configuration_sha256':build.sha256(config),'results':results}
    for repeat in range(repeats):
        engines=('native',) if native_only else (('python','native') if repeat%2==0 else ('native','python'))
        pair={}
        for engine in engines:
            destination=output/f'{repeat:02d}-{engine}'
            started=time.perf_counter()
            build.run(source,expected,destination,config,engine=engine)
            elapsed=time.perf_counter()-started
            report=json.loads((destination/'report.json').read_text())
            if report.get('status')!='candidate-only':raise ValueError('benchmark shard is incomplete')
            pair[engine]={'output':str(destination),'seconds':elapsed,
                          'counts':report['counts'],'mask_sha256':report['output_sha256']}
        if 'python' in pair and pair['python']['counts'] != pair['native']['counts']:
            raise ValueError('native/reference feature counts differ')
        if prior and prior.get('counts')!=pair['native']['counts']:
            raise ValueError('native/prior-reference feature counts differ')
        different=compare(pair['python']['output'] if 'python' in pair else reference,pair['native']['output'])
        result={'repeat':repeat,'runs':pair,'different_pixels':different,
                'speedup':pair['python']['seconds']/pair['native']['seconds'] if 'python' in pair else None}
        if reference:result['different_reference_pixels']=compare(reference,pair['native']['output'])
        results.append(result)
        (output/'benchmark.json').write_text(json.dumps(document,indent=2)+'\n')
        if different or result.get('different_reference_pixels',0):
            raise ValueError('native/reference pixels differ')
        baseline_hash=pair['python']['mask_sha256'] if 'python' in pair else prior['output_sha256']
        if discard and baseline_hash==pair['native']['mask_sha256']:
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
    parser.add_argument('--native-only',action='store_true',help='profile native changes against a pinned prior mask; does not produce a fresh paired speedup')
    parser.add_argument('--discard-matching-outputs',action='store_true',help='remove only new byte-identical benchmark mask copies after verification')
    parser.add_argument('--discard-owned-source',action='store_true',help='after full success, remove only a regenerable source copy downloaded specifically for this benchmark')
    args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    print(json.dumps(run(args.source,args.sha256,args.config,args.output,args.repeats,args.reference,args.discard_matching_outputs,args.discard_owned_source,args.native_only),indent=2))
