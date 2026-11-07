#!/usr/bin/env python3
"""Time the complete pinned prefill stage, then compare every RLE output byte."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from benchmark_stage import digest, run_stage
from exclusive_outputs import write_json_exclusive


def compare_prefill(reference,candidate):
    audits=[json.loads((root/'prefill-audit.json').read_text()) for root in (reference,candidate)]
    if any(a.get('schema')!='worldatlas-v7-prefill-class-rle-audit-v1' or a.get('status')!='staged-not-published'
           for a in audits):raise ValueError('invalid prefill audit')
    semantic=[{k:v for k,v in a.items() if k!='processing_elapsed_seconds'} for a in audits]
    if semantic[0]!=semantic[1]:raise ValueError('prefill scientific metadata differs')
    hashes={}
    for kind in ('rows','runs'):
        paths=[]
        for root,audit in zip((reference,candidate),audits):
            spec=audit['output'];name=spec[kind+'_path']
            if name!=Path(name).name or digest(root/name)!=spec.get(kind+'_sha256'):
                raise ValueError('prefill artifact hash mismatch')
            paths.append(root/name)
        with paths[0].open('rb') as left,paths[1].open('rb') as right:
            while True:
                a,b=left.read(1<<20),right.read(1<<20)
                if a!=b:raise ValueError('prefill RLE bytes differ: '+kind)
                if not a:break
        hashes[kind]=audits[0]['output'][kind+'_sha256']
    return {'status':'all-prefill-rle-bytes-and-audit-identical','output_sha256':hashes,
            'run_count':audits[0]['output']['run_count'],
            'prefill_class_cells_by_code':audits[0]['prefill_class_cells_by_code']}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('admitted','reference','code-root','out'):ap.add_argument('--'+key,type=Path,required=True)
    args=ap.parse_args();admission=json.loads(args.admitted.read_text())
    if Path(admission['invocation']['command'][1]).name!='build_prefill.py':
        raise ValueError('a complete prefill admission is required')
    timing=run_stage(args.admitted,args.code_root,args.out)
    comparison=compare_prefill(args.reference,args.out/'candidate')
    write_json_exclusive(args.out/'comparison.json',comparison,indent=2)
    print(json.dumps({'process_wall_seconds':timing['process_wall_seconds'],**comparison}))


if __name__=='__main__':main()
