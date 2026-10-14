import copy
import gzip
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source',ROOT/'scripts/qualify-source-cohort.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def row(i,level=1,parent=-1,bounds=None):
 return {'id':i,'level':level,'container':parent,'decoded_pointset_bounds':bounds or [50,50,51,51]}
def select(rows,bounds=[[0,0,1,1]],expected=None):
 parts=[{'rows':r} for r in rows]
 return m.selected_physical_metadata(parts,lambda p:b'\n'.join(json.dumps(r).encode() for r in p['rows']),bounds,
  len({r['id'] for group in rows for r in group}) if expected is None else expected)
class Metadata(unittest.TestCase):
 def test_full_scan_and_out_of_order_ancestors(self):
  rows=[[row(1),row(2,2,1)],[row(3,3,2,[0,0,1,1])]]
  self.assertEqual(set(select(rows)),{1,2,3})
  self.assertEqual(select(rows)[1],rows[0][0])
 def test_missing_parent_retained_unknown(self):
  self.assertEqual(set(select([[row(1,2,9,[0,0,1,1])]])),{1})
 def test_cycles_and_variable_depth(self):
  with self.assertRaisesRegex(ValueError,'Cyclic'):select([[row(1,2,2,[0,0,1,1]),row(2,3,1)]])
  self.assertEqual(set(select([[row(1,2,2),row(2,3,1),row(3,1,-1,[0,0,1,1])]])),{3})
  rows=[row(i,2,i+1,[0,0,1,1] if i==0 else None) for i in range(5)]+[row(5)]
  self.assertEqual(set(select([rows])),set(range(6)))
 def test_complete_count_and_empty_or_corrupt_records(self):
  with self.assertRaisesRegex(ValueError,'Incomplete'):select([[row(1)]],expected=2)
  with self.assertRaises(json.JSONDecodeError):m.selected_physical_metadata([{}],lambda p:b'broken',[],1)
 def test_original_periodic_inclusive_bbox_and_last_record_semantics(self):
  original=row(1,1,-1,[360,0,361,1]);final=row(1,1,-1,[50,50,51,51]);final['marker']='final'
  self.assertEqual(select([[original],[final]])[1],final)
  self.assertEqual(set(select([[row(1,1,-1,[1,1,2,2]),row(2,5,1,[0,0,1,1])]])),{1,2})
  self.assertEqual(set(select([[row(1,5,99,[0,0,1,1]),row(2)]])),{1})

class Native(unittest.TestCase):
 def fixture(self):
  bodies=[b'abcd',b'ef',b'ghi'];parts=[];at=0
  for i,b in enumerate(bodies):parts.append({'offset':at,'ordinal':i,'body':b});at+=len(b)
  return {'member_bytes':at,'member_sha256':hashlib.sha256(b''.join(bodies)).hexdigest(),'parts':parts}
 def test_exact_single_body_and_order(self):
  index=self.fixture();seen=[]
  body=m.physical_native_member(index,lambda p:p['body'],lambda:seen.append(True))
  self.assertIsInstance(body,bytearray);self.assertEqual(body,b'abcdefghi');self.assertEqual(len(seen),3)
 def test_late_failure_never_returns_member_for_decode(self):
  for mutation in ['offset','ordinal','hash','size','late-corrupt']:
   index=self.fixture();decoded=[]
   if mutation in ('offset','ordinal'):index['parts'][-1][mutation]+=1
   elif mutation=='hash':index['member_sha256']='0'*64
   elif mutation=='size':index['member_bytes']+=1
   else:index['parts'][-1]['body']=b'bad'
   with self.assertRaises(ValueError):
    body=m.physical_native_member(index,lambda p:p['body'],lambda:None)
    decoded.append(body)
   self.assertFalse(decoded)

class PhysicalBoundary(unittest.TestCase):
 def test_authenticated_late_corruption_refuses_before_any_geometry_decode(self):
  import numpy,shapely
  for mutation in ['encoded-hash','decoded-hash','decoded-length','whole-hash','missing-tail','offset']:
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
    root=Path(directory);(root/'data').mkdir()
    marker=root/'decoded-marker'
    method=("def decode_record(*args):\n open("+repr(str(marker))+",'w').write('called')\n").encode()
    meta=row(0,1,-1,[0,0,1,1]);meta.update(native_offset=0,native_record_bytes=9,ordinal=0,decoded_pointset_binary64_sha256='a'*64)
    metadata=gzip.compress((json.dumps(meta)+'\n').encode())
    raw_metadata=gzip.decompress(metadata)
    def part(name,body,offset,ordinal):
     encoded=gzip.compress(body);(root/'data'/name).write_bytes(encoded)
     return {'path':name,'bytes':len(encoded),'sha256':m.sha(encoded),'uncompressed_bytes':len(body),
       'uncompressed_sha256':m.sha(body),'offset':offset,'ordinal':ordinal}
    first=part('native0.gz',b'abcd',0,0);last=part('native1.gz',b'efghi',4,1)
    metadata_part=part('metadata.gz',raw_metadata,0,0)
    index={'member_bytes':9,'member_sha256':m.sha(b'abcdefghi'),'record_count':1,'parts':[first,last]}
    if mutation=='encoded-hash':last['sha256']='0'*64
    if mutation=='decoded-hash':last['uncompressed_sha256']='0'*64
    if mutation=='decoded-length':last['uncompressed_bytes']+=1
    if mutation=='whole-hash':index['member_sha256']='0'*64
    if mutation=='missing-tail':index['member_bytes']+=1
    if mutation=='offset':last['offset']+=1
    (root/'data/transport.json').write_text(json.dumps({'complete_sources':1,'entries':[{'kind':'sources','delivered':metadata_part}]}))
    (root/'data/index.json').write_text(json.dumps(index));(root/'data/comparison.py').write_bytes(method)
    (root/'data/stages.json').write_text(json.dumps([{'target':'one','consumed':{'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,0]]]}}}]))
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)
    git('init');git('add','data');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture')
    commit=git('rev-parse','HEAD').decode().strip();pins=[]
    for file in sorted((root/'data').iterdir()):
     name=file.relative_to(root).as_posix();raw=file.read_bytes();pin={'path':name,'commit':commit,'git_blob_oid':git('rev-parse',commit+':'+name).decode().strip(),'bytes':len(raw),'sha256':m.sha(raw)}
     if name.endswith('.gz'):
      descriptor=next(p for p in [metadata_part,first,last] if p['path']==file.name)
      pin.update(decoded_bytes=descriptor['uncompressed_bytes'],decoded_sha256=descriptor['uncompressed_sha256'])
     pins.append(pin)
    config={'version':1,'inputs':pins,'roles':{'stages':'data/stages.json','transport':'data/transport.json','native_index':'data/index.json','comparison':'data/comparison.py'},'metadata_prefix':'data','native_prefix':'data','resources':{'input_bytes':1000000,'output_bytes':1000000,'deadline_seconds':60},'runtime':{'python':sys.version,'numpy':numpy.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string}}
    raw=json.dumps(config).encode();(root/'config.json').write_bytes(raw)
    admission={'observed_unix_seconds':time.time(),'program_sha256':m.sha(Path(m.__file__).read_bytes()),'config_sha256':m.sha(raw),'runtime_inventory_bytes':0,'execution_reserve_bytes':0,'allowance':{'rssBytes':2147483648,'phaseBytes':2147483648}}
    (root/'admission.json').write_text(json.dumps(admission))
    with patch.object(m,'verify_runtime',return_value=None),patch.object(m,'PHYSICAL_COMPARISON_SHA',m.sha(method)):
     with self.assertRaisesRegex(ValueError,'fragment|member'):
      m.run_physical(root,root/'config.json',root/'admission.json',root/'output','coordination/engineering/test/output')
    self.assertFalse(marker.exists());self.assertFalse((root/'output').exists())

if __name__=='__main__':unittest.main()
