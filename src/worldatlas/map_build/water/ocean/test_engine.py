import json, struct, tempfile, unittest
from pathlib import Path
from worldatlas.map_build.water.ocean import engine as r


class OceanRunnerTests(unittest.TestCase):
    def snapshot(self):
        features=[]
        partitions=[]
        for i,lon in enumerate((-90,0,90)):
            features.append(dict(feature_id=f'line{i}',geometry=dict(type='LineString',coordinates=[[lon,90],[lon,-90]])))
            partitions.append(dict(id=f'p{i}',method='ocean_barrier',feature_id=f'line{i}',side_a_entity_id=100+i,side_b_entity_id=101+i))
        seeds=[]
        bindings=[]
        for i,lon in enumerate((-157.5,-67.5,22.5,112.5)):
            ident=f'area{i}'
            features.append(dict(feature_id=ident,geometry=dict(type='Polygon',coordinates=[[[lon-10,60],[lon+10,60],[lon+10,80],[lon-10,80],[lon-10,60]]])))
            seeds.append(dict(entity_id=100+i,feature_id=ident,witness=[lon,67.5]))
            bindings.append(dict(code=7+i,entity_id=100+i,physical_class='water'))
        return dict(features=features,partitions=partitions,ocean_seeds=seeds,category_bindings=bindings,
                    policies=[dict(kind='ocean_fill',definition=dict(connectivity=4,wrap_longitude=False,
                        barrier_tie_rule='left-of-oriented-route',unseeded_policy='report-only'))])

    def test_source_area_seed_requires_its_imported_polygon_and_strict_interior(self):
        s=self.snapshot()
        r.load_config(s,8,4)
        for lon in [-167.5,-130]:
            s['ocean_seeds'][0]['witness'][0]=lon
            with self.assertRaisesRegex(ValueError,'inside'):
                r.load_config(s,8,4)
        s['ocean_seeds'][0]['witness'][0]=-157.5
        s['features']=[f for f in s['features'] if f['feature_id']!='area0']
        with self.assertRaisesRegex(ValueError,'missing source area'):
            r.load_config(s,8,4)

    def grid(self, root, name, code):
        rows = root / (name + '-rows')
        runs = root / (name + '-runs')
        rows.write_bytes(struct.pack('<5I', 0, 1, 2, 3, 4))
        runs.write_bytes(struct.pack('<8I', *[x for _ in range(4) for x in (8, code)]))
        return rows, runs

    def test_full_synthetic_partition_and_pins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pr, pu = self.grid(root, 'phys', 1)
            rr, ru = self.grid(root, 'prefill', 0)
            out = root / 'out'
            r.run(
                self.snapshot(),
                'a' * 64,
                pr,
                pu,
                rr,
                ru,
                out,
                8,
                4,
                {'physical_rows_sha256': r.sha(pr)},
                2,
            )
            summary = json.loads((out / 'run-summary.json').read_text())
            layer = json.loads((out / 'ocean-layer-manifest.json').read_text())
            self.assertEqual(summary['unseeded_cell_count'], 0)
            self.assertEqual(summary['assigned_cells_total'], 32)
            self.assertEqual(len(layer['tiles']), 2)
            self.assertGreaterEqual(summary['processing_elapsed_seconds'], 0)
            rows = [
                json.loads(x)
                for t in layer['tiles']
                for x in (out / t['span_file']['path']).read_text().splitlines()
            ]
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(
                    [(s['start'], s['end'], s['code'], s['member_id']) for s in row['spans']],
                    [(0, 2, 7, '100'), (2, 4, 8, '101'), (4, 6, 9, '102'), (6, 8, 10, '103')],
                )
            with self.assertRaises(FileExistsError):
                r.run(self.snapshot(), 'a' * 64, pr, pu, rr, ru, out, 8, 4, {})

    def test_final_recheck_runs_after_export_before_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pr, pu = self.grid(root, 'phys', 1)
            rr, ru = self.grid(root, 'prefill', 0)
            out = root / 'out'

            def after_export():
                self.assertTrue((out / 'ocean-layer-manifest.json').is_file())
                raise ValueError('input changed during export')

            with self.assertRaisesRegex(ValueError, 'input changed during export'):
                r.run(
                    self.snapshot(),
                    'a' * 64,
                    pr,
                    pu,
                    rr,
                    ru,
                    out,
                    8,
                    4,
                    {},
                    2,
                    pre_summary=after_export,
                )
            self.assertFalse((out / 'run-summary.json').exists())

    def test_invalid_divider_and_seed_bindings_fail(self):
        s=self.snapshot()
        s['partitions'][0]['feature_id']='missing'
        with self.assertRaisesRegex(ValueError,'missing source feature'):
            r.load_config(s,8,4)
        s=self.snapshot()
        s['category_bindings'][0]['code']=8
        with self.assertRaises(ValueError):r.load_config(s,8,4)
        s=self.snapshot()
        s['partitions'][0]['side_a_entity_id']=999
        with self.assertRaisesRegex(ValueError,'two seeded entities'):r.load_config(s,8,4)

    def test_south_grid_extension_uses_grid_dimensions_and_requires_a_meridian(self):
        s=self.snapshot()
        for feature in s['features'][:3]:feature['geometry']['coordinates'][-1][1]=-89
        for partition in s['partitions']:partition['extend_to_south_grid_edge']=True
        paths=r.load_config(s,8,4)[1]
        self.assertTrue(all(path[-1][1]==4 for path in paths))
        s['features'][0]['geometry']['coordinates'][-1][1]=0
        with self.assertRaisesRegex(ValueError,'final grid row'):r.load_config(s,8,4)
        s['features'][0]['geometry']['coordinates'][-1]=[-89,-89]
        with self.assertRaisesRegex(ValueError,'meridian'):r.load_config(s,8,4)

    def test_unseeded_component_is_reported_not_invented(self):
        s=self.snapshot()
        s['features']=[f for f in s['features'] if f['feature_id'].startswith('area')]
        s['partitions']=[]
        for i,lon in enumerate((-108,-36,36,108)):
            s['features'].append(dict(feature_id=f'line{i}',geometry=dict(type='LineString',coordinates=[[lon,90],[lon,-54]])))
            s['partitions'].append(dict(id=f'p{i}',method='ocean_barrier',feature_id=f'line{i}',side_a_entity_id=100+i,side_b_entity_id=100+(i+1)%4))
        for i,lon in enumerate((-162,-90,-18,54)):
            s['ocean_seeds'][i]['witness']=[lon,72]
            s['features'][i]['geometry']['coordinates']=[[[lon-10,60],[lon+10,60],[lon+10,80],[lon-10,80],[lon-10,60]]]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,code in [('p',1),('c',0)]:
                (root/(name+'r')).write_bytes(struct.pack('<5I',0,1,2,3,4))
                (root/(name+'u')).write_bytes(struct.pack('<8I',*[v for _ in range(4) for v in (10,code)]))
            r.run(s,'a'*64,root/'pr',root/'pu',root/'cr',root/'cu',root/'out',10,4,{},2)
            summary=json.loads((root/'out/run-summary.json').read_text())
            self.assertEqual(summary['unseeded_cell_count'],8)
            self.assertEqual(summary['assigned_cells_total'],32)


if __name__=='__main__':unittest.main()
