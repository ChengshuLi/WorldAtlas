"""Analytic controls for unchanged binary64 geometry, closure and export failures."""
import copy
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.exact_predicates import (DiagnosticError, MAX_SEGMENTS, context, diagnose,
                                      point, prepare_geometry, geometry_state, ring_state, segment_certificate, read_inputs, original_segment)

CONTEXT = {'crs': 'local:test-cartesian', 'axis_order': ['x', 'y'],
           'numeric_vintage': 'analytic-binary64-v1', 'coordinate_encoding': 'IEEE754-binary64'}


def polygon(rings):
    return {'type': 'Polygon', 'coordinates': rings}


def square(a=0, b=0, c=4, d=4):
    return polygon([[[a, b], [c, b], [c, d], [a, d], [a, b]]])


def segment(identifier, endpoints):
    return {'id': identifier, 'endpoints': endpoints, 'context': copy.deepcopy(CONTEXT)}


class Predicates(unittest.TestCase):
    def test_analytic_interior_exterior_vertices_and_half_open_ray(self):
        rings = prepare_geometry(square())[0]
        for p, expected in [([2, 2], 'inside'), ([5, 2], 'outside'), ([0, 2], 'boundary'),
                            ([4, 4], 'boundary'), ([-1, 4], 'outside'), ([5, 0], 'outside')]:
            self.assertEqual(ring_state(point(p), rings[0]), expected)
        # Exact rational analytic probe is allowed internally; source/query API stays binary64.
        self.assertEqual(ring_state((F(1, 3), F(1, 3)), rings[0]), 'inside')
        self.assertEqual(point([0.1, 0.2])[0], F(3602879701896397, 36028797018963968))

    def test_holes_order_multipart_islands_and_tiny_positive_area(self):
        geom = polygon(square()['coordinates'] + square(1, 1, 3, 3)['coordinates'])
        for reversed_rings in (geom, polygon([list(reversed(r)) for r in geom['coordinates']])):
            prepared = prepare_geometry(reversed_rings)
            for p, expected in [([.5, .5], 'inside'), ([2, 2], 'outside'), ([1, 2], 'boundary')]:
                self.assertEqual(geometry_state(point(p), prepared), expected)
        mp = {'type': 'MultiPolygon', 'coordinates': [square()['coordinates'], square(8, 8, 9, 9)['coordinates']]}
        self.assertEqual(geometry_state(point([8.5, 8.5]), prepare_geometry(mp)), 'inside')
        tiny = square(0, 0, 2**-500, 2**-500)
        self.assertEqual(geometry_state(point([2**-501, 2**-501]), prepare_geometry(tiny)), 'inside')

    def test_invalid_and_unsupported_originals_never_repaired(self):
        geometries = [polygon([[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]]),
                      polygon([[[0, 0], [1, 0], [0, 0], [0, 1], [0, 0]]]),
                      polygon([[[0, 0], [1, 0], [1, 0], [0, 1], [0, 0]]]),
                      polygon([[[0, 0], [1, 0], [0, 1], [1, 1]]]),
                      polygon([[[0, 0], [1, 0], [2, 0], [0, 0]]]),
                      polygon(square()['coordinates'] + square(8, 8, 9, 9)['coordinates']),
                      polygon(square()['coordinates'] + square(1, 1, 3, 3)['coordinates'] + square(1.5, 1.5, 2, 2)['coordinates']),
                      {'type': 'Point', 'coordinates': [0, 0]}, {'type': 'LineString', 'coordinates': [[0, 0], [1, 1]]}, None]
        for geom in geometries:
            original = copy.deepcopy(geom)
            with self.assertRaises(DiagnosticError): prepare_geometry(geom)
            self.assertEqual(geom, original)
        for coordinate in [float('nan'), float('inf'), True, '0', 2**53 + 1]:
            with self.assertRaises(DiagnosticError): point([coordinate, 0])
        with self.assertRaises(DiagnosticError): prepare_geometry(polygon([[[0, 0]] * (MAX_SEGMENTS + 2)]))
        touching = {'type': 'MultiPolygon', 'coordinates': [square()['coordinates'], square(4, 4, 5, 5)['coordinates']]}
        with self.assertRaises(DiagnosticError) as caught: prepare_geometry(touching)
        self.assertEqual(caught.exception.status, 'unsupported')

    def test_non_dyadic_triangle_counterexample_and_exact_dyadic_control(self):
        a, b = segment('diagonal', [[0, 0], [1, 1]]), segment('gap-edge', [[0, 1], [1, -1]])
        certificate = segment_certificate(a, b)
        self.assertEqual(certificate['status'], 'export-incidence-failure')
        self.assertEqual(certificate['reason'], 'nonrepresentable-crossing')
        self.assertFalse(certificate['exactly_representable_binary64'])
        self.assertEqual(certificate['exact_node'], [{'numerator': '1', 'denominator': '3'}] * 2)
        self.assertEqual(certificate['exact_segment_incidence'], [True, False])
        gap = prepare_geometry(polygon([[[0, 1], [1, -1], [1, 1], [0, 1]]]))
        self.assertEqual(geometry_state(point(certificate['nearest_binary64']), gap), 'outside')
        d = segment('dyadic', [[0, 1], [1, 0]])
        exact = segment_certificate(a, d)
        self.assertEqual(exact['status'], 'exact-incidence')
        self.assertEqual(exact['nearest_binary64'], [.5, .5])
        self.assertEqual(segment_certificate(a, d, [.5, math.nextafter(.5, 1)])['reason'], 'altered-export-coordinate')
        changed = copy.deepcopy(d); changed['context']['numeric_vintage'] = 'other'
        self.assertEqual(segment_certificate(a, changed)['status'], 'unknown')
        self.assertEqual(segment_certificate(a, segment('line', [[0, 0], [0, 0]]))['status'], 'invalid')
        self.assertEqual(segment_certificate(a, segment('collinear', [[0, 0], [2, 2]]))['status'], 'unsupported')

    def build_request(self, root):
        request = {'version': 1, 'context': copy.deepcopy(CONTEXT), 'collections': {}, 'files': [],
                   'points': [{'id': name, 'xy': xy} for name, xy in [('first', [1, 1]), ('second', [3, 1]),
                       ('both', [2, 1]), ('neither', [2, 3]), ('gap-boundary', [0, 2]),
                       ('member-boundary', [1.5, 1]), ('outside', [5, 1])]]}
        for role, geometries in [('gap', [square()]), ('first', [square(.5, .5, 2.5, 2), square(.75, .75, 1.25, 1.25)]),
                                 ('second', [square(1.5, .5, 3.5, 2)])]:
            members = [role + '-' + str(i) for i in range(len(geometries))]
            doc = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': id, 'properties': {}, 'geometry': geom} for id, geom in zip(members, geometries)]}
            raw = (json.dumps(doc, sort_keys=True) + '\n').encode(); path = role + '.json'; (root / path).write_bytes(raw)
            request['collections'][role] = {'provider_id': 'fixture-' + role, 'member_ids': members}
            request['files'].append({'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                                     'context': copy.deepcopy(CONTEXT), 'provider_id': 'fixture-' + role, 'role': role})
        return request

    def test_four_classes_complete_members_boundaries_and_no_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.build_request(Path(directory)); before = copy.deepcopy(request)
            result = diagnose(directory, request); points = {p['point_id']: p for p in result['points']}
            for name, label in [('first', 'first-only'), ('second', 'second-only'), ('both', 'both'), ('neither', 'neither')]:
                self.assertEqual(points[name]['classes'], [label])
            self.assertEqual(points['first']['collections']['first']['inside_member_ids'], ['first-0', 'first-1'])
            self.assertEqual(points['gap-boundary']['status'], 'boundary')
            self.assertEqual(points['member-boundary']['status'], 'boundary')
            self.assertEqual(points['outside']['status'], 'outside-gap')
            self.assertNotIn('owner', json.dumps(result))
            self.assertEqual(request, before)
            prepared, _ = read_inputs(Path(directory), request)
            reference = {'role': 'first', 'member_id': 'first-0', 'source_sha256': request['files'][1]['sha256'],
                         'polygon_index': 0, 'ring_index': 0, 'segment_index': 0}
            resolved = original_segment(prepared, reference, CONTEXT)
            self.assertEqual(resolved['endpoints'], [[.5, .5], [2.5, .5]])
            for key, value in [('source_sha256', '0' * 64), ('segment_index', -1), ('member_id', 'missing')]:
                changed = dict(reference); changed[key] = value
                with self.assertRaises(DiagnosticError): original_segment(prepared, changed, CONTEXT)
            self.assertEqual(result['geometry_acceptance'], 'not-assessed')

    def test_byte_vertex_member_crs_vintage_and_unknown_negative_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); request = self.build_request(root)
            for key, value in [('crs', 'other'), ('numeric_vintage', 'other'), ('axis_order', ['y', 'x'])]:
                changed = copy.deepcopy(request); changed['files'][0]['context'][key] = value
                self.assertIn(diagnose(root, changed)['status'], ['unknown', 'unsupported'])
            changed = copy.deepcopy(request); changed['collections']['first']['member_ids'].pop()
            self.assertEqual(diagnose(root, changed)['reason'], 'omitted-duplicate-or-altered-member-closure')
            raw = (root / 'first.json').read_bytes(); doc = json.loads(raw)
            omitted = copy.deepcopy(doc); omitted['features'][0]['geometry']['coordinates'][0].pop(1)
            (root / 'first.json').write_text(json.dumps(omitted))
            self.assertEqual(diagnose(root, request)['reason'], 'original-byte-pin-mismatch')
            doc['features'][0]['geometry']['coordinates'][0][1][0] = 2.6
            (root / 'first.json').write_text(json.dumps(doc))
            self.assertEqual(diagnose(root, request)['reason'], 'original-byte-pin-mismatch')
            doc['features'][0]['geometry'] = None; updated = json.dumps(doc).encode(); (root / 'first.json').write_bytes(updated)
            changed = copy.deepcopy(request); changed['files'][1].update(bytes=len(updated), sha256=hashlib.sha256(updated).hexdigest())
            result = diagnose(root, changed)
            self.assertEqual(result['points'][0]['status'], 'unknown')
            self.assertEqual(result['points'][0]['collections']['first']['inside_member_ids'], ['first-1'])
            self.assertEqual(result['points'][0]['collections']['first']['unknown_member_ids'], ['first-0'])

    def test_cli_immutable_output_and_two_runs(self):
        spec = importlib.util.spec_from_file_location('cli', Path(__file__).resolve().parents[1] / 'scripts/exact-source-diagnostic.py')
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); request = self.build_request(root)
            for role, coordinates in [('gap', [[0, 1], [1, -1], [1, 1], [0, 1]]), ('first', [[0, 0], [1, 1], [0, 1], [0, 0]])]:
                file = root / (role + '.json'); doc = json.loads(file.read_bytes())
                doc['features'][0]['geometry'] = polygon([coordinates]); raw = json.dumps(doc).encode(); file.write_bytes(raw)
                descriptor = next(d for d in request['files'] if d['role'] == role)
                descriptor.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            refs = {role: {'role': role, 'member_id': role + '-0', 'source_sha256': next(d['sha256'] for d in request['files'] if d['role'] == role),
                           'polygon_index': 0, 'ring_index': 0, 'segment_index': 0} for role in ('first', 'gap')}
            request['crossings'] = [{'first': refs['first'], 'second': refs['gap']}]
            path = root / 'request.json'; path.write_text(json.dumps(request))
            one = cli.run(root, path, root / 'one.json'); two = cli.run(root, path, root / 'two.json')
            self.assertEqual(one, two); self.assertEqual((root / 'one.json').read_bytes(), (root / 'two.json').read_bytes())
            with self.assertRaises(FileExistsError): cli.run(root, path, root / 'one.json')
            self.assertEqual(json.loads((root / 'one.json').read_bytes())['crossings'][0]['status'], 'export-incidence-failure')


if __name__ == '__main__': unittest.main()
