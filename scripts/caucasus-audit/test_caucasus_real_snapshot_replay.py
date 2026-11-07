"""Bounded replay against an authenticated selected-export copy, not a build.

The caller supplies a previously exported snapshot and its SHA-256 plus the
real recipe and raw files. A recipe is inserted in a temporary copy only; the
input is never mutated and this does not write to Neon or run the outer path.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

import caucasus_seed_gate as gate
from caucasus_effective_snapshot import derive_verified

REQUIRED = ('CAUCASUS_SNAPSHOT', 'CAUCASUS_SNAPSHOT_SHA256', 'CAUCASUS_RECIPE',
            'CAUCASUS_HYDRO', 'CAUCASUS_AUTHOR')


@unittest.skipUnless(all(os.getenv(k) for k in REQUIRED), 'pinned real inputs required')
class SelectedSnapshotReplay(unittest.TestCase):
    def test_selected_export_with_temporary_recipe(self):
        path = Path(os.environ['CAUCASUS_SNAPSHOT'])
        original_sha = os.environ['CAUCASUS_SNAPSHOT_SHA256']
        self.assertEqual(gate.digest(path), original_sha)
        original = json.loads(path.read_bytes())
        selected = [b for b in original['mainland_boundaries'] if b['boundary_id'] == gate.BOUNDARY]
        self.assertEqual(len(selected), 1)
        self.assertNotIn('source_assembly_v1', selected[0]['provenance'])
        old_provenance = copy.deepcopy(selected[0]['provenance'])
        recipe_path = Path(os.environ['CAUCASUS_RECIPE'])
        recipe_sha = gate.digest(recipe_path)
        self.assertEqual(recipe_sha, '59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c')
        staged = copy.deepcopy(original)
        selected_copy = next(b for b in staged['mainland_boundaries'] if b['boundary_id'] == gate.BOUNDARY)
        selected_copy['provenance']['source_assembly_v1'] = {
            'schema': 'caucasus-source-assembly-v1', 'recipe_sha256': recipe_sha,
            'recipe': json.loads(recipe_path.read_bytes())}
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'snapshot.json'
            snapshot.write_text(json.dumps(staged, sort_keys=True, separators=(',', ':'), allow_nan=False))
            staged_sha = gate.digest(snapshot)
            request = Path(temp) / 'request.json'
            request.write_text(json.dumps({'inputs': {'snapshot': {'path': str(snapshot), 'sha256': staged_sha}}},
                                          sort_keys=True, separators=(',', ':')))
            view, trace = derive_verified(request, gate.digest(request), recipe_path, recipe_sha,
                                          os.environ['CAUCASUS_HYDRO'], os.environ['CAUCASUS_AUTHOR'])
            self.assertEqual(trace['effective_snapshot']['original_snapshot_sha256'], staged_sha)
            self.assertEqual(trace['source_gate']['selected_geometry_sha256'], selected[0]['geometry_sha256'])
            self.assertEqual(trace['effective_snapshot']['derived_geometry_sha256'],
                             '2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6')
            self.assertEqual(trace['source_gate']['assembly']['comparison']['possible_changed_centers'], 0)
            derived = next(b for b in view['mainland_boundaries'] if b['boundary_id'] == gate.BOUNDARY)
            for k, v in old_provenance.items():
                self.assertEqual(derived['provenance'][k], v)
            self.assertTrue(trace['effective_snapshot']['regions'])
            self.assertEqual(gate.digest(path), original_sha)
            print(json.dumps({'input_export_sha256': original_sha, 'staged_snapshot_sha256': staged_sha,
                              'derived_geometry_sha256': derived['geometry_sha256'],
                              'regions': trace['effective_snapshot']['regions']}, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
