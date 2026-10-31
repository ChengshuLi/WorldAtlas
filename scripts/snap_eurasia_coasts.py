"""Snap the three reference endpoints to connected native coastline edges."""
import json,gzip,argparse,numpy as np
from pathlib import Path
from scipy.ndimage import label,binary_dilation
parser=argparse.ArgumentParser();parser.add_argument('parent',type=Path);parser.add_argument('reference',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();p=args.parent;m=json.load(open(p/'proposal.json'));st=m['step'];r=np.frombuffer(gzip.decompress((p/'rows.u32.gz').read_bytes()),'<u4');v=np.frombuffer(gzip.decompress((p/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
def coast(bounds,seed,target):
 west,south,east,north=bounds;x0,x1=int((west+180)/st),int((east+180)/st)+1;y0,y1=int((90-north)/st),int((90-south)/st)+1;a=[]
 for y in range(y0,y1):
  rr=v[r[y]:r[y+1]];a.append(rr[np.searchsorted(rr[:,0],np.arange(x0,x1),side='right'),1])
 a=np.array(a);c,_=label(a<16);sid=c[int((90-seed[1])/st)-y0,int((seed[0]+180)/st)-x0];assert sid>0;sea=c==sid;rr,cc=np.where((a>=16)&binary_dilation(sea));lo=-180+(x0+cc+.5)*st;la=90-(y0+rr+.5)*st;dist=((lo-target[0])*np.cos(np.deg2rad(target[1])))**2+(la-target[1])**2;i=int(dist.argmin());y,x=int(rr[i]),int(cc[i])
 neighbors=[(y+dy,x+dx) for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)] if 0<=y+dy<len(a) and 0<=x+dx<a.shape[1] and sea[y+dy,x+dx]];yy,xx=neighbors[0];edge=[-180+(x0+(x+xx)/2+.5)*st,90-(y0+(y+yy)/2+.5)*st];return edge,float(np.sqrt(dist[i])*111.195)
d=json.loads(args.reference.read_text());f=d['features']
for idx,start,bounds,seed in [(0,True,(64,67.5,69,70.2),(67,69.5)),(2,True,(36,44,38,45.5),(37,44.5)),(2,False,(49,40,51,42),(50.5,41))]:
 c=f[idx]['geometry']['coordinates'];target=c[0] if start else c[-1];edge,km=coast(bounds,seed,target)
 if start:c.insert(0,edge)
 else:c.append(edge)
 f[idx]['properties'].setdefault('coast_connectors',[]).append({'target':target,'native_coast_edge':edge,'length_km':km});print(idx,start,edge,km)
json.dump(d,args.output.open('w'))
