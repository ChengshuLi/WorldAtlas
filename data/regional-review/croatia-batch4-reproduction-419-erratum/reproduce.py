#!/usr/bin/env python3
"""Guarded additive reproduction wrapper for the retained Croatian #419 work."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
SCOPE = OWNED / 'source/issue-evidence-scope.json'
SNAPSHOT = OWNED / 'source/issue-1194-api-snapshot.json'
SCOPE_SHA256 = '0f082390fe2f9c7bd3e627489b4f5160616d9b85e4cc15503ed1521c050e3cb8'
SNAPSHOT_SHA256 = '5863aa5a0f5845dbb9939a8fb841ceeeff6d1c87bc3bdee9f6e6936313389439'
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
    scope_raw=SCOPE.read_bytes(); snapshot_raw=SNAPSHOT.read_bytes()
    if sha(scope_raw)!=SCOPE_SHA256: raise ValueError('complete issue-scope evidence hash mismatch')
    if sha(snapshot_raw)!=SNAPSHOT_SHA256: raise ValueError('raw GitHub issue snapshot hash mismatch')
    issue=json.loads(scope_raw); snapshot=json.loads(snapshot_raw)
    match=re.search(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->',snapshot.get('body',''))
    if not match or json.loads(match.group(1)).get('evidence_quality')!=issue:
        raise ValueError('saved exact scope differs from pinned raw GitHub issue snapshot')
    if len(issue.get('pins',{}))!=62: raise ValueError('expected all 62 reviewed issue pins')
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

def safe_destination(dest: Path) -> Path:
    # Resolve lexical traversal, then inspect every existing path component without following links.
    dest=Path(os.path.abspath(str(dest)))
    evidence=OWNED/'evidence'
    try: relative=dest.relative_to(evidence)
    except ValueError: raise ValueError('output must stay under this packet evidence directory')
    if not relative.parts or any(part in ('.','..') for part in relative.parts):
        raise ValueError('output path contains traversal components')
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError('evidence root must be an ordinary directory')
    cursor=evidence
    for component in relative.parts[:-1]:
        cursor=cursor/component
        if cursor.is_symlink(): raise ValueError('output parent contains a symlink')
        if cursor.exists() and not cursor.is_dir(): raise ValueError('output parent is not a directory')
    if dest.is_symlink() or dest.exists():
        raise FileExistsError('output destination already exists')
    root_real=evidence.resolve()
    parent_real=dest.parent.resolve()
    try: parent_real.relative_to(root_real)
    except ValueError: raise ValueError('resolved output parent escapes the packet evidence directory')
    return dest

def publish_exclusive(scratch: Path, dest: Path, interrupt_after=None):
    dest=safe_destination(dest)
    dest.mkdir(parents=False, exist_ok=False)
    for i,name in enumerate(FILES,1):
        data=(scratch/name).read_bytes()
        with (dest/name).open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if interrupt_after == i: raise RuntimeError('injected interruption after exclusive output write')

def run(dest: Path):
    # Reject path escape, all symlink ancestors and existing names before any build.
    dest=safe_destination(dest)
    ids=preflight()
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Recheck after parent creation to catch a redirected or replaced ancestor.
    dest=safe_destination(dest)
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
