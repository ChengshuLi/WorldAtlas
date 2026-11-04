import hashlib,json,tempfile,unittest
from pathlib import Path
import migrate_land_checkpoint as migrate

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make_legacy(p):
 old=p/'old.py';new=p/'new.py';old.write_text('legacy script\n');new.write_text('corrected script\n')
 payload={'schema':'simple-v2-query-checkpoint-v1','identity':{'code_sha256':{'build_land_checkpoint.py':digest(old),'other':'unchanged'}},'next_row':42,'queries':55,'best':{2:{17:123.,18:124.},10:{19:5.25},101:{22:900.}}}
 raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode();cp=p/'legacy.json';cp.write_text(json.dumps({'payload':payload,'sha256':hashlib.sha256(raw).hexdigest()}));return cp,old,new
class PortableMigration(unittest.TestCase):
 def test_populated_legacy_conversion(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cp,old,new=make_legacy(p);before=cp.read_bytes();dest=p/'migrated.json';result=migrate.migrate(cp,old,new,dest);self.assertEqual(cp.read_bytes(),before)
   a=json.loads(before)['payload'];e=json.loads(dest.read_bytes());b=e['payload'];body=json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False).encode();self.assertEqual(e['sha256'],hashlib.sha256(body).hexdigest());self.assertEqual(a['best'],b['best']);self.assertEqual((a['queries'],a['next_row']),(b['queries'],b['next_row']));self.assertEqual(b['identity']['code_sha256']['build_land_checkpoint.py'],digest(new));self.assertEqual(result['destination_checkpoint_sha256'],digest(dest));self.assertTrue(Path(str(dest)+'.migration.json').is_file())
 def test_corrupt_or_wrong_script_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cp,old,new=make_legacy(p);e=json.loads(cp.read_text());e['payload']['best']['2']['17']=321;cp.write_text(json.dumps(e))
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):migrate.migrate(cp,old,new,p/'bad')
   self.assertFalse((p/'bad').exists())
   cp,old,new=make_legacy(p);old.write_text('changed')
   with self.assertRaisesRegex(ValueError,'script hash mismatch'):migrate.migrate(cp,old,new,p/'bad2')
   self.assertFalse((p/'bad2').exists())
 def test_existing_output_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cp,old,new=make_legacy(p);dest=p/'exists';dest.write_text('keep')
   with self.assertRaises(FileExistsError):migrate.migrate(cp,old,new,dest)
   self.assertEqual(dest.read_text(),'keep')
if __name__=='__main__':unittest.main()
