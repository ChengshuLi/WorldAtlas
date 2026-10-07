import hashlib,json,pathlib,glob,math
import numpy as np
import rasterio
from rasterio.features import geometry_window,geometry_mask
from rasterio.windows import Window
from shapely import geometry as sg, contains_xy, intersects_xy
from shapely.geometry import box,mapping
base=pathlib.Path(__file__).resolve().parent
tiles=[]
for path in sorted(glob.glob(str(base/'sources/worldcover-2021-v200'/'*_Map.tif'))):
 if not path.endswith(('S18E018_Map.tif','S21E018_Map.tif')):continue
 ds=rasterio.open(path);tiles.append((path,ds,box(*ds.bounds)))
components=json.load(open(base/'inputs/original-components.geojson'))['features']
contacts=json.load(open(base/'inputs/source-contact-features.geojson'))['features']
classes=json.load(open(base/'candidate-classifications.json'))['components']
clook={x['fragment_bindings'][0]['feature_sha256']:x for x in classes}
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def count(geom):
 acc={'valid_pixel_centers':0,'class_80_permanent_water':0,'class_90_herbaceous_wetland':0,'class_70_snow_ice':0,'nodata_pixel_centers':0,'class_counts':{}}
 audit={'pixels_compared':0,'local_mask_mismatches':0,'boundary_centers_included':0,'window_mode':'floor-start/ceil-end; coordinates from original dataset affine and global row/column indices'}
 for path,ds,tile in tiles:
  if not geom.intersects(tile):continue
  clipped=geom.intersection(tile)
  if clipped.is_empty:continue
  a=ds.transform.a;e=ds.transform.e;left=ds.transform.c;top=ds.transform.f
  minx,miny,maxx,maxy=clipped.bounds
  col0=max(0,math.floor((minx-left)/a)); col1=min(ds.width,math.ceil((maxx-left)/a))
  row0=max(0,math.floor((top-maxy)/(-e))); row1=min(ds.height,math.ceil((top-miny)/(-e)))
  if col1<=col0 or row1<=row0:continue
  win=Window(col0,row0,col1-col0,row1-row0)
  arr=ds.read(1,window=win)
  cols=np.arange(col0,col1,dtype=np.float64); rows=np.arange(row0,row1,dtype=np.float64)
  xs=left+(cols+0.5)*a; ys=top+(rows+0.5)*e
  xx,yy=np.meshgrid(xs,ys)
  direct=intersects_xy(clipped,xx,yy)
  inside_local=geometry_mask([mapping(clipped)],out_shape=arr.shape,transform=ds.window_transform(win),invert=True,all_touched=False)
  audit['pixels_compared']+=int(arr.size)
  audit['local_mask_mismatches']+=int(np.count_nonzero(direct!=inside_local))
  audit['boundary_centers_included']+=int(np.count_nonzero(direct & ~contains_xy(clipped,xx,yy)))
  vals=arr[direct]
  for val,n in zip(*np.unique(vals,return_counts=True)):
   val=int(val);n=int(n);acc['class_counts'][str(val)]=acc['class_counts'].get(str(val),0)+n
   if val==0:acc['nodata_pixel_centers']+=n
   else:acc['valid_pixel_centers']+=n
   if val==80:acc['class_80_permanent_water']+=n
   if val==90:acc['class_90_herbaceous_wetland']+=n
   if val==70:acc['class_70_snow_ice']+=n
 return acc,audit
result={'method':'Pixel class membership by exact center points from the original EPSG:4326 dataset affine and global row/column indices; intersects_xy includes boundary points. Conservative floor-start/ceil-end integer windows; no geometry edits.','files':[],'inputs':{},'components':[],'candidate_contact_intersections':[],'summary':{}}
for path,ds,tile in tiles:
 result['files'].append({'name':pathlib.Path(path).name,'bytes':pathlib.Path(path).stat().st_size,'sha256':sha(path),'crs':ds.crs.to_string(),'resolution_degrees':list(ds.res),'bounds':[ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top],'nodata':ds.nodata})
for p in ['inputs/original-components.geojson','inputs/source-contact-features.geojson','candidate-classifications.json']:
 q=base/p;result['inputs'][p]={'bytes':q.stat().st_size,'sha256':sha(q)}
contactgeoms=[(f,sg.shape(f['geometry'])) for f in contacts]
for f in components:
 prop=f['properties'];fh=prop['fragment_bindings'][0]['feature_sha256'];cid=clook[fh]['component_id'];g=sg.shape(f['geometry']);v,a=count(g)
 result['components'].append({'component_id':cid,'feature_sha256':fh,'valid_geometry':g.is_valid,'classes':v,'alignment_audit':a})
 for cf,cg in contactgeoms:
  inter=g.intersection(cg)
  if inter.is_empty or inter.area<=0:continue
  cp=cf['properties'];v,a=count(inter)
  result['candidate_contact_intersections'].append({'component_id':cid,'contact_id':f"gb:{cp['shapeGroup']}:ADM2:{cp['shapeID']}",'contact_name':cp['shapeName'],'intersection_type':inter.geom_type,'classes':v,'alignment_audit':a})
result['summary']={'components':len(result['components']),'positive_area_candidate_contact_pairs':len(result['candidate_contact_intersections']),'components_with_class80':sum(x['classes']['class_80_permanent_water']>0 for x in result['components']),'components_with_class90':sum(x['classes']['class_90_herbaceous_wetland']>0 for x in result['components']),'pairs_with_class80':sum(x['classes']['class_80_permanent_water']>0 for x in result['candidate_contact_intersections']),'pairs_with_class90':sum(x['classes']['class_90_herbaceous_wetland']>0 for x in result['candidate_contact_intersections']),'pairs_with_class80_or90':sum(x['classes']['class_80_permanent_water']+x['classes']['class_90_herbaceous_wetland']>0 for x in result['candidate_contact_intersections']),'total_pixels_compared':sum(x['alignment_audit']['pixels_compared'] for x in result['components']+result['candidate_contact_intersections']),'total_local_mask_mismatches':sum(x['alignment_audit']['local_mask_mismatches'] for x in result['components']+result['candidate_contact_intersections']),'total_boundary_centers_included':sum(x['alignment_audit']['boundary_centers_included'] for x in result['components']+result['candidate_contact_intersections'])}
print(json.dumps(result,sort_keys=True,separators=(',',':')))
