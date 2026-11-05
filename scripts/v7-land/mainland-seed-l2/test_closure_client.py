import tempfile,pathlib,unittest,hashlib,json
from decimal import Decimal
from closure_client import ClosureChecker
class Client(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);d=pathlib.Path(self.t.name);self.code=d/'code';self.code.mkdir();self.physical=d/'physical';self.physical.mkdir();self.work=d/'work';self.work.mkdir();self.checker=self.code/'checker.py'
  self.checker.write_text('''import sys,json,hashlib,pathlib\na=sys.argv; value=lambda flag:a[a.index(flag)+1]\np={'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':value('--geometry-sha256'),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'physical_report_sha256':'9'*64,'checker_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'contract_sha256':value('--contract-sha256')}
pathlib.Path(value('--output')).write_text(json.dumps(p))
''');self.hash=hashlib.sha256(self.checker.read_bytes()).hexdigest();self.contract=self.code/'contract.json';self.contract.write_text('{}');self.contract_hash=hashlib.sha256(self.contract.read_bytes()).hexdigest();self.points=[(Decimal('0'),Decimal('0')),(Decimal('1'),Decimal('1'))]
 def client(self):return ClosureChecker(self.checker,self.hash,self.physical,'b'*64,'c'*64,self.contract,self.contract_hash,self.work,lambda:None,10,physical_report_sha256='9'*64)
 def test_proof_checked(self):self.assertEqual(self.client()({},self.points)['status'],'valid')
 def test_changed_checker_rejected(self):
  c=self.client();self.checker.write_text('changed')
  with self.assertRaisesRegex(ValueError,'code/contract pin'):c({},self.points)
 def test_wrong_physical_proof_rejected(self):
  c=ClosureChecker(self.checker,self.hash,self.physical,'0'*64,'c'*64,self.contract,self.contract_hash,self.work,lambda:None,10,physical_report_sha256='9'*64)
  with self.assertRaisesRegex(ValueError,'proof pin'):c({},self.points)
 def test_terminal_proof_is_bound(self):
  terminal=self.code/'terminal.py';terminal.write_text("""import sys,json,hashlib,pathlib
a=sys.argv;v=lambda f:a[a.index(f)+1]
p={'schema':'physical-terminal-closure-proof-v1','status':'valid','geometry_sha256':v('--closure-sha256'),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'physical_report_sha256':'9'*64,'checker_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'support_checker_sha256':hashlib.sha256(pathlib.Path(__file__).with_name('validate_water_closure_v2.py').read_bytes()).hexdigest(),'contract_sha256':v('--contract-sha256'),'no_land_land_edge_touched':True,'start_geometry_sha256':v('--start-geometry-sha256'),'end_geometry_sha256':v('--end-geometry-sha256'),'start_endpoint':v('--start-endpoint'),'end_endpoint':v('--end-endpoint')}
pathlib.Path(v('--output')).write_text(json.dumps(p))
""");th=hashlib.sha256(terminal.read_bytes()).hexdigest();g={'type':'LineString','coordinates':[[0.,0.],[1.,1.]]};from regions import geometry_hash
  refs=[{'geometry':g,'geometry_sha256':geometry_hash(g),'endpoint':'start'},{'geometry':g,'geometry_sha256':geometry_hash(g),'endpoint':'end'}]
  c=ClosureChecker(self.checker,self.hash,self.physical,'b'*64,'c'*64,self.contract,self.contract_hash,self.work,lambda:None,10,terminal,th,physical_report_sha256='9'*64)
  self.assertEqual(c({},self.points,refs)['schema'],'physical-terminal-closure-proof-v1')
  refs[0]['geometry_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'terminal geometry'):c({},self.points,refs)
 def test_overlap_rejected(self):
  with self.assertRaisesRegex(ValueError,'overlaps'):ClosureChecker(self.checker,self.hash,self.physical,'b'*64,'c'*64,self.contract,self.contract_hash,self.physical,lambda:None,10,physical_report_sha256='9'*64)
if __name__=='__main__':unittest.main()
