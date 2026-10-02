"""Actual-source restoration and rejection checks; no live geography mutation."""
import copy, gzip, importlib.util, json, os, pathlib, tarfile, tempfile, unittest
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('restoration', HERE / 'produce.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASELINE = pathlib.Path(os.environ.get('WORLDATLAS_BASELINE', str(m.ROOT / 'data')))


class RestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = pathlib.Path(cls.temporary.name) / 'reproduced'
        cls.proof = m.produce(BASELINE, cls.output)
        cls.patch = m.document(cls.output / 'patch.json.gz')
        cls.old, cls.units, cls.raw_pins = m.load_baseline(BASELINE, cls.patch['baseline'])
        cls.by_id = {f['id']: f for f in cls.old}
        cls.inputs = m.document(HERE / 'source-inputs.json')
        cls.evaluation = m.ROOT / cls.inputs['evaluation_directory']

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_byte_reproducibility_and_baseline_preservation(self):
        for name in ['patch.json.gz', 'before-features.json.gz', 'creation-source.geojson', 'creation-proofs.json', 'validation.json']:
            self.assertEqual((self.output / name).read_bytes(), (HERE / 'prepared' / name).read_bytes())
        for path, expected in self.raw_pins.items():
            self.assertEqual(m.digest((BASELINE / path).read_bytes()), expected)

    def test_exact_stable_id_properties_and_49584_untouched_locations(self):
        self.assertEqual(len(self.old), 49589)
        changed = {u['location_id'] for u in self.patch['updates']}
        self.assertEqual(len(changed), 5)
        archives = {f['id']: f for f in m.document(self.output / 'before-features.json.gz')}
        for update in self.patch['updates']:
            old = self.by_id[update['location_id']]
            self.assertEqual(archives[old['id']], old)
            self.assertEqual(update['before_feature_sha256'], m.digest(m.encoded(old)))
            self.assertEqual(update['after_feature']['properties'], old['properties'])
        self.assertEqual(len(set(self.by_id) - changed), 49584)
        self.assertFalse(self.patch['historical_claims_transferred'])
        self.assertFalse(self.proof['grid_recompiled'])

    def test_every_compared_component_and_partial_scope(self):
        self.assertEqual(len(self.patch['source_proofs']), 25)
        self.assertTrue(all(r['cell_centres'] > 0 for r in self.proof['all_component_grid_centres']))
        self.assertEqual(min(r['cell_centres'] for r in self.proof['all_component_grid_centres']), 5)
        self.assertNotIn('Minamitorishima', [p['query'] for p in self.patch['source_proofs']])
        chagos = next(h for h in self.patch['holds'] if h['location_id'] == 'IOT+00?')
        self.assertIn('Peros Banhos', ' '.join(chagos['remaining']))
        self.assertFalse(self.patch['publication_ready'])

    def test_fugloy_physical_municipal_chain_and_unknown_attributes(self):
        f = self.patch['added_features'][0]
        self.assertEqual(f['id'], 'atlas:restoration:location:fugloy')
        self.assertIsNone(f['properties']['reference_owner'])
        self.assertIsNone(f['properties']['metadata']['habitation'])
        self.assertIsNone(f['properties']['metadata']['rank'])
        proof = self.patch['creation_proofs'][0]
        self.assertIn('fugloyar-municipality', proof['parent_chain'][0])
        self.assertEqual(proof['parent_chain'][1], 'framework:area:froyar:04fca3ca6320')
        self.assertNotIn('Eysturoyar', str(proof['parent_chain']))
        self.assertEqual(proof['identity_review']['archived_and_current_registry_entities_reviewed'], 85315)

    def test_named_lagoon_water_masks_are_preserved(self):
        north = next(p for p in self.patch['source_proofs'] if p['query'] == 'CocosNorth')
        self.assertGreater(north['subtracted_water_masks'], 0)
        diego = [p for p in self.patch['source_proofs'] if p['query'] == 'DiegoGarcia']
        self.assertTrue(any(any(w['id'] == '9361980' for w in p['water_lineage']) for p in diego))
        cocos = next(f for f in self.patch['existing_location_updates'] if f['id'].startswith('gb:AUS:'))
        g = m.shape(cocos['geometry'])
        self.assertGreater(sum(len(p.interiors) for p in g.geoms), 0)

    def test_source_tampering_and_water_mask_omission_rejected(self):
        plan = m.document(HERE / 'decisions.json.gz')
        candidate = next(g for g in plan['location_decisions'] if g['group_key'] == 'CocosSouth')['staged_components'][-1]
        query = next(q for q in m.document(self.evaluation / 'modern-coastline-index.json') if q['name'] == 'CocosNorth')
        with tarfile.open(self.evaluation / 'geometry-and-modern-sources.tar.gz') as archive:
            altered = copy.deepcopy(candidate)
            altered['source_xml_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'source bytes changed'):
                m.source_geometry(altered, query, archive)
            altered = copy.deepcopy(candidate)
            altered['subtracted_closed_water_rings'] = 0
            with self.assertRaisesRegex(ValueError, 'water exclusion count'):
                m.source_geometry(altered, query, archive)

    def test_wrong_baseline_pin_and_unsafe_output_rejected(self):
        pins = copy.deepcopy(self.inputs['baseline'])
        pins['hierarchy_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hierarchy changed'):
            m.load_baseline(BASELINE, pins)
        with self.assertRaisesRegex(ValueError, 'fresh and separate'):
            m.produce(BASELINE, BASELINE / 'must-not-exist')

    def test_generic_creation_contract_on_real_baseline(self):
        sys_path = str(m.ROOT / 'scripts')
        import sys
        sys.path.insert(0, sys_path)
        spec = importlib.util.spec_from_file_location('creation_validator', m.ROOT / 'scripts/validate-land-creations.py')
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        result = validator.validate({'before': self.old, 'after': self.old + self.patch['added_features'], 'units': self.units + self.patch['added_groups'], 'proofs': self.patch['creation_proofs'], 'base': str(self.output)})
        self.assertTrue(result['verified'])
        self.assertFalse(result['historical_claims_transferred'])
        self.assertEqual(len(result['creations']), 1)


if __name__ == '__main__':
    unittest.main()
