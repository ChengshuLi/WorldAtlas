#!/usr/bin/env python3
"""Guarded additive reproduction wrapper for the retained Croatian #419 work."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
SCOPE = OWNED / 'source/issue-evidence-scope.json'
BASELINE = '7646e0962afab6cc4f566439bb2f96890ae4b91e'
GEOMETRY = ROOT / 'data/regional-review/regional-review-c64d17e99f61d668/source/geoboundaries-9469f09/HRV/ADM2/geoBoundaries-HRV-ADM2.geojson'
SUMMARY = ROOT / 'data/regional-review/regional-review-ce7798317652c0c2/source/dzs-census-2021-summary-tables.xlsx'
DETAIL = ROOT / 'data/regional-review/regional-review-ce7798317652c0c2/source/dzs-census-2021-detail-extract.csv'
EXPECTED = {
 'summary': '99feecc93627db02509aee7d625b391c33a69f201f377464ac15c2fd7c16f20f',
 'detail': '225021e29f4ec2eeeffda3801031f4c0587241e91eed984394c9d2d56b09785c',
 'geometry': '68a317129a0c295fd8baf7acc0f31ffefdf65ff2f1f62f8ed90a765cc57cf01e',
}
FILES = ('assessment-summary.json','province-completeness.csv','scoped-location-assessments.csv')

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def preflight(scope_override=None):
    issue=json.loads(SCOPE.read_text())
    ids=issue['subject_ids'] if scope_override is None else scope_override
    if len(ids)!=224 or len(set(ids))!=224 or sorted(ids)!=sorted(issue['subject_ids']):
        raise ValueError('exact issue subject identity differs before output creation')
    if sha(('\n'.join(sorted(ids))).encode()) != 'c5816fc5587099904fd5c5cff51801676ec361606153cb39c70e9fb19ef0f116':
        raise ValueError('historical issue subject digest mismatch')
    for key,path in [('summary',SUMMARY),('detail',DETAIL),('geometry',GEOMETRY)]:
        actual=sha(path.read_bytes())
        if actual != EXPECTED[key]: raise ValueError(f'{key} complete source SHA-256 mismatch: {actual}')
    for key,expected in issue['pins'].items():
        commit,path=key.split(':',1)
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'])
        if sha(raw)!=expected: raise ValueError(f'issue baseline pin mismatch: {key}')
    if not (ROOT/'.git').exists(): raise ValueError('expected repository checkout missing')
    return ids

def publish_exclusive(scratch: Path, dest: Path, interrupt_after=None):
    dest.mkdir(parents=False, exist_ok=False)
    for i,name in enumerate(FILES,1):
        data=(scratch/name).read_bytes()
        with (dest/name).open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if interrupt_after == i: raise RuntimeError('injected interruption after exclusive output write')

def run(dest: Path):
    # Refuse traversal, symlinks and every existing named vintage before any build.
    dest=dest.absolute()
    try: dest.relative_to(OWNED/'evidence'); within=True
    except ValueError: within=False
    if dest.is_symlink() or not within or dest.exists():
        raise FileExistsError('output must be a new, non-symlink named vintage under this packet evidence directory')
    ids=preflight()
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.reproduce-',dir=dest.parent) as tmp:
        scratch=Path(tmp)
        sys.path.insert(0,str(ROOT/'data/regional-review/regional-review-ce7798317652c0c2'))
        import build_assessment as original
        original.build(BASELINE,scratch,GEOMETRY)
        publish_exclusive(scratch,dest)
    return {'destination':str(dest.relative_to(ROOT)), 'subjects':len(ids), 'outputs':{n:sha((dest/n).read_bytes()) for n in FILES}}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output-dir',required=True); a=p.parse_args()
    print(json.dumps(run(Path(a.output_dir)),sort_keys=True))
if __name__=='__main__': main()
