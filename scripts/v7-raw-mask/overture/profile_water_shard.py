#!/usr/bin/env python3
"""Profile a complete pinned shard through Python APIs, then verify its mask.

Instrumentation changes timings. This is attribution evidence, not a speed
comparison. The normal uninstrumented benchmark remains the timing authority.
"""
import argparse
import cProfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
from pathlib import Path
import pstats
import time

import benchmark_water_shard as benchmark

HERE=Path(__file__).resolve().parent


def run(source,expected,config,reference,output):
    source,config,reference,output=map(lambda p:Path(p).resolve(),(source,config,reference,output))
    build=benchmark.build
    for name,module in (('benchmark_water_shard.py',benchmark),('rasterize_water_shard.py',build)):
        if Path(module.__file__).resolve()!=HERE/name:raise ValueError('profiler module resolved outside selected checkout')
    if any(path.is_relative_to(output) or output.is_relative_to(path.parent) for path in (source,config,reference/'report.json')):
        raise ValueError('profile output must be outside input directories and must not contain inputs')
    prior=json.loads((reference/'report.json').read_bytes())
    config_hash=build.sha256(config);prior_hash=build.sha256(reference/'report.json')
    if (prior.get('status')!='candidate-only' or prior.get('source_sha256')!=expected or
            prior.get('configuration_sha256')!=config_hash or
            prior.get('output_sha256')!=build.sha256(reference/'water.tif')):
        raise ValueError('profile reference identity mismatch')
    code_paths={name:HERE/name for name in ('profile_water_shard.py','benchmark_water_shard.py','rasterize_water_shard.py','water_batch.py')}
    code={name:build.sha256(path) for name,path in code_paths.items()}
    output.mkdir();profiler=cProfile.Profile();started_utc=datetime.now(timezone.utc).isoformat()
    started=time.perf_counter()
    try:
        with (output/'producer.log').open('x') as log,redirect_stdout(log):
            result=profiler.runcall(build.run,source,expected,output/'gdal',config,engine='gdal')
    finally:
        profiler.dump_stats(str(output/'profile.pstats'))
    elapsed=time.perf_counter()-started;ended_utc=datetime.now(timezone.utc).isoformat()
    different=benchmark.compare(reference,output/'gdal')
    if different or result['counts']!=prior['counts']:raise ValueError('profile output differs from pinned reference')
    if (build.sha256(config)!=config_hash or build.sha256(reference/'report.json')!=prior_hash or
            build.sha256(reference/'water.tif')!=prior['output_sha256'] or
            any(build.sha256(code_paths[name])!=digest for name,digest in code.items())):
        raise ValueError('profile code or reference changed during processing')
    functions=[]
    for (filename,line,function),(primitive,total,self_seconds,cumulative,_) in pstats.Stats(profiler).stats.items():
        functions.append({'file':filename,'line':line,'function':function,'primitive_calls':primitive,
            'total_calls':total,'self_seconds':self_seconds,'cumulative_seconds':cumulative})
    functions.sort(key=lambda entry:entry['cumulative_seconds'],reverse=True)
    report={'schema':'worldatlas-water-python-profile-v1','status':'profiled-input-matches-pinned-reference',
        'source_sha256':expected,'configuration_sha256':config_hash,'script_sha256':code,
        'reference_report_sha256':prior_hash,'profiled_report_sha256':build.sha256(output/'gdal/report.json'),
        'counts':result['counts'],'different_pixels':different,'profiled_wall_seconds':elapsed,
        'started_at_utc':started_utc,'ended_at_utc':ended_utc,'functions':functions,
        'limitations':'cProfile adds per-call overhead. Self time includes native work behind Python bindings; cumulative times overlap and must not be summed. No production speedup is inferred.'}
    with (output/'profile.json').open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','sha256','config','reference','output'):parser.add_argument(name)
    args=parser.parse_args();report=run(args.source,args.sha256,args.config,args.reference,args.output)
    print(json.dumps({name:report[name] for name in ('status','profiled_wall_seconds','different_pixels')},indent=2))


if __name__=='__main__':main()
