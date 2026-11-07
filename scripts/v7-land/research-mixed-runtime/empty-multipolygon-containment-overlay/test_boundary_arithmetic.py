"""Compare the exact boundary solver with the former row-by-row scan."""
import math, random, unittest
from fractions import Fraction
from polygon_intersection import reject_boundary_centers

def legacy(geometry,grid,guard,max_visits=5000000):
 step=Fraction(str(grid['step']));west=Fraction(str(grid['west']));north=Fraction(str(grid['north']));w=grid['width'];h=grid['height'];visits=0
 def cd(v):return -((-v.numerator)//v.denominator)
 def pixel(p):return ((Fraction(p[0])-west)/step-Fraction(1,2),(north-Fraction(p[1]))/step-Fraction(1,2))
 polys=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
 for poly in polys:
  for ring in poly:
   for a,b in zip(ring,ring[1:]):
    guard();x0,y0=pixel(a);x1,y1=pixel(b)
    if y0==y1:
     if y0.denominator==1 and 0<=y0<h and max(0,cd(min(x0,x1)))<=min(w-1,math.floor(max(x0,x1))):raise ValueError('polygon boundary crosses grid cell center')
     continue
    lo=max(0,cd(min(y0,y1)));hi=min(h-1,math.floor(max(y0,y1)));visits+=max(0,hi-lo+1)
    if visits>max_visits:raise ValueError('boundary visit limit exceeded')
    for y in range(lo,hi+1):
     if (y-lo)%1024==0:guard()
     x=x0+(x1-x0)*(y-y0)/(y1-y0)
     if x.denominator==1 and 0<=x<w:raise ValueError('polygon boundary crosses grid cell center')
 return visits

def outcome(fn,geom,grid,max_visits=5000000):
 try:return ('ok',fn(geom,grid,lambda:None,max_visits))
 except ValueError as e:return ('error',str(e))

class BoundaryArithmeticTests(unittest.TestCase):
 def test_seeded_random_segments_match_legacy(self):
  r=random.Random(53372)
  for i in range(20000):
   width=r.choice([4,8,16,32,64]);grid={'width':width,'height':width//2,'west':-180,'north':90,'step':360/width}
   points=[(r.randrange(-800,801)/4,r.randrange(-500,501)/4) for _ in range(r.randrange(2,6))]
   if i%5==0:points[1]=(points[1][0],points[0][1])
   if i%7==0:points[0]=(r.random()*360-180,r.random()*180-90)
   if i%23==0:points[0]=(5e-324,-5e-324)
   geom={'type':'Polygon','coordinates':[points]};limit=r.choice([0,2,50,5000000])
   self.assertEqual(outcome(reject_boundary_centers,geom,grid,limit),outcome(legacy,geom,grid,limit),i)
 def test_guard_calls_and_failures_match_legacy(self):
  grid={'width':8192,'height':4096,'west':-180,'north':90,'step':360/8192}
  shapes=[{'type':'Polygon','coordinates':[[(-100.123,80.11),(-101.234,-80.73)]]},
          {'type':'Polygon','coordinates':[[(-100.17333984375,80),(-100.17333984375,-80)]]}]
  for shape in shapes:
   for fail_at in (None,1,2,3,4,5,6,7):
    values=[]
    for fn in (legacy,reject_boundary_centers):
     calls=[]
     def guard():
      calls.append(1)
      if len(calls)==fail_at:raise RuntimeError('cancelled')
     try:result=('ok',fn(shape,grid,guard))
     except (ValueError,RuntimeError) as e:result=(type(e).__name__,str(e))
     values.append((result,len(calls)))
    self.assertEqual(values[0],values[1],(shape,fail_at))
 def test_explicit_horizontal_vertical_and_multi(self):
  grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
  for points in [[(-157.5,67.5),(-112.5,67.5)],[(-157.5,89),(-157.5,-89)],[(-200,67.5),(-190,67.5)],[(0,89),(0,-89)],[(0,0),(0,0)],[(-500,0),(500,0)]]:
   for geom in ({'type':'Polygon','coordinates':[points]}, {'type':'MultiPolygon','coordinates':[[points],[points]]}):
    self.assertEqual(outcome(reject_boundary_centers,geom,grid),outcome(legacy,geom,grid))
if __name__=='__main__':unittest.main()
