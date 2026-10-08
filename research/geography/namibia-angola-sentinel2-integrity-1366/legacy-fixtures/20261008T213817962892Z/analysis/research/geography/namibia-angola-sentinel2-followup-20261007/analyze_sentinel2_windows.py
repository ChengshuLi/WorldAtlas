#!/usr/bin/env python3
"""Reproduce candidate/contact optical-water screens from retained S2 source windows."""
from __future__ import annotations
import argparse,hashlib,json,pathlib
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parent
PACKET=ROOT.parent/'gap-source-namibia-angola-20261006'
COMPONENTS=json.loads((PACKET/'inputs'/'original-components.geojson').read_text())['features']
CONTACTS=json.loads((PACKET/'inputs'/'source-contact-features.geojson').read_text())['features']
IDS=[f['id'] for f in COMPONENTS]
CONTACT_IDS=[f"gb:{f['properties']['shapeGroup']}:{f['properties']['shapeType']}:{f['properties']['shapeID']}" for f in CONTACTS]
SCL_CLASSES={'0':'no_data','1':'saturated_or_defective','2':'dark_area','3':'cloud_shadow','4':'vegetation','5':'bare_soil','6':'water','7':'low_probability_cloud_or_unclassified','8':'medium_probability_cloud','9':'high_probability_cloud','10':'cirrus','11':'snow_or_ice'}
CLOUD_INVALID=np.array([0,1,3,7,8,9,10,11],dtype=np.uint8)
THRESHOLDS=(-0.1,0.0,0.1)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def metrics(mask,arrays):
    n=int(mask.sum())
    if not n:
        return {'mask_center_pixels':0,'usable_index_pixels':0,'clear_fraction':None,'scl_histogram':{k:0 for k in SCL_CLASSES.values()},'mndwi_counts':{str(t):0 for t in THRESHOLDS},'ndwi_counts':{str(t):0 for t in THRESHOLDS},'scl_water_centers':0,'mndwi_scl6_concordant':0,'mndwi_median':None,'ndwi_median':None}
    g=arrays['green_dn_10m_2x2'][mask].astype(np.float64)
    nr=arrays['nir_dn_10m_2x2'][mask].astype(np.float64)
    sw=arrays['swir16_dn_20m'][mask].astype(np.float64)
    scl=arrays['scl_20m'][mask].astype(np.uint8)
    band_valid=np.all(g>0,axis=1)&np.all(nr>0,axis=1)&(sw>0)
    scl_clear=~np.isin(scl,CLOUD_INVALID)
    index_valid=band_valid&scl_clear&~(scl==2)
    g_ref=g.mean(axis=1)*0.0001
    n_ref=nr.mean(axis=1)*0.0001
    s_ref=sw*0.0001
    mden=g_ref+s_ref; nden=g_ref+n_ref
    mv=index_valid&(mden>0); nv=index_valid&(nden>0)
    mndwi=np.zeros(n,dtype=np.float64); ndwi=np.zeros(n,dtype=np.float64)
    mndwi[mv]=(g_ref[mv]-s_ref[mv])/mden[mv]
    ndwi[nv]=(g_ref[nv]-n_ref[nv])/nden[nv]
    hist={SCL_CLASSES[str(k)]:int(np.count_nonzero(scl==k)) for k in range(12)}
    return {'mask_center_pixels':n,'green_10m_subpixel_nodata_centers':int(np.count_nonzero(np.any(g==0,axis=1))),
      'nir_10m_subpixel_nodata_centers':int(np.count_nonzero(np.any(nr==0,axis=1))),
      'swir16_20m_nodata_centers':int(np.count_nonzero(sw==0)),'scl_20m_nodata_centers':int(np.count_nonzero(scl==0)),
      'all_band_valid_centers':int(np.count_nonzero(band_valid)),'usable_index_pixels':int(np.count_nonzero(mv&nv)),
      'cloud_shadow_or_unclassified_centers':int(np.count_nonzero(np.isin(scl,[3,7,8,9,10]))),
      'saturated_or_defective_centers':int(np.count_nonzero(scl==1)),'dark_area_centers':int(np.count_nonzero(scl==2)),
      'snow_or_ice_centers':int(np.count_nonzero(scl==11)),'clear_fraction':round(float(np.count_nonzero(mv&nv)/n),8),
      'scl_histogram':hist,'scl_water_centers':int(np.count_nonzero(scl==6)),
      'mndwi_counts':{str(t):int(np.count_nonzero(mv&(mndwi>=t))) for t in THRESHOLDS},
      'ndwi_counts':{str(t):int(np.count_nonzero(nv&(ndwi>=t))) for t in THRESHOLDS},
      'mndwi_scl6_concordant':int(np.count_nonzero(mv&(scl==6)&(mndwi>0))),
      'mndwi_median':round(float(np.median(mndwi[mv])),8) if np.any(mv) else None,
      'ndwi_median':round(float(np.median(ndwi[nv])),8) if np.any(nv) else None}

def build_rows():
    selected=json.loads((ROOT/'inputs'/'selected-sentinel2-items.json').read_text())
    receipts=json.loads((ROOT/'inputs'/'source-window-receipts.json').read_text())
    rows=[]
    for record in receipts['records']:
        item=next(x for x in selected['selected_items'] if x['id']==record['item_id'])
        path=ROOT/record['npz_path']; actual=sha(path)
        if actual!=record['npz_sha256']: raise RuntimeError(f'window hash mismatch {path}')
        with np.load(path,allow_pickle=False) as loaded: arrays={k:loaded[k] for k in loaded.files}
        count=len(arrays['row'])
        if any(len(arrays[k])!=count for k in ('col','green_dn_10m_2x2','nir_dn_10m_2x2','swir16_dn_20m','scl_20m','component_bits','contact_bits')): raise RuntimeError('source window arrays differ in length')
        if np.any(arrays['component_bits']==0): raise RuntimeError('window array includes pixel outside all original components')
        props=item['properties']
        for band in ('green','nir','swir16'):
            meta=item['assets'][band].get('raster:bands',[{}])[0]
            if float(meta.get('scale',0))!=0.0001 or float(meta.get('offset',0))!=0.0: raise RuntimeError(f'unexpected radiometry metadata {item["id"]}/{band}: {meta}')
        if float(props['s2:processing_baseline'])>=4 or props.get('earthsearch:boa_offset_applied') is not False: raise RuntimeError('offset ambiguity entered chosen scene set')
        for i,subject in enumerate(IDS):
            bit=1<<i; mask=(arrays['component_bits']&bit)!=0
            result=metrics(mask,arrays)
            rows.append({'mask_kind':'component','subject_id':subject,'item_id':item['id'],'window':record['window'],'datetime_utc':props['datetime'],'mgrs_tile':props['grid:code'],'processing_baseline':props['s2:processing_baseline'],'scene_cloud_percent':props.get('eo:cloud_cover'),'scene_nodata_percent':props.get('s2:nodata_pixel_percentage'),'scale_offset':{'green':[0.0001,0.0],'nir':[0.0001,0.0],'swir16':[0.0001,0.0]},'grid_resolution_m':20,'source_window_sha256':actual,'source_window_bytes':record['npz_bytes'],**result})
        for i,subject in enumerate(CONTACT_IDS):
            bit=1<<i; mask=(arrays['contact_bits']&bit)!=0
            result=metrics(mask,arrays)
            rows.append({'mask_kind':'candidate-contact-overlap_union','subject_id':subject,'item_id':item['id'],'window':record['window'],'datetime_utc':props['datetime'],'mgrs_tile':props['grid:code'],'processing_baseline':props['s2:processing_baseline'],'scene_cloud_percent':props.get('eo:cloud_cover'),'scene_nodata_percent':props.get('s2:nodata_pixel_percentage'),'scope_limit':'Candidate-union intersection with this whole source contact only; not the full administrative polygon.','scale_offset':{'green':[0.0001,0.0],'nir':[0.0001,0.0],'swir16':[0.0001,0.0]},'grid_resolution_m':20,'source_window_sha256':actual,'source_window_bytes':record['npz_bytes'],**result})
    return rows

def candidate_summaries(rows,kind,ids):
    summaries=[]
    for subject in ids:
        selected=[r for r in rows if r['mask_kind']==kind and r['subject_id']==subject]
        bywindow={}
        for window in ('2019-wet','2019-dry','2020-wet','2020-dry'):
            rs=[r for r in selected if r['window']==window]
            bywindow[window]={'tile_observation_rows':len(rs),'center_pixels_across_tiles_nonadditive':sum(r['mask_center_pixels'] for r in rs),
              'clear_index_pixels_across_tiles_nonadditive':sum(r['usable_index_pixels'] for r in rs),
              'scl_water_centers_across_tiles_nonadditive':sum(r['scl_water_centers'] for r in rs),
              'concordant_scl6_and_positive_mndwi_centers_across_tiles_nonadditive':sum(r['mndwi_scl6_concordant'] for r in rs),
              'mndwi_nonnegative_centers_across_tiles_nonadditive':sum(r['mndwi_counts']['0.0'] for r in rs),
              'mndwi_threshold_sensitivity_nonadditive':{str(t):sum(r['mndwi_counts'][str(t)] for r in rs) for t in THRESHOLDS}}
        scl_total=sum(r['scl_water_centers'] for r in selected)
        mndwi_total=sum(r['mndwi_counts']['0.0'] for r in selected)
        concordant_total=sum(r['mndwi_scl6_concordant'] for r in selected)
        clear_total=sum(r['usable_index_pixels'] for r in selected)
        masks_total=sum(r['mask_center_pixels'] for r in selected)
        if masks_total==0: disposition='no-20m-pixel-center-samples; physical status unresolved at this resolution'
        elif scl_total and mndwi_total and concordant_total: disposition='Concordant SCL water-class and positive-MNDWI pixels occur; see per-window counts and valid fractions; observational water-like signal only'
        elif scl_total and mndwi_total: disposition='SCL water-class and nonnegative-MNDWI signals occur, but no positive-MNDWI SCL6 pixel is concordant; mixed optical evidence'
        elif scl_total: disposition='SCL water-class signal occurs but MNDWI is not concordant across all sampled windows; mixed optical evidence'
        elif mndwi_total: disposition='MNDWI water-like signal occurs without SCL water-class centers; ambiguous spectral response'
        else: disposition='No SCL water-class or nonnegative MNDWI sample detected in these dates; this does not prove dry land or non-water status'
        summaries.append({'subject_id':subject,'total_mask_centers_across_tiles_and_dates_nonadditive':masks_total,'clear_index_centers_across_tiles_and_dates_nonadditive':clear_total,'scl_water_centers_across_tiles_and_dates_nonadditive':scl_total,'mndwi_nonnegative_centers_across_tiles_and_dates_nonadditive':mndwi_total,'concordant_scl6_and_positive_mndwi_centers_across_tiles_and_dates_nonadditive':concordant_total,'disposition':disposition,'seasonal_windows':bywindow})
    return summaries

def controls(rows):
    item=next(r for r in rows if r['mask_kind']=='component' and r['mask_center_pixels']>0)
    pos=next((r for r in rows if r['mask_kind']=='component' and r['scl_water_centers']>0),None)
    receipts=json.loads((ROOT/'inputs'/'source-window-receipts.json').read_text())['records']
    with np.load(ROOT/next(x['npz_path'] for x in receipts if x['item_id']==item['item_id']),allow_pickle=False) as d:
        scl=d['scl_20m']; g=d['green_dn_10m_2x2']; n=d['nir_dn_10m_2x2']; sw=d['swir16_dn_20m']; cb=d['component_bits']; co=d['contact_bits']
        results={'control_source_item':item['item_id'],'all_samples_in_original_component_union':bool(np.all(cb!=0)),
          'one_pixel_center_has_expected_2x2_10m_and_20m_spectral_shapes':bool(g.ndim==2 and g.shape[1]==4 and n.shape==g.shape and len(sw)==len(scl)),
          'component_and_contact_masks_are_subset_of_source_window':bool(np.all((co!=0)| (cb!=0))),
          'scl_class_histogram_across_retained_windows':{str(c):int(sum(np.count_nonzero(np.load(ROOT/x['npz_path'],allow_pickle=False)['scl_20m']==c) for x in receipts)) for c in range(12)},
          'nonvacuous_positive_scl_water_control':None if pos is None else {'item_id':pos['item_id'],'subject_id':pos['subject_id'],'scl_water_centers':pos['scl_water_centers']},
          'nonvacuous_nodata_and_cloud_controls':None,
          'zero_water_signal_contact_screen_present':any(r['mask_kind']=='candidate-contact-overlap_union' and r['mask_center_pixels']>0 and r['scl_water_centers']==0 and r['mndwi_counts']['0.0']==0 for r in rows),
          'mndwi_thresholds_monotonic':all(all(r['mndwi_counts'][str(a)]>=r['mndwi_counts'][str(b)] for a,b in zip(THRESHOLDS,THRESHOLDS[1:])) for r in rows)}
        results['nonvacuous_nodata_and_cloud_controls']={'nodata_centers':results['scl_class_histogram_across_retained_windows']['0'],'cloud_shadow_cirrus_centers':sum(results['scl_class_histogram_across_retained_windows'][str(c)] for c in (3,7,8,9,10))}
        def fixture(green,swir,scl_value):
            arrays={'green_dn_10m_2x2':np.array([[green]*4],dtype=np.uint16),'nir_dn_10m_2x2':np.array([[1000]*4],dtype=np.uint16),'swir16_dn_20m':np.array([swir],dtype=np.uint16),'scl_20m':np.array([scl_value],dtype=np.uint8)}
            return metrics(np.array([True]),arrays)
        positive=fixture(8000,1000,6); negative=fixture(1000,8000,5); nodata=fixture(0,0,0); cloud=fixture(8000,1000,8)
        results['synthetic_controls']={
          'positive_water_expected_scl6_and_positive_mndwi':bool(positive['scl_water_centers']==1 and positive['mndwi_counts']['0.0']==1 and positive['mndwi_scl6_concordant']==1),
          'negative_expected_no_scl6_or_nonnegative_mndwi':bool(negative['scl_water_centers']==0 and negative['mndwi_counts']['0.0']==0 and negative['usable_index_pixels']==1),
          'nodata_expected_excluded_from_valid_indices':bool(nodata['scl_20m_nodata_centers']==1 and nodata['usable_index_pixels']==0),
          'cloud_expected_excluded_from_valid_indices':bool(cloud['cloud_shadow_or_unclassified_centers']==1 and cloud['usable_index_pixels']==0),
          'positive_observed':{'scl_water_centers':positive['scl_water_centers'],'mndwi_nonnegative_centers':positive['mndwi_counts']['0.0'],'concordant':positive['mndwi_scl6_concordant']},
          'negative_observed':{'scl_water_centers':negative['scl_water_centers'],'mndwi_nonnegative_centers':negative['mndwi_counts']['0.0'],'usable_index_pixels':negative['usable_index_pixels']},
          'nodata_observed':{'scl_nodata_centers':nodata['scl_20m_nodata_centers'],'usable_index_pixels':nodata['usable_index_pixels']},
          'cloud_observed':{'cloud_centers':cloud['cloud_shadow_or_unclassified_centers'],'usable_index_pixels':cloud['usable_index_pixels']}}
    if not results['all_samples_in_original_component_union'] or not results['one_pixel_center_has_expected_2x2_10m_and_20m_spectral_shapes'] or not results['component_and_contact_masks_are_subset_of_source_window'] or not results['mndwi_thresholds_monotonic'] or not results['zero_water_signal_contact_screen_present'] or not all(results['nonvacuous_nodata_and_cloud_controls'].values()) or not all(results['synthetic_controls'][key] for key in ('positive_water_expected_scl6_and_positive_mndwi','negative_expected_no_scl6_or_nonnegative_mndwi','nodata_expected_excluded_from_valid_indices','cloud_expected_excluded_from_valid_indices')):
        raise RuntimeError('source-window controls failed')
    return results

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='sentinel2-water-analysis.json'); args=parser.parse_args()
    rows=build_rows()
    if len(rows)!=(len(IDS)+len(CONTACT_IDS))*len(json.loads((ROOT/'inputs'/'selected-sentinel2-items.json').read_text())['selected_items']):
        raise RuntimeError('full subject × scene matrix is incomplete')
    source_hashes={}
    for label,path in [('original_components',PACKET/'inputs'/'original-components.geojson'),('source_contacts',PACKET/'inputs'/'source-contact-features.geojson')]: source_hashes[label]=sha(path)
    prior=json.loads((PACKET/'evidence-quality.json').read_text())['baseline']['files']
    for name,path in [('original_components','research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson'),('source_contacts','research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson')]:
        pin=next(x for x in prior if x['path']==path)
        if pin['sha256']!=source_hashes[name]: raise RuntimeError(f'original input does not match merged pin: {name}')
    output={'version':1,'source_window_receipt_sha256':sha(ROOT/'inputs'/'source-window-receipts.json'),'selected_stac_items_sha256':sha(ROOT/'inputs'/'selected-sentinel2-items.json'),
      'original_geometry_source_sha256':source_hashes,'original_feature_counts':{'components':len(IDS),'source_contacts':len(CONTACT_IDS)},
      'summary_counts':{'selected_scene_items':len(json.loads((ROOT/'inputs'/'selected-sentinel2-items.json').read_text())['selected_items']),'scene_observation_rows':len(rows),'candidate_summaries':len(candidate_summaries(rows,'component',IDS)),'contact_overlap_summaries':len(candidate_summaries(rows,'candidate-contact-overlap_union',CONTACT_IDS))},
      'measurement_method':{'band_gsd':'B03/B08 10 m raw 2×2 blocks averaged onto native B11/SCL 20 m pixel centers','radiometry':'STAC scale 0.0001 and offset 0 for B03/B08/B11; all selected products have processing baseline <04.00 and Earth Search offset flag false; indices are computed in reflectance after the common linear scale','scl':'Scene classification retained by category; no-data, saturated/defective, shadow, clouds, cirrus, snow/ice, and dark area are separated and excluded from the clear-index class sample as specified in code','indices':'MNDWI=(Green−SWIR1)/(Green+SWIR1), NDWI=(Green−NIR)/(Green+NIR); threshold sensitivity at −0.1, 0.0, +0.1; spectral threshold is a screen, not ground truth','masking':'Original component geometries and candidate-union/contact-intersection geometries; EPSG:32733/32734 per MGRS tile; 20 m center-in-polygon sampling (all_touched=false); no repair/snap/buffer/clip of original polygons','seasonal_windows':'Jan–Mar and Aug–Oct acquisition windows in 2019 and 2020; exact per-tile dates retained. Dates are seasonal comparison bins, not contemporaneous mosaics or proof of local rainfall/hydrologic state.'},
      'scene_observations':rows,'candidate_summaries':candidate_summaries(rows,'component',IDS),'contact_overlap_summaries':candidate_summaries(rows,'candidate-contact-overlap_union',CONTACT_IDS),
      'controls':controls(rows),'limitations':['These are 20 m source-pixel-center observations from selected Level-2A dates, not exact channel banks, shoreline delineations, survey observations, or a continuous water record.','No independent ground-control registration check or candidate-edge absolute positional uncertainty estimate was available; nominal GSD and native UTM georeferencing are recorded, but narrow-edge comparisons remain unresolved.','Cloud/shadow/no-data are quantified per original mask; tile-level cloud and no-data metadata are screening context only.','A date without water-like signal does not demonstrate permanent dry land; mixed pixels, inundation timing, classification error, and geometric offsets remain possible.','Sentinel-2 optical spectral classes are independent of Landsat-derived JRC summaries but still are not legal boundary or territorial-assignment evidence.','Contact results cover only candidate-union∩contact masks, not full administrative polygons; counts across scenes/tiles/contacts are nonadditive.','No conclusion is made about processing cause, historic boundary location, national source authority, or assignment.']}
    target=ROOT/args.output; target.parent.mkdir(parents=True,exist_ok=True); raw=(json.dumps(output,sort_keys=True,indent=2)+'\n').encode();target.write_bytes(raw)
    print(json.dumps({'output':str(target),'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'components':len(output['candidate_summaries']),'contact_masks':len(output['contact_overlap_summaries']),'controls':output['controls']},indent=2))
if __name__=='__main__': main()
