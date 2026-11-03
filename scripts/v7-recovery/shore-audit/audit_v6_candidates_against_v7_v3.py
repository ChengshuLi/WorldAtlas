#!/usr/bin/env python3
"""Exact, fail-closed comparison of 5,089 V6 nearshore candidates with final V7.

Requires a final complete V7 grid and a complete resolved named-basin-only
priority layer. It never changes inputs. Every output is created O_EXCL in a
fresh run directory; partial outputs remain and a retry uses another directory.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

HELPER = Path(__file__).resolve().parents[1] / "shared-output-safety-20261103"
sys.path.insert(0, str(HELPER))
from exclusive_outputs import create_gzip_text_exclusive, create_run_directory, write_json_exclusive

W, H = 131072, 54614
STEP = 360.0 / W
CANDIDATE_SHA = "5bba54e94b2a87efb1a856f89e4995f7ed36e476b8f1113d23e9f422ff064033"
V6_ROWS_SHA = "ffd10cd2731668ef210d175bc54dcf65586e4d1aa39e1fc6e1cf505aea5d3e0f"
V6_RUNS_SHA = "e22efa18aa85b975484fbda661f160620739f70b3e110f4d385292df13c3b342"
PHYSICAL_ROWS_SHA = "dfbf12a93b1b71b4decefd14c571ad989522aaa314c8068b0d98fc04f02b8ade"
PHYSICAL_RUNS_SHA = "a4b0316162d8ad1096c55a8b8faff9c185322008dabd966ede068d5cda17f36a"
JAVA_FEEDBACK = {(35849,106874), (35825,106797), (35913,106945)}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()


def open_jsonl(path: Path):
    return gzip.open(path, 'rt', encoding='utf-8') if path.suffix == '.gz' else path.open('rt', encoding='utf-8')


def load_rle(rows_path: Path, runs_path: Path, *, expected_rows=None, expected_runs=None):
    for p, expected in ((rows_path, expected_rows),(runs_path,expected_runs)):
        if expected and sha256(p) != expected:
            raise ValueError(f"SHA-256 mismatch: {p}")
    rows=np.memmap(rows_path, mode='r', dtype='<u4')
    runs=np.memmap(runs_path, mode='r', dtype='<u4')
    if rows.size != H+1 or rows[0] != 0 or rows[-1]*2 != runs.size or runs.size%2:
        raise ValueError(f"invalid RLE dimensions/offsets: {rows_path}, {runs_path}")
    if np.any(rows[1:] < rows[:-1]): raise ValueError(f"nonmonotone row offsets: {rows_path}")
    return rows, runs


def code_at(rle, y: int, x: int) -> int:
    rows,runs=rle
    if not (0<=y<H and 0<=x<W): raise ValueError(f"cell outside grid: {y},{x}")
    a,b=int(rows[y]),int(rows[y+1])
    if a==b: raise ValueError(f"empty RLE row at candidate cell {y},{x}")
    q=runs[2*a:2*b]
    idx=int(np.searchsorted(q[0::2], x, side='right'))
    if idx>=b-a: raise ValueError(f"RLE row does not cover candidate cell {y},{x}")
    return int(q[2*idx+1])


def load_candidates(path: Path):
    if sha256(path) != CANDIDATE_SHA: raise ValueError("candidate-spans SHA does not match the completed global audit")
    byrow=defaultdict(list); cells={}; spans=0
    with open_jsonl(path) as f:
        for ln,line in enumerate(f,1):
            if not line.strip(): continue
            o=json.loads(line); y=int(o['row']); x0=int(o['start']); x1=int(o['end'])
            src=int(o['from_code']); dst=int(o['to_code'])
            if not(0<=y<H and 0<=x0<x1<=W and 1<=src<=6 and 1<=dst<=6 and src!=dst):
                raise ValueError(f"invalid candidate record line {ln}: {o}")
            spans+=1
            for x in range(x0,x1):
                key=(y,x)
                if key in cells: raise ValueError(f"duplicate candidate cell {key}")
                item={'row':y,'x':x,'from_code':src,'to_code':dst,'tile':o.get('tile')}
                cells[key]=item; byrow[y].append(item)
    if spans!=2930 or len(cells)!=5089: raise ValueError(f"candidate audit changed: spans={spans}, cells={len(cells)}")
    for vals in byrow.values(): vals.sort(key=lambda c:c['x'])
    return byrow,cells,spans


def find_digest(obj, names):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in names and isinstance(v,str) and len(v)==64: return v.lower()
        for v in obj.values():
            got=find_digest(v,names)
            if got: return got
    elif isinstance(obj,list):
        for v in obj:
            got=find_digest(v,names)
            if got: return got
    return None


def validate_final_v7_manifest(path: Path, rows_path: Path, runs_path: Path):
    m=json.loads(path.read_text(encoding='utf-8'))
    status=str(m.get('status','')).lower()
    if not any(s in status for s in ('complete','final','passed')) or any(s in status for s in ('partial','provisional','running','active','failed')):
        raise ValueError(f"V7 manifest is not final/complete: status={m.get('status')!r}")
    g=m.get('grid',m.get('invariants',{}).get('grid',{}))
    if int(g.get('width',-1))!=W or int(g.get('height',-1))!=H: raise ValueError("V7 manifest grid dimensions do not match")
    rsha=find_digest(m,{'rows_sha256','raw_rows_sha256','grid_rows_sha256','final_rows_sha256','rows_u32le_sha256','raw_rows_u32le_sha256'})
    usha=find_digest(m,{'runs_sha256','raw_runs_sha256','grid_runs_sha256','final_runs_sha256','runs_u32le_sha256','raw_runs_u32le_sha256'})
    if not rsha or not usha: raise ValueError("V7 final manifest must pin raw rows/runs SHA-256")
    if sha256(rows_path)!=rsha or sha256(runs_path)!=usha: raise ValueError("V7 grid files do not match the final manifest pins")
    return {'status':m.get('status'),'manifest':str(path),'rows_sha256':rsha,'runs_sha256':usha}


def named_manifest_assignments(path: Path, byrow):
    m=json.loads(path.read_text(encoding='utf-8'))
    status=str(m.get('status','')).lower(); cov=m.get('coverage',{})
    if not any(s in status for s in ('complete','final','passed')) or any(s in status for s in ('partial','provisional','running','active','failed')):
        raise ValueError(f"named-basin layer is not final/complete: status={m.get('status')!r}")
    if cov.get('complete') is not True or cov.get('assignment_coverage_complete') is not True:
        raise ValueError("named-basin layer manifest does not certify complete resolved assignment coverage")
    if 'named' not in str(m.get('layer_id','')).lower() and 'basin' not in str(m.get('layer_id','')).lower():
        raise ValueError("expected a named-basin-only priority layer, not generic/legacy exception data")
    if not isinstance(m.get('tiles'),list) or not m['tiles']: raise ValueError("named-basin manifest has no source tiles")
    hits={}; checked_files=0
    wanted_rows=set(byrow)
    for tile in m['tiles']:
        info=tile.get('span_file',tile.get('file',tile))
        if isinstance(info,dict): rel=info.get('path'); digest=info.get('sha256') or info.get('span_sha256')
        else: rel=info; digest=tile.get('sha256') or tile.get('span_sha256')
        if not rel or not digest: raise ValueError(f"manifest tile lacks path/hash: {tile}")
        p=Path(rel)
        if not p.is_absolute(): p=(path.parent/p).resolve()
        if not p.is_file() or sha256(p)!=digest: raise ValueError(f"named assignment file missing/hash mismatch: {p}")
        checked_files+=1
        yb=tile.get('row_bounds',[tile.get('row_start',0),tile.get('row_end_exclusive',H)])
        y0,y1=int(yb[0]),int(yb[1])
        last=-1
        with open_jsonl(p) as f:
            for ln,line in enumerate(f,1):
                if not line.strip(): continue
                rec=json.loads(line); y=int(rec.get('row',-1))
                if y<last or not 0<=y<H: raise ValueError(f"bad named assignment row {p}:{ln}")
                last=y
                if y not in wanted_rows: continue
                cands=byrow[y]
                # Few candidate cells per row; scan the row's assigned spans against them.
                for s in rec.get('spans',[]):
                    a=int(s.get('start',s.get('x_start',-1))); b=int(s.get('end',s.get('x_end_exclusive',-1))); code=int(s.get('code',s.get('to_code',-1)))
                    if not(0<=a<b<=W and 1<=code<=10): raise ValueError(f"invalid named span {p}:{ln}: {s}")
                    member=s.get('member_id') or s.get('source_member_id')
                    rule=s.get('rule_id')
                    if not member or not rule or not str(rule).startswith('approved-named-basin-'): raise ValueError(f"named assignment is missing fresh approved basin provenance {p}:{ln}: {s}")
                    for cand in cands:
                        x=cand['x']
                        if a<=x<b:
                            k=(y,x)
                            if k in hits: raise ValueError(f"unresolved duplicate named-basin overlap at {k}: {hits[k]} vs {s}")
                            hits[k]={'code':code,'member_id':member,'rule_id':rule,'source_file':p.name}
    return hits,{'layer_id':m.get('layer_id'),'status':m.get('status'),'manifest':str(path),'source_files_checked':checked_files,'candidate_cells_covered':len(hits)}


def region(y,x):
    lon=-180+(x+.5)*STEP; lat=90-(y+.5)*STEP
    if -10.0<lat<-7.0 and 110.0<lon<115.0: return 'Java'
    if 2.0<lat<3.0 and 128.0<lon<130.0: return 'North_Halmahera'
    return None


def classify(args):
    candidates,cells,span_count=load_candidates(args.candidate_spans)
    v6=load_rle(args.v6_rows,args.v6_runs,expected_rows=V6_ROWS_SHA,expected_runs=V6_RUNS_SHA)
    physical=load_rle(args.physical_rows,args.physical_runs,expected_rows=PHYSICAL_ROWS_SHA,expected_runs=PHYSICAL_RUNS_SHA)
    v7meta=validate_final_v7_manifest(args.v7_manifest,args.v7_rows,args.v7_runs)
    v7=load_rle(args.v7_rows,args.v7_runs)
    named,namedmeta=named_manifest_assignments(args.named_manifest,candidates)
    totals=Counter(); bypair=defaultdict(Counter); ledger=[]; regions=Counter(); java_rows=[]; nh_rows=[]
    for key,c in cells.items():
        y,x=key; old=code_at(v6,y,x); phys=code_at(physical,y,x); new=code_at(v7,y,x)
        if old!=c['from_code']: raise ValueError(f"candidate V6 code mismatch at {key}: {old} != {c['from_code']}")
        if phys != 1: raise ValueError(f"candidate cell is not physical WATER code 1 at {key}: {phys}")
        named_hit=named.get(key)
        expected=int(named_hit['code']) if named_hit else int(c['to_code'])
        pair=f"{c['from_code']}->{c['to_code']}"
        if expected==c['from_code'] and new==expected:
            bucket='valid_due_named_basin'
        elif expected==c['to_code'] and new==expected and old!=new:
            bucket='confirmed_v6_wrong_corrected'
        else:
            bucket='unresolved_or_other'
        totals[bucket]+=1; bypair[pair][bucket]+=1
        if named_hit: bypair[pair]['named_basin_assigned']+=1
        r=region(y,x)
        if r:
            regions[r]+=1
        lon=-180+(x+.5)*STEP; lat=90-(y+.5)*STEP
        item={**c,'lon_center':lon,'lat_center':lat,'v6_code':old,'physical_code':phys,'expected_v7_code':expected,'actual_v7_code':new,'classification':bucket,'named_basin':named_hit,'geographic_group':r}
        ledger.append(item)
        if key in JAVA_FEEDBACK: java_rows.append(item)
        if r=='North_Halmahera': nh_rows.append(item)
    if sum(regions.values())!=49 or regions['Java']!=37 or regions['North_Halmahera']!=12:
        raise ValueError(f"Java/North Halmahera candidate partition unexpected: {dict(regions)}")
    if len(java_rows)!=3: raise ValueError(f"Java feedback-cell cross-check failed: {len(java_rows)} of 3 found")
    summary={'schema':'v6-nearestshore-to-final-v7-candidate-classification-v1','status':'complete','candidate_spans':span_count,'candidate_cells':len(cells),'candidate_transition_cells':dict(sorted((f"{a}->{b}",sum(1 for c in cells.values() if c['from_code']==a and c['to_code']==b)) for a in range(1,7) for b in range(1,7) if a!=b)),'classifications':dict(totals),'by_transition':{k:dict(v) for k,v in sorted(bypair.items())},'geographic_group_counts':dict(regions),'java_feedback_cells':java_rows,'north_halmahera_cells':nh_rows,'candidate_source_sha256':sha256(args.candidate_spans),'v6_rows_sha256':sha256(args.v6_rows),'v6_runs_sha256':sha256(args.v6_runs),'physical_rows_sha256':sha256(args.physical_rows),'physical_runs_sha256':sha256(args.physical_runs),'v7_final_pins':v7meta,'named_basin_layer':namedmeta,'interpretation':{'confirmed_v6_wrong_corrected':'V6 equals candidate from_code, final named-basin expected code equals candidate to_code, and V7 equals that expected code','valid_due_named_basin':'fresh complete named-basin-only layer explicitly assigns the original V6 category and final V7 preserves it','unresolved_or_other':'any provenance, expected-code, or final-code disagreement; not counted as corrected or valid'}}
    return summary,ledger


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate-spans',type=Path,required=True)
    ap.add_argument('--v6-rows',type=Path,required=True); ap.add_argument('--v6-runs',type=Path,required=True)
    ap.add_argument('--physical-rows',type=Path,required=True); ap.add_argument('--physical-runs',type=Path,required=True)
    ap.add_argument('--v7-rows',type=Path,required=True); ap.add_argument('--v7-runs',type=Path,required=True)
    ap.add_argument('--v7-manifest',type=Path,required=True)
    ap.add_argument('--named-manifest',type=Path,required=True,help='Final, complete, resolved named-basin-only layer; legacy land exceptions excluded.')
    ap.add_argument('--output-parent',type=Path,required=True,help='Existing directory; each invocation creates a fresh unique subdirectory.')
    a=ap.parse_args()
    summary,ledger=classify(a)
    run=create_run_directory(a.output_parent,'v6-candidate-v7-audit')
    with create_gzip_text_exclusive(run/'candidate-cell-ledger.jsonl.gz') as f:
        for r in ledger: f.write(json.dumps(r,separators=(',',':'),sort_keys=True)+'\n')
    write_json_exclusive(run/'summary.json',summary,indent=2)
    print(json.dumps({'status':'complete','run_dir':str(run),'classifications':summary['classifications'],'by_transition':summary['by_transition'],'geographic_group_counts':summary['geographic_group_counts'],'java_feedback_cells':summary['java_feedback_cells']},indent=2))

if __name__=='__main__': main()
