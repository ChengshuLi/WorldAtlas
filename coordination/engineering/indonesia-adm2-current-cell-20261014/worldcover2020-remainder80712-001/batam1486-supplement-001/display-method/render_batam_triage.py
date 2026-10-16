from pathlib import Path
import json
import numpy as np
import rasterio
R=Path(__file__).resolve().parent;O=R/'batam1486-native-review-v2';O.mkdir(exist_ok=True)
cases=json.loads((R/'batam1486-native-review/land-low-signal-triage.json').read_bytes());report=json.loads((R/'rgbnir-source-observations.json').read_bytes());points={}
for t in report['tile_products']:
 for l in Path(t['observations']['path']).open():
  p=json.loads(l)
  if p['original_key']['owner']==22727:points[p['point_index']]=p
transforms={s['tile']:rasterio.Affine(*s['transform'][:6])for s in report['sources']};inventory=[]
for start in range(0,len(cases),12):
 canvas=np.full((1024,1536,3),255,np.uint8);panels=[]
 for n,d in enumerate(cases[start:start+12]):
  p=points[d['point_index']];a=p['rgbnir_composite_observation'];q=json.loads(Path(a['centre_array']).with_suffix('.json').read_bytes());w=q['window'];r=a['native_row']-w['row_off'];c=a['native_col']-w['col_off']
  with np.load(a['centre_array'],allow_pickle=False)as z:v=z['values'];m=z['masks']
  r0=max(0,r-12);r1=min(v.shape[1],r+13);c0=max(0,c-12);c1=min(v.shape[2],c+13);cf,rf=~transforms[Path(a['centre_array']).parent.name]*(p['centre_unchanged']['longitude'],p['centre_unchanged']['latitude'])
  for j,bands in enumerate([[0,1,2],[3,0,1]]):
   patch=np.moveaxis(np.clip(v[bands,r0:r1,c0:c1].astype(float)/(3000 if j==0 else 5000)*255,0,255).astype(np.uint8),0,-1);patch[np.any(m[:,r0:r1,c0:c1]==0,axis=0)]=[255,0,255]
   rr=np.arange(256)*patch.shape[0]//256;cc=np.arange(256)*patch.shape[1]//256;im=patch[rr[:,None],cc[None,:]];yy=int((rf-w['row_off']-r0)/patch.shape[0]*256);xx=int((cf-w['col_off']-c0)/patch.shape[1]*256)
   for dy,dx in [(-8,0),(-7,0),(7,0),(8,0),(0,-8),(0,-7),(0,7),(0,8)]:
    if 0<=yy+dy<256 and 0<=xx+dx<256:im[yy+dy,xx+dx]=[255,255,0]
   canvas[(n//3)*256:(n//3+1)*256,(n%3)*512+j*256:(n%3)*512+(j+1)*256]=im
  panels.append({'panel_1based':n+1,**d})
 name=f'low-signal-triage-{start//12+1:02d}.png'
 with rasterio.open(O/name,'w',driver='PNG',width=1536,height=1024,count=3,dtype='uint8')as ds:ds.write(np.moveaxis(canvas,-1,0))
 inventory.append({'path':str(O/name),'panels':panels})
(O/'low-signal-triage-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
