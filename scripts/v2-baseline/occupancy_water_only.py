import argparse,json,sys,time,math
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser(description='Conservatively estimate water-only tile crops using coarse RLE occupancy bins.')
parser.add_argument('config',help='Path to a V2 coastal resumable JSON config')
parser.add_argument('--adaptive-dir',default=str(Path(__file__).resolve().parent),help='Directory containing coastal_band_adaptive.py (default: this script directory)')
args=parser.parse_args()
sys.path.insert(0,args.adaptive_dir)
from coastal_band_adaptive import adaptive_crop
c=json.load(open(args.config));g=c['grid'];w=g['width'];h=g['height'];s=g['step']; tw=c['tile_width'];th=c['tile_height'];pad=c['pad_degrees']
R=np.memmap(c['physical_rows']['path'],dtype='<u4',mode='r');V=np.memmap(c['physical_runs']['path'],dtype='<u4',mode='r')
# Conservative occupancy: bins 256 x 256, marks any row's nonwater RLE spans.
B=256; nx=math.ceil(w/B);ny=math.ceil(h/B); diff=np.zeros((ny,nx+1),np.int64)
t=time.monotonic(); nrun=0
for y in range(h):
 a,b=map(int,(R[y],R[y+1])); ends=V[a*2:b*2:2].astype(np.int64); vals=V[a*2+1:b*2:2]; starts=np.r_[0,ends[:-1]]; mask=vals!=1
 first=starts[mask]//B;last=(ends[mask]-1)//B
 if len(first):
  np.add.at(diff[y//B],first,1);np.add.at(diff[y//B],last+1,-1);nrun+=len(first)
occ=np.cumsum(diff[:,:-1],axis=1)>0
# integral image padded
integral=np.pad(occ.astype(np.int32),((1,0),(1,0))).cumsum(axis=0).cumsum(axis=1)
def rect(x0,x1,y0,y1):
 return integral[y1,x1]-integral[y0,x1]-integral[y1,x0]+integral[y0,x0]
def occupied(crop):
 x0,x1,y0,y1=crop; ya=max(0,y0-1)//B;yb=math.ceil(min(h,y1+1)/B)
 if x1-x0>=w:return rect(0,nx,ya,yb)>0
 x0%=w; length=crop[1]-crop[0]; x1=x0+length
 if x1<=w:return rect(x0//B,math.ceil(x1/B),ya,yb)>0
 return rect(x0//B,nx,ya,yb)>0 or rect(0,math.ceil((x1-w)/B),ya,yb)>0
all_=safe=0;by=[]
for y in range(0,h,th):
 count=0
 for x in range(0,w,tw):
  crop=adaptive_crop([x,min(x+tw,w),y,min(y+th,h)],w,h,s,pad)
  empty=not occupied(crop);count+=empty;all_+=1;safe+=empty
 by.append((y,count))
print(json.dumps({'tiles':all_,'conservative_water_only_crop_tiles':safe,'fraction':safe/all_,'time_s':time.monotonic()-t,'nonwater_rle_runs':nrun,'tile_rows':by}),flush=True)
