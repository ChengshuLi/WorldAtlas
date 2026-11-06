#!/usr/bin/env python3
"""Generate one independently pinned research coastal tile in a new directory."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import coastal_core as core
from decision_snapshot import read_snapshot
from direct_lineage import validate_physical_report,validate_direct_land
from exclusive_outputs import create_directory_exclusive,create_gzip_text_exclusive,write_json_exclusive


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def open_grid(rows_path,runs_path,width,height):
    rows=np.memmap(rows_path,dtype='<u4',mode='r');runs=np.memmap(runs_path,dtype='<u4',mode='r')
    if len(rows)!=height+1 or len(runs)%2 or int(rows[0])!=0 or int(rows[-1])!=len(runs)//2 or np.any(rows[1:]<=rows[:-1]):
        raise ValueError('invalid RLE offsets')
    return rows,runs


def run(snapshot,snapshot_sha,physical,land,out,width,height,box,pad,inputs,chunk=5000,verify_inputs=None,allow_selected_research=False):
    x0,x1,y0,y1=box;step=360.0/width
    if not (0<=x0<x1<=width and 0<=y0<y1<=height) or chunk<=0:raise ValueError('invalid coastal tile')
    decision,pairs,tol,band,btol=core.policy(snapshot,allow_selected_research=allow_selected_research)
    code_paths={'algorithm':Path(__file__),'core':Path(core.__file__),'shore':Path(core.shore.__file__),'geometry':Path(core.shore.__file__)}
    code_pins={name:sha(path) for name,path in code_paths.items()}
    crop=core.shore.crop_bounds(box,width,height,step,pad)
    try:edges=core.shore.centers_for_crop(physical,land,crop,width,height,step,[p[1] for p in pairs])
    except ValueError as e:
        if str(e)!='no participant shorelines in crop':raise
        edges={'mids':np.empty((0,3))}
    idx=core.index_present(edges,pairs)
    create_directory_exclusive(out);out=Path(out);path=out/'coastal-assignments.jsonl.gz'
    cells=spans=bounded=exact=water=0
    with create_gzip_text_exclusive(path,encoding='utf8') as f:
        for y in range(y0,y1):
            p=core.shore.crop(*physical,y,x0,x1,width)
            if np.any(~np.isin(p,[1,17])):raise ValueError('invalid physical tile values')
            selected=np.flatnonzero(p==1);water+=len(selected);records=[]
            for start in range(0,len(selected),chunk):
                xs=selected[start:start+chunk]+x0
                lat=np.full(len(xs),90-(y+.5)*step);lon=-180+(xs+.5)*step
                codes,stats=core.classify(lat,lon,crop,width,height,step,pairs,tol,band,btol,idx)
                bounded+=stats['bounded'];exact+=stats['exact']
                keep=codes!=0; chosen_x=xs[keep]; chosen_codes=codes[keep]; cells+=int(keep.sum())
                if len(chosen_x):
                    cuts=np.r_[0,np.flatnonzero((np.diff(chosen_x)>1)|(chosen_codes[1:]!=chosen_codes[:-1]))+1,len(chosen_x)]
                    for i,j in zip(cuts[:-1],cuts[1:]):
                        start_x,end_x,code=int(chosen_x[i]),int(chosen_x[j-1])+1,int(chosen_codes[i])
                        if records and records[-1]['end']==start_x and records[-1]['code']==code:records[-1]['end']=end_x
                        else:records.append({'start':start_x,'end':end_x,'code':code,'rule_id':'coastal-nearest-final-center-v2',
                                             'member_id':f'coastal-policy-{decision["id"]}-code-{code}'})
            if records:
                spans+=len(records);f.write(json.dumps({'row':y,'spans':records},separators=(',',':'))+'\n')
    if verify_inputs:verify_inputs()
    if any(sha(path)!=code_pins[name] for name,path in code_paths.items()):raise ValueError('algorithm changed during generation')
    manifest={'schema':'worldatlas-coastal-tile-candidate-v1','status':'partial-unverified-research-not-published',
              'grid':{'width':width,'height':height,'angular_step_deg':step},'core_cols':[x0,x1],'core_rows':[y0,y1],
              'shore_crop_bounds':crop,'policy_id':decision['id'],'policy_definition':decision['definition'],
              'decision_snapshot_sha256':snapshot_sha,'decision_revision':snapshot['decision_revision']['id'],
              'entity_revision':snapshot['decision_revision']['entity_revision'],'inputs':inputs,
              'physical_water_cells':water,'assigned_cells':cells,'span_count':spans,'bound_certified_cells':bounded,
              'exact_cells':exact,'coastal_centers':len(edges['mids']),
              'span_file':{'path':path.name,'sha256':sha(path)},'algorithm_sha256':code_pins['algorithm'],
              'core_sha256':code_pins['core'],'shore_sha256':code_pins['shore'],
              'geometry_sha256':code_pins['geometry'],
              'coverage':'candidate core only; independent global coverage and source semantics not yet verified'}
    write_json_exclusive(out/'manifest.json',manifest,indent=2)
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('snapshot','snapshot-sha256','physical-rows','physical-rows-sha256','physical-runs','physical-runs-sha256','physical-report','physical-report-sha256',
              'land-rows','land-rows-sha256','land-runs','land-runs-sha256','land-report','land-report-sha256','input-root','out'):
        ap.add_argument('--'+k,required=True)
    ap.add_argument('--core',nargs=4,type=int,required=True,metavar=('X0','X1','Y0','Y1'))
    ap.add_argument('--pad-degrees',type=float,required=True);ap.add_argument('--allow-unverified-snapshot',action='store_true');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--allow-selected-research-policy',action='store_true')
    a=ap.parse_args()
    if not a.allow_unverified_snapshot:raise ValueError('unverified Neon snapshot requires explicit research opt-in')
    if Path(a.snapshot).stat().st_size>16*1024*1024:raise ValueError('snapshot exceeds size limit')
    snap=read_snapshot(Path(a.snapshot),a.snapshot_sha256,allow_draft=a.allow_draft)
    paths=[(a.physical_rows,a.physical_rows_sha256),(a.physical_runs,a.physical_runs_sha256),
           (a.physical_report,a.physical_report_sha256),(a.land_rows,a.land_rows_sha256),(a.land_runs,a.land_runs_sha256),(a.land_report,a.land_report_sha256),(a.snapshot,a.snapshot_sha256)]
    if any(sha(p)!=h for p,h in paths):raise ValueError('input hash mismatch')
    root=Path(a.input_root).resolve();out=Path(a.out).resolve()
    if not root.is_dir() or any(not Path(p).resolve().is_relative_to(root) for p,_ in paths):raise ValueError('all inputs must be inside input root')
    if any(out==Path(p).resolve() or Path(p).resolve().is_relative_to(out) for p,_ in paths):raise ValueError('output overlaps input')
    width,height=131072,54614
    physical={'rows_sha256':a.physical_rows_sha256,'runs_sha256':a.physical_runs_sha256}
    land={'rows_sha256':a.land_rows_sha256,'runs_sha256':a.land_runs_sha256,
          'resolved_rows':Path(a.land_rows).resolve(),'resolved_runs':Path(a.land_runs).resolve()}
    def check_lineage():
        validate_physical_report(a.physical_report,a.physical_report_sha256,physical,width,height)
        validate_direct_land(a.land_report,a.land_report_sha256,physical,land,a.snapshot_sha256,snap['decision_revision'],root,a.physical_report_sha256)
    check_lineage()
    inputs={key:sha(path) for key,path in [('physical_rows_sha256',a.physical_rows),('physical_runs_sha256',a.physical_runs),
         ('physical_report_sha256',a.physical_report),('land_rows_sha256',a.land_rows),('land_runs_sha256',a.land_runs),('land_report_sha256',a.land_report)]}
    def recheck():
        if any(sha(p)!=h for p,h in paths):raise ValueError('input changed during generation')
        check_lineage()
    m=run(snap,a.snapshot_sha256,open_grid(a.physical_rows,a.physical_runs,width,height),open_grid(a.land_rows,a.land_runs,width,height),
          out,width,height,a.core,a.pad_degrees,inputs,verify_inputs=recheck,allow_selected_research=a.allow_selected_research_policy)
    print(json.dumps({'status':m['status'],'assigned_cells':m['assigned_cells'],'output':str(out)}))

if __name__=='__main__':main()
