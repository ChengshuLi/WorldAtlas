#!/usr/bin/python3
"""Experimental fail-closed land compiler; not an assertion of reviewed rules."""
import hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions(); ogr.UseExceptions()
SENTINEL = np.uint32(0xffffffff)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def pin(entry):
    keys(entry,('path','sha256'),'input pin')
    path = Path(entry['path'])
    if len(entry['sha256']) != 64 or sha(path) != entry['sha256'].lower():
        raise ValueError(f'input digest mismatch: {path}')
    return path

def polygon(entry):
    path = pin(entry)
    if path.suffix.lower() != '.geojson': raise ValueError('cut inputs must be standalone GeoJSON files')
    ds = ogr.Open(str(path), 0)
    if ds is None: raise ValueError(f'cannot open {path}')
    layer = ds.GetLayer(0); srs = layer.GetSpatialRef(); expected = osr.SpatialReference(); expected.ImportFromEPSG(4326)
    if srs: srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    expected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if srs is None or not srs.IsSame(expected): raise ValueError('partition geometry must be EPSG:4326')
    n = 0
    for feature in layer:
        geom = feature.GetGeometryRef()
        if geom is None or geom.IsEmpty() or ogr.GT_Flatten(geom.GetGeometryType()) not in (ogr.wkbPolygon, ogr.wkbMultiPolygon) or not geom.IsValid():
            raise ValueError(f'invalid partition polygon in {path}')
        n += 1
    if n != 1: raise ValueError('each partition file must contain exactly one valid feature')
    layer.ResetReading()
    return ds, layer

def keys(obj, allowed, where):
    extra=set(obj)-set(allowed)
    if extra: raise ValueError(f'unsupported {where} fields: {sorted(extra)}')

def build(cfg_path, output):
    config_bytes = Path(cfg_path).read_bytes(); cfg = json.loads(config_bytes)
    keys(cfg, ('schema','decision_revision','revision_status','provenance_note','grid','physical_rows','physical_runs','component_rows','component_runs','strip_rows','rules'), 'config')
    if cfg.get('schema') != 'land-decision-compiler-prototype-v1': raise ValueError('unknown schema')
    if not cfg.get('decision_revision') or cfg.get('revision_status') not in ('draft','accepted') or not cfg.get('provenance_note'):
        raise ValueError('decision revision, status, and provenance note are required')
    grid = cfg['grid']; keys(grid,('width','height','step','west','north'),'grid'); w, h = grid['width'], grid['height']; step = grid['step']
    if not isinstance(w,int) or not isinstance(h,int) or w<=0 or h<=0 or not all(math.isfinite(v) for v in (step,grid['west'],grid['north'])) or not 0<step<=360 or grid['west'] < -180 or grid['west']+w*step>180.0000001 or grid['north']>90 or grid['north']-h*step< -90.0000001: raise ValueError('invalid grid')
    source_files = [pin(cfg[k]) for k in ('physical_rows','physical_runs','component_rows','component_runs')]
    pr, pv, cr, cv = [np.memmap(f, mode='r', dtype='<u4') for f in source_files]
    if len(pr)!=h+1 or len(cr)!=h+1 or pr[0]!=0 or cr[0]!=0 or len(pv)%2 or len(cv)%3 or pr[-1]!=len(pv)//2 or cr[-1]!=len(cv)//3 or np.any(pr[1:]<pr[:-1]) or np.any(cr[1:]<cr[:-1]):
        raise ValueError('invalid input offsets or lengths')
    pv=pv.reshape(-1,2); cv=cv.reshape(-1,3)
    rules={}; partition={}; layers=[]; rule_ids=set()
    for rule in cfg['rules']:
        keys(rule,('component_id','rule_id','source_evidence','kind','code','parts'),'rule')
        root=rule['component_id']; rid=rule.get('rule_id'); evidence=rule.get('source_evidence')
        if not isinstance(root,int) or not 0<=root<int(SENTINEL) or not rid or not evidence: raise ValueError('every rule needs a component, ID and source evidence')
        if root in rules: raise ValueError(f'duplicate/conflicting component rule {root}')
        if rid in rule_ids: raise ValueError(f'duplicate rule ID {rid}')
        rule_ids.add(rid)
        if rule['kind']=='whole_component':
            if 'parts' in rule: raise ValueError('whole-component rule cannot contain parts')
            code=rule['code'];
            if code not in range(17,23): raise ValueError('invalid continent code')
            rules[root]=code
        elif rule['kind']=='polygon_partition':
            if 'code' in rule: raise ValueError('partition cannot have a whole-component code')
            if not rule.get('parts') or len(rule['parts'])>255: raise ValueError('partition needs 1 to 255 parts')
            ids=[part.get('part_id') for part in rule['parts']]
            if len(set(ids)) != len(ids): raise ValueError('duplicate partition part ID')
            rules[root]=0; parts=[]
            for part in rule['parts']:
                keys(part,('part_id','code','geometry'),'partition part')
                if part['code'] not in range(17,23) or not part.get('part_id'): raise ValueError('invalid partition part')
                ds,layer=polygon(part['geometry']); layers.append((ds,layer)); parts.append((part['code'],layer,part['geometry']))
            partition[root]=parts
        else: raise ValueError('unknown rule kind')
    if not rules: raise ValueError('no rules')
    strip=cfg.get('strip_rows',128)
    if not isinstance(strip,int) or not 1<=strip<=1024: raise ValueError('invalid strip size')
    os.mkdir(output); out=Path(output); offsets=[0]; seen=set(); total_land=0
    with (out/'runs.u32le').open('xb') as stream:
        for y0 in range(0,h,strip):
            n=min(strip,h-y0); rootgrid=np.full((n,w), SENTINEL, dtype=np.uint32)
            values=np.ones((n,w),dtype=np.uint8)
            for dy in range(n):
                y=y0+dy; start=0; phys=np.ones(w,dtype=np.uint8)
                for end,code in pv[int(pr[y]):int(pr[y+1])]:
                    end=int(end); code=int(code)
                    if end<=start or end>w or code not in (1,17): raise ValueError(f'invalid physical row {y}')
                    phys[start:end]=code; start=end
                if start!=w: raise ValueError(f'incomplete physical row {y}')
                last=0
                for start,end,root in cv[int(cr[y]):int(cr[y+1])]:
                    start,end,root=int(start),int(end),int(root)
                    if start<last or end<=start or end>w or root==int(SENTINEL): raise ValueError(f'invalid component row {y}')
                    rootgrid[dy,start:end]=root; last=end; seen.add(root)
                    if root not in rules: raise ValueError(f'unassigned component ID: {root}')
                    values[dy,start:end]=rules[root]
                if np.any((rootgrid[dy]!=SENTINEL)!=(phys==17)): raise ValueError(f'physical/component footprint mismatch row {y}')
                total_land += int(np.count_nonzero(phys==17))
            active=set(int(x) for x in np.unique(rootgrid) if x!=SENTINEL)
            missing=active-rules.keys()
            if missing: raise ValueError(f'unassigned component IDs: {sorted(missing)[:20]}')
            for root in active & partition.keys():
                hits=np.zeros((n,w),dtype=np.uint8); dest=np.zeros((n,w),dtype=np.uint8); target=rootgrid==root
                for code,layer,_ in partition[root]:
                    raster=gdal.GetDriverByName('MEM').Create('',w,n,1,gdal.GDT_Byte)
                    raster.SetGeoTransform((grid['west'],step,0,grid['north']-y0*step,0,-step))
                    raster.GetRasterBand(1).Fill(0); layer.ResetReading()
                    gdal.RasterizeLayer(raster,[1],layer,burn_values=[1])
                    mask=(raster.ReadAsArray()!=0)&target; hits[mask]+=1; dest[mask]=code
                if np.any(hits[target]!=1): raise ValueError(f'partition gap or overlap on component {root} in rows {y0}:{y0+n}')
                values[target]=dest[target]
            if np.any(values==0): raise ValueError('unassigned land remains')
            for row in values:
                changes=np.flatnonzero(np.r_[row[1:]!=row[:-1],True]); pairs=np.column_stack((changes+1,row[changes])).astype('<u4'); pairs.tofile(stream); offsets.append(offsets[-1]+len(pairs))
                if offsets[-1]>np.iinfo(np.uint32).max: raise ValueError('too many runs')
    unused=set(rules)-seen
    if unused: raise ValueError(f'rules reference absent component IDs: {sorted(unused)[:20]}')
    np.asarray(offsets,dtype='<u4').tofile(out/'rows.u32le')
    if Path(cfg_path).read_bytes()!=config_bytes: raise ValueError('config changed during build')
    for k in ('physical_rows','physical_runs','component_rows','component_runs'): pin(cfg[k])
    for parts in partition.values():
        for _,_,entry in parts: pin(entry)
    (out/'config.json').write_bytes(config_bytes)
    report={'schema':'land-decision-compiler-prototype-report-v1','status':'experimental-not-published','decision_revision':cfg['decision_revision'],'revision_status':cfg['revision_status'],'config_sha256':hashlib.sha256(config_bytes).hexdigest(),'program_sha256':sha(__file__),'gdal_version':gdal.VersionInfo('--version'),'numpy_version':np.__version__,'input_sha256':{k:cfg[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')},'land_cells':total_land,'components':len(seen),'output_rows_sha256':sha(out/'rows.u32le'),'output_runs_sha256':sha(out/'runs.u32le'),'limitations':'Component IDs derive from the exact physical raster; boundary-on-center behavior uses GDAL defaults and requires independent review.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: assign_land.py CONFIG NEW_OUTPUT_DIR')
    try: print(json.dumps(build(sys.argv[1],sys.argv[2]),indent=2))
    except Exception as e: print(f'error: {e}',file=sys.stderr); raise SystemExit(1)
