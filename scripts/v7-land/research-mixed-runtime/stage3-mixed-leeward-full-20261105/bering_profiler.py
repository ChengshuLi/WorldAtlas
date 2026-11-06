"""Source-only root inside/outside profiling, never a decision selector.

Caller must authenticate source bytes, geometry derivation, same-generation
streams and policy.
"""
import math,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from osgeo import gdal,ogr,osr
from bering_intersection import readrow,equal_coverage,reject_boundary_centers

gdal.UseExceptions();ogr.UseExceptions()
def need(ok,msg):
 if not ok:raise ValueError(msg)

def profile(geometry,grid,physical_rows,physical_runs,component_rows,component_runs,strip_rows=8,max_roots=100000,max_bbox_cells=50000000):
 need(type(strip_rows) is int and 1<=strip_rows<=16 and type(max_roots) is int and 0<max_roots<=100000 and type(max_bbox_cells) is int and 0<max_bbox_cells<=50000000,'invalid limits')
 need(isinstance(grid,dict) and type(grid.get('width')) is int and 1<grid['width']<=1000000 and type(grid.get('height')) is int and 0<grid['height']<=1000000 and type(grid.get('step')) in (int,float) and math.isfinite(grid['step']) and grid['step']>0,'invalid grid bounds');reject_boundary_centers(geometry,grid);w,h=grid['width'],grid['height'];step=grid['step'];west=grid['west'];north=grid['north'];g=ogr.CreateGeometryFromJson(__import__('json').dumps(geometry,allow_nan=False));need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid source geometry')
 xmin,xmax,ymin,ymax=g.GetEnvelope();x0=max(0,math.floor((xmin-west)/step)-1);x1=min(w,math.ceil((xmax-west)/step)+1);y0=max(0,math.floor((north-ymax)/step)-1);y1=min(h,math.ceil((north-ymin)/step)+1);need(x0<x1 and y0<y1 and (x1-x0)*(y1-y0)<=max_bbox_cells,'polygon raster bbox outside limits')
 ds=ogr.GetDriverByName('Memory').CreateDataSource('');srs=osr.SpatialReference();srs.ImportFromEPSG(4326);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);layer=ds.CreateLayer('polygon',srs,ogr.wkbUnknown);f=ogr.Feature(layer.GetLayerDefn());f.SetGeometry(g);layer.CreateFeature(f);inside=defaultdict(int);total=defaultdict(int)
 with open(physical_rows,'rb') as pr,open(physical_runs,'rb') as pv,open(component_rows,'rb') as cr,open(component_runs,'rb') as cv:
  for sy in range(y0,y1,strip_rows):
   ey=min(y1,sy+strip_rows);raster=gdal.GetDriverByName('MEM').Create('',x1-x0,ey-sy,1,gdal.GDT_Byte);raster.SetGeoTransform((west+x0*step,step,0,north-sy*step,0,-step));raster.GetRasterBand(1).Fill(0);layer.ResetReading();gdal.RasterizeLayer(raster,[1],layer,burn_values=[1]);mask=raster.ReadAsArray();need(mask is not None and mask.shape==(ey-sy,x1-x0),'rasterization failed')
   for y in range(sy,ey):
    physical=readrow(pr,pv,y,w,'physical');components=readrow(cr,cv,y,w,'component');equal_coverage(physical,components,w)
    for i,(a,b,root) in enumerate(components):
     lo=max(a,x0);hi=min(b,x1)
     if lo<hi:
      n=int(np.count_nonzero(mask[y-sy,lo-x0:hi-x0]));
      if n:inside[root]+=n;need(len(inside)<=max_roots,'root limit exceeded')
   raster=None
  need(inside,'source polygon intersects no land');roots=set(inside)
  for y in range(h):
   physical=readrow(pr,pv,y,w,'physical');components=readrow(cr,cv,y,w,'component');equal_coverage(physical,components,w)
   for i,(a,b,root) in enumerate(components):
    if root in roots:total[root]+=b-a
 need(set(total)==set(inside),'root inventory mismatch');rows=[]
 for root in sorted(inside):
  need(0<inside[root]<=total[root],'inside count exceeds component');rows.append({'component_id_current_generation_only':root,'total_land_cells':total[root],'inside_polygon_cells':inside[root],'outside_polygon_cells':total[root]-inside[root]})
 return {'schema':'source-polygon-root-profile-v1','status':'diagnostic-not-a-decision','rows':rows,'gdal_version':gdal.VersionInfo('--version'),'grid':grid,'bbox_xy':[x0,y0,x1,y1],'limitations':['GDAL center-pixel semantics, not independent proof of rasterizer correctness.','Boundary contact, whole-root identity and geographic policy require independent review.','Root IDs are valid only for exact pinned component streams; V7 labels were not used.']}
