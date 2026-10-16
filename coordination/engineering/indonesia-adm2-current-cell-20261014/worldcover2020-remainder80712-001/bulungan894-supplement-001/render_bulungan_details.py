"""Display-only exact Bulungan native centre crops; source arrays unchanged."""
from pathlib import Path
import json,collections,hashlib
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parent.parent/'worker1-source';OUT=Path(__file__).resolve().parent/'native-detail-review';OUT.mkdir(exist_ok=True)
report=json.loads((ROOT/'rgbnir-source-observations.json').read_bytes());rows=[]
transforms={s['tile']:rasterio.Affine(*s['transform'][:6])for s in report['sources']}
for t in report['tile_products']:
 for line in Path(t['observations']['path']).open():
  p=json.loads(line)
  if p['original_key']['owner']==22698:rows.append(p)
rows.sort(key=lambda p:(p['tile'],p['rgbnir_composite_observation']['centre_array'],p['point_index']))
decisions=json.loads((Path(__file__).resolve().parent/'manual-panel-decisions-first-pass.json').read_text());wide=json.loads((Path(__file__).resolve().parent/'native-centre-review-v2/contact-inventory.json').read_text());selected_ids={r['point_index']for page in wide['pages']for r in page['panels']if r['panel_1based']in decisions[str(page['page_1based'])].get('A',[])}|{2415,5198};wide_by_id={r['point_index']:{'page_1based':page['page_1based'],'panel_1based':r['panel_1based']}for page in wide['pages']for r in page['panels']};rows=[p for p in rows if p['point_index']in selected_ids];assert len(rows)==280
pages=[];current_array=None;v=m=q=None
for start in range(0,len(rows),12):
 subset=rows[start:start+12];canvas=np.full((1056,1536,3),255,np.uint8);index=[]
 for n,p in enumerate(subset):
  a=p['rgbnir_composite_observation'];path=a['centre_array']
  if path!=current_array:
   with np.load(path,allow_pickle=False)as z:v=z['values'];m=z['masks']
   q=json.loads(Path(path).with_suffix('.json').read_bytes());current_array=path
  w=q['window'];r=a['native_row']-w['row_off'];c=a['native_col']-w['col_off'];r0=max(0,r-8);r1=min(v.shape[1],r+9);c0=max(0,c-8);c1=min(v.shape[2],c+9)
  for j,bands in enumerate([[0,1,2],[3,0,1]]):
   patch=np.moveaxis(np.clip(v[bands,r0:r1,c0:c1].astype(float)/(3000 if j==0 else 5000)*255,0,255).astype(np.uint8),0,-1);patch[np.any(m[:,r0:r1,c0:c1]==0,axis=0)]=[255,0,255]
   rr=np.arange(256)*patch.shape[0]//256;cc=np.arange(256)*patch.shape[1]//256;im=patch[rr[:,None],cc[None,:]];lon=p['centre_unchanged']['longitude'];lat=p['centre_unchanged']['latitude'];cf,rf=~transforms[Path(path).parent.name]*(lon,lat);yy=int((rf-w['row_off']-r0)/patch.shape[0]*256);xx=int((cf-w['col_off']-c0)/patch.shape[1]*256)
   for dy,dx in [(-5,0),(-4,0),(4,0),(5,0),(0,-5),(0,-4),(0,4),(0,5)]:
    if 0<=yy+dy<256 and 0<=xx+dx<256:im[yy+dy,xx+dx]=[255,255,0]
   y=(n//3)*264;x=(n%3)*512+j*256;canvas[y:y+256,x:x+256]=im
  index.append({'panel_1based':n+1,'wide_locator':wide_by_id[p['point_index']],'point_index':p['point_index'],'original_key':p['original_key'],'retained_context_scope':p['retained_context_scope'],'worldcover_class':p['source_observation']['class_code'],'rgbnir_values':a['band_values'],'rgbnir_masks':a['band_masks'],'array':path,'crop_native_window':{'row_off':r0+w['row_off'],'col_off':c0+w['col_off'],'height':r1-r0,'width':c1-c0},'actual_composite_tile':Path(path).parent.name,'fractional_centre_in_crop':{'row':rf-w['row_off']-r0,'col':cf-w['col_off']-c0}})
 name=f'bulungan-detail-{start//12+1:02d}.png'
 with rasterio.open(OUT/name,'w',driver='PNG',width=canvas.shape[1],height=canvas.shape[0],count=3,dtype='uint8')as ds:ds.write(np.moveaxis(canvas,-1,0))
 b=(OUT/name).read_bytes();pages.append({'page_1based':start//12+1,'path':str(OUT/name),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'panels':index})
(OUT/'contact-inventory.json').write_text(json.dumps({'keys':len(rows),'page_layout':'3columns4rows,row-major;eachpanelleftRGB/rightNIR-R-G;12panels perpage','display_stretch_rgb':[0,3000],'display_stretch_falsecolour':[0,5000],'resampling':'nearest display only, native scientific arrays unchanged','centre_marker':'yellow hollowcross at actual fractional normative point in source affine; centrepixelunpainted','author':'/root/physical_remainder_source_limits','scope':'894Bulunganonly,localcachednativearrays,noHTTP/producerreplay','pages':pages},indent=2)+'\n')
print('pages',len(pages),'keys',len(rows))
