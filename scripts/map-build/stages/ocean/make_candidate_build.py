#!/usr/bin/env python3
"""Bind a completed physical candidate and draft decision snapshot for research."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'water'))
sys.path.insert(0, str(HERE.parents[1]))
from decision_snapshot import read_snapshot
from map_build.execution.outputs import write_json_exclusive


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(4<<20), b''): h.update(chunk)
    return h.hexdigest()


def build(snapshot_path, snapshot_sha, physical_dir, physical_report_sha, output):
    snapshot_path=Path(snapshot_path).resolve(); physical_dir=Path(physical_dir).resolve(); output=Path(output).resolve()
    snapshot=read_snapshot(snapshot_path,snapshot_sha,allow_draft=True)
    if snapshot['decision_revision']['status']!='draft': raise ValueError('candidate build requires a draft snapshot')
    if output.is_relative_to(physical_dir) or physical_dir.is_relative_to(output) or snapshot_path.is_relative_to(output):
        raise ValueError('output must be separate from physical inputs and snapshot')
    rp=physical_dir/'report.json'
    if sha(rp)!=physical_report_sha: raise ValueError('physical report hash mismatch')
    report=json.loads(rp.read_text()); hashes=report.get('output_sha256',{})
    if report.get('status')!='candidate-only': raise ValueError('completed physical candidate required')
    for name in ('rows.u32le','runs.u32le','physical-dry.tif'):
        if sha(physical_dir/name)!=hashes.get(name): raise ValueError(f'physical output hash mismatch: {name}')
    import pyproj
    doc={'schema':'worldatlas-direct-candidate-build-v1','status':'unverified-research-not-published',
         'decision_snapshot_sha256':snapshot_sha,'decision_revision':snapshot['decision_revision']['id'],
         'entity_revision':snapshot['decision_revision']['entity_revision'],'grid':report['grid'],
         'physical_report_sha256':physical_report_sha,'physical_rows_sha256':hashes['rows.u32le'],
         'physical_runs_sha256':hashes['runs.u32le'],'physical_mask_sha256':hashes['physical-dry.tif'],
         'software_versions':{'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},
         'limitations':'Research input binding only; neither decision authority nor source correctness is established.'}
    if (sha(snapshot_path)!=snapshot_sha or sha(rp)!=physical_report_sha
            or any(sha(physical_dir/name)!=hashes[name] for name in ('rows.u32le','runs.u32le','physical-dry.tif'))):
        raise ValueError('input changed during build')
    write_json_exclusive(output,doc,indent=2)
    return doc


def main(argv=None, *, emit=print):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','snapshot-sha256','physical-dir','physical-report-sha256','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--allow-draft-snapshot',action='store_true')
    a=p.parse_args(argv)
    if not a.allow_draft_snapshot: raise ValueError('explicit draft research opt-in required')
    build(a.snapshot,a.snapshot_sha256,a.physical_dir,a.physical_report_sha256,a.out)
    emit(json.dumps({'status':'unverified-research-not-published','sha256':sha(a.out)}))

if __name__=='__main__':main()
