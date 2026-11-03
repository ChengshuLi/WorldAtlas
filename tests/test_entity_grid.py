import json
import struct
import tempfile
import unittest
from pathlib import Path
from scripts.build_entity_grid import build

class EntityGridTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.rows = self.root / 'rows'; self.runs = self.root / 'runs'
        self.rows.write_bytes(struct.pack('<3I', 0, 3, 5))
        self.runs.write_bytes(struct.pack('<10I', 2, 1, 4, 17, 6, 7, 3, 7, 6, 1))
        self.meta = {'width': 6, 'height': 2,
            'entity_registry': {'schema_version': 'worldatlas-entity-registry-v1', 'revision': 'r1', 'status': 'draft',
                'entities': [{'id': 42, 'name':'Africa', 'level':'continent', 'parent_id':None}, {'id': 77, 'name':'Atlantic Ocean', 'level':'continent', 'parent_id':None}]},
            'categories': [{'id':1,'entity_id':42,'physical_class':'water'},
                {'id':17,'entity_id':42,'physical_class':'land'},
                {'id':7,'entity_id':77,'physical_class':'water'}]}

    def test_stable_ids_merge_land_and_water_and_preserve_cells(self):
        out = self.root / 'out'; result = build(self.meta, self.rows, self.runs, out)
        self.assertEqual(struct.unpack('<3I', (out/'rows.u32le').read_bytes()), (0, 2, 4))
        self.assertEqual(struct.unpack('<8I', (out/'runs.u32le').read_bytes()), (4,42,6,77,3,77,6,42))
        self.assertEqual(result['registry_revision'], 'r1')
        self.assertEqual(json.loads((out/'manifest.json').read_text()), result)
        with self.assertRaises(FileExistsError): build(self.meta, self.rows, self.runs, out)

    def test_rejects_mismatched_identity_or_unbound_code(self):
        self.meta['categories'][1]['entity_id'] = 77
        with self.assertRaisesRegex(ValueError, 'same entity'): build(self.meta,self.rows,self.runs,self.root/'one')
        self.meta['categories'][1]['entity_id'] = 42
        self.runs.write_bytes(struct.pack('<10I', 2, 1, 4, 99, 6, 7, 3, 7, 6, 1))
        with self.assertRaisesRegex(ValueError, 'unbound'): build(self.meta,self.rows,self.runs,self.root/'two')

if __name__ == '__main__': unittest.main()
