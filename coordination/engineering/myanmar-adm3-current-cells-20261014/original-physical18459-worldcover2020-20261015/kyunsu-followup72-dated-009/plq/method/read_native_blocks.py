"""Batch the established native Sentinel window observation over one complete coherent single-scene group.

No physical classifier or authority predicate. Disk outputs are streamed; native
source blocks and one date's point observations are the resident image carry.
"""
import collections, contextlib, datetime, gc, hashlib, json, math, pathlib
import resource, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
BASE = pathlib.Path('/Users/chengshuli/Documents/Codex/2026-10-13/task/vietnam-next/original-decisions-20261015')
OUT = ROOT / 'actual-native-blocks-001'
assert not OUT.exists(), 'Fresh owned output required'
OUT.mkdir()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
phase_bytes = 768 * 1024**2
disk_cap = 2048 * 1024**2
node = 'configured-existing-runtime:codex-primary-runtime/dependencies/node/bin/node'
helper = BASE / 'worldcover800/accepted-9f40-code/scripts/check-effective-geographic-regression.mjs'
js = ('import {processingAllowance} from '+json.dumps(str(helper))+
      ';const available=process.availableMemory();console.log(JSON.stringify({available,'
      'headroomBytes:572882944,currentRssCreditBytes:0,concurrentReservedBytes:0,'
      'allowance:processingAllowance({availableBytes:available,currentRssBytes:0,'
      'headroomBytes:572882944,concurrentReservedBytes:0,phaseBytes:'+str(phase_bytes)+
      ',rssBytes:'+str(phase_bytes)+'})}));')
admission = json.loads(subprocess.check_output([node, '--input-type=module', '-e', js], text=True, timeout=20))
plan_path = ROOT / 'native-block-plan.json'
input_path = ROOT / 'chosen-centres.json'
plan_data = plan_path.read_bytes()
plan = json.loads(plan_data)
assert plan['original_package'] == 'gb-MMR-ADM3--physical-interpretation' and plan['selected_count'] == 2 and plan['count'] == 2 and plan['block_count'] == 2
assert len({tuple(p['original_key'][k] for k in ['owner','y','x']) for p in plan['points']}) == 2
assert hashlib.sha256(input_path.read_bytes()).hexdigest() == plan['source_input_sha256']
scene_paths = [ROOT/'scene-item.json']
items = [json.loads(p.read_text()) for p in scene_paths]
assert [i['id'] for i in items] == ['S2A_47PLQ_20200105_0_L2A']
assert all(i['properties']['earthsearch:boa_offset_applied'] is False for i in items)
cost = {'existing_reader_numpy_files':90300286, 'python':18058560,
        'node_preflight':121304480, 'accepted_admission_code':304941,
        'frozen_input_bytes':input_path.stat().st_size+len(plan_data)+sum(p.stat().st_size for p in scene_paths)+pathlib.Path(__file__).stat().st_size,
        'parsed_input_carry':64*1024**2, 'per_date_point_observations':96*1024**2,
        'source_block_decode':80*1024**2, 'native_arrays_and_masks':24*1024**2,
        'gdal_cache':16*1024**2, 'rendering_live_carry':96*1024**2,
        'output_write_hash_buffers':16*1024**2, 'metadata_manifest':16*1024**2,
        'other_runtime':24*1024**2, 'other_expansion':64*1024**2}
assert sum(cost.values()) <= admission['allowance']['phaseBytes']
sys.path.insert(0, '/tmp/worldatlas-worldcover-reader-20261014')
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import Affine
from PIL import Image, ImageDraw

disk_bytes = 0
inventory = []

def guard():
    assert time.monotonic()-start < 1200, '1200-second operation deadline exceeded'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss <= admission['allowance']['rssBytes'], 'Observed lifetime RSS exceeds allowance'
    assert disk_bytes <= disk_cap, 'Complete owned disk-output cap exceeded'

def register(path):
    global disk_bytes
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda:src.read(1024**2), b''):
            h.update(chunk)
    disk_bytes += size
    r = {'path':str(path.relative_to(OUT)), 'bytes':size, 'sha256':h.hexdigest()}
    inventory.append(r)
    guard()
    return r

def write_json(path, value):
    assert not path.exists()
    data = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()
    assert len(data) <= 32*1024**2, 'Single JSON output cap exceeded'
    path.write_bytes(data)
    return register(path)

write_json(OUT/'admission.json', {'started_utc':started,'admission':admission,
    'maximum_declared_live_carry':cost,'prospective_total':sum(cost.values()),
    'separate_streamed_disk_output_cap':disk_cap,
    'limits':'No whole-tile decode or claim that all disk outputs reside in RAM; source windows are hashed as written. No aggregate network-byte/process-tree enforcement claim.'})
dates = []
with rasterio.Env(GDAL_CACHEMAX=16*1024**2, GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                  GDAL_HTTP_TIMEOUT='20', GDAL_HTTP_MAX_RETRY='0', VSI_CACHE='FALSE'):
    for date_index, item in enumerate(items, 1):
        date_dir = OUT / item['id']
        date_dir.mkdir()
        point_records = [{'index':p['index'],'original_key':p['original_key'],
                          'longitude':p['longitude'],'latitude':p['latitude'],
                          'physical_block':p['physical_block'],'request_record_index':p['request_record_index'],'source_sids':p['source_sids'],'planning_group':p['planning_group'],'assets':{}} for p in plan['points']]
        block_records = []
        with contextlib.ExitStack() as stack:
            datasets = {}
            source_metadata = {}
            for key in ['red','green','blue','nir','scl']:
                ds = stack.enter_context(rasterio.open(item['assets'][key]['href']))
                expected = 20 if key == 'scl' else 10
                expected_affine = Affine(*(plan['source_20m_transform'] if key=='scl' else plan['source_10m_transform'])[:6])
                assert ds.crs.to_epsg()==32647 and ds.count==1 and ds.res==(expected,expected) and ds.nodata==0
                assert ds.transform==expected_affine
                assert ds.shape==((5490,5490) if key=='scl' else (10980,10980))
                assert ds.block_shapes==([(512,512)] if key=='scl' else [(1024,1024)])
                datasets[key]=ds
                source_metadata[key]={'url':item['assets'][key]['href'],'shape':list(ds.shape),
                    'transform':list(ds.transform),'blocks':ds.block_shapes,'dtype':str(ds.dtypes[0]),
                    'crs':str(ds.crs),'nodata':ds.nodata,'raster_bands':item['assets'][key].get('raster:bands')}
            for block_number, block in enumerate(plan['blocks'],1):
                guard()
                br,bc = block['block']
                folder = date_dir / ('block-%02d-%02d'%(br,bc))
                folder.mkdir()
                arrays = {}
                block_assets = {}
                for key,ds in datasets.items():
                    raw = block['native_20m_window'] if key=='scl' else block['native_10m_window']
                    left,top=max(0,raw[0]-1),max(0,raw[1]-1)
                    right,bottom=min(ds.width,raw[0]+raw[2]+1),min(ds.height,raw[1]+raw[3]+1)
                    w=Window(left,top,right-left,bottom-top)
                    data=ds.read(1,window=w)
                    mask=ds.read_masks(1,window=w)
                    assert data.shape==mask.shape==(bottom-top,right-left)
                    affine=ds.window_transform(w)
                    target=folder/(key+'.tif')
                    with rasterio.open(target,'w',driver='GTiff',height=data.shape[0],width=data.shape[1],count=1,
                        dtype=data.dtype,crs=ds.crs,transform=affine,nodata=0,compress='deflate') as dst:
                        dst.write(data,1)
                        dst.update_tags(source_item=item['id'],source_asset=item['assets'][key]['href'],
                            acquired=item['properties']['datetime'],operation='Integer native source-block window with one-pixel halo; no resampling')
                    file_record=register(target)
                    mask_target=folder/(key+'-source-mask.tif')
                    with rasterio.open(mask_target,'w',driver='GTiff',height=mask.shape[0],width=mask.shape[1],
                        count=1,dtype='uint8',crs=ds.crs,transform=affine,compress='deflate') as dst:
                        dst.write(mask,1)
                        dst.update_tags(source_item=item['id'],source_asset=item['assets'][key]['href'],
                            acquired=item['properties']['datetime'],operation='Literal original uint8 source validity mask, not a physical class')
                    mask_record=register(mask_target)
                    for index in block['indices']:
                        p=plan['points'][index]
                        sr,sc=p['source_20m_pixel'] if key=='scl' else p['source_10m_pixel']
                        rr,cc=sr-top,sc-left
                        assert 1<=rr<data.shape[0]-1 and 1<=cc<data.shape[1]-1
                        point_records[index]['assets'][key]={'value':int(data[rr,cc]),'valid_mask':int(mask[rr,cc]),
                            'source_pixel':[sr,sc],'local_pixel':[rr,cc],
                            'neighbourhood':data[rr-1:rr+2,cc-1:cc+2].tolist(),
                            'neighbour_masks':mask[rr-1:rr+2,cc-1:cc+2].tolist()}
                    block_assets[key]={'window':[left,top,right-left,bottom-top],'transform':list(affine),
                        'valid_pixel_count':int(np.count_nonzero(mask)),'total_pixels':int(mask.size),
                        'output':file_record,'source_mask_output':mask_record}
                    if key!='scl':arrays[key]=data
                    guard()
                displays=[]
                for name,channels in [('rgb',['red','green','blue']),('nir-red-green',['nir','red','green'])]:
                    a=np.stack([arrays[k] for k in channels],axis=-1)
                    display=np.clip(a.astype(np.float32)/3000*255,0,255).astype('uint8')
                    im=Image.fromarray(display)
                    target=folder/(name+'-native.png');im.save(target);displays.append(register(target))
                    draw=ImageDraw.Draw(im)
                    left,top=block_assets['red']['window'][:2]
                    for index in block['indices']:
                        row,col=plan['points'][index]['source_10m_subpixel'];x,y=col-left,row-top
                        draw.line((x-3,y,x+3,y),fill=(255,255,0),width=1)
                        draw.line((x,y-3,x,y+3),fill=(255,255,0),width=1)
                        draw.text((x+3,y-8),str(index),fill=(255,255,0))
                    target=folder/(name+'-centres.png');im.save(target);displays.append(register(target))
                    del a,display,im,draw
                    guard()
                block_records.append({'block':block['block'],'indices':block['indices'],'point_count':block['count'],
                    'assets':block_assets,'displays':displays})
                del arrays,data,mask
                gc.collect()
                print(json.dumps({'item':item['id'],'blocks_completed':block_number,'total_blocks':len(plan['blocks'])}),flush=True)
        assert all(set(p['assets'])=={'red','green','blue','nir','scl'} for p in point_records)
        summary={'count':len(point_records),'scl_centre_counts':dict(collections.Counter(p['assets']['scl']['value'] for p in point_records)),
            'valid_centre_masks_by_band':{k:dict(collections.Counter(p['assets'][k]['valid_mask'] for p in point_records)) for k in datasets},
            'interpretation':'Literal source observations only, not physical completion or hold clearance.'}
        result={'item':item['id'],'acquisition_datetime':item['properties']['datetime'],'properties':item['properties'],
            'original_package':plan['original_package'],'selected_count':plan['selected_count'],'source_input_sha256':plan['source_input_sha256'],'source_metadata':source_metadata,
            'points':point_records,'blocks':block_records,'summary':summary,
            'display':'Native fixed DN0..3000 scaling; centre overlays are display only. Raw TIFFs unchanged.',
            'limits':['Partial native windows, no whole remote COG hash.','Local model masks are not independent physical truth.',
                      'No fitted shift, shoreline extraction, physical classifier, authority, repair or completed-review credit.']}
        record=write_json(date_dir/'native-observations.json',result)
        dates.append({'item':item['id'],'result':record,'summary':summary})
        del result,point_records,block_records
        gc.collect()
        guard()
write_json(OUT/'complete-output-inventory.json',{'files':list(inventory),'dates':dates,
    'scope':'Complete output inventory excluding this inventory and final execution receipt, neither of which existed when listed.'})
receipt={'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'seconds':time.monotonic()-start,'observed_process_lifetime_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'admission':admission,'prospective_live_carry':cost,'prospective_total':sum(cost.values()),
    'streamed_disk_bytes_before_final_receipt':disk_bytes,'disk_cap':disk_cap,
    'runtime':{'python':sys.version,'rasterio':rasterio.__version__,'gdal':rasterio.__gdal_version__,'numpy':np.__version__},
    'dates':dates,'method':'Existing native-GDAL window observation, source blocks streamed for one complete coherent original-key group; no new classifier.'}
guard()
write_json(OUT/'execution-receipt.json',receipt)
print(json.dumps({'status':'completed','original_centres':2,'dates':1,'source_context_blocks':2,
    'seconds':time.monotonic()-start,'observed_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'disk_output_bytes':disk_bytes,'resolved_review_credit':0}),flush=True)
