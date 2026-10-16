"""Display-only exact remaining Aru native centre crops; source arrays unchanged."""
from pathlib import Path
import json,collections,hashlib,gzip
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'aru623-native-review-001';OUT.mkdir(exist_ok=True)
report=json.loads((ROOT/'rgbnir-source-observations.json').read_bytes());rows=[]
selected={p['point_index']for p in map(json.loads,gzip.open(ROOT/'proposed-rgbnir-physical-location-dispositions.jsonl.gz','rt'))if p['original_key']['owner']==22734 and not p['proposed_bounded_answer']}
assert len(selected)==623
transforms={s['tile']:rasterio.Affine(*s['transform'][:6])for s in report['sources']}
for t in report['tile_products']:
 for line in Path(t['observations']['path']).open():
  p=json.loads(line)
  if p['point_index'] in selected:rows.append(p)
rows.sort(key=lambda p:(p['tile'],p['rgbnir_composite_observation']['centre_array'],p['point_index']))
assert len(rows)==623
pages=[];current_array=None;v=m=q=None
for start in range(0,len(rows),48):
 subset=rows[start:start+48];canvas=np.full((1056,1536,3),255,np.uint8);index=[]
 for n,p in enumerate(subset):
  a=p['rgbnir_composite_observation'];path=a['centre_array']
  if path!=current_array:
   with np.load(path,allow_pickle=False)as z:v=z['values'];m=z['masks']
   q=json.loads(Path(path).with_suffix('.json').read_bytes());current_array=path
  w=q['window'];r=a['native_row']-w['row_off'];c=a['native_col']-w['col_off'];r0=max(0,r-24);r1=min(v.shape[1],r+25);c0=max(0,c-24);c1=min(v.shape[2],c+25)
  for j,bands in enumerate([[0,1,2],[3,0,1]]):
   patch=np.moveaxis(np.clip(v[bands,r0:r1,c0:c1].astype(float)/(3000 if j==0 else 5000)*255,0,255).astype(np.uint8),0,-1);patch[np.any(m[:,r0:r1,c0:c1]==0,axis=0)]=[255,0,255]
   rr=np.arange(128)*patch.shape[0]//128;cc=np.arange(128)*patch.shape[1]//128;im=patch[rr[:,None],cc[None,:]];lon=p['centre_unchanged']['longitude'];lat=p['centre_unchanged']['latitude'];cf,rf=~transforms[Path(a['centre_array']).parent.name]*(lon,lat);yy=int((rf-w['row_off']-r0)/patch.shape[0]*128);xx=int((cf-w['col_off']-c0)/patch.shape[1]*128)
   for dy,dx in [(-5,0),(-4,0),(4,0),(5,0),(0,-5),(0,-4),(0,4),(0,5)]:
    if 0<=yy+dy<128 and 0<=xx+dx<128:im[yy+dy,xx+dx]=[255,255,0]
   y=(n//6)*132;x=(n%6)*256+j*128;canvas[y:y+128,x:x+128]=im
  index.append({'panel_1based':n+1,'point_index':p['point_index'],'original_key':p['original_key'],'retained_context_scope':p['retained_context_scope'],'worldcover_class':p['source_observation']['class_code'],'rgbnir_values':a['band_values'],'rgbnir_masks':a['band_masks'],'array':path,'crop_native_window':{'row_off':r0+w['row_off'],'col_off':c0+w['col_off'],'height':r1-r0,'width':c1-c0}})
 name=f'aru-centres-{start//48+1:02d}.png'
 with rasterio.open(OUT/name,'w',driver='PNG',width=canvas.shape[1],height=canvas.shape[0],count=3,dtype='uint8')as ds:ds.write(np.moveaxis(canvas,-1,0))
 b=(OUT/name).read_bytes();pages.append({'page_1based':start//48+1,'path':str(OUT/name),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'panels':index})
(OUT/'contact-inventory.json').write_text(json.dumps({'keys':623,'page_layout':'6columns8rows,row-major;eachpanelleftRGB/rightNIR-R-G;48panels perpage','display_stretch_rgb':[0,3000],'display_stretch_falsecolour':[0,5000],'resampling':'nearest display only, native scientific arrays unchanged','centre_marker':'yellow hollowcross at actual fractional normative point in source affine; centrepixelunpainted','pages':pages},indent=2)+'\n')
print('pages',len(pages),'keys',len(rows))
