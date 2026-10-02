"""Actual native-source migration fixtures; no writes to real atlas products."""
import contextlib,copy,gzip,importlib.util,io,json,pathlib,subprocess,sys,tempfile,unittest,zipfile
import numpy as np,rasterio
from rasterio.transform import from_origin
from shapely.geometry import box,mapping,Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('incremental_references',ROOT/'scripts/prepare-reference-incremental.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def put(path,value):path.write_text(m.dump(value));return m.sha(path)
def feature(id,g):return {'id':id,'properties':{'id':id},'geometry':mapping(g)}
def rows(path):
 index=m.load(path/'index.json');result={}
 for part in index['parts']:
  for id,values in m.load(path/part):result.setdefault(id,[]).extend(values)
 return index,result
class ReferenceMigrations(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.old=self.root/'old';self.old.mkdir();self.sources={}
  self.before=[feature('change',box(0,0,2,2)),feature('keep',box(4,0,6,2)),feature('removed',box(6,0,7,2))]
  self.after=[feature('change',box(0,0,3,2)),feature('keep',box(4,0,6,2)),feature('new',box(0,2,2,3))]
  self.b=self.root/'before.json';self.a=self.root/'after.json';put(self.b,{'features':self.before});put(self.a,{'features':self.after})
  cells=np.ones((4,8),dtype='uint8');cells[:,2:]=4
  def raster(path,data):
   with rasterio.open(path,'w',driver='GTiff',width=8,height=4,count=1,dtype='uint8',crs='EPSG:4326',transform=from_origin(0,4,1,1),nodata=0) as r:r.write(data,1)
  rasters={};archive=self.root/'climate.zip'
  with zipfile.ZipFile(archive,'w') as z:
   for begin,end in [(1901,1930),(1931,1960),(1961,1990),(1991,2020)]:
    path=self.root/f'climate-{begin}.tif';raster(path,cells);rasters[str(begin)]=path;z.write(path,f'{begin}_{end}/koppen_geiger_0p00833333.tif')
  topo=self.root/'topography.tif';raster(topo,cells)
  eco=self.root/'ecoregions.json';put(eco,{'features':[{'geometry':mapping(box(0,0,2,4)),'properties':{'BIOME_NAME':'Montane Grasslands & Shrublands','ECO_ID':1}},{'geometry':mapping(box(2,0,8,4)),'properties':{'BIOME_NAME':'Deserts & Xeric Shrublands','ECO_ID':2}}]})
  self.sources={'climate_archive':archive,'climate_rasters':rasters,'vegetation':eco,'topography':topo}
  self.index=copy.deepcopy(m.load(ROOT/'data/reference-attributes/index.json'))
  self.index['inputs']['climate_archive']=m.sha(archive);self.index['inputs']['ecoregions']=m.sha(eco)
  for t in self.index['types']:
   if t['attribute']=='vegetation':t['metadata']['source_geometry_sha256']=m.sha(eco)
   if t['attribute']=='topography':t['metadata']['source_sha256']=m.sha(topo)
  self.index['merged_sources']['topography-reference']['inputs'].update(terrain=m.sha(topo),algorithm=m.sha(ROOT/'scripts/prepare-topography.py'))
  self.oldrows=[[f['id'],[[ti,0 if t['attribute']=='climate' else 29 if t['attribute']=='vegetation' else 44,.75,1.0] for ti,t in enumerate(self.index['types']) if t['status']=='reference']] for f in self.before]
  ph=m.write_gzip(self.old/'part.json.gz',self.oldrows);self.index.update(parts=['part.json.gz'],parts_sha256={'part.json.gz':ph},records=21,locations=3,represented_locations=3,footprints_sha256=m.OWN.published_footprint_hash(m.OWN.feature_snapshot(self.b)))
  put(self.old/'index.json',self.index);self.receipt=self.root/'receipt.json';self.refresh_receipt()
 def tearDown(self):self.tmp.cleanup()
 def refresh_receipt(self):
  before=m.OWN.feature_snapshot(self.b);after=m.OWN.feature_snapshot(self.a);_,changed,removed,added=m.geometry_delta(before,after)
  put(self.receipt,{'before_footprints_sha256':m.OWN.published_footprint_hash(before),'after_footprints_sha256':m.OWN.published_footprint_hash(after),'changed_ids':sorted(changed-added),'removed_ids':sorted(removed),'added_ids':sorted(added),'source_evidence':[{'url':'https://source.example/test-native-fixture','source_sha256':m.sha(self.sources['vegetation'])}]})
 def run_prepare(self):
  with contextlib.redirect_stdout(io.StringIO()):return m.prepare(self.b,self.a,self.receipt,self.old,self.root/'stage',self.sources)
 def test_changed_added_removed_and_unchanged_source_records(self):
  before_sha=m.sha(self.old/'index.json');self.run_prepare();index,result=rows(self.root/'stage')
  self.assertEqual(result['keep'],self.oldrows[1][1]);self.assertNotIn('removed',result);self.assertEqual(set(result),{'change','keep','new'})
  self.assertEqual(index['types'][:8],self.index['types']);self.assertEqual(index['values'][:54],self.index['values']);self.assertEqual(m.sha(self.old/'index.json'),before_sha)
  self.assertEqual(index['incremental_preparation']['reused_records'],7);self.assertEqual(index['incremental_preparation']['recomputed_locations'],2)
  climate=[r for r in result['change'] if index['types'][r[0]]['attribute']=='climate'];self.assertEqual(len(climate),5)
  self.assertTrue(all(index['values'][r[1]]=='Af tropical rainforest' for r in climate));self.assertAlmostEqual(climate[0][2],2/3,places=6)
  self.assertEqual(sorted((index['types'][r[0]]['valid_from'],index['types'][r[0]]['valid_to']) for r in climate),[(1901,1931),(1931,1961),(1961,1991),(1991,2021),(2026,2027)])
  archived=dict(m.load(self.root/'stage/migration-before-records.json.gz'));self.assertEqual(archived['change'],self.oldrows[0][1]);self.assertEqual(archived['removed'],self.oldrows[2][1]);self.assertNotIn('keep',archived)
 def test_no_change_copies_original_part_bytes_without_rederivation(self):
  put(self.a,{'features':copy.deepcopy(self.before)});self.refresh_receipt();result=self.run_prepare()
  self.assertEqual(m.sha(self.old/'part.json.gz'),m.sha(self.root/'stage/part.json.gz'));self.assertEqual(result['incremental_preparation']['derived_records'],0);self.assertEqual(result['records'],21)
 def test_stale_before_receipt_part_and_source_proofs_fail_before_stage(self):
  for kind in ['before','receipt','part','native-climate','native-terrain','vegetation']:
   with self.subTest(kind=kind):
    if kind=='before':path=self.b;saved=path.read_bytes();put(path,{'features':self.after})
    elif kind=='receipt':path=self.receipt;saved=path.read_bytes();r=m.load(path);r['changed_ids']=[];put(path,r)
    elif kind=='part':path=self.old/'part.json.gz';saved=path.read_bytes();path.write_bytes(saved+b' ')
    elif kind=='native-climate':path=self.sources['climate_rasters']['1901'];saved=path.read_bytes();path.write_bytes(saved+b' ')
    elif kind=='native-terrain':path=self.sources['topography'];saved=path.read_bytes();path.write_bytes(saved+b' ')
    else:path=self.sources['vegetation'];saved=path.read_bytes();path.write_bytes(saved+b' ')
    with self.assertRaises(ValueError):self.run_prepare()
    self.assertFalse((self.root/'stage').exists());path.write_bytes(saved)
 def test_unknown_or_partial_native_land_never_gets_a_fabricated_value(self):
  with rasterio.open(self.sources['climate_rasters']['1901']) as raster:
   result,reason=m.climate_summary(box(0,-5,2,1),raster)
  self.assertIsNone(result);self.assertEqual(reason['reason'],'less_than_half_supported_native_land_cells')
  with rasterio.open(self.sources['topography']) as raster:
   result,reason,coverage=m.TOPO.summarize(box(0,-5,2,1),m.RasterGrid(raster),raster.transform)
  self.assertIsNone(result);self.assertLess(coverage,.5)
 def test_precise_biome_union_and_unknown_source_class(self):
  geos=[box(0,0,2,1),box(1,0,3,1)];features=[{'properties':{'BIOME_NAME':'N/A','ECO_ID':1}},{'properties':{'BIOME_NAME':'N/A','ECO_ID':2}}]
  result,proof=m.VEG.chosen_summary(box(0,0,3,1),[0,1],geos,features)
  self.assertIsNone(result['value']);self.assertEqual(result['status'],'unknown');self.assertEqual(result['share'],1);self.assertEqual(result['coverage'],1)
 def test_part_identity_and_duplicate_resolved_intervals_are_rejected(self):
  for bad in [[['unregistered',self.oldrows[0][1]]],[['change',self.oldrows[0][1]+self.oldrows[0][1]],*self.oldrows[1:]]]:
   ph=m.write_gzip(self.old/'part.json.gz',bad);self.index['parts_sha256']['part.json.gz']=ph;self.index['records']=sum(len(r) for _,r in bad);put(self.old/'index.json',self.index)
   with self.assertRaises(ValueError):self.run_prepare()
   self.assertFalse((self.root/'stage').exists())
 def test_future_replacement_supports_many_added_and_removed_ids(self):
  self.after=[feature('new'+str(i),box((i%4)*2,0,(i%4)*2+1,1)) for i in range(12)]+[self.before[1]];put(self.a,{'features':self.after});self.refresh_receipt();self.run_prepare();index,result=rows(self.root/'stage')
  self.assertEqual(index['locations'],13);self.assertEqual(index['incremental_preparation']['recomputed_locations'],12);self.assertEqual(result['keep'],self.oldrows[1][1]);self.assertEqual(set(result),{'keep',*[f'new{i}' for i in range(12)]})
 def test_dateline_location_samples_two_small_sides_not_the_whole_world(self):
  path=self.root/'dateline.tif';cells=np.zeros((2,360),dtype='uint8');cells[:,0]=1;cells[:,-1]=1
  with rasterio.open(path,'w',driver='GTiff',width=360,height=2,count=1,dtype='uint8',crs='EPSG:4326',transform=from_origin(-180,2,1,1)) as raster:raster.write(cells,1)
  geometry=m.canonical(Polygon([(179,0),(-179,0),(-179,2),(179,2),(179,0)]))
  with rasterio.open(path) as raster:result,reason=m.climate_summary(geometry,raster)
  self.assertEqual(result,(1,1.0,1.0));self.assertIsNone(reason)
 def test_cli_uses_explicit_pinned_sources_and_writes_only_a_stage(self):
  manifest=self.root/'sources.json';put(manifest,{**{key:str(value) for key,value in self.sources.items() if key!='climate_rasters'},'climate_rasters':{key:str(value) for key,value in self.sources['climate_rasters'].items()}})
  command=[sys.executable,'-W','ignore::PendingDeprecationWarning',str(ROOT/'scripts/prepare-reference-incremental.py'),'--before',str(self.b),'--after',str(self.a),'--receipt',str(self.receipt),'--references',str(self.old),'--output',str(self.root/'stage'),'--sources',str(manifest)]
  finished=subprocess.run(command,check=True,capture_output=True,text=True);receipt=json.loads(finished.stdout.strip().splitlines()[-1]);self.assertEqual(receipt['recomputed_locations'],2);self.assertEqual(receipt['derived_records'],14);self.assertTrue((self.root/'stage/index.json').exists())
 def test_other_historical_intervals_are_not_overwritten(self):
  self.index['types'][5]['valid_from']=1800;put(self.old/'index.json',self.index)
  with self.assertRaises(ValueError):self.run_prepare()
  self.assertFalse((self.root/'stage').exists())
 def test_unknown_changed_preserves_originals_without_native_source_reads(self):
  result=m.prepare(self.b,self.a,self.receipt,self.old,self.root/'stage',{},True);index,values=rows(self.root/'stage')
  self.assertEqual(index['incremental_preparation']['derived_records'],0);self.assertEqual(values['keep'],self.oldrows[1][1]);self.assertNotIn('change',values);self.assertEqual(result['types'],self.index['types']);self.assertTrue(m.load(self.root/'stage/incremental-receipt.json')['unknown_changed'])
 def test_second_generation_retains_earlier_archives_and_uses_distinct_delta_names(self):
  self.run_prepare();first=self.root/'stage';next_path=self.root/'next.json';next_features=copy.deepcopy(self.after);next_features[0]['geometry']=mapping(box(0,0,3,1));put(next_path,{'features':next_features});receipt=self.root/'next-receipt.json';before=m.OWN.feature_snapshot(self.a);after=m.OWN.feature_snapshot(next_path);reused,changed,removed,added=m.geometry_delta(before,after)
  put(receipt,{'before_footprints_sha256':m.OWN.published_footprint_hash(before),'after_footprints_sha256':m.OWN.published_footprint_hash(after),'changed_ids':sorted(changed-added),'added_ids':sorted(added),'removed_ids':sorted(removed),'relationships':[],'source_evidence':[{'url':'https://example.org/test','source_sha256':'a'*64}]})
  second=m.prepare(self.a,next_path,receipt,first,self.root/'second',self.sources);proof=m.load(self.root/'second/incremental-receipt.json');self.assertTrue(any(p.endswith('incremental-receipt.json') for p in proof['retained_prior_archives']));self.assertTrue(second['parts']);self.assertEqual(len(second['parts']),len(set(second['parts'])))
if __name__=='__main__':unittest.main()
