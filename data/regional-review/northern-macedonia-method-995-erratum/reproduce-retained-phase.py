#!/usr/bin/env python3
"""Offline, immutable reproduction of the retained 2016 MKD source comparison.

Never accesses AKN, never changes old evidence, and refuses to overwrite output.
"""
from __future__ import annotations
import hashlib, importlib.util, io, json, pathlib, subprocess, sys, zipfile
from datetime import date
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = ROOT / 'data/regional-review/northern-macedonia-method-995-erratum'
BASELINE = 'b6cfaada43a1e0472cd833d16733d1fd6065eaec'
DESCRIPTORS = OWNED / 'baseline-inputs.json'
RUNNER_PIN = OWNED / 'runner-pin.json'
EXPECTED_RUNNER = 'data/regional-review/northern-macedonia-method-995-erratum/reproduce-retained-phase.py'
EXPECTED_HELPERS = {
 'data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py':'9055d094ab0392ecbfc23cbe47876a8c9ad77bccfc2ea30b6860ae82f0d2dfb6',
 'scripts/evidence/geometry.py':'944541968fcdf065b9c4b6105be227c3e0e14b6a20916f4fa21f851338c7a305',
 'scripts/ellipsoidal_area.py':'4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12',
}

def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],stderr=subprocess.PIPE)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def baseline_blob(path):
    row=git('ls-tree','-z',BASELINE,'--',path).decode().rstrip('\0')
    if not row.startswith('100644 ') or row.split('\t',1)[-1] != path: raise ValueError('baseline not ordinary file: '+path)
    oid=row.split()[2]
    return git('cat-file','blob',oid)
def load_pinned(desc):
    raw=baseline_blob(desc['path'])
    if len(raw)!=desc['bytes'] or digest(raw)!=desc['sha256']: raise ValueError('baseline bytes mismatch: '+desc['path'])
    if len(raw)>32*1024*1024: raise ValueError('individual input exceeds 32 MiB')
    return raw

def main():
    ownraw=DESCRIPTORS.read_bytes(); index=json.loads(ownraw)
    if digest((json.dumps({k:v for k,v in index.items() if k!='sha256'},indent=2)+'\n').encode())!=index['sha256']: raise ValueError('descriptor self-hash mismatch')
    if index['baseline_commit']!=BASELINE or len(index['files'])!=30: raise ValueError('wrong baseline or descriptor inventory')
    blobs={d['path']:load_pinned(d) for d in index['files']}
    if sum(map(len,blobs.values()))!=20_430_279: raise ValueError('ordinary input aggregate mismatch')
    for path,expected in EXPECTED_HELPERS.items():
        if digest(blobs[path])!=expected: raise ValueError('pinned helper/code mismatch: '+path)
    runner_hash=digest(pathlib.Path(__file__).read_bytes())
    if json.loads(RUNNER_PIN.read_text())['sha256']!=runner_hash: raise ValueError('runner code pin mismatch')
    sys.path.insert(0,str(ROOT/'scripts'))
    helper_path=ROOT/'data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py'
    if digest(helper_path.read_bytes())!=EXPECTED_HELPERS[str(helper_path.relative_to(ROOT))]: raise ValueError('working tree reproducer differs from pinned code')
    spec=importlib.util.spec_from_file_location('pinned_original_reproducer',helper_path)
    original=importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    original.SOURCE_FILE=pathlib.Path('/nonexistent')
    original.HDX_ZIP=pathlib.Path('/nonexistent')
    # Extract only from already pinned Git blobs. ZIP remains in memory.
    source_raw=blobs['data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-MKD-ADM2.geojson']
    zip_path='data/regional-review/followup-northern-macedonia-422-roster-20261005/source/hdx-rimwge/mkd_admn_adm_py_eurogeographics-ntes_pp.zip'
    zip_raw=blobs[zip_path]
    with zipfile.ZipFile(io.BytesIO(zip_raw)) as z:
        bad=z.testzip()
        if bad: raise ValueError('ZIP CRC failure: '+bad)
        members=z.infolist()
        decoded=sum(x.file_size for x in members)
        if len(members)!=24 or decoded!=387_976 or any(x.file_size>32*1024*1024 for x in members): raise ValueError('archive admission mismatch')
    hdx_rows,hdx_geometries=original.read_hdx_adm4(zip_raw)
    source=json.loads(source_raw); features=source['features']
    assessment_path='data/regional-review/regional-review-3c4fe25a21fa428d/source/subject-assessments.json'
    assessments=json.loads(blobs[assessment_path])['subjects']
    scoped={r['location_id']:r for r in assessments if r.get('location_id','').startswith('gb:MKD:ADM2:')}
    if len(scoped)!=84 or len(features)!=84: raise ValueError('expected exact native 84 subject scope')
    by_name={f['properties']['shapeName']:f for f in features}
    if len(by_name)!=84 or set(by_name)!=set(hdx_geometries): raise ValueError('source pair roster mismatch')
    trans=Transformer.from_crs('EPSG:4258','EPSG:4326',always_xy=True).transform
    pairs=[]
    for name in sorted(by_name):
        feat=by_name[name]; sid='gb:MKD:ADM2:'+feat['properties']['shapeID']
        if sid not in scoped: raise ValueError('pair outside exact subject scope: '+sid)
        left=transform(trans,hdx_geometries[name]); right=shape(feat['geometry'])
        denominator=original.land_area_m2(left)
        delta=original.land_area_or_zero(left.symmetric_difference(right))/denominator
        pairs.append({'location_id':sid,'source_name':name,'symmetric_difference_area_fraction':delta,'below_1e-8_area_fraction_screen':delta<1e-8})
    if {p['location_id'] for p in pairs}!=set(scoped): raise ValueError('not every native subject appears exactly once')
    if any(p['symmetric_difference_area_fraction']<=0 for p in pairs): raise ValueError('expected nonzero residual for every pair')
    maximum=max(p['symmetric_difference_area_fraction'] for p in pairs)
    parents=sorted({r['parent_id'] for r in scoped.values()})
    if len(parents)!=8: raise ValueError('expected eight read-only parent contexts')
    report={'version':1,'issue':1166,'baseline_commit':BASELINE,'retrieved_at':'2026-10-06','source_phase':'retained HDX 2016 ADM4 vs retained geoBoundaries MKD ADM2 2016','inputs':{d['path']:{'bytes':d['bytes'],'sha256':d['sha256']} for d in index['files']},'archive':{'sha256':digest(zip_raw),'members':len(members),'decoded_bytes':decoded,'crc':'passed'},'scope':{'native_subject_count':len(pairs),'unique_subject_count':len({p['location_id'] for p in pairs}),'parent_context_ids':parents,'parent_context_role':'reference only'},'method':{'source_crs':'EPSG:4258','target_crs':'EPSG:4326','axis_order':'longitude-latitude','area_method':'WGS84 straight-source-edge ellipsoidal integral','metric':'area(symmetric_difference) / area(transformed HDX source)','units':'dimensionless area fraction','tolerance':1e-8,'tolerance_interpretation':'area-fraction screen only; not a distance tolerance','hausdorff_distance_computed':False,'projected_distance_computed':False},'results':{'pair_count':len(pairs),'nonzero_residual_count':sum(p['symmetric_difference_area_fraction']>0 for p in pairs),'within_area_fraction_screen_count':sum(p['below_1e-8_area_fraction_screen'] for p in pairs),'maximum_symmetric_difference_area_fraction':maximum,'pairs':pairs},'limits':['No EPSG:3035 transform or Hausdorff distance is computed.','Does not verify current AKN geometry, legal boundary correctness, or stored Atlas geometry equality.','Source vintage is identified as 2016 by retained source metadata; legal effective date is not established.','The 1e-8 threshold is a dimensionless area fraction, not a millimetre distance.']}
    output=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else OWNED/'v1/run-one.json'
    if not output.is_absolute(): output=ROOT/output
    if ROOT not in output.parents or not str(output).startswith(str(OWNED)+ '/'): raise ValueError('output must be inside declared owned path')
    output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(report,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
    fd=None
    import os
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    fd=os.open(output,flags,0o644)
    with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    print(json.dumps({'output':str(output.relative_to(ROOT)),'bytes':len(raw),'sha256':digest(raw),'pairs':len(pairs),'maximum_area_fraction':maximum},sort_keys=True))
if __name__=='__main__': main()
