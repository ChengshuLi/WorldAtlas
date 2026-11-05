import sqlite3,struct,tempfile,unittest
from pathlib import Path
import numpy as np
import hints

def put(path,values): Path(path).write_bytes(struct.pack('<'+'I'*len(values),*values))
class HintTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);self.rows=self.p/'rows';self.runs=self.p/'runs';self.db=self.p/'work.sqlite'
  # width 8, height 3.  Root 9 is seeded, 1 and 2 are independent islands.
  put(self.rows,[0,2,4,5]);put(self.runs,[0,2,9,7,8,1, 2,4,9,4,6,2, 7,8,1])
 def tearDown(self):self.t.cleanup()
 def test_inventory_current_roots_and_witnesses(self):
  self.assertEqual(hints.inventory(self.rows,self.runs,[9],8,3,self.db),2)
  with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('select * from roots order by id').fetchall(),[(1,0,7),(2,1,4)])
 def test_missing_seed_and_existing_file_fail(self):
  with self.assertRaisesRegex(ValueError,'seed roots missing'):hints.inventory(self.rows,self.runs,[11],8,3,self.db)
  with self.assertRaises(FileExistsError):hints.inventory(self.rows,self.runs,[9],8,3,self.db)
 def test_bad_offsets_or_overlapping_rows_fail(self):
  put(self.rows,[0,2,1,5])
  with self.assertRaisesRegex(ValueError,'offset'):hints.inventory(self.rows,self.runs,[9],8,3,self.db)
  self.db.unlink();put(self.rows,[0,2,4,5]);put(self.runs,[0,3,9,2,4,1, 2,4,9,4,6,2, 7,8,1])
  with self.assertRaisesRegex(ValueError,'component row'):hints.inventory(self.rows,self.runs,[9],8,3,self.db)
 def test_hint_seed_points_and_dateline(self):
  hints.inventory(self.rows,self.runs,[9],8,3,self.db)
  # root 1 at lon 157.5 is nearer code 17 at lon -157.5 across the date line.
  reps=np.array([[0,0,0,0,17],[0,0,1,4,18]],dtype=np.uint32)
  results=list(hints.choose_hints(self.db,reps,8,3,45,90,[17,18],batch=1))
  self.assertEqual([int(x[0][0]) for x in results],[1,2]);self.assertEqual([int(x[1][0]) for x in results],[17,18])
 def test_sqlite_uri_special_chars(self):
  db=self.p/'special?#.sqlite';hints.inventory(self.rows,self.runs,[9],8,3,db)
  reps=np.array([[0,0,0,0,17],[0,0,1,4,18]],dtype=np.uint32)
  self.assertEqual(sum(len(z[0]) for z in hints.choose_hints(db,reps,8,3,45,90,[17,18])),2)
 def test_invalid_reps_and_grid_rejected(self):
  hints.inventory(self.rows,self.runs,[9],8,3,self.db)
  reps=np.array([[0,0,0,0,17]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'representatives'):list(hints.choose_hints(self.db,reps,8,3,45,90,[17,18]))
  with self.assertRaisesRegex(ValueError,'grid'):list(hints.choose_hints(self.db,reps,8,3,44,90,[17]))
  with self.assertRaisesRegex(ValueError,'representatives'):list(hints.choose_hints(self.db,reps,8,3,45,90,[17],batch=999999))
class ResolutionTests(unittest.TestCase):
 def test_current_claims_and_stale_pins(self):
  kw=dict(grid={'width':8},input_sha256={'component_rows':'a','component_runs':'b'},snapshot_sha256='s',component_manifest_sha256='m',decision_revision='d',entity_revision='e')
  r=dict(schema='mainland-witness-resolution-v1',status='selected-research-identity-claims-not-mainland-proof',publishable=False,groups=[dict(group_id='a',role='mainland',target_entity_ids=['asia'],component_id_current_generation_only=9),dict(group_id='b',role='sentinel',target_entity_ids=[],component_id_current_generation_only=2)],**kw)
  self.assertEqual(hints.seed_roots_from_resolution(r,**kw),[9])
  bad=dict(kw);bad['snapshot_sha256']='wrong'
  with self.assertRaisesRegex(ValueError,'mismatched'):hints.seed_roots_from_resolution(r,**bad)
  r['groups'][1]['component_id_current_generation_only']=9
  with self.assertRaisesRegex(ValueError,'conflicting'):hints.seed_roots_from_resolution(r,**kw)
if __name__=='__main__':unittest.main()
