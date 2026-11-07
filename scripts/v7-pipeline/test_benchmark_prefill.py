import json
from pathlib import Path
import tempfile
import unittest
from benchmark_prefill import compare_prefill
from benchmark_stage import digest


class PrefillComparisonTests(unittest.TestCase):
    def fixture(self,root):
        root.mkdir();output={'run_count':1}
        for kind in ('rows','runs'):
            path=root/('prefill-'+kind+'.u32le');path.write_bytes(b'\0'*8)
            output.update({kind+'_path':path.name,kind+'_sha256':digest(path)})
        (root/'prefill-audit.json').write_text(json.dumps({'schema':'worldatlas-v7-prefill-class-rle-audit-v1',
            'status':'staged-not-published','output':output,'prefill_class_cells_by_code':{'0':1}}))

    def test_exact_outputs_and_hash_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in ('reference','candidate'):self.fixture(root/name)
            self.assertEqual(compare_prefill(root/'reference',root/'candidate')['run_count'],1)
            (root/'candidate/prefill-runs.u32le').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact hash mismatch'):
                compare_prefill(root/'reference',root/'candidate')


if __name__=='__main__':unittest.main()
