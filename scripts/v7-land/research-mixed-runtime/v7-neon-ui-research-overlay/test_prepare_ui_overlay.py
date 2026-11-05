import builtins
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import prepare_ui_overlay as ui

class ReadPinnedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'input';self.raw=b'original bytes';self.path.write_bytes(self.raw)
        self.pin=hashlib.sha256(self.raw).hexdigest()
    def test_valid_and_oversized(self):
        self.assertEqual(ui.read_pinned(self.path,self.pin,100),'original bytes')
        with self.assertRaisesRegex(ValueError,'oversized'):ui.read_pinned(self.path,self.pin,3)
    def test_inplace_mutation_fails(self):
        original_open=builtins.open
        class Mutating:
            def __init__(self,fd):self.fd=fd
            def __enter__(self):return self
            def __exit__(self,*args):return self.fd.__exit__(*args)
            def fileno(self):return self.fd.fileno()
            def read(self,n):
                with original_open(self_path,'wb') as out:out.write(b'altered bytes!')
                return self.fd.read(n)
        self_path=self.path
        def wrapped(*args,**kw):return Mutating(original_open(*args,**kw))
        with patch('builtins.open',side_effect=wrapped):
            with self.assertRaisesRegex(ValueError,'changed while reading'):ui.read_pinned(self.path,self.pin,100)
    def test_path_swap_cannot_substitute_unpinned_bytes(self):
        original_open=builtins.open
        old=self.path.with_suffix('.old');self_path=self.path
        class Swapping:
            def __init__(self,fd):self.fd=fd
            def __enter__(self):return self
            def __exit__(self,*args):return self.fd.__exit__(*args)
            def fileno(self):return self.fd.fileno()
            def read(self,n):
                os.rename(self_path,old)
                with original_open(self_path,'wb') as out:out.write(b'untrusted bytes')
                return self.fd.read(n)
        def wrapped(*args,**kw):return Swapping(original_open(*args,**kw))
        with patch('builtins.open',side_effect=wrapped):
            try: result=ui.read_pinned(self.path,self.pin,100)
            except ValueError: return  # changed metadata is also fail-closed
        self.assertEqual(result,'original bytes')
    def test_manifest_renderer_and_release_pins(self):
        manifest={'schema':'worldatlas-presentation-parity-manifest-v2','release_id':'fictional','assets':{'candidate_module':'a'*64}}
        raw=json.dumps(manifest).encode();self.path.write_bytes(raw)
        args=SimpleNamespace(manifest=self.path,manifest_sha256=hashlib.sha256(raw).hexdigest(),release_id='fictional',renderer_sha256='b'*64)
        with self.assertRaisesRegex(ValueError,'renderer does not match'):ui.build(args)
        args.release_id='different';args.renderer_sha256='a'*64
        with self.assertRaisesRegex(ValueError,'renderer does not match'):ui.build(args)
    def test_duplicate_manifest_keys_rejected(self):
        raw=b'{"schema":"first","schema":"second"}';self.path.write_bytes(raw)
        args=SimpleNamespace(manifest=self.path,manifest_sha256=hashlib.sha256(raw).hexdigest(),release_id='fictional',renderer_sha256='a'*64)
        with self.assertRaisesRegex(ValueError,'duplicate manifest key'):ui.build(args)

if __name__=='__main__':unittest.main()
