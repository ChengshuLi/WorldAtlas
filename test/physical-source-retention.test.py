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
if __name__=='__main__':unittest.main()
