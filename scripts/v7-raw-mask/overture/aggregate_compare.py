#!/usr/bin/env python3
"""Union explicitly pinned candidate masks; optionally compare to a pinned reference."""
import hashlib,json,math,os,shutil,sys
from pathlib import Path
import numpy as np
from osgeo import gdal,osr

gdal.UseExceptions()

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def open_mask(entry,grid):
    path=Path(entry['path']).resolve()
    if sha(path)!=entry['sha256']:raise ValueError(f'input hash mismatch: {path}')
    ds=gdal.Open(str(path));w,h,west,north,step=(grid[k] for k in ('width','height','west','north','step'))
    if ds is None or ds.RasterXSize!=w or ds.RasterYSize!=h or ds.GetGeoTransform()!=(west,step,0,north,0,-step):raise ValueError(f'grid mismatch: {path}')
    actual=ds.GetSpatialRef();expected=osr.SpatialReference();expected.ImportFromEPSG(4326)
    if actual is None:raise ValueError(f'missing CRS: {path}')
    actual.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if not actual.IsSame(expected):raise ValueError(f'CRS mismatch: {path}')
    return ds

def union_mask(ds, water, y):
    """Union a mask, skipping only GeoTIFF blocks guaranteed to read as zero."""
    width=water.shape[1];rows=water.shape[0];band=ds.GetRasterBand(1)
    nodata=band.GetNoDataValue()
    if ds.RasterCount != 1:raise ValueError('candidate mask must have one band')
    if (ds.GetDriver().ShortName != 'GTiff' or band.DataType != gdal.GDT_Byte or
            nodata not in (None,0) or not hasattr(band,'GetDataCoverageStatus')):
        windows=[(0,width)]
    else:
        block_width,_=band.GetBlockSize()
        windows=[]
        for x in range(0,width,block_width):
            n=min(block_width,width-x)
            flags,_=band.GetDataCoverageStatus(x,y,n,rows)
            if flags != gdal.GDAL_DATA_COVERAGE_STATUS_EMPTY:
                windows.append((x,n))
    for x,n in windows:
        arr=band.ReadAsArray(x,y,n,rows)
        if np.any((arr != 0) & (arr != 1)):raise ValueError('nonbinary candidate input')
        view=water[:,x:x+n]
        np.bitwise_or(view,arr,out=view)

def verify_lineage(cfg, grid):
    """Bind every raster and report to one complete, pinned raw-source manifest."""
    spec=cfg.get('source_manifest')
    if not isinstance(spec,dict) or sha(spec['path']) != spec['sha256']:
        raise ValueError('pinned source manifest required')
    manifest=json.loads(Path(spec['path']).read_bytes())
    files=manifest.get('files')
    if not isinstance(files,list) or manifest.get('file_count') != len(files) or not files:
        raise ValueError('source manifest must list every raw shard')
    expected=[f.get('sha256') for f in files]
    if any(not isinstance(v,str) or len(v)!=64 or any(ch not in '0123456789abcdef' for ch in v) for v in expected) or len(set(expected)) != len(expected):
        raise ValueError('source manifest hashes must be unique SHA-256 values')
    seen=[]; policies=[]; scripts=[];kernels=[]
    for shard in cfg['shards']:
        report=shard.get('report')
        if not isinstance(report,dict) or sha(report['path']) != report['sha256']:
            raise ValueError('pinned shard report required')
        doc=json.loads(Path(report['path']).read_bytes())
        row_count=doc.get('rows_in_source');script=doc.get('script_sha256')
        if (doc.get('status') != 'candidate-only' or doc.get('output_sha256') != shard['sha256'] or
                doc.get('grid') != grid or doc.get('invalid_feature_ids') or
                doc.get('counts',{}).get('missing_classification',0) or doc.get('counts',{}).get('invalid_polygon',0) or not doc.get('policy') or
                not isinstance(script,str) or len(script)!=64 or any(ch not in '0123456789abcdef' for ch in script) or
                not isinstance(row_count,int) or isinstance(row_count,bool) or row_count<0 or
                row_count != doc.get('counts',{}).get('rows')):
            raise ValueError('incomplete or inconsistent shard report')
        native=doc.get('native_kernel')
        if doc.get('rasterizer') not in (None,'python','native','gdal'):raise ValueError('unknown water rasterizer')
        if doc.get('rasterizer')=='native':
            if (not isinstance(native,dict) or native.get('method') not in ('hybrid','vector','tiled') or
                    any(not isinstance(native.get(k),str) or len(native[k])!=64 or
                    any(ch not in '0123456789abcdef' for ch in native[k]) for k in
                    ('source_sha256','binding_sha256','binary_sha256')) or
                    sha(Path(report['path']).parent/'water-native.so')!=native['binary_sha256']):
                raise ValueError('invalid native water kernel')
            kernels.append((doc['rasterizer'],native['method'],native['source_sha256'],native['binding_sha256'],native.get('gdal')))
        elif doc.get('rasterizer')=='gdal':
            kernel=doc.get('gdal_kernel')
            if (native is not None or not isinstance(kernel,dict) or
                    kernel.get('implementation')!='python-gdal-c-api-v1' or
                    kernel.get('method') not in ('hybrid','tiled') or
                    not isinstance(kernel.get('binding_sha256'),str) or len(kernel['binding_sha256'])!=64 or
                    any(ch not in '0123456789abcdef' for ch in kernel['binding_sha256'])):
                raise ValueError('invalid in-process GDAL water kernel')
            kernels.append(('gdal',kernel['method'],kernel['binding_sha256'],kernel.get('gdal')))
        else:
            if native is not None:raise ValueError('unexpected native water kernel')
            kernels.append((doc.get('rasterizer','python'),))
        seen.append(doc.get('source_sha256')); policies.append(doc.get('policy')); scripts.append(doc.get('script_sha256'))
    if len(seen)!=len(expected) or set(seen)!=set(expected) or len(set(seen))!=len(seen):
        raise ValueError('shard reports do not cover the pinned source manifest exactly')
    if any(p != policies[0] for p in policies):
        raise ValueError('inconsistent shard selection policy')
    if any(p != scripts[0] for p in scripts):
        raise ValueError('inconsistent shard rasterizer')
    if any(k != kernels[0] for k in kernels):raise ValueError('inconsistent native water kernels')

def run(config_path,output,*,emit=print):
    config_path=Path(config_path).resolve();data=config_path.read_bytes();cfg=json.loads(data);output=Path(output).resolve()
    if cfg.get('schema')!='water-union-comparison-v1' or not cfg.get('selection_notes'):raise ValueError('explicit schema and selection notes required')
    grid=cfg['grid'];w,h,west,north,step=(grid[k] for k in ('width','height','west','north','step'))
    if (not isinstance(w,int) or isinstance(w,bool) or w<=0 or not isinstance(h,int) or isinstance(h,bool) or h<=0 or
        not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (west,north,step)) or step<=0 or west < -180 or west+w*step>180.0000001 or north>90 or north-h*step< -90.0000001):raise ValueError('invalid grid')
    shards=cfg['shards'];reference=cfg.get('reference'); reserve=cfg.get('minimum_free_bytes',2*(1<<30))
    rows_per_block=cfg.get('rows_per_block',128)
    if not isinstance(shards,list) or not shards or cfg.get('shard_count')!=len(shards):raise ValueError('complete explicit shard list required')
    if not isinstance(reserve,int) or isinstance(reserve,bool) or reserve<0:raise ValueError('invalid free-space reserve')
    if type(rows_per_block) is not int or rows_per_block<1:raise ValueError('invalid rows_per_block')
    if any(s.get('status')!='candidate-only' for s in shards):raise ValueError('incomplete shard cannot be aggregated')
    verify_lineage(cfg,grid)
    inputs=[config_path,Path(cfg['source_manifest']['path']).resolve()]+[Path(x['path']).resolve() for x in shards]+[Path(x['report']['path']).resolve() for x in shards]+([Path(reference['path']).resolve()] if reference else [])
    if len(set(inputs))!=len(inputs):raise ValueError('input paths must be unique')
    if any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):raise ValueError('output must be outside input directories and must not contain inputs')
    masks=[open_mask(s,grid) for s in shards];ref=open_mask(reference,grid) if reference else None
    os.mkdir(output)
    tif=gdal.GetDriverByName('GTiff').Create(str(output/'water-union.tif'),w,h,1,gdal.GDT_Byte,
        options=['TILED=YES','BLOCKXSIZE=512','BLOCKYSIZE=512','NBITS=1','COMPRESS=DEFLATE','SPARSE_OK=YES','BIGTIFF=YES'])
    tif.SetGeoTransform((west,step,0,north,0,-step));s=osr.SpatialReference();s.ImportFromEPSG(4326);tif.SetSpatialRef(s)
    candidate=historic=extra=missing=spans=0
    with (output/'mismatch-spans.jsonl').open('x') as out:
        for y in range(0,h,rows_per_block):
            if shutil.disk_usage(output).free<reserve:raise ValueError('free disk below configured reserve; partial output preserved')
            n=min(rows_per_block,h-y);water=np.zeros((n,w),dtype=np.uint8)
            for ds in masks:
                union_mask(ds,water,y)
            old=ref.ReadAsArray(0,y,w,n) if ref else None
            if old is not None and np.any((old != 0) & (old != 1)):raise ValueError('nonbinary reference')
            candidate+=int(np.count_nonzero(water))
            if old is not None:
                historic+=int(np.count_nonzero(old))
                extra+=int(np.count_nonzero((water==1)&(old==0)));missing+=int(np.count_nonzero((water==0)&(old==1)))
            tif.GetRasterBand(1).WriteArray(water,0,y)
            for offset,(a,b) in enumerate(zip(old,water) if old is not None else []):
                if not np.any(a!=b):continue
                cuts=np.flatnonzero(np.r_[True,(a[1:]!=a[:-1])|(b[1:]!=b[:-1]),True])
                for x0,x1 in zip(cuts[:-1],cuts[1:]):
                    if a[x0]!=b[x0]:
                        out.write(json.dumps({'row':y+offset,'start':int(x0),'end':int(x1),'reference':int(a[x0]),'candidate':int(b[x0])},separators=(',',':'))+'\n');spans+=1
            progress={'rows_done':y+n,'candidate_water_cells':candidate}
            if reference:progress.update({'extra_cells':extra,'missing_cells':missing})
            emit(json.dumps(progress),flush=True)
    tif.FlushCache();tif=None;ref=None;masks=[]
    for item in shards+([reference] if reference else []):
        if sha(item['path'])!=item['sha256']:raise ValueError('input changed during comparison')
    if config_path.read_bytes()!=data:raise ValueError('configuration changed during comparison')
    verify_lineage(cfg,grid)
    report={'status':'candidate-only','configuration_sha256':hashlib.sha256(data).hexdigest(),
            'grid':grid,'source_manifest':cfg['source_manifest'],'shard_count':len(shards),
            'rows_per_block':rows_per_block,'shards':shards,
            'candidate_water_cells':candidate,'reference_water_cells':historic,'candidate_extra_cells':extra,'candidate_missing_cells':missing,
            'mismatch_spans':spans,'mismatch_spans_sha256':sha(output/'mismatch-spans.jsonl'),'union_sha256':sha(output/'water-union.tif'),
            'limitations':'Grid comparison only; provenance, source equivalence, and decisions require independent review.'}
    if reference is None:
        for key in ('reference_water_cells','candidate_extra_cells','candidate_missing_cells','mismatch_spans','mismatch_spans_sha256'):
            report.pop(key)
        report['limitations'] = 'Candidate water mask; source selection and geographic correctness require independent review.'
    with (output/'config.json').open('xb') as f:f.write(data)
    with (output/'report.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    return report
if __name__=='__main__':
    if len(sys.argv)!=3:sys.exit('usage: aggregate_compare.py CONFIG.json NEW_OUTPUT_DIRECTORY')
    try:print(json.dumps(run(sys.argv[1],sys.argv[2]),indent=2),flush=True)
    except Exception as e:sys.exit(f'failed: {e}')
