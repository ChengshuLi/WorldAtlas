import hashlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import verify_presentation_release as v

class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        assets={}
        for key,(name,_) in v.LIMITS.items():
            data=b'{}' if name.endswith('.json') else b'// synthetic\n'
            (self.root/name).write_bytes(data)
            assets[key]=hashlib.sha256(data).hexdigest()
        self.manifest={'schema':'worldatlas-presentation-parity-manifest-v1','release_id':'fictional-release','assets':assets}
        self.path=self.root/'manifest.json'
        self.write_manifest()
        self.mock=patch.object(v,'run_checker',return_value={'original':{},'migrated':{},'report':{'full_index_equal':True,'land_leaves':1}})
        self.mock.start()
        self.addCleanup(self.mock.stop)
        self.addCleanup(self.temp.cleanup)

    def write_manifest(self):
        data=json.dumps(self.manifest,sort_keys=True).encode()
        self.path.write_bytes(data)
        self.pin=hashlib.sha256(data).hexdigest()

    def test_matching_pinned_inputs(self):
        self.assertEqual(v.verify(self.path,self.pin,self.root)['status'],'parity-verified-not-deployed')

    def test_wrong_manifest_pin_rejected(self):
        with self.assertRaisesRegex(ValueError,'manifest hash mismatch'):
            v.verify(self.path,'0'*64,self.root)

    def test_same_size_record_swap_rejected(self):
        (self.root/'presentation-records-local.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'input hash mismatch: records'):
            v.verify(self.path,self.pin,self.root)

    def test_same_size_proposal_swap_rejected(self):
        (self.root/'proposal.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError,'input hash mismatch: proposal'):
            v.verify(self.path,self.pin,self.root)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for data in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e400}'):
            with self.assertRaises(ValueError):
                v.strict_json(data)

    def test_high_precision_numbers_do_not_collapse(self):
        for raw in (b'1.00000000000000001',b'1.00000000000000002',b'9007199254740993'):
            with self.assertRaisesRegex(ValueError,'loses precision'):
                v.strict_json(raw)
        self.assertEqual(v.strict_json(b'9007199254740992'),9007199254740992)
        self.assertFalse(v.equal_json(True,1))
        self.assertTrue(v.equal_json(v.strict_json(b'1'),v.strict_json(b'1.0')))

    def test_full_parity_rejects_js_rounded_decimal(self):
        raw=b'{"coordinate":1.00000000000000001}'
        (self.root/'review-references.json').write_bytes(raw)
        self.manifest['assets']['references']=hashlib.sha256(raw).hexdigest()
        self.write_manifest()
        v.run_checker.return_value={'original':{'coordinate':1},'migrated':{'coordinate':1},'report':{'full_index_equal':True,'land_leaves':1}}
        with self.assertRaisesRegex(ValueError,'loses precision'):
            v.verify(self.path,self.pin,self.root)

    def test_failed_parity_is_rejected(self):
        v.run_checker.side_effect=ValueError('index parity failed')
        with self.assertRaisesRegex(ValueError,'index parity failed'):
            v.verify(self.path,self.pin,self.root)

    def test_sealed_descriptor_blocks_mutation(self):
        fd=v.sealed(b'test')
        try:
            flags=fcntl.fcntl(fd,v.F_GET_SEALS)
            self.assertTrue(flags & v.F_SEAL_WRITE)
            with self.assertRaises(OSError):os.write(fd,b'x')
        finally:os.close(fd)

    def test_subprocess_output_cap(self):
        proc=subprocess.Popen([sys.executable,'-c','import sys;sys.stdout.write("x"*100000)'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        with self.assertRaisesRegex(ValueError,'exceeded output limit'):
            v.collect_limited(proc,stdout_limit=1024)

if __name__=='__main__':
    unittest.main()

