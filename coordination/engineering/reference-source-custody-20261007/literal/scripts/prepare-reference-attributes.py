"""Sourced reference summaries and settlement estimates; no ancient extrapolation."""
import subprocess
import importlib.util
import collections,gzip,hashlib,json,pathlib,math
import numpy as np,rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds,Window
from shapely import STRtree,make_valid,prepare
from shapely.geometry import shape,Point,mapping
from majority import area
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache/research';OUT=D/'reference-attributes';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
expected_footprints=subprocess.check_output(['node','scripts/stamp-prepared.mjs','--hash'],cwd=R,text=True).strip()
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];geoms=[shape(f['geometry']) for f in fs]
classes=['unknown','Af tropical rainforest','Am tropical monsoon','Aw tropical savanna','BWh hot desert','BWk cold desert','BSh hot steppe','BSk cold steppe','Csa hot-summer Mediterranean','Csb warm-summer Mediterranean','Csc cold-summer Mediterranean','Cwa dry-winter humid subtropical','Cwb subtropical highland','Cwc cold subtropical highland','Cfa humid subtropical','Cfb oceanic','Cfc subpolar oceanic','Dsa hot dry-summer continental','Dsb warm dry-summer continental','Dsc cold dry-summer continental','Dsd very cold dry-summer continental','Dwa hot dry-winter continental','Dwb warm dry-winter continental','Dwc dry-winter subarctic','Dwd very cold dry-winter subarctic','Dfa hot humid continental','Dfb warm humid continental','Dfc subarctic','Dfd very cold subarctic','ET tundra','EF ice cap']
records=[];climate_source='Beck et al. (2023), High-resolution Köppen–Geiger climate classifications; CC BY 4.0';climate_url='https://doi.org/10.1038/s41597-023-02549-6';climate_counts={};missing={}
for begin,end in [(1901,1930),(1931,1960),(1961,1990),(1991,2020)]:
 path=C/f'koppen-tif/{begin}_{end}/koppen_geiger_0p00833333.tif';count=0;missing_ids=[]
 with rasterio.open(path) as raster:
  for i,(f,g) in enumerate(zip(fs,geoms)):
   wins=[]
   pieces=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
   total=0;weights=np.zeros(31,dtype=float)
   for piece in pieces:
    w=from_bounds(*piece.bounds,raster.transform);col=max(0,int(math.floor(w.col_off)));row=max(0,int(math.floor(w.row_off)));width=min(raster.width-col,int(math.ceil(w.col_off+w.width))-col);height=min(raster.height-row,int(math.ceil(w.row_off+w.height))-row)
    if width<=0 or height<=0:continue
    w=Window(col,row,width,height);data=raster.read(1,window=w);mask=~geometry_mask([mapping(piece)],out_shape=data.shape,transform=raster.window_transform(w))
    y=90-(np.arange(row,row+height)+.5)/120;cos=np.cos(np.deg2rad(y))[:,None];weighted=mask*cos;total+=weighted.sum();weights+=np.bincount(data[mask].astype(int),weights=np.broadcast_to(cos,data.shape)[mask],minlength=31)[:31]
   valid=weights[1:].sum()
   if total<=0 or valid/total<.5:missing_ids.append(f['id']);continue
   cls=int(np.argmax(weights[1:])+1);record={'id':f'climate:{f["id"]}:{begin}','location_id':f['id'],'attribute':'climate','value':classes[cls],'valid_from':begin,'valid_to':end+1,'method':'reference','status':'reference','source':climate_source,'metadata':{'source_url':climate_url,'normal_period':[begin,end],'resolution':'1 km / 1/120 degree','aggregation':'Dominant land class by latitude-weighted native raster cells; small unsupported footprints remain unknown','share':round(float(weights[cls]/valid),6),'coverage':round(float(valid/total),6),'footprint':'modern reference'}};records.append(record);count+=1
   if begin==1991:records.append({**record,'id':f'climate:{f["id"]}:modern','valid_from':2026,'valid_to':2027,'metadata':{**record['metadata'],'note':'Modern reference using the 1991–2020 climatology; not a 2026 annual observation'}})
   if i%10000==0:print(f'Climate {begin}: {i}/{len(fs)}',flush=True)
 climate_counts[str(begin)]=count;missing[str(begin)]=missing_ids
# Potential natural vegetation is explicitly marked as a biome reference.
# Import the independently audited helper without executing its selective-update main.
vegetation_spec=importlib.util.spec_from_file_location('vegetation_precise',R/'scripts/recheck-vegetation.py')
vegetation_module=importlib.util.module_from_spec(vegetation_spec);vegetation_spec.loader.exec_module(vegetation_module)
eco=read(R/'.cache/semantic/resolve-ecoregions.geojson')['features'];eg=[make_valid(shape(f['geometry'])) for f in eco];prepare(eg);et=STRtree(eg);veg=0
vegetation_metadata={'source_url':'https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef','aggregation':'Largest covered potential-natural biome by precise WGS84 ellipsoidal surface area; source polygons unioned per biome, footprint coverage is the source union divided by the entire location land footprint','area_method':'WGS84 latitude-strip boundary integral, 16-point Gauss-Legendre quadrature for straight longitude/latitude source edges','area_algorithm_sha256':hashlib.sha256((R/'scripts/ellipsoidal_area.py').read_bytes()).hexdigest(),'source_geometry_sha256':hashlib.sha256((R/'.cache/semantic/resolve-ecoregions.geojson').read_bytes()).hexdigest(),'coverage_rule':'At least half the entire location land footprint must be covered; source N/A is an explicit unknown value','source_year':2017,'note':'Potential natural biome, not observed farmland or contemporary land cover'}
for i,(f,g) in enumerate(zip(fs,geoms)):
 candidates=[int(j) for j in et.query(g) if eg[int(j)].intersects(g)]
 summary,evidence=vegetation_module.chosen_summary(g,candidates,eg,eco)
 if summary is None:continue
 missing_class=summary['status']=='unknown'
 records.append({'id':f'biome:{f["id"]}:reference','location_id':f['id'],'attribute':'vegetation','value':summary['value'],'valid_from':2026,'valid_to':2027,'method':'reference','status':summary['status'],'source':'RESOLVE Ecoregions 2017, CC BY 4.0; potential natural vegetation biome reference','metadata':{**vegetation_metadata,'share':summary['share'],'coverage':summary['coverage'],**({'source_value':summary['source_value'],'missing_reason':'Source biome class is not supplied'} if missing_class else {})}});veg+=int(not missing_class)
parts=[]
for i in range(0,len(records),3000):
 p=f'part-{i//3000}.json.gz';raw=json.dumps(records[i:i+3000],separators=(',',':')).encode();(OUT/p).write_bytes(gzip.compress(raw,mtime=0));parts.append(p)
write(OUT/'index.json',{'version':1,'parts':parts,'records':len(records),'climate_counts':climate_counts,'vegetation_references':veg,'missing_climate':missing,'inputs':{'geography':hashlib.sha256(''.join(hashlib.sha256((D/p).read_bytes()).hexdigest() for p in read(D/'world-index.json')['parts']).encode()).hexdigest(),'climate_archive':hashlib.sha256((C/'koppen-geiger-tif.zip').read_bytes()).hexdigest(),'ecoregions':hashlib.sha256((R/'.cache/semantic/resolve-ecoregions.geojson').read_bytes()).hexdigest()}})
subprocess.run(['python',str(R/'scripts/prepare-settlements.py')],cwd=R,check=True)

import runpy
runpy.run_path(str(R/'scripts/compact-reference-attributes.py'),run_name='__main__')

subprocess.run(['node','scripts/stamp-prepared.mjs','reference-attributes',expected_footprints],cwd=R,check=True)
