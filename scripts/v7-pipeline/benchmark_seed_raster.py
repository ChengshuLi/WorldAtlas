#!/usr/bin/env python3
"""Compare serial/parallel Python-API seed builds from authenticated sources.

Recreated polygons must match archived source geometry bytes. Old seed labels
are expected outputs only, never assignments or rasterizer inputs. This is a
research kernel replay, not a final-land pipeline or geography acceptance.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from benchmark_land_sweep import STAGE2, digest
from compare_land_sweeps import source_module
from exclusive_outputs import create_directory_exclusive, write_json_exclusive

RASTER=STAGE2.parent/'neon-mainland-regions-20261104/rasterizer'


def configuration(staged, recovered):
    plan=json.loads((staged/'plan.json').read_bytes());assets=plan['assets']
    report_path=recovered/'report.json';sources=json.loads(report_path.read_bytes())
    if (sources['status']!='exact-pinned-polygons-recreated-with-fresh-closure-proofs' or
            sources['publishable'] is not False or sources['staging_plan_sha256']!=digest(staged/'plan.json')):
        raise ValueError('authenticated fresh source-region report required')
    paths={name:staged/name for name in ('fresh-stage2-seed-report','fresh-stage2-core-config','fresh-components-rows','fresh-components-runs')}
    for name,path in paths.items():
        if digest(path)!=assets[name]['sha256'] or path.stat().st_size!=assets[name]['size_bytes']:
            raise ValueError('staged source differs: '+name)
    seed=json.loads(paths['fresh-stage2-seed-report'].read_bytes());core=json.loads(paths['fresh-stage2-core-config'].read_bytes())
    archive=staged/'additional-metadata/fresh-stage2-rasterizer-report'
    if digest(archive)!=seed['rasterizer_report_sha256'] or digest(archive)!=sources['rasterizer_report_sha256']:
        raise ValueError('archived source/report binding differs')
    expected=json.loads(archive.read_bytes())
    if expected['grid']!=plan['grid'] or core['grid']!=plan['grid'] or seed['grid']!=plan['grid']:
        raise ValueError('grid source differs')
    regions=[]
    for region in sources['regions']:
        path=Path(region['geometry']['path']).resolve(strict=True)
        if digest(path)!=region['geometry']['sha256'] or not any(pin['sha256']==digest(path) for pin in expected['input_pins']):
            raise ValueError('recreated polygon differs')
        proof=path.with_name(path.name+'.report.json')
        if digest(proof)!=region['report_sha256']:raise ValueError('fresh polygon proof differs')
        regions.append({'id':region['region_id'],'geometry':region['geometry'],
            'witnesses':[{'lon':float(w['lon']),'lat':float(w['lat']),'inside':w['inside']} for w in region['witnesses']]})
    rules=[{'component_id':rule['component_id_current_generation_only'],'region_id':rule['region_id'],
        'inside_code':rule['inside_code'],'outside_code':rule['outside_code']} for rule in seed['seed_rules']]
    component={key:{'path':str(paths[name].resolve()),'sha256':assets[name]['sha256']}
        for key,name in (('component_rows','fresh-components-rows'),('component_runs','fresh-components-runs'))}
    for key,pin in component.items():
        if expected[key+'_sha256']!=pin['sha256'] or core['inputs'][key]['sha256']!=pin['sha256']:
            raise ValueError('component source differs')
    config={'schema':'direct-region-seed-research-v1','grid':{**plan['grid'],'crs':'EPSG:4326'},
        **component,'regions':regions,'rules':rules,'evidence':[{'path':str(report_path.resolve()),'sha256':digest(report_path)}],
        'strip_rows':seed['resource_controls']['strip_rows'],'reserve_bytes':0}
    return config,expected


def run(staged, recovered, out, workers):
    if type(workers) is not int or workers<1:raise ValueError('positive workers required')
    config,expected=configuration(staged,recovered)
    sources={name:digest(RASTER/name) for name in ('build_seed.py','seed_runtime.py')}
    builder=source_module('_seed_raster_benchmark',RASTER/'build_seed.py',sources['build_seed.py'])
    create_directory_exclusive(out)
    invocation={'schema':'worldatlas-seed-raster-api-pair-v1','driver_sha256':digest(Path(__file__)),
        'staged_plan_sha256':digest(staged/'plan.json'),'recovered_report_sha256':digest(recovered/'report.json'),
        'code_sha256':sources,'workers':[1,workers],'config':config,'started_at_utc':datetime.now(timezone.utc).isoformat()}
    write_json_exclusive(out/'invocation.json',invocation,indent=2)
    create_directory_exclusive(out/'requests')
    results=[]
    for name,concurrency in (('serial',1),('parallel',workers)):
        cfg=out/'requests'/(name+'.json');write_json_exclusive(cfg,{**config,'workers':concurrency},indent=2)
        started_at=datetime.now(timezone.utc).isoformat();start=time.perf_counter()
        result=builder.build(cfg,out/name);elapsed=time.perf_counter()-start
        for field in ('outputs_sha256','rule_population','category_cell_counts'):
            if result[field]!=expected[field]:raise ValueError(name+' complete raster differs: '+field)
        results.append({'variant':name,'workers':concurrency,'elapsed_seconds':elapsed,
            'started_at_utc':started_at,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'outputs_sha256':result['outputs_sha256'],'report_sha256':digest(out/name/'report.json')})
    if {name:digest(RASTER/name) for name in sources}!=sources or digest(Path(__file__))!=invocation['driver_sha256']:
        raise ValueError('benchmark code changed')
    if configuration(staged,recovered)!=(config,expected):raise ValueError('source identity changed')
    report={**invocation,'status':'complete-seed-streams-and-populations-exact','publishable':False,
        'results':results,'serial_over_parallel':results[0]['elapsed_seconds']/results[1]['elapsed_seconds'],
        'limitations':['One serial-first pair; cache order is not balanced.',
            'This times Python-API seed rasterization/composition only, not an entire land pipeline.',
            'Archived expected outputs and reports are used only after each fresh build.']}
    write_json_exclusive(out/'comparison.json',report,indent=2)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged-inputs',type=Path,required=True);parser.add_argument('--recovered-regions',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1)
    args=parser.parse_args();print(json.dumps(run(args.staged_inputs,args.recovered_regions,args.out,args.workers),indent=2))
