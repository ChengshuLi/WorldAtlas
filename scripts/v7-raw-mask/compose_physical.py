#!/usr/bin/python3
"""Compose candidate physical land/water grid; optionally compare to a baseline."""
import hashlib,json,math,os,shutil,sys
from pathlib import Path
import numpy as np
from osgeo import gdal,osr
from build import sha,validate_reference,compare_row

gdal.UseExceptions();gdal.SetCacheMax(64*1024*1024)

def open_mask(spec,grid):
    path=Path(spec['path']).resolve()
    if sha(path)!=spec['sha256']:raise ValueError(f'input hash mismatch: {path}')
    ds=gdal.Open(str(path));w,h,west,north,step=(grid[k] for k in ('width','height','west','north','step'))
    if ds is None or ds.RasterXSize!=w or ds.RasterYSize!=h or ds.GetGeoTransform()!=(west,step,0,north,0,-step):raise ValueError(f'grid mismatch: {path}')
    actual=ds.GetSpatialRef(); expected=osr.SpatialReference();expected.ImportFromEPSG(4326)
    if actual is None: raise ValueError(f'missing CRS: {path}')
    actual.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if not actual.IsSame(expected):raise ValueError(f'CRS mismatch: {path}')
    return ds

def main(config_path,output):
    config_path=Path(config_path).resolve();data=config_path.read_bytes();cfg=json.loads(data)
    if cfg.get('schema')!='candidate-physical-composition-v1' or not cfg.get('selection_notes'):raise ValueError('explicit schema and selection notes required')
    g=cfg['grid'];w,h,west,north,step=(g[k] for k in ('width','height','west','north','step'))
    if (not isinstance(w,int) or isinstance(w,bool) or w<=0 or not isinstance(h,int) or isinstance(h,bool) or h<=0 or
        not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (west,north,step)) or step<=0 or west < -180 or west+w*step>180.0000001 or north>90 or north-h*step< -90.0000001):raise ValueError('invalid grid')
    reserve=cfg.get('minimum_free_bytes',2*(1<<30))
    if not isinstance(reserve,int) or isinstance(reserve,bool) or reserve<0:raise ValueError('invalid free-space reserve')
    output=Path(output).resolve()
    has_ref=bool(cfg.get('reference_mask')); has_streams=bool(cfg.get('reference_streams'))
    if has_ref != has_streams:raise ValueError('reference mask and streams must be provided together')
    keys=('land','water','reference_mask') if has_ref else ('land','water')
    inputs=[config_path]+[Path(cfg[k]['path']).resolve() for k in keys]+([Path(cfg['reference_streams'][k]['path']).resolve() for k in ('rows','runs')] if has_ref else [])
    if len(set(inputs))!=len(inputs):raise ValueError('inputs must be distinct')
    if any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):raise ValueError('output must be outside input directories and must not contain inputs')
    masks=[open_mask(cfg[k],g) for k in keys]
    rr,rv=validate_reference(cfg['reference_streams'],w,h) if has_ref else (None,None)
    os.mkdir(output);out=Path(output)
    tif=gdal.GetDriverByName('GTiff').Create(str(out/'physical-dry.tif'),w,h,1,gdal.GDT_Byte,
        options=['TILED=YES','BLOCKXSIZE=512','BLOCKYSIZE=512','NBITS=1','COMPRESS=DEFLATE','SPARSE_OK=YES','BIGTIFF=YES'])
    tif.SetGeoTransform((west,step,0,north,0,-step));s=osr.SpatialReference();s.ImportFromEPSG(4326);tif.SetSpatialRef(s)
    offsets=[0];extra=missing=0;candidate_count=historic_count=0;spancount=0
    with (out/'runs.u32le').open('xb') as runs,(out/'mismatch-spans.jsonl').open('x') as diff:
        for y in range(0,h,128):
            if shutil.disk_usage(out).free < reserve:raise ValueError('free disk below configured reserve; partial output preserved')
            n=min(128,h-y); arrays=[ds.ReadAsArray(0,y,w,n) for ds in masks];land,water=arrays[:2];ref=arrays[2] if has_ref else None
            if any(np.any((x!=0)&(x!=1)) for x in arrays):raise ValueError('nonbinary mask')
            dry=land & (1-water);tif.GetRasterBand(1).WriteArray(dry,0,y)
            candidate_count+=int(np.count_nonzero(dry))
            if has_ref:
                historic_count+=int(np.count_nonzero(ref))
                extra+=int(np.count_nonzero((dry==1)&(ref==0)));missing+=int(np.count_nonzero((dry==0)&(ref==1)))
            for i,a in enumerate(dry,y):
                if has_ref:
                    old=ref[i-y];historic_codes=np.where(old,17,1).astype(np.uint8)
                    reference_runs=rv[int(rr[i]):int(rr[i+1])]
                    nbad,_=compare_row(historic_codes,reference_runs,w)
                    if nbad:raise ValueError(f'historic binary mask disagrees with historic physical stream at row {i}')
                codes=np.where(a,17,1).astype(np.uint8)
                end=np.flatnonzero(np.r_[codes[1:] != codes[:-1], True]);pairs=np.column_stack((end+1,codes[end])).astype('<u4');pairs.tofile(runs)
                offsets.append(offsets[-1]+len(pairs))
                if offsets[-1]>np.iinfo(np.uint32).max:raise ValueError('too many runs for u32 offsets')
                spans=compare_row(codes,reference_runs,w)[1] if has_ref else []
                for start,end,oldcode,newcode in spans:
                    diff.write(json.dumps({'row':i,'start':start,'end':end,'reference':oldcode,'candidate':newcode},separators=(',',':'))+'\n');spancount+=1
            progress={'rows_done':y+n,'candidate_dry_cells':candidate_count}
            if has_ref:progress.update({'candidate_extra_land':extra,'candidate_missing_land':missing,'mismatch_spans':spancount})
            print(json.dumps(progress),flush=True)
    tif.FlushCache();tif=None;masks=[]
    with (out/'rows.u32le').open('xb') as f:np.asarray(offsets,dtype='<u4').tofile(f)
    for key in keys:
        if sha(cfg[key]['path'])!=cfg[key]['sha256']:raise ValueError(f'{key} changed during processing')
    if has_ref:validate_reference(cfg['reference_streams'],w,h)
    if config_path.read_bytes()!=data:raise ValueError('config changed during processing')
    report={'status':'candidate-only','configuration_sha256':hashlib.sha256(data).hexdigest(),
       'grid':g,'inputs':{'land':cfg['land'],'water':cfg['water']},
       'candidate_dry_cells':candidate_count,'historic_dry_cells':historic_count,'candidate_extra_land_cells':extra,
       'candidate_missing_land_cells':missing,'mismatch_spans':spancount,'mismatch_spans_sha256':sha(out/'mismatch-spans.jsonl'),
       'output_sha256':{name:sha(out/name) for name in ('physical-dry.tif','rows.u32le','runs.u32le')},
       'limitations':'Approximate physical land/water only, not V2 continent assignments or historic raw-source reproduction. Review every mismatch before use.'}
    if not has_ref:
        for key in ('historic_dry_cells','candidate_extra_land_cells','candidate_missing_land_cells','mismatch_spans','mismatch_spans_sha256'):
            report.pop(key)
        report['limitations']='Candidate physical land/water only, not V2 continent assignments or historic source reproduction.'
    with (out/'config.json').open('xb') as f:f.write(data)
    with (out/'report.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    if len(sys.argv)!=3:sys.exit('usage: compose_physical.py CONFIG_JSON NEW_OUTPUT_DIRECTORY')
    try:main(sys.argv[1],sys.argv[2])
    except Exception as e:sys.exit(f'failed: {e}')
