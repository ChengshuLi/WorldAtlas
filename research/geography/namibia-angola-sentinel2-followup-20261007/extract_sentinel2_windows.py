#!/usr/bin/env python3
"""Capture exact candidate-mask pixel windows from pinned public Sentinel-2 COGs."""
from __future__ import annotations
import hashlib, io, json, pathlib, zipfile
import numpy as np
import rasterio
from rasterio.errors import WindowError
from rasterio.features import geometry_mask, geometry_window
from rasterio.windows import Window
from shapely.geometry import mapping, shape
from shapely.ops import transform as transform_geometry, unary_union
from pyproj import Transformer
from rasterio.enums import Resampling

ROOT=pathlib.Path(__file__).resolve().parent
PACKET=ROOT.parent/'gap-source-namibia-angola-20261006'
OUT=ROOT/'sources'/'windows'
SELECTED=json.loads((ROOT/'inputs'/'selected-sentinel2-items.json').read_text())
ITEMS=SELECTED['selected_items']
COMPONENTS=json.loads((PACKET/'inputs'/'original-components.geojson').read_text())['features']
CONTACTS=json.loads((PACKET/'inputs'/'source-contact-features.geojson').read_text())['features']
COMPONENT_IDS=[f['id'] for f in COMPONENTS]
CONTACT_IDS=[f"gb:{f['properties']['shapeGroup']}:{f['properties']['shapeType']}:{f['properties']['shapeID']}" for f in CONTACTS]
VALID_ASSETS=['green','nir','swir16','scl']

def deterministic_npz(path, arrays):
    """Write stable ZIP/NPY members so byte hashes survive independent runs."""
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            buff=io.BytesIO(); np.lib.format.write_array(buff,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f'{key}.npy',(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o600<<16
            zf.writestr(info,buff.getvalue(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_heads():
    rows=json.loads((ROOT/'inputs'/'cog-object-head-receipts.json').read_text())
    return {(r['item_id'],r['asset']):r for r in rows}

def transform_geometries(crs):
    epsg=crs.to_epsg()
    transformer=Transformer.from_crs('EPSG:4326',f'EPSG:{epsg}',always_xy=True)
    convert=lambda g: transform_geometry(transformer.transform,g)
    components=[convert(shape(f['geometry'])) for f in COMPONENTS]
    contacts=[convert(shape(f['geometry'])) for f in CONTACTS]
    union=unary_union(components)
    return components,contacts,[union.intersection(g) for g in contacts]

def clipped_window(ds,geom):
    try: win=geometry_window(ds,[mapping(geom)],boundless=True)
    except WindowError: return None
    try: win=win.intersection(Window(0,0,ds.width,ds.height)).round_offsets().round_lengths()
    except WindowError: return None
    return win if win.width>0 and win.height>0 else None

def npy_arrays_for_item(item,heads):
    datasets={}; vrts={}; metadata={}
    for band in VALID_ASSETS:
        asset=item['assets'][band]; receipt=heads[(item['id'],band)]
        if receipt['headers'].get('ETag') is None or receipt['headers'].get('Accept-Ranges','').lower()!='bytes':
            raise RuntimeError(f'COG object lacks immutable/range receipt: {item["id"]}/{band}')
        ds=rasterio.open(asset['href']); datasets[band]=ds
        metadata[band]={'url':asset['href'],'etag':receipt['headers']['ETag'],'last_modified':receipt['headers'].get('Last-Modified'),
          'content_length':int(receipt['headers']['Content-Length']),'raster_crs':ds.crs.to_string(),'width':ds.width,'height':ds.height,
          'transform':list(ds.transform)[:6],'resolution':list(ds.res),'nodata':ds.nodata,'dtype':ds.dtypes[0],
          'stac_raster_bands':asset.get('raster:bands'),'stac_gsd':asset.get('gsd')}
    scl=datasets['scl']; b11=datasets['swir16']
    for band in ('scl','swir16'):
        ds=datasets[band]
        if ds.crs!=scl.crs or ds.transform!=scl.transform or ds.width!=scl.width or ds.height!=scl.height:
            raise RuntimeError(f'20 m grid mismatch {item["id"]} {band}')
    for band in ('green','nir'):
        ds=datasets[band]
        if ds.crs!=scl.crs or ds.width!=2*scl.width or ds.height!=2*scl.height:
            raise RuntimeError(f'10-to-20 m grid geometry mismatch {item["id"]} {band}')
        if (ds.transform.c,ds.transform.f)!=(scl.transform.c,scl.transform.f) or ds.transform.a*2!=scl.transform.a or ds.transform.e*2!=scl.transform.e:
            raise RuntimeError(f'10-to-20 m grid origin/resolution mismatch {item["id"]} {band}')
    components,contacts,contact_masks=transform_geometries(scl.crs)
    pixels={}; windows=[]
    for index,geom in enumerate(components):
        if geom.is_empty or not geom.is_valid: raise RuntimeError(f'invalid original geometry: {COMPONENT_IDS[index]}')
        win=clipped_window(scl,geom)
        if win is None: continue
        mask=geometry_mask([mapping(geom)],out_shape=(int(win.height),int(win.width)),transform=scl.window_transform(win),invert=True,all_touched=False)
        if not mask.any(): continue
        b11_values=b11.read(1,window=win,masked=False)
        scl_values=scl.read(1,window=win,masked=False)
        green_values=datasets['green'].read(1,window=Window(win.col_off*2,win.row_off*2,win.width*2,win.height*2),masked=False)
        nir_values=datasets['nir'].read(1,window=Window(win.col_off*2,win.row_off*2,win.width*2,win.height*2),masked=False)
        row_local,col_local=np.where(mask)
        row_abs=row_local+int(win.row_off); col_abs=col_local+int(win.col_off)
        for rr,cc,lr,lc in zip(row_abs,col_abs,row_local,col_local):
            g4=green_values[2*lr:2*lr+2,2*lc:2*lc+2].reshape(4).astype(np.uint16,copy=False)
            n4=nir_values[2*lr:2*lr+2,2*lc:2*lc+2].reshape(4).astype(np.uint16,copy=False)
            key=(int(rr),int(cc))
            values=(g4.copy(),n4.copy(),np.uint16(b11_values[lr,lc]),np.uint8(scl_values[lr,lc]))
            if key in pixels:
                old=pixels[key]
                if not (np.array_equal(old[0],values[0]) and np.array_equal(old[1],values[1]) and old[2:4]==values[2:4]):
                    raise RuntimeError('one source grid cell yielded inconsistent values')
                old[4]|=1<<index
            else:
                pixels[key]=[values[0],values[1],values[2],values[3],1<<index,0]
        windows.append({'mask_kind':'component','mask_id':COMPONENT_IDS[index],'row_off':int(win.row_off),'col_off':int(win.col_off),'height':int(win.height),'width':int(win.width),'center_pixels':int(mask.sum()),'green_window_10m':[int(win.row_off*2),int(win.col_off*2),int(win.height*2),int(win.width*2)],'nir_window_10m':[int(win.row_off*2),int(win.col_off*2),int(win.height*2),int(win.width*2)],'swir16_window_20m':[int(win.row_off),int(win.col_off),int(win.height),int(win.width)],'scl_window_20m':[int(win.row_off),int(win.col_off),int(win.height),int(win.width)]})
    for index,geom in enumerate(contact_masks):
        if geom.is_empty or not geom.is_valid: raise RuntimeError(f'invalid contact intersection: {CONTACT_IDS[index]}')
        win=clipped_window(scl,geom)
        if win is None: continue
        mask=geometry_mask([mapping(geom)],out_shape=(int(win.height),int(win.width)),transform=scl.window_transform(win),invert=True,all_touched=False)
        row_local,col_local=np.where(mask)
        for lr,lc in zip(row_local,col_local):
            key=(int(lr+win.row_off),int(lc+win.col_off))
            if key not in pixels: raise RuntimeError(f'contact mask pixel is outside sampled component union: {CONTACT_IDS[index]} {key}')
            pixels[key][5]|=1<<index
        windows.append({'mask_kind':'contact-overlap-union','mask_id':CONTACT_IDS[index],'row_off':int(win.row_off),'col_off':int(win.col_off),'height':int(win.height),'width':int(win.width),'center_pixels':int(mask.sum()),'green_window_10m':[int(win.row_off*2),int(win.col_off*2),int(win.height*2),int(win.width*2)],'nir_window_10m':[int(win.row_off*2),int(win.col_off*2),int(win.height*2),int(win.width*2)],'swir16_window_20m':[int(win.row_off),int(win.col_off),int(win.height),int(win.width)],'scl_window_20m':[int(win.row_off),int(win.col_off),int(win.height),int(win.width)]})
    keys=sorted(pixels)
    arrays={'row':np.array([k[0] for k in keys],dtype=np.int32),'col':np.array([k[1] for k in keys],dtype=np.int32),
      'green_dn_10m_2x2':np.stack([pixels[k][0] for k in keys]) if keys else np.empty((0,4),dtype=np.uint16),
      'nir_dn_10m_2x2':np.stack([pixels[k][1] for k in keys]) if keys else np.empty((0,4),dtype=np.uint16),
      'swir16_dn_20m':np.array([pixels[k][2] for k in keys],dtype=np.uint16),'scl_20m':np.array([pixels[k][3] for k in keys],dtype=np.uint8),
      'component_bits':np.array([pixels[k][4] for k in keys],dtype=np.uint32),'contact_bits':np.array([pixels[k][5] for k in keys],dtype=np.uint16)}
    result={'item_id':item['id'],'window':next(w for w,ids in SELECTED['windows'].items() if item['id'] in ids['item_ids']),
      'datetime':item['properties']['datetime'],'platform':item['properties']['platform'],'product_uri':item['properties']['s2:product_uri'],
      'processing_baseline':item['properties']['s2:processing_baseline'],'earthsearch_boa_offset_applied':item['properties'].get('earthsearch:boa_offset_applied'),
      'grid_code':item['properties']['grid:code'],'epsg':scl.crs.to_epsg(),'pixel_size_m':20,'mask_rule':'rasterio.features.geometry_mask(all_touched=False), i.e. source 20 m pixel-center sampling',
      'sampled_pixel_count':len(keys),'component_mask_windows':windows,'asset_metadata':metadata,'npz_path':f'sources/windows/{item["id"]}.npz'}
    target=ROOT/'sources'/'windows'/f'{item["id"]}.npz'; result['npz_sha256']=deterministic_npz(target,arrays); result['npz_bytes']=target.stat().st_size
    for ds in datasets.values(): ds.close()
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True); heads=read_heads(); records=[]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_MAX_RETRY='3',GDAL_HTTP_RETRY_DELAY='1',GDAL_HTTP_MERGE_CONSECUTIVE_RANGES='YES',GDAL_CACHEMAX=64,VSI_CACHE='TRUE',VSI_CACHE_SIZE='33554432'):
        for i,item in enumerate(ITEMS,1):
            print(f'[{i}/{len(ITEMS)}] {item["id"]}',flush=True)
            records.append(npy_arrays_for_item(item,heads))
    content={'version':1,'source':'Earth Search public COG mirror of Sentinel-2 L2A; only original source windows selected by exact pixel-center masks are retained.','method':'Per-MGRS native 20 m grid; B03 and B08 raw 10 m DN 2x2 blocks, B11 and SCL 20 m values; unmodified original candidate masks and candidate-union/contact-overlap masks.','component_ids':COMPONENT_IDS,'contact_ids':CONTACT_IDS,'records':records}
    raw=(json.dumps(content,sort_keys=True,indent=2)+'\n').encode(); path=ROOT/'inputs'/'source-window-receipts.json'; path.write_bytes(raw)
    print(json.dumps({'records':len(records),'sampled_pixels':sum(r['sampled_pixel_count'] for r in records),'window_bytes':sum(r['npz_bytes'] for r in records),'receipt_sha256':hashlib.sha256(raw).hexdigest(),'receipt_bytes':len(raw)},indent=2))
if __name__=='__main__': main()
