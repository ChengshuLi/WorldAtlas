import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import extract_seavox_feature as mod


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.root = self.base/'input'; self.root.mkdir()
        self.archive = self.root/'source.zip'
        with zipfile.ZipFile(self.archive,'w') as z:
            for ext in ('.shp','.shx','.dbf','.prj'): z.writestr('seavox'+ext, b'test')
        self.geometry = {'type':'Polygon','coordinates':[[[1,1],[2,1],[1,2],[1,1]]]}
        self.feature = {'type':'Feature','properties':{'mrgid_sr':'24063'},'geometry':self.geometry}
        self.sha = mod.digest(self.archive)
        snapshot = {'schema':'worldatlas-geography-decision-export-v1','source':'neon-export',
                    'decision_revision':{'id':'r1','entity_revision':'e1','status':'accepted'},
                    'basins':[{'id':'gulf','source_id':'seavox','source_version':'v19','source_feature_id':'24063',
                               'geometry_sha256':mod.canonical_hash(self.geometry)}],
                    'sources':[{'source_id':'seavox','version':'v19','sha256':self.sha}]}
        self.policy = self.root/'policy.json'; self.policy.write_text(json.dumps(snapshot))
        self.args = ['tool','--input-root',str(self.root),'--archive',str(self.archive),
                     '--policy',str(self.policy),'--policy-sha256',mod.digest(self.policy),
                     '--decision-id','gulf','--allow-unverified-snapshot','--out',str(self.base/'out')]

    def run_main(self, args=None):
        with patch.object(sys,'argv',args or self.args), patch.object(mod,'extract_feature',return_value=self.feature), \
             patch.object(mod.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()):
            run.return_value.stdout = 'GDAL test'; mod.main()

    def test_build_binds_hashes_and_refuses_reuse(self):
        self.run_main(); out=self.base/'out'; manifest=json.loads((out/'manifest.json').read_text())
        self.assertEqual(manifest['archive_sha256'],self.sha)
        self.assertEqual(manifest['geometry_sha256'],mod.canonical_hash(self.geometry))
        self.assertEqual(manifest['feature_file_sha256'],mod.digest(out/'source.geojson'))
        self.assertEqual(manifest['decision_id'],'gulf')
        self.assertEqual(manifest['decision_snapshot_sha256'],mod.digest(self.policy))
        with self.assertRaises(FileExistsError): self.run_main()

    def test_mismatched_decision_geometry_fails_before_output(self):
        self.feature['geometry']={'type':'Polygon','coordinates':[[[0,0],[1,0],[0,1],[0,0]]]}
        with self.assertRaisesRegex(ValueError,'does not match'): self.run_main()
        self.assertFalse((self.base/'out').exists())

    def test_archive_hash_and_safe_members(self):
        with self.assertRaisesRegex(ValueError,'hash mismatch'): mod.validate_archive(self.archive,'0'*64)
        unsafe=self.root/'unsafe.zip'
        with zipfile.ZipFile(unsafe,'w') as z: z.writestr('../x.shp','bad')
        with self.assertRaisesRegex(ValueError,'unsafe'): mod.validate_archive(unsafe,mod.digest(unsafe))

    def test_feature_filter_rejects_sql(self):
        with self.assertRaisesRegex(ValueError,'digits only'): mod.extract_feature(self.archive,"1' OR 1=1")

    def test_snapshot_must_explicitly_be_test_only(self):
        args=[x for x in self.args if x!='--allow-unverified-snapshot']
        with self.assertRaisesRegex(ValueError,'not implemented'): self.run_main(args)


if __name__ == '__main__': unittest.main()
