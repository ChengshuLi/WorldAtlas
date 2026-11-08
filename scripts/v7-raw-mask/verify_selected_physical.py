#!/usr/bin/env python3
"""Verify final physical streams from complete paired water masks and fresh land.

All processing uses ordinary Python stage functions. Land is unchanged and
shared once; this is a complete-input parity proof, not a paired total timing.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
if str(HERE/'overture') not in sys.path:sys.path.insert(0,str(HERE/'overture'))
from build import sha
import rasterize_land
import aggregate_compare
import compose_physical
import benchmark_selected_water


def pin(path):return {'path':str(Path(path).resolve()),'sha256':sha(path)}


def cached_land_configuration(cfg,selection,cache_root):
    """Resolve the supported cache layout, validating every consumed source pin."""
    cache_root=Path(cache_root).resolve();selection=Path(selection).resolve();checked={}
    def local(path):
        path=Path(path)
        if not path.is_absolute():path=selection.parent/path
        path=path.resolve(strict=True)
        if not path.is_relative_to(cache_root):raise ValueError('land source escapes selected input cache')
        return path
    def check(path,spec):
        path=local(path)
        if 'size_bytes' in spec and path.stat().st_size!=spec['size_bytes']:
            raise ValueError('cached land source size mismatch')
        if str(path) not in checked:
            if sha(path)!=spec['sha256']:
                raise ValueError('cached land source pin mismatch')
            checked[str(path)]=spec['sha256']
        elif checked[str(path)]!=spec['sha256']:raise ValueError('inconsistent cached land source pin')
        return path
    def resolve(spec):
        if isinstance(spec,str):return local(spec)
        if 'archive' in spec:
            archive=spec['archive'];member=Path(spec['member'])
            if member.is_absolute() or '..' in member.parts or '\\' in spec['member']:
                raise ValueError('unsafe land archive member')
            check(cache_root/'inputs'/archive['sha256']/Path(archive['r2_key']).name,archive)
            return check(cache_root/'inputs'/archive['sha256']/member,spec)
        if 'r2_key' in spec:
            return check(cache_root/'inputs'/spec['sha256']/Path(spec['r2_key']).name,spec)
        return check(spec['path'],spec)
    result=copy.deepcopy(cfg['sources']['land_config']['json'])
    for entry in result['land']:
        entry['dataset']=str(resolve(entry['dataset']))
        entry['files']=[{'path':str(resolve(spec)),'sha256':spec['sha256']} for spec in entry['files']]
    return result,checked


def run(selection,water_output,cache_root,output):
    code_paths={'verifier':HERE/'verify_selected_physical.py','land':HERE/'rasterize_land.py',
                'input_validation':HERE/'build.py','union':HERE/'overture/aggregate_compare.py',
                'composition':HERE/'compose_physical.py','paired_verifier':HERE/'overture/benchmark_selected_water.py'}
    modules={'land':rasterize_land,'input_validation':sys.modules[sha.__module__],
             'union':aggregate_compare,'composition':compose_physical,'paired_verifier':benchmark_selected_water}
    for name,module in modules.items():
        if Path(module.__file__).resolve()!=code_paths[name]:
            raise ValueError('physical verifier module resolved outside selected checkout: '+name)
    selection=Path(selection).resolve();data=selection.read_bytes();cfg=json.loads(data)
    if cfg.get('schema')!='worldatlas-end-to-end-pipeline-v1':
        raise ValueError('selected pipeline configuration required')
    if cfg['sources']['land_config']['json']['grid']!=cfg['sources']['water_config']['json']['grid']:
        raise ValueError('selected land and water grids differ')
    water_output=Path(water_output).resolve();receipt=water_output/'benchmark.json';water=json.loads(receipt.read_bytes())
    water_pin=pin(receipt)
    manifest=cfg['sources']['raw_manifest']['json'];files=manifest['files'];indices=list(range(len(files)))
    if (water.get('status')!='all-selected-inputs-pixels-and-diagnostics-identical' or
            water.get('scope')!='complete-manifest' or water.get('selected_ordinals')!=indices or
            water.get('selection_sha256')!=sha(selection) or
            [item['ordinal'] for item in water.get('results',[])]!=indices or manifest['file_count']!=len(files)):
        raise ValueError('complete matching all-shard parity receipt required')
    for name in ('rasterize_water_shard.py','water_batch.py'):
        if water['script_sha256'][name]!=sha(HERE/'overture'/name):
            raise ValueError('paired water producer changed')
    for i,item in enumerate(water['results']):
        benchmark_selected_water.verify_completed(item,files[i],water_output/'shards'/f'{i:05d}',
                                                  water_output/'configs/water-config.json',water['repeats'])
        for engine in ('python','gdal'):
            report=json.loads((water_output/'shards'/f'{i:05d}'/f'00-{engine}'/'report.json').read_bytes())
            if report['script_sha256']!=water['script_sha256']['rasterize_water_shard.py']:
                raise ValueError('paired rasterizer identity mismatch')
            if engine=='gdal' and report['gdal_kernel']['binding_sha256']!=water['script_sha256']['water_batch.py']:
                raise ValueError('paired GDAL binding identity mismatch')
    land,sources=cached_land_configuration(cfg,selection,cache_root)
    output=Path(output).resolve();output.mkdir();(output/'configs').mkdir()
    code={name:sha(path) for name,path in code_paths.items()};timings={}
    def document(name,value):
        path=output/'configs'/(name+'.json');path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');return path
    def stage(name,call):
        utc=datetime.now(timezone.utc).isoformat();started=time.perf_counter();result=call()
        timings[name]={'processing_seconds':time.perf_counter()-started,'started_at_utc':utc,
                       'ended_at_utc':datetime.now(timezone.utc).isoformat()}
        return result
    land_config=document('land',land)
    stage('land',lambda:rasterize_land.run(land_config,output/'land'))
    raw_manifest=document('raw-manifest',manifest);grid=land['grid'];unions={}
    for engine in ('python','gdal'):
        shards=[]
        for i,item in enumerate(water['results']):
            folder=water_output/'shards'/f'{i:05d}'/f'00-{engine}'
            shards.append({**pin(folder/'water.tif'),'status':'candidate-only','report':pin(folder/'report.json')})
        request={'schema':'water-union-comparison-v1','grid':grid,'selection_notes':cfg['selection_notes'],
            'source_manifest':pin(raw_manifest),'minimum_free_bytes':cfg['physical_controls']['minimum_free_bytes'],
            'rows_per_block':cfg['physical_controls'].get('union_rows_per_block',128),
            'shard_count':len(shards),'shards':shards}
        request=document('union-'+engine,request);target=output/('union-'+engine)
        stage('union-'+engine,lambda:aggregate_compare.run(request,target));unions[engine]=target/'water-union.tif'
    outputs={}
    for engine in ('python','gdal'):
        request={'schema':'candidate-physical-composition-v1','grid':grid,'selection_notes':cfg['selection_notes'],
            'minimum_free_bytes':cfg['physical_controls']['minimum_free_bytes'],
            'rows_per_block':cfg['physical_controls'].get('physical_rows_per_block',128),
            'land':pin(output/'land/land.tif'),'water':pin(unions[engine])}
        if engine=='gdal':
            reference=output/'physical-python'
            request.update(reference_mask=pin(reference/'physical-dry.tif'),reference_streams={
                'rows':pin(reference/'rows.u32le'),'runs':pin(reference/'runs.u32le')})
        request=document('compose-'+engine,request);target=output/('physical-'+engine)
        outputs[engine]=stage('physical-'+engine,lambda:compose_physical.main(request,target))
    candidate=outputs['gdal']
    if (candidate['candidate_extra_land_cells'] or candidate['candidate_missing_land_cells'] or
            any(outputs['python']['output_sha256'][name]!=candidate['output_sha256'][name]
                for name in ('rows.u32le','runs.u32le'))):
        raise ValueError('complete physical mask or stream parity failed')
    if selection.read_bytes()!=data or sha(receipt)!=water_pin['sha256']:
        raise ValueError('selected input or paired water receipt changed')
    if any(sha(path)!=code[name] for name,path in code_paths.items()) or any(sha(path)!=digest for path,digest in sources.items()):
        raise ValueError('physical verifier code or land source changed')
    result={'status':'complete-physical-pixels-and-streams-identical','selection':pin(selection),
        'paired_water_receipt':water_pin,'land_source_sha256':sources,'script_sha256':code,'timings':timings,
        'grid':grid,'grid_cells':grid['width']*grid['height'],'raw_shard_count':len(files),
        'raw_source_rows':sum(item['results'][0]['runs']['python']['counts']['rows'] for item in water['results']),
        'runtime':{'python':sys.version,'numpy':compose_physical.np.__version__,
                   'gdal':rasterize_land.gdal.VersionInfo('--version')},
        'scope':'all raw water shards plus one fresh unchanged land raster; both complete unions and physical compositions',
        'different_physical_cells':0,'output_sha256':candidate['output_sha256'],
        'producer_reports':{name:pin(output/name/'report.json') for name in
            ('land','union-python','union-gdal','physical-python','physical-gdal')}}
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selected_pipeline_config');parser.add_argument('paired_water_output')
    parser.add_argument('input_cache_root');parser.add_argument('new_output')
    args=parser.parse_args()
    print(json.dumps(run(args.selected_pipeline_config,args.paired_water_output,args.input_cache_root,args.new_output),indent=2))
