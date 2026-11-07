"""Rasterize selected polygon features and resolve intersected current roots.

Caller must authenticate the Neon snapshot, source files, component lineage,
code and input hashes, and run this in an independently guarded child. This
module emits ephemeral component IDs, not geographic proof or cell patches.
"""
import math,struct
from decimal import Decimal,ROUND_FLOOR
from fractions import Fraction
import numpy as np
from osgeo import gdal,ogr,osr

gdal.UseExceptions();ogr.UseExceptions();U=struct.Struct('<II');T=struct.Struct('<III');P=struct.Struct('<II')
def need(v,m):
 if not v:raise ValueError(m)
def ceil(x):return -((-x.numerator)//x.denominator)
def reject_boundary_centers(geometry,grid,guard,max_visits=5000000):
 """Reject exact binary64 polygon-boundary/grid-center coincidence."""
 step=Fraction(str(grid['step']));west=Fraction(str(grid['west']));north=Fraction(str(grid['north']));w=grid['width'];h=grid['height'];visits=0
 need(type(w) is int and type(h) is int and w>0 and h>0 and west==-180 and north==90 and step==Fraction(360,w) and Fraction(float(step))==step and h*step<=180,'unsupported non-dyadic global grid')
 polys=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
 def pixel(p):return ((Fraction(p[0])-west)/step-Fraction(1,2),(north-Fraction(p[1]))/step-Fraction(1,2))
 for poly in polys:
  for ring in poly:
   for a,b in zip(ring,ring[1:]):
    guard();x0,y0=pixel(a);x1,y1=pixel(b)
    if y0==y1:
     if y0.denominator==1 and 0<=y0<h and max(0,ceil(min(x0,x1)))<=min(w-1,math.floor(max(x0,x1))):raise ValueError('polygon boundary crosses grid cell center')
     continue
    lo=max(0,ceil(min(y0,y1)));hi=min(h-1,math.floor(max(y0,y1)));visits+=max(0,hi-lo+1);need(visits<=max_visits,'boundary visit limit exceeded')
    for y in range(lo,hi+1):
     if (y-lo)%1024==0:guard()
     x=x0+(x1-x0)*(y-y0)/(y1-y0)
     need(not (x.denominator==1 and 0<=x<w),'polygon boundary crosses grid cell center')
 return visits
def readrow(rows,runs,y,width,kind):
 rows.seek(y*4);b=rows.read(8);need(len(b)==8,'truncated row index');a,z=U.unpack(b);size=12 if kind=='component' else 8;need(a<=z and z-a<=width,'invalid row index');runs.seek(a*size);buf=runs.read((z-a)*size);need(len(buf)==(z-a)*size,'truncated row');return list((T if kind=='component' else P).iter_unpack(buf))
def equal_coverage(p,c,width):
 spans=[];x=0
 for end,code in p:
  need(x<end<=width and code in (1,17),'invalid physical row')
  if code==17:
   if spans and spans[-1][1]==x:spans[-1]=(spans[-1][0],end)
   else:spans.append((x,end))
  x=end
 need(x==width,'incomplete physical row');actual=[];last=0
 for a,b,root in c:
  need(last<=a<b<=width and root<0xffffffff,'invalid component row')
  if actual and actual[-1][1]==a:actual[-1]=(actual[-1][0],b)
  else:actual.append((a,b))
  last=b
 need(actual==spans,'component/physical mismatch')
def witness_root(w,grid,pr,pv,cr,cv):
 lon=Decimal(w['lon']);lat=Decimal(w['lat']);step=Decimal(str(grid['step']));west=Decimal(str(grid['west']));north=Decimal(str(grid['north']));x0=(lon-west)/step;y0=(north-lat)/step
 need(x0!=x0.to_integral_value() and y0!=y0.to_integral_value(),'witness on grid boundary');x=int(x0.to_integral_value(rounding=ROUND_FLOOR));y=int(y0.to_integral_value(rounding=ROUND_FLOOR));need(0<=x<grid['width'] and 0<=y<grid['height'],'witness out of grid')
 p=readrow(pr,pv,y,grid['width'],'physical');c=readrow(cr,cv,y,grid['width'],'component');equal_coverage(p,c,grid['width']);hits=[r for a,b,r in c if a<=x<b];need(len(hits)==1,'witness not in unique land component');return hits[0]
def intersect(geometries,grid,physical_rows,physical_runs,component_rows,component_runs,include,exclude,guard,strip_rows=8,max_roots=1000000):
 need(isinstance(geometries,list) and 0<len(geometries)<=1000 and callable(guard) and type(strip_rows) is int and 1<=strip_rows<=16 and type(max_roots) is int and 0<max_roots<=1000000,'invalid limits')
 w=grid['width'];h=grid['height'];step=grid['step'];west=grid['west'];north=grid['north'];need(type(w) is int and type(h) is int and 1<w<=1000000 and 0<h<=1000000 and isinstance(step,(int,float)) and step>0,'invalid grid')
 hits=set();per=[];per_cells=[];driver=ogr.GetDriverByName('Memory');srs=osr.SpatialReference();srs.ImportFromEPSG(4326);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
 with open(physical_rows,'rb') as pr,open(physical_runs,'rb') as pv,open(component_rows,'rb') as cr,open(component_runs,'rb') as cv:
  for geometry in geometries:
   guard();reject_boundary_centers(geometry,grid,guard);g=ogr.CreateGeometryFromJson(__import__('json').dumps(geometry,allow_nan=False));need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid polygon');xmin,xmax,ymin,ymax=g.GetEnvelope();x0=max(0,math.floor((xmin-west)/step)-1);x1=min(w,math.ceil((xmax-west)/step)+1);y0=max(0,math.floor((north-ymax)/step)-1);y1=min(h,math.ceil((north-ymin)/step)+1);need(x0<x1 and y0<y1,'polygon outside grid')
   ds=driver.CreateDataSource('');layer=ds.CreateLayer('polygon',srs,ogr.wkbUnknown);feat=ogr.Feature(layer.GetLayerDefn());feat.SetGeometry(g);layer.CreateFeature(feat);found=set();cell_counts={}
   for sy in range(y0,y1,strip_rows):
    guard();ey=min(y1,sy+strip_rows);raster=gdal.GetDriverByName('MEM').Create('',x1-x0,ey-sy,1,gdal.GDT_Byte);raster.SetGeoTransform((west+x0*step,step,0,north-sy*step,0,-step));raster.GetRasterBand(1).Fill(0);layer.ResetReading();gdal.RasterizeLayer(raster,[1],layer,burn_values=[1]);mask=raster.ReadAsArray()
    for y in range(sy,ey):
     physical=readrow(pr,pv,y,w,'physical');components=readrow(cr,cv,y,w,'component');equal_coverage(physical,components,w)
     for a,b,root in components:
      lo=max(a,x0);hi=min(b,x1)
      if lo<hi:
       count=int(np.count_nonzero(mask[y-sy,lo-x0:hi-x0]))
       if count:found.add(root);cell_counts[str(root)]=cell_counts.get(str(root),0)+count;need(len(found)<=max_roots,'root limit exceeded')
    raster=None
   need(found,'source polygon hits no land component');hits.update(found);need(len(hits)<=max_roots,'root limit exceeded');per.append(len(found));per_cells.append(cell_counts);feat=layer=ds=None
  guard();included=[witness_root(x,grid,pr,pv,cr,cv) for x in include];excluded=[witness_root(x,grid,pr,pv,cr,cv) for x in exclude]
 need(len(set(included))==len(included) and len(set(excluded))==len(excluded) and not (set(included)&hits) and set(excluded)<=hits,'invalid inclusion/exclusion witnesses');selected=(hits-set(excluded))|set(included);need(selected,'empty selection')
 return sorted(selected),{'method':'gdal-center-pixel-component-intersection-v1','gdal_version':gdal.VersionInfo('--version'),'per_feature_components':per,'per_feature_root_inside_cells':per_cells,'intersected_components':len(hits),'included_components':len(included),'excluded_components':len(excluded),'selected_components':len(selected),'limitations':['Center-pixel rasterization follows GDAL behavior; source-polygon contact alone does not establish whole-component geographic identity.','Per-feature counts may overlap and must not be summed as a union.','Caller must independently authenticate input and rehash after execution.']}
