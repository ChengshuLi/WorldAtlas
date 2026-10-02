#!/usr/bin/env python3
"""Stage compact reference-v2 after a receipted footprint migration, never live data."""
import argparse,ast,collections,copy,gzip,hashlib,importlib.util,json,math,pathlib,shutil,sys,tempfile,zipfile,zlib
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window,from_bounds
from shapely import STRtree,make_valid,prepare as prepare_geometries
from shapely.geometry import shape,mapping
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from majority import canonical
sys.dont_write_bytecode=True

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
OWN=module('reference_identity_helpers',ROOT/'scripts/prepare-ownership-incremental.py')
VEG=module('reference_biome_helpers',ROOT/'scripts/recheck-vegetation.py')
TOPO=module('reference_topography_helpers',ROOT/'scripts/prepare-topography.py')
sha=OWN.sha;load=OWN.load;dump=OWN.dump

def write_gzip(path,value):
 path.write_bytes(gzip.compress(dump(value).encode(),mtime=0));return sha(path)

def geometry_delta(before,after):
 reused={id for id in before.keys()&after.keys() if dump(before[id])==dump(after[id])}
 return reused,set(after)-reused,set(before)-set(after),set(after)-set(before)

def climate_summary(geometry,raster):
 """Same native-centre/cos(latitude) classes; unsupported source extent stays unknown."""
 weights=np.zeros(31,dtype=float);total=0.0
 for piece in list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]:
  w=from_bounds(*piece.bounds,raster.transform);col=max(0,math.floor(w.col_off));stop_col=min(raster.width,math.ceil(w.col_off+w.width))
  if stop_col<=col:continue
  start_row=math.floor(w.row_off);stop_row=math.ceil(w.row_off+w.height)
  for row in range(start_row,stop_row,128):
   height=min(128,stop_row-row);win=Window(col,row,stop_col-col,height);transform=rasterio.windows.transform(win,raster.transform)
   mask=~geometry_mask([mapping(piece)],out_shape=(height,stop_col-col),transform=transform)
   if not mask.any():continue
   cos=np.cos(np.deg2rad(raster.transform.f+(np.arange(row,row+height)+.5)*raster.transform.e))[:,None]
   total+=float((mask*cos).sum());cells=np.zeros(mask.shape,dtype=np.uint8);first=max(0,row);last=min(raster.height,row+height)
   if last>first:cells[first-row:last-row]=raster.read(1,window=Window(col,first,stop_col-col,last-first))
   if cells.max()>30:raise ValueError('Climate source class exceeds verified 0–30 crosswalk')
   weights+=np.bincount(cells[mask],weights=np.broadcast_to(cos,cells.shape)[mask],minlength=31)
 valid=float(weights[1:].sum())
 if total<=0:return None,{'reason':'no_native_cell_centre'}
 if valid/total<.5:return None,{'reason':'less_than_half_supported_native_land_cells','coverage':round(valid/total,6)}
 code=int(np.argmax(weights[1:])+1)
 return (code,round(float(weights[code]/valid),6),round(valid/total,6)),None

class RasterGrid:
 def __init__(self,raster):self.raster=raster;self.shape=(raster.height,raster.width)
 def __getitem__(self,key):
  row,col=key;return self.raster.read(1,window=Window(col.start,row.start,col.stop-col.start,row.stop-row.start))

def source_proof(index,sources):
 expected=index['inputs'];result={}
 for key,path in [('climate_archive',sources['climate_archive']),('ecoregions',sources['vegetation'])]:
  if sha(path)!=expected[key]:raise ValueError('Reference source changed: '+key)
  result[key]={'path':str(path),'sha256':expected[key]}
 topo_types=[t for t in index['types'] if t['attribute']=='topography'];veg_types=[t for t in index['types'] if t['attribute']=='vegetation']
 if len(topo_types)!=1 or not veg_types:raise ValueError('Expected independently sourced topography/vegetation references')
 terrain_sha=topo_types[0]['metadata']['source_sha256']
 if index['merged_sources']['topography-reference']['inputs']['terrain']!=terrain_sha:raise ValueError('Inconsistent frozen terrain source proof')
 if sha(sources['topography'])!=terrain_sha:raise ValueError('Reference terrain source changed')
 result['topography']={'path':str(sources['topography']),'sha256':terrain_sha}
 if any(t['metadata'].get('source_geometry_sha256')!=expected['ecoregions'] for t in veg_types):raise ValueError('Inconsistent vegetation source geometry proof')
 area_sha=sha(ROOT/'scripts/ellipsoidal_area.py')
 if expected.get('vegetation_area_algorithm')!=area_sha or any(t['metadata'].get('area_algorithm_sha256')!=area_sha for t in veg_types):raise ValueError('Precise vegetation algorithm changed; full preparation required')
 topo_algorithm=index['merged_sources']['topography-reference']['inputs']['algorithm']
 if sha(ROOT/'scripts/prepare-topography.py')!=topo_algorithm:raise ValueError('Terrain summary algorithm changed; full preparation required')
 result['algorithms']={name:sha(ROOT/'scripts'/name) for name in ['ellipsoidal_area.py','majority.py','recheck-vegetation.py','prepare-topography.py','prepare-reference-attributes.py']}
 # Verify all extracted native rasters against the already pinned source archive.
 with zipfile.ZipFile(sources['climate_archive']) as archive:
  for begin,end in [(1901,1930),(1931,1960),(1961,1990),(1991,2020)]:
   name=f'{begin}_{end}/koppen_geiger_0p00833333.tif';entry=archive.getinfo(name);path=sources['climate_rasters'][str(begin)]
   crc=0;size=0
   with path.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1048576),b''):crc=zlib.crc32(chunk,crc);size+=len(chunk)
   if size!=entry.file_size or crc!=entry.CRC:raise ValueError('Extracted climate raster differs from pinned archive: '+name)
   result['climate:'+str(begin)]={'path':str(path),'sha256':sha(path),'archive_entry':name,'crc32':crc}
 return result

def type_schema(index):
 types=index['types'];climate={t['valid_from']:i for i,t in enumerate(types) if t['attribute']=='climate'}
 if set(climate)!={1901,1931,1961,1991,2026}:raise ValueError('Unsupported climate intervals: incremental preparation must preserve existing supported periods')
 for begin,end in [(1901,1931),(1931,1961),(1961,1991),(1991,2021),(2026,2027)]:
  if types[climate[begin]]['valid_to']!=end or types[climate[begin]]['method']!='reference' or types[climate[begin]]['metadata']['normal_period']!=([1991,2020] if begin==2026 else [begin,end-1]):raise ValueError('Climate interval/method differs from fixed reference contract')
 if any(t['attribute'] not in ('climate','vegetation','topography') for t in types):raise ValueError('New attribute requires its own explicit incremental source adapter')
 for t in types:
  if t['attribute']!='climate' and (t['valid_from'],t['valid_to'],t['method'])!=(2026,2027,'reference'):raise ValueError('Incremental reference preparation never overwrites other historical evidence')
 return climate

def summarize_changed(ids,after,index,sources):
 climate_types=type_schema(index);rows={id:[] for id in sorted(ids)};missing=collections.defaultdict(dict);evidence={};geometries={id:canonical(shape(after[id])) for id in ids}
 def value_index(value):
  if value not in index['values']:index['values'].append(value)
  return index['values'].index(value)
 # Read the pinned published categorical crosswalk, without executing the worldwide preparer.
 tree=ast.parse((ROOT/'scripts/prepare-reference-attributes.py').read_text());classes=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='classes' for t in n.targets))
 for begin in [1901,1931,1961,1991]:
  with rasterio.open(sources['climate_rasters'][str(begin)]) as raster:
   if raster.crs.to_epsg()!=4326 or raster.dtypes[0]!='uint8' or raster.transform.e>=0:raise ValueError('Unexpected climate native spatial/class format')
   for id in sorted(ids):
    result,reason=climate_summary(geometries[id],raster)
    if result is None:missing['climate:'+str(begin)][id]=reason;continue
    code,share,coverage=result;vi=value_index(classes[code]);rows[id].append([climate_types[begin],vi,share,coverage])
    if begin==1991:rows[id].append([climate_types[2026],vi,share,coverage])
 eco=load(sources['vegetation'])['features'];geoms=[make_valid(shape(f['geometry'])) for f in eco];prepare_geometries(geoms);spatial=STRtree(geoms)
 known_type=next(i for i,t in enumerate(index['types']) if t['attribute']=='vegetation' and t['status']=='reference')
 for id in sorted(ids):
  g=geometries[id];candidates=[int(i) for i in spatial.query(g) if geoms[int(i)].intersects(g)]
  result,proof=VEG.chosen_summary(g,candidates,geoms,eco);evidence[id]={'vegetation':proof}
  if result is None:missing['vegetation'][id]=proof;continue
  ti=known_type
  if result['status']=='unknown':
   ti=next((i for i,t in enumerate(index['types']) if t['attribute']=='vegetation' and t['status']=='unknown' and t['metadata'].get('source_value')==result['source_value']),None)
   if ti is None:
    t=copy.deepcopy(index['types'][known_type]);t['status']='unknown';t['metadata'].update(source_value=result['source_value'],missing_reason='Source biome class is not supplied');ti=len(index['types']);index['types'].append(t)
  rows[id].append([ti,value_index(result['value']),result['share'],result['coverage']])
 with rasterio.open(sources['topography']) as raster:
  if raster.crs.to_epsg()!=4326 or raster.dtypes[0]!='uint8' or raster.transform.e>=0:raise ValueError('Unexpected terrain native spatial/class format')
  grid=RasterGrid(raster);ti=next(i for i,t in enumerate(index['types']) if t['attribute']=='topography')
  for id in sorted(ids):
   result,reason,coverage=TOPO.summarize(geometries[id],grid,raster.transform)
   if result is None:missing['topography'][id]={'reason':reason,'coverage':coverage};continue
   code,share,coverage=result;rows[id].append([ti,value_index(TOPO.CLASSES[code]),share,coverage])
 return rows,dict(missing),evidence

def prepare(before_path,after_path,receipt_path,references,output,sources,unknown_changed=False):
 references=references.resolve();output=output.resolve();start_index_sha=sha(references/'index.json');wrapper_sha=sha(pathlib.Path(__file__))
 if output.exists():raise ValueError('Output must be a new staging directory')
 if output.is_relative_to(references) or references.is_relative_to(output):raise ValueError('Stage must be separate from immutable prepared references')
 index=load(references/'index.json')
 if index.get('version')!=2:raise ValueError('Incremental references require compact codec v2')
 type_schema(index);before=OWN.feature_snapshot(before_path);after=before if before_path.resolve()==after_path.resolve() else OWN.feature_snapshot(after_path)
 bh=OWN.published_footprint_hash(before);ah=bh if before is after else OWN.published_footprint_hash(after)
 if index.get('footprints_sha256')!=bh or index.get('locations')!=len(before):raise ValueError('Before geography does not match frozen references')
 reused,changed,removed,added=geometry_delta(before,after);receipt=load(receipt_path);receipt['_before_ids']=list(before);receipt['_after_ids']=list(after)
 OWN.check_receipt(receipt,bh,ah,changed,removed,added)
 proof={'mode':'unknown-changed','original_inputs':copy.deepcopy(index['inputs'])} if unknown_changed else source_proof(index,sources);old_types=copy.deepcopy(index['types']);old_values=copy.deepcopy(index['values']);archived=collections.defaultdict(list);old_records=collections.defaultdict(list);part_hashes={}
 for name in index['parts']:
  path=OWN.safe_path(references,name);expected=index.get('parts_sha256',{}).get(name)
  if not expected or sha(path)!=expected:raise ValueError('Original reference asset proof mismatch: '+name)
  part_hashes[name]=expected
  for id,rows in load(path):
   if id not in before:raise ValueError('Reference row identity is absent from before geography: '+id)
   for row in rows:
    if len(row)!=4 or not 0<=row[0]<len(old_types) or not 0<=row[1]<len(old_values):raise ValueError('Invalid compact reference tuple')
   old_records[id]+=rows
   if id in changed or id in removed:archived[id]+=rows
 if sum(map(len,old_records.values()))!=index['records']:raise ValueError('Frozen reference row count does not match index')
 for id,rows in old_records.items():
  seen=set()
  for row in rows:
   t=old_types[row[0]];key=(t['attribute'],t['valid_from'],t['valid_to'])
   if key in seen:raise ValueError('Duplicate resolved reference attribute interval: '+id)
   seen.add(key)
 fresh,missing,evidence=({},{'unknown_changed':sorted(changed)},{}) if unknown_changed else summarize_changed(changed,after,index,sources) if changed else ({},{},{})
 if index['types'][:len(old_types)]!=old_types or index['values'][:len(old_values)]!=old_values:raise ValueError('Original source/category dictionaries were renumbered')
 if sha(references/'index.json')!=start_index_sha or sha(pathlib.Path(__file__))!=wrapper_sha:raise ValueError('Reference inputs/code changed during preparation')
 if OWN.published_footprint_hash(OWN.feature_snapshot(before_path))!=bh or OWN.published_footprint_hash(OWN.feature_snapshot(after_path))!=ah:raise ValueError('Input footprints changed during preparation')
 if not unknown_changed and source_proof(index,sources)!=proof:raise ValueError('Native sources changed during preparation')
 output.parent.mkdir(parents=True,exist_ok=True);pending=tempfile.TemporaryDirectory(prefix=output.name+'.pending-',dir=output.parent);stage=pathlib.Path(pending.name);parts=[];active_records=collections.defaultdict(list);reused_records=0
 for name in index['parts']:
  previous=load(references/name);kept=[[id,rows] for id,rows in previous if id in reused]
  if not kept:continue
  if kept==previous:shutil.copyfile(references/name,stage/name)
  else:write_gzip(stage/name,kept)
  parts.append(name)
  for id,rows in kept:active_records[id]+=rows;reused_records+=len(rows)
 changed_rows=[[id,rows] for id,rows in sorted(fresh.items()) if rows]
 for offset in range(0,len(changed_rows),1500):
  name=f'incremental-{sha(receipt_path)[:16]}-delta-{offset//1500}.json.gz'
  if name in parts:raise ValueError('Incremental output part name already exists')
  write_gzip(stage/name,changed_rows[offset:offset+1500]);parts.append(name)
 for id,rows in fresh.items():active_records[id]+=rows
 archive_rows=[[id,archived.get(id,[])] for id in sorted((changed|removed)&set(before))]
 archive_hash=write_gzip(stage/'migration-before-records.json.gz',archive_rows)
 previous_names=['prior-archives','incremental-receipt.json','migration-before-records.json.gz','migration-new-evidence.json.gz']
 retained_archives=OWN.retain_prior_archives(references,stage,index,previous_names)
 counts=collections.Counter();missing_climate={str(y):[] for y in [1901,1931,1961,1991]}
 for id in sorted(after):
  by_attribute={}
  for ti,vi,share,coverage in active_records.get(id,[]):
   t=index['types'][ti];counts[(t['attribute'],t['valid_from'],t['status'])]+=1;by_attribute[(t['attribute'],t['valid_from'])]=True
  for year in missing_climate:
   if ('climate',int(year)) not in by_attribute:missing_climate[year].append(id)
 records=sum(map(len,active_records.values()));known_topo=counts[('topography',2026,'reference')]
 report={'version':1,'before_footprints_sha256':bh,'after_footprints_sha256':ah,'original_index_sha256':start_index_sha,'migration_receipt_sha256':sha(receipt_path),'before_snapshot_sha256':sha(before_path),'after_snapshot_sha256':sha(after_path),'wrapper_sha256':wrapper_sha,'sources':proof,'changed_ids':sorted(changed-added),'added_ids':sorted(added),'removed_ids':sorted(removed),'reused_locations':len(reused),'recomputed_locations':0 if unknown_changed else len(changed),'unknown_changed':bool(unknown_changed),'reused_records':reused_records,'derived_records':sum(map(len,fresh.values())),'archive':{'path':'migration-before-records.json.gz','sha256':archive_hash,'locations':len(archive_rows),'records':sum(len(rows) for _,rows in archive_rows)},'missing_changed':missing,'historical_claims_transferred':False,'source_intervals_unchanged':True,'source_dictionaries_prefix_preserved':True,'after_records':records}
 write_gzip(stage/'migration-new-evidence.json.gz',evidence);(stage/'incremental-receipt.json').write_text(dump(report))
 report['retained_prior_archives']=retained_archives;(stage/'incremental-receipt.json').write_text(dump(report))
 index.update(parts=parts,parts_sha256={name:sha(stage/name) for name in parts},records=records,locations=len(after),represented_locations=sum(bool(rows) for rows in active_records.values()),footprints_sha256=ah,climate_counts={str(y):counts[('climate',y,'reference')] for y in [1901,1931,1961,1991]},missing_climate=missing_climate,vegetation_references=counts[('vegetation',2026,'reference')],unknown_source_records=counts[('vegetation',2026,'unknown')],incremental_preparation={'receipt':'incremental-receipt.json','receipt_sha256':sha(stage/'incremental-receipt.json'),**{k:report[k] for k in ['original_index_sha256','reused_locations','recomputed_locations','reused_records','derived_records']}})
 index['merged_sources']['topography-reference']['records']=known_topo
 index['inputs'].setdefault('original_preparation_geography',index['inputs'].get('geography'))
 after_manifest=load(after_path);index['inputs']['geography']=hashlib.sha256(''.join(sha(OWN.safe_path(after_path.parent,p)) for p in after_manifest['parts']).encode()).hexdigest() if isinstance(after_manifest,dict) and 'parts' in after_manifest else sha(after_path)
 index['inputs'].update(footprints_sha256=ah,incremental_migration_sha256=sha(receipt_path))
 if 'vegetation_numerical_review' in index:index['vegetation_numerical_review_applicability']='Original review retained for unchanged IDs; changed footprints are covered by incremental preparation receipt'
 (stage/'index.json').write_text(dump(index));stage.rename(output);pending.cleanup();print(dump(report),flush=True);return index

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['before','after','receipt','output']:p.add_argument('--'+name,type=pathlib.Path,required=True)
 p.add_argument('--references',type=pathlib.Path,default=ROOT/'data/reference-attributes');p.add_argument('--sources',type=pathlib.Path,help='Optional explicit native source path manifest')
 p.add_argument('--unknown-changed',action='store_true',help='Retain unchanged references; archive changed footprint values and leave new/changed fields unknown without native source recomputation')
 args=p.parse_args();cache=ROOT/'.cache/research'
 sources=load(args.sources) if args.sources else {'climate_archive':str(cache/'koppen-geiger-tif.zip'),'climate_rasters':{str(a):str(cache/f'koppen-tif/{a}_{b}/koppen_geiger_0p00833333.tif') for a,b in [(1901,1930),(1931,1960),(1961,1990),(1991,2020)]},'vegetation':str(ROOT/'.cache/semantic/resolve-ecoregions.geojson'),'topography':str(cache/'terrain-geom_1KMmaj_GMTEDmd.tif')}
 sources={**sources,**{key:pathlib.Path(sources[key]) for key in ['climate_archive','vegetation','topography']},'climate_rasters':{key:pathlib.Path(value) for key,value in sources['climate_rasters'].items()}}
 prepare(args.before,args.after,args.receipt,args.references,args.output,sources,args.unknown_changed)
