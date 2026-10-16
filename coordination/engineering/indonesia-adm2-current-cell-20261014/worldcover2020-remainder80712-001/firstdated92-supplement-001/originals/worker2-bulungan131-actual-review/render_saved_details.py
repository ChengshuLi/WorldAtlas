"""Display-only saved PB02 arrays: no source/network/reprojection/indices/classifier."""
from pathlib import Path
import json,hashlib,functools,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
T=Path(__file__).resolve().parents[2];ROOT=T/'idn-physical-dated778-plan-001/worker6-metadata';B=ROOT/'first-raw-native-observation-001/S2B_50NNJ_20200222_0_L2A';OUT=Path(__file__).resolve().parent/'native-detail-pages';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(l)for l in(B/'point-observations.jsonl').open()];assert len(rows)==131
complete=json.load(open(B/'item-complete.json'));assert complete['point_count']==131 and complete['asset_block_count']==85
metas={};pins={}
for asset in ['red','green','blue','nir','scl']:
 metas[asset]={}
 for q in(B/asset).glob('block-*.json'):
  d=json.load(open(q));metas[asset][tuple(d['native_block'])]=d;pins[str(q.relative_to(T))]={'bytes':q.stat().st_size,'sha256':sha(q)}
@functools.lru_cache(maxsize=8)
def array(asset,br,bc):
 m=metas[asset][(br,bc)];q=ROOT/m['array']['file'];assert sha(q)==m['array']['sha256']and q.stat().st_size==m['array']['bytes'];pins[str(q.relative_to(T))]={'bytes':q.stat().st_size,'sha256':sha(q)}
 with np.load(q,allow_pickle=False)as z:return z['values'].copy(),z['mask'].copy()
def crop(r,a):
 p=r['planned_native_context'][a];left,top,w,h=p['actual_available_context_window'];vals=np.zeros((h,w),np.uint16);mask=np.zeros((h,w),np.uint8);bs=512 if a=='scl' else 1024
 for br in range(top//bs,(top+h-1)//bs+1):
  for bc in range(left//bs,(left+w-1)//bs+1):
   v,m=array(a,br,bc);x,y,ww,hh=metas[a][(br,bc)]['native_window'];x0=max(x,left);x1=min(x+ww,left+w);y0=max(y,top);y1=min(y+hh,top+h);vals[y0-top:y1-top,x0-left:x1-left]=v[y0-y:y1-y,x0-x:x1-x];mask[y0-top:y1-top,x0-left:x1-left]=m[y0-y:y1-y,x0-x:x1-x]
 rr,cc=p['containing_pixel'];assert int(vals[rr-top,cc-left])==r['assets'][a]['raw_value']and int(mask[rr-top,cc-left])==r['assets'][a]['native_valid_mask'];return vals,mask
rows=[r for r in rows if all(r['assets'][a]['native_valid_mask']==255 for a in ['red','green','blue','nir'])];assert len(rows)==109
pages=[]
for start in range(0,len(rows),12):
 subset=rows[start:start+12];im=Image.new('RGB',(1536,1152),'white');draw=ImageDraw.Draw(im);panels=[]
 for i,r in enumerate(subset):
  data=[];masks=[]
  for a in ['red','green','blue','nir']:
   v,m=crop(r,a);data.append(v[16:33,16:33]);masks.append(m[16:33,16:33])
  values=np.stack(data,-1);valid=np.all(np.stack(masks,-1)!=0,-1);x0=(i%3)*512;y0=(i//3)*288
  p=r['planned_native_context']['red'];left,top,w,h=p['actual_available_context_window'];assert w==h==49;left+=16;top+=16;w=h=17;fr,fc=p['fractional_pixel'];px=(fc-left)*256/w;py=(fr-top)*256/h
  for n,bands in enumerate([[0,1,2],[3,0,1]]):
   # PB02 scale .0001 offset0: physical fixed display range0...0.30 RGB,0...0.50 FCC.
   reflectance=values[:,:,bands].astype(float)*.0001;pic=np.clip(reflectance/(.30 if n==0 else .50)*255,0,255).astype(np.uint8);pic[~valid]=[255,0,255];v=Image.fromarray(pic).resize((256,256),Image.Resampling.NEAREST);vd=ImageDraw.Draw(v)
   for dx,dy in [(-6,0),(-5,0),(5,0),(6,0),(0,-6),(0,-5),(0,5),(0,6)]:vd.point((round(px+dx),round(py+dy)),fill=(255,255,0))
   im.paste(v,(x0+n*256,y0))
  raw=[r['assets'][a]['raw_value']for a in ['red','green','blue','nir']];mask=[r['assets'][a]['native_valid_mask']for a in ['red','green','blue','nir']];scl=r['assets']['scl']['raw_value'];text='%d p%d  DN%s SCL%s M%s'%(i+1,r['point_index'],','.join(map(str,raw)),scl,mask[0]);draw.text((x0+2,y0+257),text,fill='black');draw.text((x0+2,y0+272),'RGB 0-.30 | NIR-R-G 0-.50 2020-02-22',fill='black');panels.append({'panel_1based':i+1,'point_index':r['point_index'],'original_key':r['original_key'],'native_fractional_position_in_crop':[fr-top,fc-left],'raw_values':raw,'native_masks':mask,'SCL':scl,'SCL_mask':r['assets']['scl']['native_valid_mask'],'native_window':[left,top,w,h]})
 q=OUT/('bulungan109-detail-%02d.png'%(len(pages)+1));im.save(q);pages.append({'page_1based':len(pages)+1,'path':str(q),'bytes':q.stat().st_size,'sha256':sha(q),'panels':panels})
(OUT/'contact-inventory.json').write_text(json.dumps({'kind':'saved-native-PB02-display-only','source_points':{'path':str(B/'point-observations.jsonl'),'sha256':sha(B/'point-observations.jsonl')},'count':109,'layout':'3columns4rows;12points/page;leftRGB/rightNIR-R-G;256px per17native crop;all109validcentres','conversion':'PB02 rawDN*.0001 exactlyonce,offset0; fixed RGB0...0.30 /FCC0...0.50 display-only;nearest display enlargement','invalid_pixels':'Any RGBNIR mask0 shown magenta; no imputation','marker':'Actual fractional source centre hollow yellow cross; centre pixel unpainted','pages':pages,'source_metadata_and_array_pins':[{'path':p,**d}for p,d in sorted(pins.items())]},indent=2)+'\n');print({'pages':len(pages),'points':len(rows),'arrays_pinned':sum(p.endswith('.npz')for p in pins),'output':str(OUT/'contact-inventory.json')})
