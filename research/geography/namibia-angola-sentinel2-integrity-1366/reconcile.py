#!/usr/bin/env python3
"""Authenticate and independently reconcile the retained Namibia–Angola S2 packet.

Inputs are read from immutable Git objects, never from mutable working-tree paths.
The only output is admitted into a new, exclusive run directory.
"""
from __future__ import annotations
import hashlib, io, json, os, pathlib, subprocess, sys, zipfile
from datetime import datetime, timezone

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geom_transform
from shapely import contains_xy

BASE = pathlib.Path(__file__).resolve().parent
REPO = BASE.parents[2]
OLD = "research/geography/namibia-angola-sentinel2-followup-20261007/"
PACKET = "f513f7d6cb5fb088c1fca0238d915426a14ecfa8"
GEOM = "c53f0aa473eb32c07a5cf4f57df3a86663a625ae"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
EXPECTED_KEYS = {"col", "component_bits", "contact_bits", "green_dn_10m_2x2", "nir_dn_10m_2x2", "row", "scl_20m", "swir16_dn_20m"}
SELF_PIN = 'd2de7d6e68258caf9714ba9ec5a9f001d4e3132bad6b373df5f66791b4ac9858'

def blob(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO, check=True, stdout=subprocess.PIPE).stdout

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_candidate(path):
    target=BASE/path
    if not target.resolve().is_relative_to(BASE.resolve()): raise ValueError('candidate evidence path escaped owned directory')
    for ancestor in (target,*target.parents):
        if ancestor==BASE.parent: break
        if ancestor.is_symlink(): raise ValueError('symlink in candidate evidence path')
    if not target.is_file() or target.stat().st_size>MAX_FILE: raise ValueError('candidate file missing or exceeds cap')
    return target.read_bytes()

def verify_self():
    raw=read_candidate('reconcile.py')
    validate_code_bytes(raw,SELF_PIN)
    return digest(raw)

def validate_code_bytes(raw, expected):
    if raw.count(expected.encode())!=1 or digest(raw.replace(expected.encode(),b'0'*64))!=expected:
        raise ValueError('reconciliation executable differs from its embedded byte pin')

def latest_receipt(prefix):
    candidates=sorted((BASE/'controls').glob(prefix+'*.json'))
    if not candidates: raise ValueError('required control receipt missing: '+prefix)
    path=max(candidates,key=lambda p:p.stat().st_mtime_ns)
    return path,read_candidate(str(path.relative_to(BASE)))

def bounded_npz(raw: bytes) -> dict[str, np.ndarray]:
    if len(raw) > MAX_FILE:
        raise ValueError("source archive exceeds per-file cap")
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for info in z.infolist():
            if info.file_size > MAX_FILE:
                raise ValueError("decoded member exceeds per-file cap")
            total += info.file_size
        if total > MAX_TOTAL:
            raise ValueError("decoded archive exceeds aggregate cap")
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        if set(z.files) != EXPECTED_KEYS:
            raise ValueError("unexpected NPZ member inventory")
        arrays = {k: z[k] for k in z.files}
    return arrays

def validate_roster(selected_ids, receipt_ids):
    if len(selected_ids)!=16 or len(set(selected_ids))!=16 or len(receipt_ids)!=16 or len(set(receipt_ids))!=16 or set(receipt_ids)!=set(selected_ids):
        raise ValueError('selected roster and complete unique window receipt differ')

def validate_membership(expected, actual, label):
    if not np.array_equal(expected,actual):
        raise ValueError('independent native-grid membership mismatch: '+label)

def validate_window_bytes(raw, receipt, path):
    if digest(raw)!=receipt['npz_sha256'] or len(raw)!=receipt['npz_bytes']:
        raise ValueError('window bytes differ from immutable issue/manifest pins: '+path)

def validate_arrays(a):
    count=len(a['row'])
    if set(a)!=EXPECTED_KEYS or any(len(a[k])!=count for k in EXPECTED_KEYS): raise ValueError('array inventory or lengths differ')
    if a['green_dn_10m_2x2'].shape!=(count,4) or a['nir_dn_10m_2x2'].shape!=(count,4): raise ValueError('10m block layout differs')
    if not all(a[k].dtype==np.dtype(t) for k,t in [('row','int32'),('col','int32'),('component_bits','uint32'),('contact_bits','uint16'),('green_dn_10m_2x2','uint16'),('nir_dn_10m_2x2','uint16'),('swir16_dn_20m','uint16'),('scl_20m','uint8')]): raise ValueError('array dtype differs')
    return count

def validate_scene_grid(item, receipt, count):
    props=item['properties']; asset_meta=receipt['asset_metadata']
    if receipt.get('product_uri')!=props.get('s2:product_uri') or receipt.get('processing_baseline')!=props.get('s2:processing_baseline'):
        raise ValueError('scene product/baseline identity differs')
    if float(props['s2:processing_baseline'])>=4 or props.get('earthsearch:boa_offset_applied') is not False:
        raise ValueError('scene radiometric offset is not admitted')
    expected={'green':10,'nir':10,'swir16':20,'scl':20}
    for band,resolution in expected.items():
        stac=item['assets'][band]; meta=asset_meta[band]
        stac_resolution=stac.get('gsd',stac['raster:bands'][0].get('spatial_resolution'))
        if float(meta['resolution'][0])!=resolution or float(meta['resolution'][1])!=resolution or float(stac_resolution)!=resolution:
            raise ValueError('scene band ground resolution differs: '+band)
        if list(meta['transform'])!=list(stac['proj:transform']) or [meta['height'],meta['width']]!=list(stac['proj:shape']):
            raise ValueError('scene band grid transform/shape differs: '+band)
        if meta['raster_crs']!='EPSG:'+str(props['proj:epsg']): raise ValueError('scene CRS differs: '+band)
        if band in ('green','nir','swir16'):
            raster=stac['raster:bands'][0]
            if float(raster['scale'])!=0.0001 or float(raster['offset'])!=0.0: raise ValueError('scene radiometry differs: '+band)
    if receipt.get('sampled_pixel_count')!=count: raise ValueError('sample count differs from window receipt')

def metrics(mask, a):
    # Function body is byte-for-byte equivalent in semantics to the pinned v1
    # metric routine; the exact source hash is recorded in evidence-quality.json.
    n=int(mask.sum())
    if n == 0:
        return {"mask_center_pixels":0,"usable_index_pixels":0,"clear_fraction":None,"scl_histogram":{k:0 for k in ('no_data','saturated_or_defective','dark_area','cloud_shadow','vegetation','bare_soil','water','low_probability_cloud_or_unclassified','medium_probability_cloud','high_probability_cloud','cirrus','snow_or_ice')},"mndwi_counts":{"-0.1":0,"0.0":0,"0.1":0},"ndwi_counts":{"-0.1":0,"0.0":0,"0.1":0},"scl_water_centers":0,"mndwi_scl6_concordant":0,"mndwi_median":None,"ndwi_median":None}
    g=a['green_dn_10m_2x2'][mask].astype(np.float64); nr=a['nir_dn_10m_2x2'][mask].astype(np.float64); sw=a['swir16_dn_20m'][mask].astype(np.float64); scl=a['scl_20m'][mask].astype(np.uint8)
    band=np.all(g>0,axis=1)&np.all(nr>0,axis=1)&(sw>0); clear=~np.isin(scl,[0,1,3,7,8,9,10,11]); valid=band&clear&(scl!=2)
    gr=g.mean(axis=1)*.0001; n_ref=nr.mean(axis=1)*.0001; sr=sw*.0001
    mv=valid&((gr+sr)>0); nv=valid&((gr+n_ref)>0); m=np.zeros(n); d=np.zeros(n); m[mv]=(gr[mv]-sr[mv])/(gr[mv]+sr[mv]); d[nv]=(gr[nv]-n_ref[nv])/(gr[nv]+n_ref[nv])
    names=['no_data','saturated_or_defective','dark_area','cloud_shadow','vegetation','bare_soil','water','low_probability_cloud_or_unclassified','medium_probability_cloud','high_probability_cloud','cirrus','snow_or_ice']
    hist={names[i]:int(np.count_nonzero(scl==i)) for i in range(12)}
    thresholds=(-0.1,0.0,0.1)
    return {'mask_center_pixels':n,'green_10m_subpixel_nodata_centers':int(np.count_nonzero(np.any(g==0,axis=1))),'nir_10m_subpixel_nodata_centers':int(np.count_nonzero(np.any(nr==0,axis=1))),'swir16_20m_nodata_centers':int(np.count_nonzero(sw==0)),'scl_20m_nodata_centers':int(np.count_nonzero(scl==0)),'all_band_valid_centers':int(np.count_nonzero(band)),'usable_index_pixels':int(np.count_nonzero(mv&nv)),'cloud_shadow_or_unclassified_centers':int(np.count_nonzero(np.isin(scl,[3,7,8,9,10]))),'saturated_or_defective_centers':int(np.count_nonzero(scl==1)),'dark_area_centers':int(np.count_nonzero(scl==2)),'snow_or_ice_centers':int(np.count_nonzero(scl==11)),'clear_fraction':round(float(np.count_nonzero(mv&nv)/n),8),'scl_histogram':hist,'scl_water_centers':int(np.count_nonzero(scl==6)),'mndwi_counts':{str(t):int(np.count_nonzero(mv&(m>=t))) for t in thresholds},'ndwi_counts':{str(t):int(np.count_nonzero(nv&(d>=t))) for t in thresholds},'mndwi_scl6_concordant':int(np.count_nonzero(mv&(scl==6)&(m>0))),'mndwi_median':round(float(np.median(m[mv])),8) if np.any(mv) else None,'ndwi_median':round(float(np.median(d[nv])),8) if np.any(nv) else None}

def aggregate_summaries(rows,kind,subjects):
    # Independently aggregate the admitted row ledger, then compare every field
    # with the 21 component and 10 contact summaries in the retained report.
    out=[]; windows=('2019-wet','2019-dry','2020-wet','2020-dry'); thresholds=('-0.1','0.0','0.1')
    for subject in subjects:
        selected=[r for r in rows if r['mask_kind']==kind and r['subject_id']==subject]
        bywindow={}
        for window in windows:
            rs=[r for r in selected if r['window']==window]
            bywindow[window]={'tile_observation_rows':len(rs),'center_pixels_across_tiles_nonadditive':sum(r['mask_center_pixels'] for r in rs),
              'clear_index_pixels_across_tiles_nonadditive':sum(r['usable_index_pixels'] for r in rs),
              'scl_water_centers_across_tiles_nonadditive':sum(r['scl_water_centers'] for r in rs),
              'concordant_scl6_and_positive_mndwi_centers_across_tiles_nonadditive':sum(r['mndwi_scl6_concordant'] for r in rs),
              'mndwi_nonnegative_centers_across_tiles_nonadditive':sum(r['mndwi_counts']['0.0'] for r in rs),
              'mndwi_threshold_sensitivity_nonadditive':{t:sum(r['mndwi_counts'][t] for r in rs) for t in thresholds}}
        scl=sum(r['scl_water_centers'] for r in selected); mndwi=sum(r['mndwi_counts']['0.0'] for r in selected)
        concordant=sum(r['mndwi_scl6_concordant'] for r in selected)
        if not sum(r['mask_center_pixels'] for r in selected): disposition='no-20m-pixel-center-samples; physical status unresolved at this resolution'
        elif scl and mndwi and concordant: disposition='Concordant SCL water-class and positive-MNDWI pixels occur; see per-window counts and valid fractions; observational water-like signal only'
        elif scl and mndwi: disposition='SCL water-class and nonnegative-MNDWI signals occur, but no positive-MNDWI SCL6 pixel is concordant; mixed optical evidence'
        elif scl: disposition='SCL water-class signal occurs but MNDWI is not concordant across all sampled windows; mixed optical evidence'
        elif mndwi: disposition='MNDWI water-like signal occurs without SCL water-class centers; ambiguous spectral response'
        else: disposition='No SCL water-class or nonnegative MNDWI sample detected in these dates; this does not prove dry land or non-water status'
        out.append({'subject_id':subject,'total_mask_centers_across_tiles_and_dates_nonadditive':sum(r['mask_center_pixels'] for r in selected),
          'clear_index_centers_across_tiles_and_dates_nonadditive':sum(r['usable_index_pixels'] for r in selected),
          'scl_water_centers_across_tiles_and_dates_nonadditive':scl,'mndwi_nonnegative_centers_across_tiles_and_dates_nonadditive':mndwi,
          'concordant_scl6_and_positive_mndwi_centers_across_tiles_and_dates_nonadditive':concordant,'disposition':disposition,'seasonal_windows':bywindow})
    return out

def main():
    code_sha256=verify_self()
    # Authenticate the consumed packet manifest and issue pins before reading data.
    inherited_manifest_raw=blob(PACKET,OLD+'evidence-quality.json')
    manifest=json.loads(inherited_manifest_raw)
    # Execute the shared guard only from its authenticated original Git blob.
    helper_path='scripts/evidence/immutable.py'
    helper_pin=next(x for x in manifest['baseline']['files'] if x['path']==helper_path)
    helper_source=blob(manifest['baseline']['commit'],helper_path)
    if digest(helper_source)!=helper_pin['sha256'] or len(helper_source)!=helper_pin['bytes']:
        raise ValueError('shared evidence helper drift')
    helper_ns={'__name__':'worldatlas_immutable_pinned'}
    exec(compile(helper_source,helper_path,'exec'),helper_ns)
    baseline=helper_ns['Baseline'](REPO,manifest['baseline']['commit'],manifest['baseline']['files'])
    baseline_paths={x['path'] for x in manifest['baseline']['files']}
    declared={x['path']:x['sha256'] for x in manifest['baseline']['files']}
    declared[OLD+'evidence-quality.json']=digest(inherited_manifest_raw)
    descriptors=[]
    for group in (manifest.get('sources',[]), [manifest.get('outputs',[])]):
        if group and isinstance(group[0],list): group=group[0]
        for entry in group:
            descriptors.extend(entry.get('files',[entry] if 'path' in entry else []))
    for entry in descriptors:
        declared[entry['path']]=entry['sha256']
    source={}; source_commits={}
    for path,sha in declared.items():
        # Files that existed before the 2019–2020 packet are pinned at the
        # original baseline; newly retained files are pinned at the packet merge.
        commit=manifest['baseline']['commit'] if path in baseline_paths else PACKET
        raw=blob(commit,path)
        if digest(raw)!=sha: raise ValueError('inherited source does not match its retained pin: '+path)
        source[path]=raw; source_commits[path]=commit
    issue_snapshot_path=BASE/'inputs'/'issue-contract-snapshot.json'
    issue_snapshot_raw=read_candidate('inputs/issue-contract-snapshot.json')
    baseline.admit('candidate:inputs/issue-contract-snapshot.json',len(issue_snapshot_raw))
    issue_snapshot=json.loads(issue_snapshot_raw)
    marker='<!-- worldatlas-work:v1\n'
    start=issue_snapshot['body'].rfind(marker)
    end=issue_snapshot['body'].find('-->',start)
    if start<0 or end<0: raise ValueError('saved issue work contract missing')
    work_contract=json.loads(issue_snapshot['body'][start+len(marker):end])
    issue_pins=work_contract['evidence_quality']['pins']
    alias_files=manifest['baseline'].get('pin_files',{})
    verified_issue_pins={}
    for name,want in issue_pins.items():
        path=name if name.startswith(('data/','coordination/','research/','scripts/')) else alias_files[name]
        raw=source.get(path)
        if raw is None:
            for commit in (GEOM,PACKET):
                try: candidate=blob(commit,path)
                except subprocess.CalledProcessError: continue
                if digest(candidate)==want:
                    raw=candidate; source[path]=raw; source_commits[path]=commit; break
        if raw is None or digest(raw)!=want: raise ValueError('issue whole-file pin not authenticated: '+name)
        verified_issue_pins[name]={'path':path,'sha256':want,'bytes':len(raw)}
    if len(verified_issue_pins)!=39: raise ValueError('expected all 39 declared issue pins')
    selected_raw=source[OLD+'inputs/selected-sentinel2-items.json']; receipts_raw=source[OLD+'inputs/source-window-receipts.json']
    selected=json.loads(selected_raw)['selected_items']; receipts=json.loads(receipts_raw)['records']
    ids=[x['id'] for x in selected]
    validate_roster(ids,[r['item_id'] for r in receipts])
    discovery={}
    discovery_pages=[(p,raw) for p,raw in source.items() if p.startswith(OLD+'inputs/earth-search-stac-') and ('2019-' in p or '2020-' in p) and '-page-' in p]
    if len(discovery_pages)!=8: raise ValueError('complete 2019-2020 discovery page inventory differs')
    for page_path,page_raw in discovery_pages:
        page=json.loads(page_raw)
        if any(link.get('rel')=='next' for link in page.get('links',[])) and page_path.endswith('page-02.json'):
            raise ValueError('retained terminal discovery page unexpectedly has another page')
        for feature in page['features']: discovery.setdefault(feature['id'],[]).append(feature)
    for item in selected:
        copies=discovery.get(item['id'],[])
        if len(copies)!=1 or copies[0]!=item: raise ValueError('selected item is absent, repeated or differs from complete discovery page: '+item['id'])
    cf=json.loads(source['research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson'])['features']
    tf=json.loads(source['research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson'])['features']
    comp=[shape(f['geometry']) for f in cf]; contacts=[shape(f['geometry']) for f in tf]
    comp_ids=[f['id'] for f in cf]; contact_ids=[f"gb:{f['properties']['shapeGroup']}:{f['properties']['shapeType']}:{f['properties']['shapeID']}" for f in tf]
    stac={x['id']:x for x in selected}; rows=[]; membership_checked=0; bytes_total=0; delta_rows=[]
    for rec in receipts:
        p=OLD+rec['npz_path']; raw=source.get(p)
        if raw is None: raw=blob(PACKET,p); source[p]=raw
        validate_window_bytes(raw,rec,p)
        bytes_total+=len(raw); a=bounded_npz(raw); item=stac[rec['item_id']]
        # Account decoded archive members against the helper's complete phase cap.
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for info in z.infolist(): baseline.admit(p+':'+info.filename,info.file_size)
        count=validate_arrays(a); validate_scene_grid(item,rec,count)
        epsg=int(item['properties']['proj:epsg']); trans=item['assets']['scl']['proj:transform']; x=trans[2]+(a['col']+.5)*trans[0]; y=trans[5]+(a['row']+.5)*trans[4]
        to_native=Transformer.from_crs(4326,epsg,always_xy=True)
        native_comp=[geom_transform(to_native.transform,g) for g in comp]; native_contacts=[geom_transform(to_native.transform,g) for g in contacts]
        cb=np.zeros(count,dtype=np.uint32); tb=np.zeros(count,dtype=np.uint16)
        for i,g in enumerate(native_comp): cb |= contains_xy(g,x,y).astype(np.uint32)<<i
        for i,g in enumerate(native_contacts): tb |= contains_xy(g,x,y).astype(np.uint16)<<i
        validate_membership(cb,a['component_bits'],rec['item_id']+' components')
        validate_membership(tb,a['contact_bits'],rec['item_id']+' contacts')
        membership_checked+=count
        props=item['properties']; native=None
        xmlpath=OLD+f"sources/metadata/{rec['item_id']}_granule_metadata.xml"
        if xmlpath in source:
            import re
            m=re.search(rb'<SENSING_TIME\b[^>]*>([^<]+)</SENSING_TIME>',source[xmlpath]); native=m.group(1).decode() if m else None
        if not native: raise ValueError('native granule sensing time missing: '+rec['item_id'])
        catalog=props['datetime']; delta=None
        if native:
            dt=lambda s: datetime.fromisoformat(s.replace('Z','+00:00'))
            delta=(dt(catalog)-dt(native)).total_seconds(); delta_rows.append(delta)
        for kind,subjects,bits in [('component',comp_ids,a['component_bits']),('candidate-contact-overlap_union',contact_ids,a['contact_bits'])]:
            for i,subject in enumerate(subjects):
                row={'mask_kind':kind,'subject_id':subject,'item_id':rec['item_id'],'window':rec['window'],'datetime_utc':catalog,'catalog_datetime_utc':catalog,'native_sensing_time_utc':native,'sensing_time_delta_seconds':delta,'sensing_time_discrepancy_over_1_second':bool(delta is not None and abs(delta)>1),'mgrs_tile':props['grid:code'],'processing_baseline':props['s2:processing_baseline'],'scene_cloud_percent':props.get('eo:cloud_cover'),'scene_nodata_percent':props.get('s2:nodata_pixel_percentage'),'scale_offset':{'green':[.0001,0.0],'nir':[.0001,0.0],'swir16':[.0001,0.0]},'grid_resolution_m':20,'source_window_sha256':digest(raw),'source_window_bytes':len(raw)}
                row.update(metrics((bits&(1<<i))!=0,a)); rows.append(row)
    for path,raw in source.items(): baseline.admit(path,len(raw))
    issue_contract_desc={'path':'research/geography/namibia-angola-sentinel2-integrity-1366/inputs/issue-contract-snapshot.json','bytes':len(issue_snapshot_raw),'sha256':digest(issue_snapshot_raw),'hash_kind':'file-bytes'}
    local_scripts={name:read_candidate(name) for name in ('reconcile.py','input_controls.py','writer_controls.py','legacy_entrypoint_controls.py')}
    for name,raw in local_scripts.items(): baseline.admit('candidate:'+name,len(raw))
    input_control_path,input_control_raw=latest_receipt('input-controls')
    writer_control_path,writer_control_raw=latest_receipt('writer-probes')
    legacy_control_path,legacy_control_raw=latest_receipt('legacy-entrypoints')
    input_control=json.loads(input_control_raw); writer_control=json.loads(writer_control_raw); legacy_control=json.loads(legacy_control_raw)
    baseline.admit('candidate:'+str(input_control_path.relative_to(BASE)),len(input_control_raw))
    baseline.admit('candidate:'+str(writer_control_path.relative_to(BASE)),len(writer_control_raw))
    baseline.admit('candidate:'+str(legacy_control_path.relative_to(BASE)),len(legacy_control_raw))
    if not all(v for k,v in input_control['tests'].items() if k.endswith('_rejected')) or not writer_control['results']['completion_receipt_absent_after_failure']:
        raise ValueError('required negative control receipt absent or failing')
    legacy=legacy_control['results']
    if not (legacy['analysis']['complete_output_matches_retained_run_one'] and legacy['analysis']['occupied_output_overwritten'] and legacy['analysis']['outside_path_traversal_created'] and legacy['analysis']['dangling_symlink_followed'] and legacy['analysis']['partial_result_bytes_after_os_failure']==1024 and legacy['selection']['occupied_output_overwritten'] and legacy['selection']['dangling_symlink_followed'] and legacy['extractor_writer']['occupied_npz_overwritten'] and legacy['extractor_writer']['dangling_npz_symlink_followed']):
        raise ValueError('actual legacy writer regression evidence missing or no longer reproduces')
    expected={(kind,sid,i) for kind,sids in [('component',comp_ids),('candidate-contact-overlap_union',contact_ids)] for sid in sids for i in ids}
    actual=[(r['mask_kind'],r['subject_id'],r['item_id']) for r in rows]
    if len(actual)!=496 or len(set(actual))!=496 or set(actual)!=expected: raise ValueError('subject×scene identity matrix incomplete, duplicate or foreign')
    oldrun=json.loads(source[OLD+'runs/run-one.json'])
    oldrows={(r['mask_kind'],r['subject_id'],r['item_id']):r for r in oldrun['scene_observations']}
    checked_fields=sorted(set(oldrun['scene_observations'][0]))
    for r in rows:
        old=oldrows[(r['mask_kind'],r['subject_id'],r['item_id'])]
        diffs=[k for k in checked_fields if r.get(k)!=old.get(k)]
        if diffs: raise ValueError('retained measurement differs from independent recomputation: '+r['item_id']+'/'+r['subject_id']+': '+','.join(diffs))
    candidate_summary=aggregate_summaries(rows,'component',comp_ids)
    contact_summary=aggregate_summaries(rows,'candidate-contact-overlap_union',contact_ids)
    if candidate_summary!=oldrun['candidate_summaries'] or contact_summary!=oldrun['contact_overlap_summaries']:
        raise ValueError('independent aggregate summaries differ from retained 21-component/10-contact summaries')
    attempts=read_candidate('attempts.json'); baseline.admit('candidate:attempts.json',len(attempts))
    report={'version':1,'evidence_vintage':'2026-10-08; source files retrieved in their pinned historical vintages','issue_contract_snapshot':issue_contract_desc,'issue_pin_count':len(verified_issue_pins),'issue_whole_file_pins_verified':verified_issue_pins,'authenticated_commits':{'original_geometry':GEOM,'retained_packet':PACKET},'authenticated_files':[{'path':p,'commit':source_commits[p],'bytes':len(raw),'sha256':digest(raw)} for p,raw in sorted(source.items())],'executed_code_files':{name:{'bytes':len(raw),'sha256':digest(raw)} for name,raw in sorted(local_scripts.items())},'reconcile_executable_sha256':code_sha256,'reconcile_embedded_normalized_sha256':SELF_PIN,'attempts_sha256':digest(attempts),'negative_control_receipts':{'input_controls_path':str(input_control_path.relative_to(BASE)),'input_controls_sha256':digest(input_control_raw),'writer_controls_path':str(writer_control_path.relative_to(BASE)),'writer_controls_sha256':digest(writer_control_raw)},'authenticated_file_count':len(source),'authenticated_raw_bytes':sum(map(len,source.values())),'source_window_raw_bytes':bytes_total,'discovery_pages_checked':len(discovery_pages),'selected_scenes_exactly_reconciled_to_discovery_pages':len(ids),'native_scene_grids_reconciled':len(ids),'selected_scene_count':len(ids),'component_count':len(comp),'contact_count':len(contacts),'reconciled_observation_rows':len(rows),'exact_unique_identity_matrix':True,'independent_geometry_membership':{'pixel_centers':membership_checked,'component_bit_mismatches':0,'contact_bit_mismatches':0,'crs_handling':'WGS84 source geometry transformed to native UTM with pyproj always_xy=True; Shapely contains_xy at affine pixel centers'},'independent_measurements_match_retained_report':{'fields_per_row':checked_fields,'rows':len(rows),'mismatches':0},'aggregate_summaries_match_retained_report':{'candidate_summaries':len(candidate_summary),'contact_overlap_summaries':len(contact_summary),'total_summaries':len(candidate_summary)+len(contact_summary),'mismatches':0},'candidate_summaries':candidate_summary,'contact_overlap_summaries':contact_summary,'sensing_time_reconciliation':{'per_scene_deltas_seconds':{r['item_id']:r['sensing_time_delta_seconds'] for r in rows if r['mask_kind']=='component' and r['subject_id']==comp_ids[0]},'over_one_second_count':sum(abs(x)>1 for x in delta_rows),'cause':'unresolved; both catalog and native values retained'},'scene_observations':rows}
    report['negative_control_receipts']['legacy_entrypoints_path']=str(legacy_control_path.relative_to(BASE))
    report['negative_control_receipts']['legacy_entrypoints_sha256']=digest(legacy_control_raw)
    out=json.dumps(report,sort_keys=True,indent=2).encode()+b'\n'
    vintage='reconciliation-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')
    writer=helper_ns['NewVintage'](baseline,'research/geography/namibia-angola-sentinel2-integrity-1366/',vintage,['reconciliation.json'])
    published=writer.publish({'reconciliation.json':report})
    run=writer.root
    print(json.dumps({'run':str(run.relative_to(BASE)),'rows':len(rows),'membership_pixels':membership_checked,'over_1s_time_differences':sum(abs(x)>1 for x in delta_rows),'sha256':published[0]['sha256']}))

if __name__=='__main__': main()
