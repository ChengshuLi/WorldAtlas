import json
import os
from pathlib import Path
import tempfile
import unittest
import hashlib
from copy import deepcopy

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.map_build.inputs.selection import read_selection, read_saved, validate_bindings


class BindingTests(unittest.TestCase):
    def setUp(self):
        bindings = [
            dict(code=301, entity_id=81, physical_class='land'),
            dict(code=999, entity_id=42, physical_class='land'),
            dict(code=4321, entity_id=81, physical_class='water'),
        ]
        self.selection = dict(
            schema='worldatlas-input-selection-v1',
            domains={
                name: dict(category_bindings=deepcopy(bindings))
                for name in ('mainland', 'regional', 'water', 'ocean')
            },
        )
        self.selection['domains']['water'].update(features=[], basins=[])

    def test_reordered_rows_and_different_registry_names_keep_the_same_meanings(self):
        for name, domain in self.selection['domains'].items():
            domain['entity_revision'] = {'id': name}
            domain['category_bindings'].reverse()
        validate_bindings(self.selection['domains'])

    def test_saved_replay_preserves_legacy_document_metadata(self):
        selected = dict(self.selection, documents=[dict(
            source_id='saved-construction', version='1', document_text=' {"a": 1}\n',
            sha256='a' * 64, size_bytes=10,
        )])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'
            path.write_text(json.dumps(selected))
            self.assertEqual(read_saved(path), selected)

    def test_replay_rejects_swapped_entity_meanings_in_every_stage(self):
        for name in self.selection['domains']:
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as directory:
                selected = deepcopy(self.selection)
                bindings = selected['domains'][name]['category_bindings']
                bindings[0]['entity_id'], bindings[1]['entity_id'] = (
                    bindings[1]['entity_id'],
                    bindings[0]['entity_id'],
                )
                path = Path(directory) / 'selection.json'
                path.write_text(json.dumps(selected))
                with self.assertRaisesRegex(ValueError, 'category bindings differ'):
                    read_saved(path)

    def test_physical_classes_and_missing_rows_are_part_of_the_mapping(self):
        for change in ('class', 'missing'):
            with self.subTest(change=change):
                selected = deepcopy(self.selection)
                bindings = selected['domains']['regional']['category_bindings']
                if change == 'class':
                    bindings[1]['physical_class'] = 'water'
                else:
                    bindings.pop()
                with self.assertRaisesRegex(ValueError, 'category bindings differ'):
                    validate_bindings(selected['domains'])

    def test_duplicate_codes_or_entity_classes_cannot_hide_a_disagreement(self):
        for duplicate in (
            dict(code=301, entity_id=42, physical_class='water'),
            dict(code=123, entity_id=81, physical_class='land'),
        ):
            with self.subTest(binding=duplicate):
                selected = deepcopy(self.selection)
                selected['domains']['regional']['category_bindings'].append(duplicate)
                with self.assertRaisesRegex(ValueError, 'duplicate category bindings'):
                    validate_bindings(selected['domains'])


@unittest.skipUnless(
    os.environ.get('WORLDATLAS_TEST_DATABASE_URL'), 'requires disposable PostgreSQL'
)
class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ['WORLDATLAS_TEST_DATABASE_URL']
        self.writer = psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.writer.close)
        self.addCleanup(self.remove)
        self.writer.execute(
            "INSERT INTO atlas.geographic_entity_ids(id,color_rgb) VALUES (970000001,'#123456')"
        )
        self.writer.execute(
            "INSERT INTO atlas.entity_registry_revisions VALUES ('__selection_entities')"
        )
        self.writer.execute(
            "INSERT INTO atlas.geographic_entities(revision,id,name,level) "
            "VALUES ('__selection_entities',970000001,'Selected entity','continent')"
        )
        self.writer.execute(
            "INSERT INTO atlas.decision_revisions VALUES ('__selection_water','__selection_entities','{}')"
        )

    def remove(self):
        self.writer.execute(
            "DELETE FROM atlas.decision_revisions WHERE revision='__selection_water'"
        )
        self.writer.execute(
            "DELETE FROM atlas.geographic_entities WHERE revision='__selection_entities'"
        )
        self.writer.execute(
            "DELETE FROM atlas.entity_registry_revisions WHERE revision='__selection_entities'"
        )
        self.writer.execute('DELETE FROM atlas.geographic_entity_ids WHERE id=970000001')

    def test_later_queries_keep_the_same_view_when_another_worker_commits(self):
        writer = self.writer

        class ConcurrentEditCursor(psycopg.Cursor):
            def execute(self, query, *args, **kwargs):
                self.domain = isinstance(query, str) and query.startswith('WITH')
                return super().execute(query, *args, **kwargs)

            def fetchone(self):
                row = super().fetchone()
                if self.domain:
                    writer.execute(
                        "UPDATE atlas.geographic_entity_ids SET color_rgb='#ABCDEF' WHERE id=970000001"
                    )
                return row

        with psycopg.connect(self.url, cursor_factory=ConcurrentEditCursor) as reader:
            result = read_selection(reader, {'water': '__selection_water'})
            self.assertEqual(reader.info.transaction_status, psycopg.pq.TransactionStatus.IDLE)
        self.assertEqual(
            result['registry_colors']['__selection_entities'],
            [{'entity_id': 970000001, 'color_rgb': '#123456'}],
        )
        self.assertEqual(
            writer.execute(
                'SELECT color_rgb FROM atlas.geographic_entity_ids WHERE id=970000001'
            ).fetchone()[0],
            '#ABCDEF',
        )

    def test_saved_replay_keeps_old_values_after_an_edit(self):
        with psycopg.connect(self.url) as database:
            selected = read_selection(database, {'water': '__selection_water'})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'
            path.write_text(json.dumps(selected))
            self.writer.execute(
                "UPDATE atlas.geographic_entity_ids SET color_rgb='#ABCDEF' WHERE id=970000001"
            )
            self.assertEqual(read_saved(path, selected['revisions']), selected)
            with self.assertRaisesRegex(ValueError, 'different geographic revisions'):
                read_saved(path, {'water': 'different'})

    def test_missing_revision_is_rejected(self):
        with psycopg.connect(self.url) as database:
            with self.assertRaisesRegex(ValueError, 'missing'):
                read_selection(database, {'water': 'missing'})

    def test_live_selection_rejects_conflicting_registry_bindings(self):
        with self.writer.transaction():
            self.writer.execute("INSERT INTO atlas.geographic_entity_ids(id) VALUES (970000002)")
            self.writer.execute(
                "INSERT INTO atlas.geographic_entities(revision,id,name,level) "
                "VALUES ('__selection_entities',970000002,'Second entity','continent')"
            )
            self.writer.execute(
                "INSERT INTO atlas.entity_registry_revisions VALUES ('__selection_alternate')"
            )
            self.writer.execute(
                "INSERT INTO atlas.geographic_entities(revision,id,name,level) "
                "SELECT '__selection_alternate',id,name,level FROM atlas.geographic_entities "
                "WHERE revision='__selection_entities'"
            )
            self.writer.execute(
                "INSERT INTO atlas.decision_revisions VALUES "
                "('__selection_regional','__selection_alternate','{}')"
            )
            self.writer.execute(
                "INSERT INTO atlas.review_category_bindings VALUES "
                "('__selection_entities',301,970000001,'land'),"
                "('__selection_entities',999,970000002,'land'),"
                "('__selection_alternate',999,970000001,'land'),"
                "('__selection_alternate',301,970000002,'land')"
            )
        try:
            with psycopg.connect(self.url) as reader:
                with self.assertRaisesRegex(ValueError, 'category bindings differ'):
                    read_selection(
                        reader, {'water': '__selection_water', 'regional': '__selection_regional'}
                    )
        finally:
            with self.writer.transaction():
                self.writer.execute(
                    "DELETE FROM atlas.decision_revisions WHERE revision='__selection_regional';"
                    "DELETE FROM atlas.review_category_bindings "
                    "WHERE revision IN ('__selection_entities','__selection_alternate');"
                    "DELETE FROM atlas.geographic_entities WHERE revision='__selection_alternate';"
                    "DELETE FROM atlas.entity_registry_revisions WHERE revision='__selection_alternate';"
                    "DELETE FROM atlas.geographic_entities "
                    "WHERE revision='__selection_entities' AND id=970000002;"
                    "DELETE FROM atlas.geographic_entity_ids WHERE id=970000002"
                )

    def test_regional_rules_are_optional_and_all_selected_source_links_are_frozen(self):
        with psycopg.connect(self.url) as database:
            result = read_selection(database, {'regional': '__selection_water'})
        self.assertEqual(result['regional_partitions'], [])
        try:
            with self.writer.transaction():
                for ident in ('__line_source', '__policy_source'):
                    self.writer.execute(
                        'INSERT INTO atlas.source_assets '
                        '(source_id,version,title,provider,source_uri,license_name,license_uri,'
                        'attribution,r2_bucket,r2_key,sha256,size_bytes) '
                        "VALUES (%s,'1','Test','Test','test:source','Test','test:license',"
                        "'Test','test',%s,%s,1)",
                        (ident, ident + '.json', 'a' * 64),
                    )
                geometry = dict(type='LineString', coordinates=[[0, 1], [0, -1]])
                checksum = hashlib.sha256(
                    json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
                ).hexdigest()
                for ident in ('a', 'b'):
                    self.writer.execute(
                        'INSERT INTO atlas.geographic_line_observations '
                        '(line_id,source_id,source_version,geometry,geometry_sha256,coordinate_reference,provenance) '
                        "VALUES (%s,'__line_source','1',%s,%s,'OGC:CRS84','{}')",
                        ('__selection_' + ident, Jsonb(geometry), checksum),
                    )
                    self.writer.execute(
                        'INSERT INTO atlas.regional_island_rule_sets '
                        '(revision,rule_set_id,enabled,line_id,definition,evidence) '
                        "VALUES ('__selection_water',%s,true,%s,%s,'{}')",
                        (
                            ident,
                            '__selection_' + ident,
                            Jsonb({'sources': [{'source_id': '__policy_source', 'version': '1'}]}),
                        ),
                    )
            with psycopg.connect(self.url) as database:
                result = read_selection(database, {'regional': '__selection_water'})
            self.assertEqual(
                [rule['rule_set_id'] for rule in result['regional_partitions']], ['a', 'b']
            )
            self.assertEqual(
                {source['source_id'] for source in result['raw_sources']},
                {'__line_source', '__policy_source'},
            )
        finally:
            self.writer.execute(
                "DELETE FROM atlas.regional_island_rule_sets WHERE revision='__selection_water'"
            )
            self.writer.execute(
                "DELETE FROM atlas.geographic_line_observations WHERE line_id IN ('__selection_a','__selection_b')"
            )
            self.writer.execute(
                "DELETE FROM atlas.source_assets WHERE source_id IN ('__line_source','__policy_source')"
            )

    def test_geometry_and_source_metadata_survive_separate_record_reads(self):
        geometry = {'type': 'Point', 'coordinates': [12.25, 45.5]}
        digest = hashlib.sha256(
            json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
        ).hexdigest()
        self.writer.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes) '
            "VALUES ('__selection_raw','1','Test','Test','test:source','Test','test:license',"
            "'Test','test','source.geojson',%s,1)",
            ('a' * 64,),
        )
        try:
            self.writer.execute(
                'INSERT INTO atlas.decision_features '
                '(revision,feature_id,source_id,source_version,source_feature_id,geometry_sha256,'
                'geometry,coordinate_reference,evidence) '
                "VALUES ('__selection_water','point','__selection_raw','1','provider-point',%s,%s,'OGC:CRS84','{}')",
                (digest, Jsonb(geometry)),
            )
            document = '{ "method": "selected_vector_features", "basis": "Selected source — côte" }'
            self.writer.execute('INSERT INTO atlas.construction_records(source_id,version,document) VALUES (%s,%s,%s::jsonb)',
                                ('__selected_construction','1',document))
            self.writer.execute("UPDATE atlas.decision_features SET construction_id='__selected_construction',construction_version='1' "
                                "WHERE revision='__selection_water'")
            with psycopg.connect(self.url) as database:
                result = read_selection(database, {'water': '__selection_water'})
            feature = result['domains']['water']['features'][0]
            self.assertEqual(feature['geometry'], geometry)
            self.assertEqual(feature['geometry_sha256'], digest)
            self.assertEqual(feature['source_feature_id'], 'provider-point')
            self.assertEqual(result['raw_sources'][0]['source_id'], '__selection_raw')
            self.assertEqual(result['schema'], 'worldatlas-input-selection-v2')
            self.assertEqual(result['construction_records'], [dict(
                source_id='__selected_construction', version='1', document=json.loads(document))])
            self.writer.execute(
                'INSERT INTO atlas.construction_records(source_id,version,document) VALUES (%s,%s,%s::jsonb)',
                ('__selected_construction','2',json.dumps(json.loads(document), sort_keys=True, indent=2)),
            )
            self.writer.execute("UPDATE atlas.decision_features SET construction_version='2' "
                                "WHERE revision='__selection_water'")
            with psycopg.connect(self.url) as database:
                reordered = read_selection(database, {'water': '__selection_water'})
            self.assertEqual(reordered['construction_records'][0]['document'], result['construction_records'][0]['document'])
            self.assertEqual(reordered['construction_records'][0]['version'], '2')
            with self.assertRaises(psycopg.errors.ForeignKeyViolation), self.writer.transaction():
                self.writer.execute("DELETE FROM atlas.construction_records WHERE source_id='__selected_construction'")

        finally:
            self.writer.execute(
                "DELETE FROM atlas.decision_features WHERE revision='__selection_water'"
            )
            self.writer.execute("DELETE FROM atlas.construction_records WHERE source_id='__selected_construction'")
            self.writer.execute("DELETE FROM atlas.source_assets WHERE source_id='__selection_raw'")
