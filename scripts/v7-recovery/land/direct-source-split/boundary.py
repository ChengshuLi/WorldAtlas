"""Data-independent geometry checks for an explicitly selected source cut."""
import math, os
import numpy as np
from selection import need

def nearest_side(lon,lat,coords):
 raise RuntimeError('planar nearest-side method retired; a reviewed WGS84 replacement is required')

class TripleRows:
 """Read checked uint32 triple rows with bounded per-row memory."""
 def __init__(self,rows_path,spans_path,height,*,max_width=None):
  need(type(height) is int and height>0 and (max_width is None or type(max_width) is int and max_width>0),'invalid row bounds')
  with open(rows_path,'rb',buffering=0) as f:
   need(os.fstat(f.fileno()).st_size==(height+1)*4,'invalid triple offset file size')
   self.offsets=np.fromfile(f,dtype='<u4',count=height+1)
   need(len(self.offsets)==height+1 and f.read(1)==b'' and os.fstat(f.fileno()).st_size==(height+1)*4,'triple offset file changed or truncated')
  self.fd=os.open(spans_path,os.O_RDONLY)
  try:
   need(self.offsets[0]==0 and np.all(self.offsets[1:]>=self.offsets[:-1]),'invalid triple row offsets')
   need(max_width is None or np.all(self.offsets[1:]-self.offsets[:-1]<=max_width),'triple row span count exceeds width')
   need(os.fstat(self.fd).st_size==int(self.offsets[-1])*12,'invalid triple stream size')
  except BaseException:
   os.close(self.fd);self.fd=None;raise
 def row(self,y):
  need(type(y) is int and 0<=y<len(self.offsets)-1,'row out of range')
  a,b=map(int,self.offsets[y:y+2]);data=os.pread(self.fd,(b-a)*12,a*12)
  need(len(data)==(b-a)*12,'short triple row')
  return np.frombuffer(data,dtype='<u4').reshape(-1,3)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
 def __del__(self):
  if getattr(self,'fd',None) is not None:self.close()

def reject_center_hits(path,width,height,eps=1e-9,*,guard=lambda:None,max_work=100000000):
 # In grid coordinates, fail rather than apply the inherited left-side tie.
 need(callable(guard) and type(max_work) is int and max_work>0,'invalid center-hit work guard')
 work=0
 for (x0,y0),(x1,y1) in zip(path,path[1:]):
  guard()
  work+=math.ceil(abs(x1-x0))+1
  need(work<=max_work,'center-hit work limit reached')
  dx=x1-x0
  if abs(dx)<=eps:
   ix=round(x0-.5);near=abs(x0-(ix+.5))<=eps and abs(x1-(ix+.5))<=eps
   first=max(0,math.ceil(min(y0,y1)-.5-eps));last=min(height-1,math.floor(max(y0,y1)-.5+eps))
   if near and 0<=ix<width and first<=last:raise ValueError('source line intersects a cell center')
  else:
   first=max(0,math.ceil(min(x0,x1)-.5-eps));last=min(width-1,math.floor(max(x0,x1)-.5+eps))
   for ix in range(first,last+1):
    t=(ix+.5-x0)/dx
    if -eps<=t<=1+eps:
     y=y0+t*(y1-y0);iy=round(y-.5)
     if 0<=iy<height and abs(y-(iy+.5))<=eps:raise ValueError('source line intersects a cell center')

def reject_terminal_near_land(path,width,height,eligible,eps=1e-9):
 # An endpoint within one graph-edge length of a land center could truncate a
 # land-to-land cut. Fail closed instead of extrapolating the boundary.
 for x,y in (path[0],path[-1]):
  for iy in range(max(0,math.floor(y)-2),min(height,math.floor(y)+3)):
   for ix in range(max(0,math.floor(x)-2),min(width,math.floor(x)+3)):
    if (ix+.5-x)**2+(iy+.5-y)**2 <= (1+eps)**2 and eligible(ix,iy):
     raise ValueError('source endpoint too close to selected land')

def verify_witness_assignments(stream,checks):
 for code,cells in checks.items():
  for x,y in cells:
   row=stream.row(y);i=int(np.searchsorted(row[:,1],x,side='right'))
   need(i<len(row) and int(row[i,0])<=x<int(row[i,1]) and int(row[i,2])==code,'witness assignment mismatch')

def resolve_fragments(groups,cuts,line,west,north,step,width,height,eligible,max_cells=100000,side_codes=None):
 need(isinstance(side_codes,tuple) and len(side_codes)==2 and side_codes[0]!=side_codes[1],'invalid side codes')
 # A cut-created fragment must touch the cut, have one unambiguous side,
 # and never use the finite line's endpoint as an extrapolation.
 result={};total=0;seen=set()
 for group,points in groups.items():
  need(points,'empty fragment');total+=len(points);need(total<=max_cells,'residual resource cap');need(len(set(points))==len(points) and not seen.intersection(points),'duplicate fragment cell');seen.update(points)
  touched=False;signs=set()
  for x,y in points:
   need(type(x) is int and type(y) is int and 0<=x<width and 0<=y<height,'invalid fragment cell')
   touched |= ((x<width-1 and x in cuts.horizontal.get(y,()) and eligible(x+1,y)) or (x>0 and x-1 in cuts.horizontal.get(y,()) and eligible(x-1,y)) or (y<height-1 and x in cuts.vertical.get(y,()) and eligible(x,y+1)) or (y>0 and x in cuts.vertical.get(y-1,()) and eligible(x,y-1)) or ((x==0 or x==width-1) and y in cuts.wrap and eligible(width-1 if x==0 else 0,y)))
   sign,_=nearest_side(west+(x+.5)*step,north-(y+.5)*step,line);need(sign!=0,'ambiguous residual side');signs.add(sign)
  need(touched,'disconnected fragment does not touch source cut');need(len(signs)==1,'fragment spans conflicting line sides');result[group]=side_codes[0] if next(iter(signs))>0 else side_codes[1]
 return result


def select_witnesses(witnesses, xy, eligible, line, inside_code, outside_code):
    """Derive orientation from all unambiguous selected witnesses, not labels."""
    need(isinstance(witnesses, list) and witnesses and inside_code != outside_code,
         'missing witnesses or invalid side codes')
    seeds, checks = {}, {inside_code: [], outside_code: []}
    signs = {True: set(), False: set()}
    for witness in witnesses:
        need(isinstance(witness, dict) and set(witness) == {'lon', 'lat', 'inside'}
             and type(witness['inside']) is bool, 'invalid witness')
        need(all(type(witness[k]) in (int,float,str) and len(str(witness[k]))<=80 for k in ('lon','lat')), 'invalid witness coordinates')
        try:
            lon, lat = float(witness['lon']), float(witness['lat'])
        except (TypeError, ValueError, OverflowError):
            raise ValueError('invalid witness coordinates') from None
        need(math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180
             and -90 <= lat <= 90, 'invalid witness coordinates')
        sign, _ = nearest_side(lon, lat, line)
        if sign:
            signs[witness['inside']].add(sign)
        code = inside_code if witness['inside'] else outside_code
        cell = xy(lon, lat)
        if eligible(*cell):
            checks[code].append(cell)
            seeds.setdefault(code, cell)
    need(set(seeds) == {inside_code, outside_code}, 'missing eligible side witness')
    need(len(signs[True]) == len(signs[False]) == 1
         and next(iter(signs[True])) == -next(iter(signs[False])),
         'missing or conflicting witness orientation')
    positive = inside_code if next(iter(signs[True])) == 1 else outside_code
    negative = outside_code if positive == inside_code else inside_code
    return seeds, checks, (positive, negative)

