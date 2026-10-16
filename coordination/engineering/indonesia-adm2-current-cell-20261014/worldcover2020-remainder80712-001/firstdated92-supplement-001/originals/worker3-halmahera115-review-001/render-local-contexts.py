from pathlib import Path
from functools import lru_cache
import json,gzip,math
import numpy as np
import struct,zlib
FONT={
"0":["111","101","101","101","111"],"1":["010","110","010","010","111"],"2":["111","001","111","100","111"],"3":["111","001","111","001","111"],"4":["101","101","111","001","001"],"5":["111","100","111","001","111"],"6":["111","100","111","101","111"],"7":["111","001","010","010","010"],"8":["111","101","111","101","111"],"9":["111","101","111","001","111"],"/":["001","001","010","100","100"],"-":["000","000","111","000","000"],"S":["111","100","111","001","111"],"C":["111","100","100","100","111"],"L":["100","100","100","100","111"],"R":["110","101","110","101","101"],"G":["111","100","101","101","111"],"B":["110","101","110","101","110"],"N":["101","111","111","111","101"],"I":["111","010","010","010","111"],"|":["010","010","010","010","010"]}
def label(a,x,y,t):
 for ch in t:
  for yy,line in enumerate(FONT.get(ch,["000"]*5)):
   for xx,b in enumerate(line):
    if b=="1":a[y+yy*2:y+yy*2+2,x+xx*2:x+xx*2+2]=0
  x+=8
def png(path,a):
 h,w,_=a.shape
 def chunk(t,v):return struct.pack(">I",len(v))+t+v+struct.pack(">I",zlib.crc32(t+v)&0xffffffff)
 raw=b"".join(b"\x00"+r.tobytes() for r in a)
 path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b""))
P=Path('idn-physical-dated778-plan-001/worker6-metadata');O=Path(__file__).resolve().parent
rows=[]
for f in (P/'first-raw-native-observation-001').glob('*/point-observations.jsonl'):
 for line in f.open():
  r=json.loads(line)
  if r['original_key']['owner']==22796:rows.append(r)
rows.sort(key=lambda r:(r['original_key']['y'],r['original_key']['x']))
assert len(rows)==115
@lru_cache(maxsize=8)
def block(item,band,br,bc):
 f=P/'first-raw-native-observation-001'/item/band/f'block-{br:02d}-{bc:02d}.npz'
 with np.load(f) as d:return d['values'].copy(),d['mask'].copy()
def context(r,band):
 a=r['assets'][band];col,row,w,h=a['native_context_window_plan']['actual_available_context_window'];size=a['actual_header']['block_shapes'][0][0]
 values=np.zeros((h,w),dtype=np.uint16);masks=np.zeros((h,w),dtype=np.uint8)
 for br in range(row//size,(row+h-1)//size+1):
  for bc in range(col//size,(col+w-1)//size+1):
   v,m=block(r['item_id'],band,br,bc);x0=max(col,bc*size);y0=max(row,br*size);x1=min(col+w,bc*size+v.shape[1]);y1=min(row+h,br*size+v.shape[0]);values[y0-row:y1-row,x0-col:x1-col]=v[y0-br*size:y1-br*size,x0-bc*size:x1-bc*size];masks[y0-row:y1-row,x0-col:x1-col]=m[y0-br*size:y1-br*size,x0-bc*size:x1-bc*size]
 return values,masks
for start in range(0,len(rows),20):
 page=np.full((5*188,1200,3),245,dtype=np.uint8)
 for slot,r in enumerate(rows[start:start+20]):
  i=start+slot;k=r['original_key'];x=(slot%4)*300;y=(slot//4)*188
  bands={b:context(r,b) for b in ['red','green','blue','nir']}
  for j,order in enumerate([['red','green','blue'],['nir','red','green']]):
   v=np.stack([bands[b][0] for b in order],axis=-1);valid=np.logical_and.reduce([bands[b][1]>0 for b in order]);rgb=(np.clip(v.astype(float)/4000,0,1)**0.65*255).astype('uint8');rgb[~valid]=[255,0,255]
   im=np.repeat(np.repeat(rgb,3,axis=0),3,axis=1);page[y+30:y+177,x+j*150:x+j*150+147]=im
   fr,fc=r['assets']['red']['native_fractional_pixel'];c0,r0,_,_=r['assets']['red']['native_context_window_plan']['actual_available_context_window'];px=int(x+j*150+(fc-c0)*3);py=int(y+30+(fr-r0)*3)
   page[py-7:py-3,px]=[255,255,0];page[py+4:py+8,px]=[255,255,0];page[py,px-7:px-3]=[255,255,0];page[py,px+4:px+8]=[255,255,0]
  label(page,x+2,y+1,f'{i:03d} {k["y"]}/{k["x"]} S{r["assets"]["scl"]["raw_value"]}')
  label(page,x+2,y+15,r['acquisition_datetime'][:10]+' RGB | NIR-R-G')
 png(O/f'contact-{start//20+1:02d}.png',page)

(O/'ordered-points.json').write_text(json.dumps([{'review_index':i,'key':r['original_key'],'item':r['item_id'],'date':r['acquisition_datetime'],'SCL_context_only':r['assets']['scl']['raw_value'],'bands':{b:r['assets'][b]['raw_value'] for b in ['red','green','blue','nir']}} for i,r in enumerate(rows)],indent=2)+'\n')
print('Rendered115 saved contexts; no remote/source/GIS/native operation.')
