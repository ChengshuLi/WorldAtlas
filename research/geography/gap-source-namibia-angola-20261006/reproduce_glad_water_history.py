import argparse,hashlib,json,math,pathlib
import numpy as np
import rasterio
from rasterio.windows import Window
from shapely import contains_xy,intersects_xy
from shapely.geometry import box,shape,mapping
base=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Reproduce GLAD water-history statistics for the original Namibia–Angola candidates and contacts.')
parser.add_argument('--tiles-root',required=True,type=pathlib.Path,help='Directory containing download-receipts.json and tiles/<tile>/<filename>.tif')
parser.add_argument('--output',type=pathlib.Path,default=base/'glad-water-1999-2023-analysis.json')
args=parser.parse_args()
root=args.tiles_root.resolve()
receipts=json.load(open(root/'download-receipts.json'))
rec_by_name={x['name'].split('/')[-1]:x for x in receipts['files']}
components=json.load(open(base/'inputs/original-components.geojson'))['features']
contacts=json.load(open(base/'inputs/source-contact-features.geojson'))['features']
# Subjects are unchanged packet geometries; component-contact intersections are computed without repair.
subjects=[]
for f in components:
 g=shape(f['geometry']);subjects.append({'kind':'component','id':f['id'],'prefix':f['id'].split(':')[-1][:8],'geometry':g,'feature_sha256':f['properties']['fragment_bindings'][0]['feature_sha256']})
contact_rows=[]
for f in contacts:
 p=f['properties'];g=shape(f['geometry']);cid=f"gb:{p['shapeGroup']}:ADM2:{p['shapeID']}"
 row={'kind':'contact','id':cid,'name':p.get('shapeName'),'geometry':g,'feature_sha256':p.get('source_feature_sha256')}
 contact_rows.append(row);subjects.append(row)
pairs=[]
for c in subjects[:len(components)]:
 for t in contact_rows:
  inter=c['geometry'].intersection(t['geometry'])
  if not inter.is_empty and inter.area>0:
   pairs.append({'kind':'candidate_contact_intersection','id':f"{c['id']} × {t['id']}",'component_id':c['id'],'component_prefix':c['prefix'],'contact_id':t['id'],'contact_name':t['name'],'geometry':inter,'geometry_type':inter.geom_type,'geometry_valid':inter.is_valid})
subjects.extend(pairs)
tiles={
 '10S_010E':box(10,-20,20,-10),
 '10S_020E':box(20,-20,30,-10),
}
# Derive globally indexed pixel-center masks from each original source transform.
maskplans={}
source_rasters={}
for tile_name,tilegeom in tiles.items():
 fname='2023_percent.tif';path=root/'tiles'/tile_name/fname
 ds=rasterio.open(path);source_rasters[tile_name]=ds
 if ds.width!=40000 or ds.height!=40000 or ds.crs.to_string()!='EPSG:4326' or ds.nodata!=255:raise RuntimeError(f'unexpected grid {tile_name}: {ds.profile}')
 for s in subjects:
  clipped=s['geometry'].intersection(tilegeom)
  if clipped.is_empty:continue
  a=ds.transform.a;e=ds.transform.e;left=ds.transform.c;top=ds.transform.f
  minx,miny,maxx,maxy=clipped.bounds
  c0=max(0,math.floor((minx-left)/a));c1=min(ds.width,math.ceil((maxx-left)/a))
  r0=max(0,math.floor((top-maxy)/(-e)));r1=min(ds.height,math.ceil((top-miny)/(-e)))
  if c1<=c0 or r1<=r0:continue
  cols=np.arange(c0,c1,dtype=np.float64);rows=np.arange(r0,r1,dtype=np.float64)
  xs=left+(cols+0.5)*a;ys=top+(rows+0.5)*e
  xx,yy=np.meshgrid(xs,ys)
  direct=intersects_xy(clipped,xx,yy)
  boundary=int(np.count_nonzero(direct & ~contains_xy(clipped,xx,yy)))
  maskplans[(tile_name,s['id'])]=(Window(c0,r0,c1-c0,r1-r0),direct,boundary)
# Confirm product transform is the same in every tile.
meta=[]
for obj in receipts['files']:
 name=obj['name'].split('/')[-1];tile_name=obj['name'].split('/')[1]
 meta.append({'name':name,'tile':tile_name,'bytes':obj['bytes'],'sha256':obj['sha256'],'md5_hex':obj['md5_hex'],'generation':obj['generation']})
# Extract annual and climatological monthly water percentage for exact centers.
series={s['id']:{'metadata':{k:v for k,v in s.items() if k not in ('geometry',)},'annual':[],'monthly_climatology':[]} for s in subjects}
def extract(fname,seasonal):
 tile_stats={}
 for tile_name,ds in source_rasters.items():
  path=root/'tiles'/tile_name/fname
  with rasterio.open(path) as raster:
   if raster.transform!=ds.transform or raster.nodata!=255:raise RuntimeError('grid changed')
   total_pixels=0;total_valid=0;total_water50=0;total_nodata=0;total_sum=0
   for s in subjects:
    plan=maskplans.get((tile_name,s['id']))
    if plan is None:continue
    win,mask,_=plan
    vals=raster.read(1,window=win)[mask]
    total_pixels+=len(vals)
    valid=vals!=255;v=vals[valid];n=len(v);w=int(np.count_nonzero(v>=50));nd=int(len(vals)-n)
    total_valid+=n;total_water50+=w;total_nodata+=nd;total_sum+=int(v.astype(np.uint64).sum())
    entry={'raster':fname,'tile':tile_name,'pixel_centers':int(len(vals)),'valid_centers':n,'nodata_centers':nd,'centers_ge50_percent':w,'water_percent_sum':int(v.astype(np.uint64).sum()),'mean_water_percent':(float(np.mean(v)) if n else None),'water_center_fraction':(w/n if n else None)}
    key='monthly_climatology' if seasonal else 'annual'
    series[s['id']][key].append(entry)
   tile_stats[tile_name]={'geometry_window_center_tests':total_pixels,'valid_centers_sum_over_all_geometries':total_valid,'nodata_centers_sum_over_all_geometries':total_nodata,'centers_ge50_sum_over_all_geometries':total_water50,'mean_water_percent_over_all_geometry_centers':(total_sum/total_valid if total_valid else None)}
 return tile_stats
annual_files=sorted([x for x in rec_by_name if x.endswith('_percent.tif')],key=lambda x:int(x[:4]))
monthly_files=sorted([x for x in rec_by_name if '_mean_99_23.tif' in x],key=lambda x:int(x[:2]))
for f in annual_files:extract(f,False)
for f in monthly_files:extract(f,True)
def combine_tiles(entries, periods, period_name):
 grouped={}
 for entry in entries:
  period=int(entry['raster'][:4]) if period_name=='year' else entry['raster'][:2]
  grouped.setdefault(period,[]).append(entry)
 result=[]
 for period in periods:
  records=grouped.get(period,[])
  tile_values={entry['tile']:{'pixel_centers':entry['pixel_centers'],'valid_centers':entry['valid_centers'],'nodata_centers':entry['nodata_centers'],'centers_ge50_percent':entry['centers_ge50_percent'],'water_percent_sum':entry['water_percent_sum']} for entry in records}
  pixels=sum(x['pixel_centers'] for x in records);valid=sum(x['valid_centers'] for x in records);nodata=sum(x['nodata_centers'] for x in records);water=sum(x['centers_ge50_percent'] for x in records);water_sum=sum(x['water_percent_sum'] for x in records)
  item={period_name:period,'pixel_centers':pixels,'valid_centers':valid,'nodata_centers':nodata,'centers_ge50_percent':water,'water_percent_sum':water_sum,'mean_water_percent':(water_sum/valid if valid else None),'water_center_fraction':(water/valid if valid else None),'tile_counts':tile_values}
  result.append(item)
 return result

for s in subjects:
 o=series[s['id']]
 o['annual']=combine_tiles(o['annual'],[int(x[:4]) for x in annual_files],'year')
 o['monthly_climatology']=combine_tiles(o['monthly_climatology'],[x[:2] for x in monthly_files],'month')
 o['summary']={
  'annual_years_with_any_ge50_center':sum(x['centers_ge50_percent']>0 for x in o['annual']),
  'annual_years_with_valid_centers':sum(x['valid_centers']>0 for x in o['annual']),
  'years_with_zero_valid_centers':[x['year'] for x in o['annual'] if x['valid_centers']==0],
  'years_with_any_ge50_center':[x['year'] for x in o['annual'] if x['centers_ge50_percent']>0],
  'annual_years_ge50_mean_for_geometry':[x['year'] for x in o['annual'] if x['mean_water_percent'] is not None and x['mean_water_percent']>=50],
  'monthly_climatology_months_with_any_ge50_center':sum(x['centers_ge50_percent']>0 for x in o['monthly_climatology']),
  'monthly_mean_percent_by_month':{x['month']:x['mean_water_percent'] for x in o['monthly_climatology']},
  'pixel_center_count_by_tile':{t:int(maskplans.get((t,s['id']),(None,np.zeros((0,0),bool),0))[1].sum()) for t in tiles},
  'boundary_centers_count_by_tile':{t:maskplans[(t,s['id'])][2] if (t,s['id']) in maskplans else 0 for t in tiles}
 }
for ds in source_rasters.values():ds.close()
inputs={}
for p in ['inputs/original-components.geojson','inputs/source-contact-features.geojson']:
 q=base/p;inputs[p]={'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()}
out={'method':'For each tile, point-centre membership was evaluated from the original EPSG:4326 transform and global row/column indices using conservative floor-start/ceil-end windows. Values 0–100 are recorded as GLAD annual or month-of-year mean water percentages; 255 is NoData. No geometry was changed. Center thresholds >=50% follow the published 2020 GLAD product paper’s dominant water definition; unthresholded means are also retained.','source_page':'https://storage.googleapis.com/earthenginepartners-hansen/waterC2/download.html','publication':'Pickens et al. 2020, https://doi.org/10.1016/j.rse.2020.111792','source_year_claim':'Current web page advertises 1999–2025; public Google Cloud Storage objects retrieved for these tiles stop at 2023 (25 annual products 1999–2023 and 12 climatological monthly means 1999–2023).','source_sensor':'Landsat 5/7/8/9 Collection 2; this is a separate GLAD classification/product method, not an independent sensor family from JRC/DE Africa WOfS.','grid':{'crs':'EPSG:4326','width':40000,'height':40000,'pixel_size_degrees':0.00025,'approx_meters_at_equator':30,'nodata':255,'bands':1},'limits':['Water percentages are computed only from land and water observations; file docs do not provide per-pixel valid observation counts. A zero or NoData must not be read as proof that the location was dry.','The 30 m grid cannot resolve many narrow river channels or small candidates. Mixed shoreline pixels, clouds/observability, registration uncertainty, and seasonal vegetation remain material.','The 2020 study defines open surface water as unobscured water covering at least 50% of a 30 m pixel. Its reported classification accuracy and edge-pixel caveats are global/sample-based, not candidate-specific. The maps are not statistical area estimators.'], 'inputs':inputs,'source_files':meta,'subjects':list(series.values()),'summary':{'component_count':len(components),'contact_count':len(contacts),'positive_area_component_contact_pairs':len(pairs),'components_with_any_ge50_center_any_year':sum(any(y['centers_ge50_percent']>0 for y in series[s['id']]['annual']) for s in subjects[:len(components)]),'components_with_any_valid_center_any_year':sum(any(y['valid_centers']>0 for y in series[s['id']]['annual']) for s in subjects[:len(components)]),'pairs_with_any_ge50_center_any_year':sum(any(y['centers_ge50_percent']>0 for y in series[p['id']]['annual']) for p in pairs),'pairs_with_any_valid_center_any_year':sum(any(y['valid_centers']>0 for y in series[p['id']]['annual']) for p in pairs),'center_windows_compared':sum(sum(y['pixel_centers'] for y in series[s['id']]['annual']+series[s['id']]['monthly_climatology']) for s in subjects),'source_bytes':receipts['total_bytes'],'source_verified_files':receipts['verified_objects']}}
path=args.output.resolve();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps(out['summary'],sort_keys=True));print('bytes',path.stat().st_size,'sha256',hashlib.sha256(path.read_bytes()).hexdigest())
