"""Run real raw rasterization, land assignment and water composition together."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import ogr

from map_build.build import Pipeline, pin, write
from map_build.core.rle import open_grid, row
from map_build.land import test_seeds as fixtures
from map_build.water.test_build import selection as water_selection


class EndToEndTests(unittest.TestCase):
    def test_raw_sources_through_final_grid_and_resume(self):
        fixtures.SeedBuildTests.setUp(self)
        self.root = self.root.resolve()
        raw = self.root / 'raw'
        raw.mkdir()
        rectangles = [(-112.5, 0, -67.5, 22.5), (45, 0, 90, 22.5)]
        features = []
        for west, south, east, north in rectangles:
            features.append(dict(type='Feature', properties={}, geometry=dict(
                type='Polygon', coordinates=[[[west, south], [east, south],
                                            [east, north], [west, north], [west, south]]])))
        coastline = write(raw / 'coast.geojson', dict(type='FeatureCollection', features=features))
        lake = bytes(ogr.CreateGeometryFromWkt(
            'POLYGON ((0 80,5 80,5 85,0 85,0 80))').ExportToWkb())
        table = pa.Table.from_pylist([dict(id='water', subtype='lake', **{'class': 'lake'},
            sources=[dict(property='', dataset='OpenStreetMap')], geometry=lake)])
        table = table.replace_schema_metadata({b'geo': json.dumps(dict(primary_column='geometry',
            columns=dict(geometry=dict(encoding='WKB')))).encode()})
        shard = raw / 'water.parquet'
        pq.write_table(table, shard)
        manifest = write(raw / 'manifest.json', dict(file_count=1, files=[dict(
            path=shard.name, sha256=pin(shard)['sha256'])]))
        selected = water_selection()
        bindings = selected['domains']['water']['category_bindings']
        bindings.extend([dict(entity_id=707, physical_class='land', code=77),
                         dict(entity_id=707, physical_class='water', code=123)])
        for policy in selected['domains']['water']['policies']:
            if 'tie_rules' in policy['definition']:
                policy['definition']['tie_rules']['priority_entity_ids'] = [81, 42, 707]
        self.domain['category_bindings'] = bindings
        self.domain['land_baseline_policy']['tie_tolerance_metres'] = '0.00001'
        selected['domains'].update(mainland=self.domain, regional=dict(
            features=[], affiliations=[], category_bindings=bindings))
        selected['revisions'] = dict(mainland='test', regional='test', water='test', ocean='test')
        selection = write(raw / 'selection.json', selected)
        config = dict(schema='worldatlas-end-to-end-pipeline-v1', input_root=str(self.root),
            selection_notes='Independent synthetic integration',
            sources=dict(
                land_config=dict(json=dict(schema='land-raster-candidate-v1', grid=vars(self.grid),
                    selection_notes='test', strip_rows=4, minimum_free_bytes=0,
                    land=[dict(dataset=str(coastline), files=[pin(coastline)], where=None)])),
                water_config=dict(json=dict(schema='water-shard-candidate-v2', grid=vars(self.grid),
                    tile_size=8, minimum_free_bytes=0, selection_notes='test',
                    policy=dict(method='overture-inland-subtype-v1'))),
                raw_manifest=pin(manifest)),
            physical_controls=dict(minimum_free_bytes=0, max_parallel_shards=1),
            seed_controls=dict(strip_rows=4, workers=1),
            land_controls=dict(numerical_guard_metres=1000, chunk_columns=1024))
        request = write(raw / 'config.json', config)
        output = self.root / 'run'
        report = Pipeline(request, output, selection=selection).run()
        self.assertEqual(report['status'], 'complete')
        with open_grid(Path(report['final']['rows']['path']).parent, self.grid) as data:
            ends, codes = row(data, 3, self.grid.width)
            labels = codes[ends.searchsorted([3, 4, 10, 11], side='right')]
            self.assertEqual(labels.tolist(), [301, 999, 77, 77])
        with patch('map_build.physical.build.run', side_effect=AssertionError('completed build repeated')):
            resumed = Pipeline(request, output, resume=True).run()
        self.assertEqual(resumed, report)
