#!/usr/bin/env python3
"""Pair complete original/numeric prefill APIs on one ordinary pinned plan."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from benchmark_prefill import compare_prefill
from benchmark_stage import digest, environment, invoke_stage
import benchmark_prefill, benchmark_stage, execution_state, exclusive_outputs, run_pipeline
from exclusive_outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive, validate_fresh_output
from execution_state import code_identity
from run_pipeline import stage_scratch


OPTIONS = ('--allow-unverified-snapshot', '--allow-draft-snapshot',
           '--allow-research-shore', '--allow-historical-v6')


def run_pair(plan, input_root, out, code_root, *, options=(), candidate_first=False, arrow_spans=False):
    plan, input_root, code_root = (Path(path).resolve(strict=True) for path in (plan,input_root,code_root))
    out = validate_fresh_output(input_root, out, (plan,))
    if not input_root.is_dir() or any(option not in OPTIONS for option in options):
        raise ValueError('existing input root and explicit supported prefill options are required')
    builder = code_root / 'scripts/v7-replay/build_prefill.py'
    if not builder.is_file():raise ValueError('selected prefill producer is missing')
    plan_pin=digest(plan); sources=code_identity(code_root/'scripts')
    supports={'benchmark':Path(__file__), **{module.__name__:Path(module.__file__)
              for module in (benchmark_prefill,benchmark_stage,execution_state,exclusive_outputs,run_pipeline)}}
    support_pins={name:digest(path) for name,path in supports.items()}
    invocation={'schema':'worldatlas-prefill-column-pair-v1','source_plan_sha256':plan_pin,
                'code_sha256':sources,'benchmark_support_sha256':support_pins,
                'environment':environment(),'options':list(options),
                'candidate_first':bool(candidate_first),'execution_mode':'in-process-python-api',
                'candidate_span_reader':'pyarrow-columns' if arrow_spans else 'legacy-tuples',
                'scope':'Complete stages on already-local inputs, including each producer input/hash validation and RLE writing; module loading included, interpreter startup and comparison excluded.'}
    create_directory_exclusive(out);scratch=out/'scratch';scratch.mkdir()
    write_json_exclusive(out/'invocation.json',invocation,indent=2)
    names=['tuple-reference','column-candidate']
    if candidate_first:names.reverse()
    timings={}
    for name in names:
        arguments=['--plan',str(plan),'--input-root',str(input_root),'--out',str(out/name),*options]
        if name=='column-candidate':arguments.append('--column-engine')
        if name=='column-candidate' and arrow_spans:arguments.append('--arrow-spans')
        started_utc=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
        with create_text_exclusive(out/(name+'.log')) as log,stage_scratch(str(scratch)):
            invoke_stage(builder,arguments,log)
        elapsed=time.perf_counter()-started;ended_utc=datetime.now(timezone.utc).isoformat()
        audit=json.loads((out/name/'prefill-audit.json').read_text())
        timings[name]={'stage_wall_seconds':elapsed,'producer_processing_seconds':audit['processing_elapsed_seconds'],
                       'started_utc':started_utc,'completed_utc':ended_utc}
    if (digest(plan)!=plan_pin or code_identity(code_root/'scripts')!=sources
            or any(digest(path)!=support_pins[name] for name,path in supports.items())):
        raise ValueError('prefill benchmark plan or source code changed')
    comparison=compare_prefill(out/'tuple-reference',out/'column-candidate')
    result={**invocation,'timings':timings,'comparison':comparison,
            'limitations':['One sequential pair does not balance input/cache order.',
                           'This tests the supplied complete plan, not raw-source production or a full water pipeline.']}
    write_json_exclusive(out/'report.json',result,indent=2)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','input-root','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--code-root',type=Path,default=Path(__file__).resolve().parents[2])
    for option in OPTIONS:ap.add_argument(option,action='store_true')
    ap.add_argument('--candidate-first',action='store_true')
    ap.add_argument('--arrow-spans',action='store_true',help='candidate only: stream Arrow span columns')
    args=ap.parse_args()
    options=[option for option in OPTIONS if getattr(args,option[2:].replace('-','_'))]
    print(json.dumps(run_pair(args.plan,args.input_root,args.out,args.code_root,
                              options=options,candidate_first=args.candidate_first,arrow_spans=args.arrow_spans)))


if __name__=='__main__':main()
