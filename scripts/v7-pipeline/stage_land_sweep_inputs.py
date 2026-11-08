#!/usr/bin/env python3
"""Stage exact existing land-sweep evidence, without launching a pipeline.

Metadata-only by default. --stage-streams additionally reads the pinned global
RLE/root artifacts. Source configurations/reports are preserved byte for byte;
no historical paths are rewritten and no cloud object is changed.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import re

from benchmark_land_sweep import digest

METADATA = ('fresh-components-manifest','fresh-components-report','fresh-physical-report',
    'fresh-stage2-core-config','fresh-stage2-derived-manifest','fresh-stage2-hints-report',
    'fresh-stage2-land-report','fresh-stage2-seed-report','fresh-stage2-writer-report')
STREAMS = ('fresh-components-rows','fresh-components-runs','fresh-physical-rows',
    'fresh-physical-runs','fresh-stage2-hint-roots','fresh-stage2-hints',
    'fresh-stage2-seed-rows','fresh-stage2-seed-runs','fresh-stage2-land-rows','fresh-stage2-land-runs')
INPUTS = {'component_rows':'fresh-components-rows','component_runs':'fresh-components-runs',
    'physical_rows':'fresh-physical-rows','physical_runs':'fresh-physical-runs',
    'seed_rows':'fresh-stage2-seed-rows','seed_runs':'fresh-stage2-seed-runs',
    'seed_report':'fresh-stage2-seed-report','hint_roots':'fresh-stage2-hint-roots','hint_codes':'fresh-stage2-hints'}


def plan(catalog_path, config_path):
    catalog=json.loads(catalog_path.read_bytes());config=json.loads(config_path.read_bytes())
    selected={}
    for name in (*METADATA,*STREAMS):
        matches=[row for row in catalog if row.get('source_id')==name]
        if len(matches)!=1:
            raise ValueError('one exact catalog entry required: '+name)
        row=matches[0]
        if (not re.fullmatch(r'[0-9a-f]{64}',row['sha256']) or not row['r2_bucket'] or
                not row['r2_key'] or int(row['size_bytes'])<0):
            raise ValueError('invalid catalog pin: '+name)
        selected[name]={key:row[key] for key in ('source_id','r2_bucket','r2_key','sha256')}
        selected[name]['size_bytes']=int(row['size_bytes'])
    if digest(config_path)!=selected['fresh-stage2-core-config']['sha256']:
        raise ValueError('core config differs from catalog pin')
    for name,source in INPUTS.items():
        if config['inputs'][name]['sha256']!=selected[source]['sha256']:
            raise ValueError('catalog/core input mismatch: '+name)
    return {'schema':'worldatlas-land-sweep-staging-plan-v1','catalog_sha256':digest(catalog_path),
            'core_config_sha256':digest(config_path),'grid':config['grid'],'assets':selected,
            'scope':'replay coverage and writer from existing evidence, not fresh geographic decisions',
            'stream_bytes':sum(selected[name]['size_bytes'] for name in STREAMS)}


def fetch(client, pin, destination):
    if destination.exists():
        if destination.stat().st_size!=pin['size_bytes'] or digest(destination)!=pin['sha256']:
            raise ValueError('existing staged input differs: '+str(destination))
        return
    response=client.get_object(Bucket=pin['r2_bucket'],Key=pin['r2_key'])
    with closing(response['Body']) as body, destination.open('xb') as stream:
        if response['ContentLength']!=pin['size_bytes']:
            raise ValueError('cloud input length differs: '+pin['source_id'])
        for chunk in iter(lambda:body.read(1 << 20),b''):
            stream.write(chunk)
    if destination.stat().st_size!=pin['size_bytes'] or digest(destination)!=pin['sha256']:
        raise ValueError('cloud input size/hash differs: '+pin['source_id'])


def stage(catalog_path, config_path, out, client, *, stage_streams=False):
    identity=plan(catalog_path,config_path)
    if not out.exists():out.mkdir(mode=0o700)
    identity_path=out/'plan.json'
    if identity_path.exists():
        if json.loads(identity_path.read_bytes())!=identity:
            raise ValueError('staging identity changed')
    else:
        with identity_path.open('x') as stream:json.dump(identity,stream,sort_keys=True,indent=2);stream.write('\n')
    for name in (*METADATA,*(STREAMS if stage_streams else ())):
        fetch(client,identity['assets'][name],out/name)
    report=json.loads((out/'fresh-stage2-land-report').read_bytes())
    checkpoint_hash=report['checkpoint_sha256']
    core=identity['assets']['fresh-stage2-core-config']
    prefix=core['r2_key'].split('/sha256/')[0]+'/'
    candidates=[]
    for page in client.get_paginator('list_objects_v2').paginate(Bucket=core['r2_bucket'],Prefix=prefix):
        for item in page.get('Contents',[]):
            if 'checkpoint' in item['Key'].lower() or checkpoint_hash in item['Key']:
                candidates.append({'r2_bucket':core['r2_bucket'],'r2_key':item['Key'],'size_bytes':item['Size']})
    summary={'schema':'worldatlas-land-sweep-staging-report-v1','status':'streams-staged' if stage_streams else 'metadata-staged',
        'grid':identity['grid'],'stream_bytes':identity['stream_bytes'],'checkpoint_sha256':checkpoint_hash,
        'checkpoint_candidates':candidates,'checkpoint_search_prefix':prefix,
        'inputs':{name:{'path':str((out/source).resolve()),'sha256':identity['assets'][source]['sha256']}
                  for name,source in INPUTS.items() if source in (*METADATA,*(STREAMS if stage_streams else ()))},
        'limitations':'No source rebuild or geodesic search was run. A completed assignment checkpoint is still required for independent writer replay.'}
    target=out/('streams-staged.json' if stage_streams else 'metadata-staged.json')
    data=json.dumps(summary,sort_keys=True,indent=2)+'\n'
    if target.exists():
        if target.read_text()!=data:raise ValueError('staging result changed; inspect existing evidence')
    else:
        with target.open('x') as stream:stream.write(data)
    if identity!=plan(catalog_path,config_path):raise ValueError('staging source identity changed')
    return summary


def stage_search_inputs(catalog_path, config_path, out, client):
    identity=plan(catalog_path,config_path)
    if json.loads((out/'plan.json').read_bytes())!=identity:
        raise ValueError('staging identity changed')
    catalog=json.loads(catalog_path.read_bytes());config=json.loads(config_path.read_bytes())
    sources={'representatives':'fresh-stage2-representatives','tile_manifest':'fresh-stage2-tile-manifest',
             'decision_snapshot':'v24-stage2-land-snapshot'}
    pins={}
    for name,source in sources.items():
        matches=[row for row in catalog if row.get('source_id')==source]
        if len(matches)!=1 or matches[0]['sha256']!=config['inputs'][name]['sha256']:
            raise ValueError('search catalog/core input mismatch: '+name)
        pin=dict(matches[0]);pin['size_bytes']=int(pin['size_bytes'])
        fetch(client,pin,out/source)
        pins[name]={'path':str((out/source).resolve()),'sha256':pin['sha256'],
                    'size_bytes':pin['size_bytes'],'r2_bucket':pin['r2_bucket'],'r2_key':pin['r2_key']}
    result={'schema':'worldatlas-land-search-staged-inputs-v1','parent_plan_sha256':digest(out/'plan.json'),'inputs':pins}
    target=out/'search-inputs.json'
    if target.exists():
        if json.loads(target.read_bytes())!=result:raise ValueError('search staging identity changed')
    else:
        with target.open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--core-config',type=Path,required=True)
    parser.add_argument('--endpoint-url',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--stage-streams',action='store_true')
    parser.add_argument('--stage-search',action='store_true',help='stage pinned representatives, manifest and snapshot for a fresh in-process search')
    args=parser.parse_args()
    if not re.fullmatch(r'https://[0-9a-f]{32}(?:\.(?:eu|us|fedramp))?\.r2\.cloudflarestorage\.com',args.endpoint_url):
        raise ValueError('an HTTPS Cloudflare R2 account endpoint is required')
    import boto3
    with closing(boto3.client('s3',endpoint_url=args.endpoint_url,region_name='auto')) as client:
        result=stage(args.catalog,args.core_config,args.out,client,stage_streams=args.stage_streams)
        if args.stage_search:result['search_inputs']=stage_search_inputs(args.catalog,args.core_config,args.out,client)
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
