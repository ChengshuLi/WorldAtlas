"""Display-only literal saved rawDN native crops. No network/source acquisition, gain/offset, reflectance or indices."""
from pathlib import Path
import json,hashlib,collections
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'native-rawDN-context-pages';OUT.mkdir(exist_ok=True)
plan=json.loads((ROOT/'next-distinct-native-block-plan34.json').read_text());items={i['item_id']:i for i in plan['items']};rows=[];held=[]
for folder in (ROOT/'next-distinct-raw-native-observation-001').glob('S2*'):
 f=folder/'point-observations.jsonl'
 if not f.exists():continue
 for l in f.read_text().splitlines():
  r=json.loads(l)
  if r['original_key']['owner']!=22727:continue
  rows.append(r)
assert len(rows)==34 and not held
rows.sort(key=lambda p:(p['item_id'],p['assets']['red']['native_containing_pixel'],p['point_index']))
pages=[];pageimages=[];pageindex=[];page_number=0
cached_item=None;arrays={};all_source_array_pins={}
for global_index,p in enumerate(rows):
 if p['item_id']!=cached_item:
  arrays.clear();item=items[p['item_id']]
  assert item['normalization_contract']['raw_native_DN_and_masks_preserved'] is True
  for band in ('red','green','blue','nir','scl'):
   arrays[band]={}
   for block in item['assets'][band]['native_blocks']:
    br,bc=block['block'];meta=ROOT/'next-distinct-raw-native-observation-001'/p['item_id']/band/('block-%02d-%02d.json'%(br,bc));m=json.loads(meta.read_text());f=ROOT/m['array']['file']
    assert f.stat().st_size==m['array']['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['array']['sha256'];all_source_array_pins[m['array']['file']]=m['array']
    with np.load(f,allow_pickle=False) as z:values=z['values'];mask=z['mask']
    arrays[band][(br,bc)]=(values,mask,m['native_window'])
  cached_item=p['item_id']
 raw=np.zeros((4,49,49),np.uint16);masks=np.zeros((4,49,49),np.uint8);sources=[]
 for b,band in enumerate(('red','green','blue','nir')):
  a=p['assets'][band];window=a['native_context_window_plan']['requested_context_window'];left,top,width,height=window;assert width==height==49;bh,bw=item['assets'][band]['actual_header']['block_shapes'][0];H=item['assets'][band]['actual_header']['height'];W=item['assets'][band]['actual_header']['width']
  for rr in range(49):
   sr=top+rr
   for cc in range(49):
    sc=left+cc
    if not (0<=sr<H and 0<=sc<W):continue
    values,mask,w=arrays[band][(sr//bh,sc//bw)];raw[b,rr,cc]=values[sr-w[1],sc-w[0]];masks[b,rr,cc]=mask[sr-w[1],sc-w[0]]
  row,col=a['native_containing_pixel'];assert int(raw[b,row-top,col-left])==a['raw_value'] and int(masks[b,row-top,col-left])==a['native_valid_mask'];sources.append(a['containing_array'])
 rowf,colf=p['assets']['red']['native_fractional_pixel'];left,top,_,_=p['assets']['red']['native_context_window_plan']['requested_context_window'];cy,cx=rowf-top,colf-left;images=[]
 # Uncalibrated RAWDN qualitative display ONLY: no gain/offset/BOA units.
 rawdisplay=raw.astype(np.float64)
 for bands,hi in [([0,1,2],3000),([3,0,1],5000)]:
  patch=np.moveaxis(np.clip(rawdisplay[bands]/hi*255,0,255).astype(np.uint8),0,-1);patch[np.any(masks==0,axis=0)]=[255,0,255]
  ii=np.arange(192)*49//192;im=patch[ii[:,None],ii[None,:]].copy();yy=int(cy/49*192);xx=int(cx/49*192)
  for dy,dx in [(-5,0),(-4,0),(4,0),(5,0),(0,-5),(0,-4),(0,4),(0,5)]:
   if 0<=yy+dy<192 and 0<=xx+dx<192:im[yy+dy,xx+dx]=[255,255,0]
  images.append(im)
 # Native17-pixel detail and separately enlarged native25-pixel SCL context.
 detail_images=[]
 for bands,hi in [([0,1,2],3000),([3,0,1],5000)]:
  patch=np.moveaxis(np.clip(raw[bands,16:33,16:33].astype(np.float64)/hi*255,0,255).astype(np.uint8),0,-1);patch[np.any(masks[:,16:33,16:33]==0,axis=0)]=[255,0,255]
  ii=np.arange(256)*17//256;im=patch[ii[:,None],ii[None,:]].copy();yy=int((cy-16)/17*256);xx=int((cx-16)/17*256)
  for dy,dx in [(-6,0),(-5,0),(5,0),(6,0),(0,-6),(0,-5),(0,5),(0,6)]:
   if 0<=yy+dy<256 and 0<=xx+dx<256:im[yy+dy,xx+dx]=[255,255,0]
  detail_images.append(im)
 a=p['assets']['scl'];lefts,tops,ws,hs=a['native_context_window_plan']['actual_available_context_window'];assert ws==hs==25
 sv=np.zeros((25,25),np.uint8);sm=np.zeros((25,25),np.uint8);bh,bw=item['assets']['scl']['actual_header']['block_shapes'][0]
 for rr in range(25):
  for cc in range(25):
   sr,sc=tops+rr,lefts+cc;values,mask,w=arrays['scl'][(sr//bh,sc//bw)];sv[rr,cc]=values[sr-w[1],sc-w[0]];sm[rr,cc]=mask[sr-w[1],sc-w[0]]
 rr,cc=a['native_containing_pixel'];assert int(sv[rr-tops,cc-lefts])==a['raw_value'] and int(sm[rr-tops,cc-lefts])==a['native_valid_mask']
 palette=np.array([[0,0,0],[255,0,0],[70,70,70],[90,55,25],[0,160,0],[230,190,70],[0,80,230],[140,140,140],[185,185,185],[255,255,255],[100,220,255],[255,160,220]],np.uint8)
 assert sv.max()<len(palette);patch=palette[sv];patch[sm==0]=[255,0,255];ii=np.arange(256)*25//256;im=patch[ii[:,None],ii[None,:]].copy();rf,cf=a['native_fractional_pixel'];yy=int((rf-tops)/25*256);xx=int((cf-lefts)/25*256)
 for dy,dx in [(-6,0),(-5,0),(5,0),(6,0),(0,-6),(0,-5),(0,5),(0,6)]:
  if 0<=yy+dy<256 and 0<=xx+dx<256:im[yy+dy,xx+dx]=[255,255,0]
 detail_images.append(im);detail=OUT/f"point-{p['point_index']}-native17-RGB-FCC-SCL25.png";canvas_detail=np.concatenate(detail_images,axis=1)
 with rasterio.open(detail,'w',driver='PNG',width=768,height=256,count=3,dtype='uint8') as ds:ds.write(np.moveaxis(canvas_detail,-1,0))
 pageimages.append(np.concatenate(images,axis=1));pageindex.append({'global_index_zero_based':global_index,'panel_1based':len(pageindex)+1,'point_index':p['point_index'],'original_key':p['original_key'],'item_id':p['item_id'],'acquisition_datetime':p['acquisition_datetime'],'raw_RGBNIR':[p['assets'][b]['raw_value'] for b in ('red','green','blue','nir')],'raw_masks':[p['assets'][b]['native_valid_mask'] for b in ('red','green','blue','nir')],'raw_SCL_value':p['assets']['scl']['raw_value'],'raw_SCL_mask':p['assets']['scl']['native_valid_mask'],'fractional_centre_in_crop':[cy,cx],'native_requested_window':[left,top,49,49],'context_complete':p['assets']['red']['native_context_window_plan']['context_complete_within_source_frame'],'source_array_pins':sources})
 if len(pageimages)==24 or global_index==len(rows)-1:
  page_number+=1;canvas=np.full((1176,1536,3),255,np.uint8)
  for n,im in enumerate(pageimages):canvas[(n//4)*196:(n//4)*196+192,(n%4)*384:(n%4)*384+384]=im
  f=OUT/f'batam34-rawDN-{page_number:02d}.png'
  with rasterio.open(f,'w',driver='PNG',width=1536,height=1176,count=3,dtype='uint8') as ds:ds.write(np.moveaxis(canvas,-1,0))
  b=f.read_bytes();pages.append({'page_1based':page_number,'file':str(f.relative_to(OUT.parent)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'panels':pageindex});pageimages=[];pageindex=[]
(OUT/'contact-inventory.json').write_text(json.dumps({'scope':34,'source_plan_sha256':__import__('hashlib').sha256((ROOT/'next-distinct-native-block-plan34.json').read_bytes()).hexdigest(),'current_original_Batam_held_scope':237,'prior_actual_cloud_haze_held_cohort':34,'new_PB05_raw_only_hold_count':0,'pages':pages,'all_loaded_source_array_pins':[all_source_array_pins[k]for k in sorted(all_source_array_pins)],'display':'4 columns x 6 rows; each panel left RGB, right NIR-R-G. Literal uncalibrated rawDN fixed RGB0..3000/FCC0..5000 qualitative display only for every point. No gain/offset, BOA units, indices or quantitative reflectance interpretation. Both new source items have PB02.13 metadata contracts; these are retained without applying normalization in this display. All prior source radiometry limits remain unchanged. Nearest enlargement; hollow actual fractional-centre cross leaves centre unpainted. Magenta denotes an actual mask0 or absent source context; no clamp or imputation.','detail_images':'point-ID-native17-RGB-FCC-SCL25.png: left17-native RGB, middle17-native raw NIR-R-G, right separate25-native20m SCL. SCL is source context only, never body truth; native512px blocks indexed as512. Nearest enlargement with actual fractional marker; no cross-grid resampling.', 'new_physical_credit':0},indent=2)+'\n')
print(json.dumps({'qualitative_literal_rawDN34':True,'pages':len(pages),'loaded_arrays_whole_hash_verified':len(all_source_array_pins),'new_PB05radiometry_hold_count':0}))
