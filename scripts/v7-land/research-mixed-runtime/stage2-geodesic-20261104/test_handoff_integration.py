import ast
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import witness_compare
import test_witness_compare as fixtures

HERE = Path(__file__).parent


def sha(p):
 return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def pin(path, guard=lambda:None):
 p=Path(path).resolve(strict=True); guard(); return {'path':str(p),'sha256':sha(p)}

def checked(spec, guard=lambda:None):
 guard(); p=Path(spec['path']).resolve(strict=True)
 if sha(p)!=spec['sha256']:raise ValueError('pin mismatch')
 return p

def bounded(path, limit, guard=lambda:None):
 guard(); data=Path(path).read_bytes()
 if len(data)>limit:raise ValueError('too large')
 return data

def write_json(path, obj):
 Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n')

def need(value, message):
 if not value:raise ValueError(message)

def branch(filename, function, condition):
 tree=ast.parse((HERE/filename).read_text())
 fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==function)
 node=next(x for x in ast.walk(fn) if isinstance(x,ast.If) and isinstance(x.test,ast.Name) and x.test.id==condition)
 return compile(ast.fix_missing_locations(ast.Module(body=node.body, type_ignores=[])),filename,'exec')

CREATE=branch('orchestrate_stage2.py','run','handoff')
RESUME=branch('orchestrate_stage2.py','finish_from_marker','handoff')
CORE=branch('build_stage2.py','_build','handoff_pin')

class HandoffIntegration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.work=Path(self.tmp.name).resolve()
  for name in ('requests','resolution'):(self.work/name).mkdir()
  fixture=fixtures.Compare();fixture.setUp()
  self.old_req=self.work/'original-request.json';self.old_req.write_bytes(fixtures.dump(fixture.req))
  self.original=self.work/'original-resolution.json';self.original.write_bytes(fixtures.dump(fixture.report))
  self.request=json.loads(self.old_req.read_bytes()); self.report=json.loads(self.original.read_bytes())
  self.new_code={k:format(i+1,'064x') for i,k in enumerate(sorted(self.request['code_sha256']))}
  self.rnames={k:k for k in self.new_code};self.paths={'resolution_request':self.old_req}
  self.handoff=({'resolution_sha256':sha(self.original)},{'inputs':{'resolution':pin(self.original)}})
  self.vi=SimpleNamespace(bounded_bytes=bounded)
  self.common={'verify_inputs':self.vi,'build_stage2':SimpleNamespace(pin=checked),'witness_compare':witness_compare,'pin':pin,'need':need,'work':self.work,'guard':lambda:None,'json':json,'os':os,'hashlib':hashlib,'Path':Path}
 def fake_fresh(self, req, changed=False):
  result=copy.deepcopy(self.report);result['code_sha256']=req['code_sha256'];result.pop('request_sha256')
  if changed:result['groups'][0]['component_id_current_generation_only']+=1
  return result
 def create(self):
  def run(cmd, check):
   req_path,report_path=map(Path,cmd[-2:]);req=json.loads(req_path.read_bytes());r=self.fake_fresh(req);r['request_sha256']=sha(req_path);write_json(report_path,r)
  env=dict(self.common,rr=self.old_req,rout=self.work/'resolution'/'report.json',handoff=self.handoff,pins={'resolution_request':sha(self.old_req)},code=self.new_code,rnames=self.rnames,write_json=write_json,subprocess=SimpleNamespace(run=run),sys=SimpleNamespace(executable='python3'),HERE=HERE)
  exec(CREATE,env);return env
 def resume(self, created):
  env=dict(self.common,handoff=self.handoff,recheck=created['recheck'],cfg={'inputs':{'resolution_request':pin(self.old_req)}},artifacts={'resolution_report':pin(self.work/'resolution'/'report.json')})
  exec(RESUME,env)
 def core(self,created,changed=False):
  rr=json.loads(self.old_req.read_bytes());resolver=SimpleNamespace(resolve=lambda r:self.fake_fresh(r,changed))
  env=dict(self.common,paths={'resolution_request':self.old_req,'resolution_report':self.work/'resolution'/'report.json'},rr=rr,expected_resolver=self.new_code,resolver=resolver,derived={'witness_recheck':created['recheck']})
  exec(CORE,env)
 def test_reuses_original_hash_and_resumes_and_core_rechecks(self):
  env=self.create();linked=self.work/'resolution'/'report.json'
  self.assertEqual(sha(linked),sha(self.original));self.assertEqual(os.stat(linked).st_ino,os.stat(self.original).st_ino)
  self.assertEqual(env['recheck']['comparison']['old_report_sha256'],sha(self.original));self.resume(env);self.core(env)
 def test_tampered_stored_recheck_is_rejected_on_resume(self):
  env=self.create();p=Path(env['recheck']['report']['path']);p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaisesRegex(ValueError,'pin mismatch'):self.resume(env)
 def test_comparison_binding_tampering_is_rejected(self):
  env=self.create();env['recheck']['comparison']['new_report_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'witness recheck changed'):self.resume(env)
  with self.assertRaisesRegex(ValueError,'fresh witness comparison'):self.core(env)
 def test_changed_fresh_roots_rejected_by_core(self):
  env=self.create()
  with self.assertRaisesRegex(ValueError,'resolutions differ'):self.core(env,changed=True)

if __name__=='__main__':unittest.main()
