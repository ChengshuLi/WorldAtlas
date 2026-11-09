#!/usr/bin/env python3
"""Measure and sample supplied projected-linear source lines on WGS84."""
import argparse,bisect,json,math
from pathlib import Path
from geodesic_tools import METHOD,GEOMETRY,coordinate,geodistance,transformer,line_sha256

def generate(coordinates,start,end,section,spacing,epsg):
 if not (type(start) is int and type(end) is int and 0<=start<end<len(coordinates)):raise ValueError('start and end must be ordered, valid vertex indices')
 if isinstance(spacing,bool) or not isinstance(spacing,(int,float)) or not math.isfinite(spacing) or spacing<=0:raise ValueError('spacing must be positive')
 points=[coordinate(p) for p in coordinates];forward,reverse=transformer(epsg);projected=[forward.TransformPoint(*p)[:2] for p in points]
 records=[];total=0.
 for i in range(start,end):
  a,b=points[i],points[i+1];chord=geodistance(a,b)
  if a==b or chord<=0 or chord>=19900000:raise ValueError('zero-length or ambiguous source edge')
  count=max(1,math.ceil(chord/80.))
  if count>1000000 or len(records)+count>1000000:raise ValueError('source sampling limit exceeded')
  pa,pb=projected[i],projected[i+1];previous=a
  for k in range(1,count+1):
   t=k/count;x=pa[0]+t*(pb[0]-pa[0]);y=pa[1]+t*(pb[1]-pa[1]);current=coordinate(reverse.TransformPoint(x,y)[:2]);d=geodistance(previous,current)
   if d<=0 or d>100.01:raise ValueError('source geodesic subdivision is degenerate or too long')
   records.append((total,total+d,i,(k-1)/count,t));total+=d;previous=current
 if total/spacing>1000000:raise ValueError('output sample limit exceeded')
 ends=[r[1] for r in records];features=[];position=0.
 while position<=total:
  j=min(bisect.bisect_left(ends,position),len(records)-1);lo,hi,i,t0,t1=records[j];a,b=projected[i],projected[i+1]
  def at(t):return coordinate(reverse.TransformPoint(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))[:2])
  target=max(0.,min(hi-lo,position-lo));origin=at(t0);left,right=t0,t1
  if target==0:lon,lat=origin
  elif target==hi-lo:lon,lat=at(t1)
  else:
   for _ in range(48):
    mid=(left+right)/2;candidate=at(mid);distance=geodistance(origin,candidate)
    if abs(distance-target)<=1e-5:break
    if distance<target:left=mid
    else:right=mid
   else:raise RuntimeError('geodesic sample position did not converge')
   lon,lat=candidate
  features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[lon,lat]},'properties':{'section':section,'source_edge_index':i,'distance_along_section_m':position}});position+=spacing
 return {'type':'FeatureCollection','distance_method':METHOD,'source_geometry_method':GEOMETRY,'projected_epsg':epsg,'source_line_sha256':line_sha256(points),'section':section,'start_vertex':start,'end_vertex':end,'geodesic_chord_step_limit_m':100.01,'length_approximation':'sum_of_wgs84_geodesic_chords','features':features}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--line',required=True);p.add_argument('--start-vertex',type=int,required=True);p.add_argument('--end-vertex',type=int,required=True);p.add_argument('--section',type=int,required=True);p.add_argument('--spacing-m',type=float,default=500);p.add_argument('--epsg',type=int,required=True);p.add_argument('--output',required=True);a=p.parse_args()
 data=json.loads(Path(a.line).read_text())
 if data.get('type')!='LineString':raise ValueError('line must be a GeoJSON LineString geometry')
 Path(a.output).write_text(json.dumps(generate(data['coordinates'],a.start_vertex,a.end_vertex,a.section,a.spacing_m,a.epsg),indent=2)+'\n')
if __name__=='__main__':main()
