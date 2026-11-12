#!/usr/bin/env python3
"""Generate one independently pinned research coastal tile in a new directory."""
import argparse,hashlib,json,math
import time
from pathlib import Path
import numpy as np
from map_build.water import coastal_core as core
from map_build.water import coastal_rect
from map_build.water import coastal_shore_index
from decision_snapshot import read_snapshot
import local_water_overlay
from direct_lineage import validate_physical_report,validate_direct_land
from map_build.execution.outputs import create_directory_exclusive,create_gzip_text_exclusive,write_json_exclusive


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


def coast_crop_bounds(box,width,height,step,latitude_pad,longitude_pad):
    """Independent latitude/longitude halos, wrapping longitude as needed."""
    import math
    if any(not math.isfinite(x) or x<=0 for x in (latitude_pad,longitude_pad)):raise ValueError('pad must be positive and finite')
    x0,x1,y0,y1=box;xp=math.ceil(longitude_pad/step);yp=math.ceil(latitude_pad/step);xa,xb=x0-xp,x1+xp
    if xb-xa>=width:xa,xb=0,width
    return xa,xb,max(0,y0-yp),min(height,y1+yp)


def run(snapshot,snapshot_sha,physical,land,out,width,height,box,pad,inputs,chunk=5000,verify_inputs=None,allow_selected_research=False,longitude_pad_degrees=None,processing_started=None,shore_index=None):
    if processing_started is None:processing_started=time.perf_counter()
    x0,x1,y0,y1=box;step=360.0/width
    if not (0<=x0<x1<=width and 0<=y0<y1<=height) or chunk<=0:raise ValueError('invalid coastal tile')
    decision,pairs,tol,band,btol=core.policy(snapshot)
    code_paths={'algorithm':Path(__file__),'core':Path(core.__file__),'shore':Path(core.shore.__file__),'geometry':Path(core.shore.__file__),'accelerator':Path(coastal_rect.__file__),
                'shore_index':Path(coastal_shore_index.__file__)}
    code_pins={name:sha(path) for name,path in code_paths.items()}
    crop=coast_crop_bounds(box,width,height,step,pad,pad if longitude_pad_degrees is None else longitude_pad_degrees)
    shore_started=time.perf_counter()
    try:
        if shore_index is None:
            edges=coastal_rect.centers_for_crop(physical,land,crop,width,height,step,[p[1] for p in pairs])
        else:
            if (shore_index.width,shore_index.height)!=(width,height):raise ValueError('shore index grid mismatch')
            edges=shore_index.centers_for_crop(crop,step,[p[1] for p in pairs])
    except ValueError as e:
        if str(e)!='no participant shorelines in crop':raise
        edges={'mids':np.empty((0,3))}
    shore_elapsed=time.perf_counter()-shore_started
    index_started=time.perf_counter();idx=core.index_present(edges,pairs)
    index_elapsed=time.perf_counter()-index_started
    create_directory_exclusive(out);out=Path(out);path=out/'coastal-assignments.jsonl.gz'
    cells=spans=bounded=exact=water=0;classification_elapsed=0.
    # Only the coordinates vary per span. Encode the policy strings once while
    # retaining the exact JSON key order, escaping and decompressed bytes.
    suffixes={code:json.dumps({'code':code,'rule_id':'coastal-nearest-final-center-v2',
                    'member_id':f'coastal-policy-{decision["id"]}-code-{code}'},separators=(',',':'))[1:]
              for _,_,code in pairs}
    with create_gzip_text_exclusive(path,encoding='utf8') as f:
        for first_y in range(y0,y1,64):
            last_y=min(first_y+64,y1);water_grid=np.empty((last_y-first_y,x1-x0),dtype=bool)
            for i,y in enumerate(range(first_y,last_y)):
                p=core.shore.crop(*physical,y,x0,x1,width)
                if np.any((p!=1)&(p!=17)):raise ValueError('invalid physical tile values')
                water_grid[i]=p==1
            water+=int(water_grid.sum())
            classify_started=time.perf_counter()
            codes,stats=coastal_rect.classify(water_grid,x0,first_y,crop,width,height,step,pairs,tol,band,btol,idx)
            classification_elapsed+=time.perf_counter()-classify_started
            bounded+=stats['bounded'];exact+=stats['exact']
            for i,y in enumerate(range(first_y,last_y)):
                chosen=np.flatnonzero(water_grid[i]&(codes[i]!=0));chosen_codes=codes[i,chosen];chosen_x=chosen+x0;cells+=len(chosen);records=[]
                if len(chosen):
                    cuts=np.r_[0,np.flatnonzero((np.diff(chosen_x)>1)|(chosen_codes[1:]!=chosen_codes[:-1]))+1,len(chosen_x)]
                    for a,b in zip(cuts[:-1],cuts[1:]):
                        start_x,end_x,code=int(chosen_x[a]),int(chosen_x[b-1])+1,int(chosen_codes[a])
                        records.append('{"start":'+str(start_x)+',"end":'+str(end_x)+','+suffixes[code])
                if records:
                    spans+=len(records);f.write('{"row":'+str(y)+',"spans":['+','.join(records)+']}\n')
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
              'geometry_sha256':code_pins['geometry'],'accelerator_sha256':code_pins['accelerator'],
              'shore_index_sha256':code_pins['shore_index'],
              'stage_processing_elapsed_seconds':{'shore_centers':shore_elapsed,'nearest_index':index_elapsed,'classification':classification_elapsed},
              'coverage':'candidate core only; independent global coverage and source semantics not yet verified'}
    manifest['processing_elapsed_seconds']=time.perf_counter()-processing_started
    write_json_exclusive(out/'manifest.json',manifest,indent=2)
    return manifest


def main():
    processing_started=time.perf_counter()
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('snapshot','snapshot-sha256','physical-rows','physical-rows-sha256','physical-runs','physical-runs-sha256','physical-report','physical-report-sha256',
              'land-rows','land-rows-sha256','land-runs','land-runs-sha256','land-report','land-report-sha256','input-root','out'):
        ap.add_argument('--'+k,required=True)
    ap.add_argument('--core',nargs=4,type=int,required=True,metavar=('X0','X1','Y0','Y1'))
    ap.add_argument('--pad-degrees',type=float,required=True);ap.add_argument('--longitude-pad-degrees',type=float);ap.add_argument('--allow-unverified-snapshot',action='store_true');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--allow-selected-research-policy',action='store_true')
    a=ap.parse_args()
    if not a.allow_unverified_snapshot:raise ValueError('unverified Neon snapshot requires explicit research opt-in')
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
        validate_direct_land(a.land_report,a.land_report_sha256,physical,land,local_water_overlay.land_snapshot_hash(snap,a.snapshot_sha256),snap['decision_revision'],root,a.physical_report_sha256)
    check_lineage()
    inputs={key:sha(path) for key,path in [('physical_rows_sha256',a.physical_rows),('physical_runs_sha256',a.physical_runs),
         ('physical_report_sha256',a.physical_report),('land_rows_sha256',a.land_rows),('land_runs_sha256',a.land_runs),('land_report_sha256',a.land_report)]}
    def recheck():
        if any(sha(p)!=h for p,h in paths):raise ValueError('input changed during generation')
        check_lineage()
    m=run(snap,a.snapshot_sha256,open_grid(a.physical_rows,a.physical_runs,width,height),open_grid(a.land_rows,a.land_runs,width,height),
          out,width,height,a.core,a.pad_degrees,inputs,verify_inputs=recheck,allow_selected_research=a.allow_selected_research_policy,longitude_pad_degrees=a.longitude_pad_degrees,processing_started=processing_started)
    print(json.dumps({'status':m['status'],'assigned_cells':m['assigned_cells'],'output':str(out)}))

if __name__=='__main__':main()

