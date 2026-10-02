"""Meaningful regression checks for physical identity and dry-land correction."""
import importlib.util, pathlib, tempfile, unittest
from shapely.geometry import shape

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cook_prepare', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class CookPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='worldatlas-cook-test-')
        cls.out = pathlib.Path(cls.temp.name) / 'prepared'
        prepare.prepare(cls.out)
        cls.patch = prepare.read(cls.out / 'candidate-patch.json')
        cls.archive = prepare.read(cls.out / 'originals-and-records.json.gz')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_names_are_corrected_without_moving_physical_ids(self):
        original = {f['id']: f for f in self.archive['locations']}
        updates = {f['id']: f for f in self.patch['existing_location_updates']}
        for identifier, name in [('COK-4951', 'Manuae'), ('COK-4956', 'Aitutaki')]:
            self.assertEqual(updates[identifier]['properties']['name'], name)
            self.assertEqual(updates[identifier]['geometry'], original[identifier]['geometry'])
            self.assertEqual(updates[identifier]['properties']['parent_id'], original[identifier]['properties']['parent_id'])
        self.assertFalse(self.patch['history_transfer'])
        self.assertTrue(all(not row['historical_claims_transfer'] for row in self.patch['operations']))

    def test_manihiki_preserves_identity_but_excludes_sourced_water(self):
        row = self.patch['source_checks']['Manihiki']
        self.assertEqual(row['coastline_land_rings'], 84)
        self.assertEqual(len(row['explicit_water_ways']), 2)
        self.assertGreater(row['water_mask_removed_m2'], 20000)
        self.assertEqual(row['old_outline_retained_dry_land_m2'], 0)
        self.assertGreater(row['old_outline_reclassified_nonland_m2'], 1800000)
        self.assertEqual(self.patch['existing_location_updates'][2]['id'], 'COK-4961')

    def test_palmerston_is_distinct_complete_unknown_attribute_territory(self):
        feature = self.patch['added_features'][0]
        self.assertEqual(feature['id'], prepare.PALMERSTON)
        self.assertEqual(len(self.patch['added_parent_chain']), 5)
        self.assertNotIn('reference_owner', feature['properties'])
        self.assertEqual(self.patch['source_checks']['Palmerston']['coastline_land_rings'], 34)
        self.assertTrue(all(not row['Palmerston_positive_area_predecessors'] for row in self.patch['archived_identity_scan']))
        self.assertFalse(self.patch['publication_ready'])
        self.assertFalse(self.archive['live_private_records_checked'])
        grid = prepare.read(self.out / 'grid-check.json')
        self.assertEqual({r['name']: r['whole_dry_land_cell_centers'] for r in grid['rows']}['Palmerston'], 144)
        self.assertEqual({r['name']: r['whole_dry_land_cell_centers'] for r in grid['rows']}['Manihiki'], 229)

    def test_source_masks_and_durable_creation_proof_match_exact_geometry(self):
        footprints = {f['id']: shape(f['geometry']) for f in prepare.read(self.out / 'source-dry-land.geojson.gz')['features']}
        for name, row in self.patch['source_checks'].items():
            self.assertTrue(footprints[name].is_valid)
            for water in row['explicit_water_ways']:
                self.assertLessEqual(prepare.area(footprints[name].intersection(shape(water['geometry']))), .001)
        proof = self.patch['creation_proof_after_name_crosswalk']
        raw_source = self.out / proof['source']['path']
        self.assertEqual(prepare.sha(raw_source), proof['source']['sha256'])
        self.assertEqual(prepare.read(raw_source)['features'][0]['geometry'], self.patch['added_features'][0]['geometry'])
        self.assertNotIn('COK-4956', proof['identity_review']['same_name_existing_ids'])

    def test_replay_is_byte_reproducible_and_never_reuses_output(self):
        another = pathlib.Path(self.temp.name) / 'replay'
        prepare.prepare(another)
        self.assertEqual({p.name: p.read_bytes() for p in self.out.iterdir()},
                         {p.name: p.read_bytes() for p in another.iterdir()})
        with self.assertRaisesRegex(ValueError, 'fresh output'):
            prepare.prepare(self.out)


if __name__ == '__main__':
    unittest.main()
