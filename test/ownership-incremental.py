#!/usr/bin/env python3
"""Meaningful synthetic ownership migrations; no real atlas writes."""
import collections,copy,gzip,hashlib,importlib.util,json,pathlib,shutil,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('incremental',ROOT/'scripts/prepare-ownership-incremental.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from shapely.geometry import box,mapping,Polygon

def feature(id,geo):return {'type':'Feature','id':id,'properties':{'id':id},'geometry':mapping(geo)}
def put(path,value):path.write_text(m.dump(value));return m.sha(path)
def read_rows(path):
 index=m.load(path/'index.json');evidence=[v for p in index['evidence_parts'] for v in m.load(path/p['path'])];return index,{id:rows for p in index['parts'] for id,rows in m.load(path/p['path'])},evidence

class IncrementalOwnership(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.old=self.root/'original';self.source=self.root/'political';self.old.mkdir();self.source.mkdir()
  alg=self.old/'algorithms/exact';alg.mkdir(parents=True);entries=[]
  for name in ['majority.py','prepare-ownership.py','ellipsoidal_area.py']:
   shutil.copyfile(ROOT/'data/ownership-history/algorithms/exact'/name,alg/name);entries.append({'path':'algorithms/exact/'+name,'sha256':m.sha(alg/name)})
  self.before=[feature('change',box(0,0,2,1)),feature('keep',box(40,0,41,1)),feature('removed',box(40,0,41,1)),feature('version',box(60,0,61,1))]
  self.after=[feature('aaa-dateline',Polygon([(179,70),(-179,70),(-179,71),(179,71),(179,70)])),feature('change',box(0,0,4,1)),feature('high-latitude',box(10,0,20,80)),feature('keep',box(40,0,41,1)),feature('version',box(60,0,61,1))]
  self.before_path=self.root/'before.json';self.after_path=self.root/'after.json';put(self.before_path,{'features':self.before});put(self.after_path,{'features':self.after})
  self.bv=self.root/'before-boundaries.json';self.av=self.root/'after-boundaries.json';put(self.bv,[]);put(self.av,[{'location_id':'version','valid_from':10,'valid_to':20,'geometry':mapping(box(0,0,4,1)),'is_example':False},{'location_id':'keep','valid_from':1,'valid_to':2,'geometry':mapping(box(0,0,1,1)),'is_example':True}])
  def src(id,geo,owner='QA',start=1,end=100):return {'type':'Feature','id':id,'geometry':mapping(geo),'properties':{'name':'A' if owner=='QA' else 'B','wikidata':owner,'valid_from':start,'valid_to':end}}
  source_features=[src('keep-source',box(40,0,41,1)),src('left',box(0,0,1.2,1)),src('right',box(1.2,0,2.5,1)),src('tail',box(2.5,0,4,1),owner='QB',end=50),src('overlap',box(2,0,4,1),owner='QB',start=50),src('half',box(0,0,2,1),start=100,end=150),src('full',box(0,0,4,1),start=150,end=200),src('dateline',Polygon([(179,70),(-179.5,70),(-179.5,71),(179,71),(179,70)])),src('north',box(10,40,20,80)),src('south',box(10,0,20,40),owner='QB')]
  self.pi={'url':'https://example.org/test-only','records':[{'id':f['id'],'chunk':'part.json','valid_from':f['properties']['valid_from'],'valid_to':f['properties']['valid_to']} for f in source_features]};put(self.source/'index.json',self.pi);put(self.source/'part.json',{'features':source_features})
  self.old_rows=[['change',[[1,100,0,0,1]]],['keep',[[1,100,0,0,0]]],['removed',[[1,100,0,0,0]]],['version',[]]]
  evidence=[[0,1,1,[[0,1]],[0],0],[0,1,1,[[0,1]],[1,2],0]]
  part=m.write_gzip(self.old/'compact-part-0.json.gz',self.old_rows);part['locations']=4;ep=m.write_gzip(self.old/'evidence-0.json.gz',evidence)
  before_dict=m.feature_snapshot(self.before_path);bh=m.published_footprint_hash(before_dict);self.helpers=m.exact_helpers(self.old,{'execution_algorithms':entries,'inputs':{'algorithm_sha256':''.join(e['sha256'] for e in entries)}});_,bvh,_=m.boundary_versions(self.bv,self.helpers.canonical,before_dict)
  self.index={'version':2,'locations':4,'intervals':3,'parts':[part],'evidence_parts':[ep],'evidence_records':2,'owner_ids':['owner:QA','owner:QB'],'labels':['A'],'source_ids':['keep-source','left','right'],'statuses_order':['derived','disputed','no-majority','unknown'],'statuses':{'derived':3},'entities':{'owner:QA':{'id':'owner:QA','name':'A'},'owner:QB':{'id':'owner:QB','name':'B'}},'valid_from':-3000,'valid_to':2025,'footprints_sha256':bh,'inputs':{'footprints_sha256':bh,'boundary_versions':bvh,'algorithm_sha256':''.join(e['sha256'] for e in entries),'cliopatria/index.json':m.sha(self.source/'index.json'),'cliopatria/part.json':m.sha(self.source/'part.json')},'execution_algorithms':entries,'source':'Synthetic fixture only','source_url':'https://example.org/test-only'}
  put(self.old/'index.json',self.index);self.receipt=self.root/'receipt.json';self.refresh_receipt()
 def tearDown(self):self.tmp.cleanup()
 def refresh_receipt(self):
  before=m.feature_snapshot(self.before_path);after=m.feature_snapshot(self.after_path);_,_,bv=m.boundary_versions(self.bv,self.helpers.canonical,before);_,_,av=m.boundary_versions(self.av,self.helpers.canonical,after);_,changed,removed,_=m.classify(before,after,bv,av,self.helpers.canonical);added=set(after)-set(before)
  put(self.receipt,{'before_footprints_sha256':m.published_footprint_hash(before),'after_footprints_sha256':m.published_footprint_hash(after),'changed_ids':sorted(changed-added),'removed_ids':sorted(removed),'added_ids':sorted(added),'relationships':[{'before_ids':['removed'],'after_ids':['aaa-dateline','high-latitude'],'kind':'test-only-replacement'}] if removed else [],'source_evidence':[{'url':'https://example.org/test-only','source_sha256':m.sha(self.source/'part.json')}]})
 def run_prepare(self):return m.prepare(self.before_path,self.after_path,self.bv,self.av,self.receipt,self.old,self.source,self.root/'stage')
 def test_same_polity_union_strict_majority_conflicts_and_gaps(self):
  self.run_prepare();index,rows,e=read_rows(self.root/'stage');change=rows['change'];status=lambda r:index['statuses_order'][r[3]]
  self.assertEqual([(r[0],r[1],status(r)) for r in change],[(1,50,'derived'),(50,100,'disputed'),(100,150,'no-majority'),(150,200,'derived')])
  self.assertAlmostEqual(e[change[0][4]][1],.625,places=11);self.assertEqual(change[0][2],0);self.assertIsNone(change[1][2]);self.assertIsNone(change[2][2]);self.assertEqual(e[change[2][4]][1],.5)
  self.assertFalse(any(r[0]<=-100<r[1] or r[0]<=2024<r[1] for r in change));self.assertEqual(rows['version'][0][:4],[10,20,0,0]);self.assertEqual(e[rows['version'][0][4]][5],1)
 def test_latitude_and_antimeridian_not_planar_area(self):
  self.run_prepare();index,rows,e=read_rows(self.root/'stage');self.assertEqual(rows['aaa-dateline'][0][2],0);self.assertAlmostEqual(e[rows['aaa-dateline'][0][4]][1],.75,places=11)
  self.assertEqual(rows['high-latitude'][0][2],1);self.assertGreater(e[rows['high-latitude'][0][4]][1],.6)
 def test_unchanged_bytes_dictionary_prefix_archive_and_sorted_index_mapping(self):
  before_hash=m.sha(self.old/'index.json');self.run_prepare();index,rows,e=read_rows(self.root/'stage');self.assertEqual(rows['keep'],self.old_rows[1][1]);self.assertEqual(index['owner_ids'],self.index['owner_ids']);self.assertEqual(index['labels'][:1],self.index['labels']);self.assertEqual(index['source_ids'][:3],self.index['source_ids']);self.assertEqual(e[:2],m.load(self.old/'evidence-0.json.gz'));self.assertEqual(m.sha(self.old/'index.json'),before_hash)
  archive=m.load(self.root/'stage/archive-index.json');old={id:r for p in archive['parts'] for id,r in m.load(self.root/'stage'/p['path'])};self.assertEqual(old['removed'],self.old_rows[2][1]);self.assertEqual(old['change'],self.old_rows[0][1]);self.assertNotIn('removed',rows)
  mapping=m.load(self.root/'stage/location-identity-map.json.gz');keep=next(r for r in mapping if r[0]=='keep');self.assertEqual(keep[1:4],[1,3,'reused']);self.assertEqual(index['incremental_preparation']['reused_locations'],1)
 def test_unsafe_source_algorithm_before_date_and_receipt_changes_are_rejected(self):
  for kind in ['source','algorithm','before-dates','receipt']:
   with self.subTest(kind=kind):
    if kind=='source':p=self.source/'part.json';saved=p.read_bytes();p.write_bytes(saved+b' ')
    elif kind=='algorithm':p=self.old/'algorithms/exact/majority.py';saved=p.read_bytes();p.write_bytes(saved+b'\n')
    elif kind=='before-dates':p=self.bv;saved=p.read_bytes();put(p,[['keep',1,2,mapping(box(40,0,41,1))]])
    else:p=self.receipt;saved=p.read_bytes();r=m.load(p);r['changed_ids']=[];put(p,r)
    with self.assertRaises(ValueError):self.run_prepare()
    self.assertFalse((self.root/'stage').exists());p.write_bytes(saved)
 def test_no_geometry_change_reuses_complete_original_part_bytes(self):
  put(self.after_path,{'features':copy.deepcopy(self.before)});put(self.av,[]);self.refresh_receipt();result=self.run_prepare();self.assertEqual(result['incremental_preparation']['source_records_scanned'],0);self.assertEqual(result['incremental_preparation']['derived_intervals'],0);self.assertEqual(m.sha(self.root/'stage'/result['parts'][0]['path']),self.index['parts'][0]['sha256']);self.assertEqual(result['parts'][0]['locations'],4)
 def test_undeclared_geometry_and_ambiguous_dated_footprints_are_rejected(self):
  original=self.av.read_bytes()
  for rows in [[{'location_id':'version','valid_from':10,'valid_to':20,'geometry':mapping(box(0,0,4,1))}], [['version',0,20,mapping(box(0,0,4,1))]], [['version',10,20,mapping(box(0,0,4,1))],['version',15,30,mapping(box(0,0,4,1))]]]:
   put(self.av,rows)
   with self.assertRaises(ValueError):self.run_prepare()
   self.assertFalse((self.root/'stage').exists())
  self.av.write_bytes(original);r=m.load(self.receipt);r['added_ids']=[];put(self.receipt,r)
  with self.assertRaises(ValueError):self.run_prepare()
 def test_original_identity_cannot_be_inherited_from_a_positional_index(self):
  rows=copy.deepcopy(self.old_rows);rows[1][0]='some-other-ID';part=m.write_gzip(self.old/'compact-part-0.json.gz',rows);part['locations']=4;self.index['parts']=[part];put(self.old/'index.json',self.index)
  with self.assertRaisesRegex(ValueError,'identity coverage'):self.run_prepare()
  self.assertFalse((self.root/'stage').exists())
 def test_standalone_cli_writes_only_the_requested_stage(self):
  command=[sys.executable,str(ROOT/'scripts/prepare-ownership-incremental.py'),'--before',str(self.before_path),'--after',str(self.after_path),'--before-boundaries',str(self.bv),'--after-boundaries',str(self.av),'--receipt',str(self.receipt),'--ownership',str(self.old),'--source',str(self.source),'--output',str(self.root/'stage')]
  completed=subprocess.run(command,check=True,capture_output=True,text=True);receipt=json.loads(completed.stdout.strip().splitlines()[-1]);self.assertEqual(receipt['source_records_scanned'],10);self.assertEqual(receipt['reused_intervals'],1);self.assertTrue((self.root/'stage/index.json').exists())
 def test_runtime_compiler_decodes_appended_evidence_without_renumbering(self):
  self.run_prepare();spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/prepare-ownership-runtime.py');runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime);compiled=runtime.prepare(self.root/'stage',self.root/'runtime');bucket=next(b for b in compiled['buckets'] if b['valid_from']<=10<b['valid_to']);body=m.load(self.root/'runtime'/bucket['path']);r=next(rows for part in body['parts'] for id,rows in part if id=='keep')[0];self.assertEqual(body['evidence'][r[4]],[0,1,1,[[0,1]],[0],0])
if __name__=='__main__':unittest.main()
