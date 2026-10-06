"""Pinned exact-face proposal; exclusive outputs, never installs geography."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import shapely
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity

from exact_arrangement import point, inside_ring, signed_area, export_rings
from exact_faces_v2 import arrange, boundaries, validate_noding
from exact_collinear_v3 import split_exact_walk, reduce_ring

ROOT = Path(__file__).resolve().parents[3]
PREFIX = Path(__file__).resolve().parent.relative_to(ROOT).as_posix()
INPUT_COMMIT = '06bf4087bf5aec0e7071830ba61e99105f2c3697'
STAGED = 'coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json'
SOURCE_PACKET = 'coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/evidence-quality.json'
SOURCE_HELPER = 'coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py'
TARGETS = {'IRN': 'gb:IRN:ADM2:26516999B17111396986996',
           'PAK': 'gb:PAK:ADM2:60131773B78019453337506'}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def read(commit, path):
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Immutable commit required')
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + path])
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('Whole input exceeds evidence bound')
    return raw


def descriptor(commit, path, raw):
    return {'commit': commit, 'path': path, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'}


def rings(geometry):
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    result = []
    for polygon in polygons:
        for ring in polygon:
            if ring[0] != ring[-1]:
                raise ValueError('Unclosed original ring')
            result.append([point(p) for p in ring[:-1]])
    return result


def classify(p, values):
    states = [inside_ring(p, ring) for ring in values]
    if None in states:
        raise ValueError('Face witness lies on a classification boundary')
    return sum(states) % 2 == 1


def exact_area(geometry):
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    return sum(abs(signed_area([point(p) for p in polygon[0][:-1]])) -
               sum(abs(signed_area([point(p) for p in hole[:-1]])) for hole in polygon[1:])
               for polygon in polygons)


def split_rounded(original):
    """Preserve every directed edge and all zero-area rounded remnants."""
    rounded = [point((float(x), float(y))) for x, y in original]
    stack, positions, cycles = [], {}, []
    for p in rounded + rounded[:1]:
        if p in positions:
            n = positions[p]
            cycles.append(stack[n:])
            for deleted in stack[n + 1:]:
                del positions[deleted]
            stack = stack[:n + 1]
        else:
            positions[p] = len(stack)
            stack.append(p)
    if len(stack) != 1 or sum(signed_area(c) for c in cycles) != signed_area(rounded):
        raise ValueError('Rounded cycle decomposition changed area')
    original_edges = sorted(zip(rounded, rounded[1:] + rounded[:1]))
    cycle_edges = sorted(e for c in cycles for e in zip(c, c[1:] + c[:1]))
    if original_edges != cycle_edges:
        raise ValueError('Rounded cycle decomposition lost an edge')
    return cycles


def rational_rings(values):
    return [[[str(x), str(y)] for x, y in ring] for ring in values]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluation-commit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    # Refuse execution of unstaged/unpinned producer code before creating outputs.
    producer = []
    for name in ('reproduce.py', 'exact_arrangement.py', 'exact_faces_v2.py', 'exact_collinear_v3.py'):
        path = PREFIX + '/' + name
        raw = read(args.evaluation_commit, path)
        if raw != (ROOT / path).read_bytes():
            raise ValueError('Producer differs from execution pin: ' + path)
        producer.append(descriptor(args.evaluation_commit, path, raw))
    output = Path(args.out).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('Fresh owned output directory required')
    output.mkdir(parents=True, exist_ok=False)
    inputs = []

    def original(path):
        raw = read(INPUT_COMMIT, path)
        inputs.append(descriptor(INPUT_COMMIT, path, raw))
        return raw

    staged = json.loads(original(STAGED))
    if staged['subject_ids'] != list(TARGETS.values()) or len(staged['baseline']) != 11:
        raise ValueError('Unexpected exact scope')
    packet = json.loads(original(SOURCE_PACKET))
    sys.path.insert(0, str(ROOT / 'scripts'))
    namespace = {'__name__': 'pinned_source_helper', '__file__': str(ROOT / SOURCE_HELPER)}
    exec(compile(original(SOURCE_HELPER), SOURCE_HELPER, 'exec'), namespace)
    sources = {}
    for country, index, relation in [('IRN', 0, 6555069), ('PAK', 3, 3229274)]:
        entry = next(f for f in packet['sources'][index]['files'] if f['path'].endswith('full.json'))
        raw = original(entry['path'])
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Reviewed original source bytes differ')
        geometry, _ = namespace['assemble_osm_boundary'](json.loads(raw), relation)
        sources[country] = mapping(geometry)
    baseline = {f['id']: f['geometry'] for f in staged['baseline']}
    component = staged['component']['geometry']
    polygon_rings = {**{'old:' + k: rings(g) for k, g in baseline.items()},
                     **{'source:' + k: rings(g) for k, g in sources.items()},
                     'component': rings(component)}
    bounds = shape(component).bounds
    segments = []
    for label, values in polygon_rings.items():
        for ring in values:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if label.startswith('source:') and (max(a[0], b[0]) < bounds[0] or
                    min(a[0], b[0]) > bounds[2] or max(a[1], b[1]) < bounds[1] or min(a[1], b[1]) > bounds[3]):
                    continue
                segments.append((a, b))
    arrangement = arrange(segments)
    noding = validate_noding(segments, arrangement, bbox_reference=True)
    labels, records = [], []
    original_areas = {k: Fraction(0) for k in baseline}
    component_area = Fraction(0)
    for n, (_, area, witness) in enumerate(arrangement['faces']):
        before = [k for k in baseline if classify(witness, polygon_rings['old:' + k])]
        within = classify(witness, polygon_rings['component'])
        named = [k for k in sources if classify(witness, polygon_rings['source:' + k])] if within and not before else []
        after = before or ([TARGETS[named[0]]] if within and len(named) == 1 else [])
        for owner in before:
            original_areas[owner] += area
        if within:
            component_area += area
        labels.append(after)
        records.append({'face': n, 'before': before, 'after': after, 'component': within,
                        'source_labels': named, 'exact_area': str(area),
                        'witness': [str(v) for v in witness],
                        'rings': rational_rings(arrangement['face_rings'][n])})
    if any(original_areas[k] != exact_area(g) for k, g in baseline.items()) or component_area != exact_area(component):
        raise ValueError('Full original/component exact area reconstruction failed')
    candidates, cycles, summaries = {}, {}, {}
    for owner in TARGETS.values():
        walks = boundaries(arrangement, labels, owner)
        assigned_area = sum(area for (_, area, _), owners in zip(arrangement['faces'], labels) if owner in owners)
        if sum(signed_area(r) for r in walks) != assigned_area:
            raise ValueError('Owned boundary differs from assigned exact faces')
        retained, certificates = [], []
        for walk in walks:
            for original in split_exact_walk(walk):
                reduced, removed = reduce_ring(original)
                rounded = split_rounded(reduced)
                certificates.append({'original': rational_rings([original])[0],
                                     'removed_collinear_vertices': removed,
                                     'rounded_cycles': rational_rings(rounded),
                                     'zero_area_cycles': [i for i, c in enumerate(rounded) if signed_area(c) == 0]})
                retained.extend(c for c in rounded if signed_area(c) != 0)
        candidate = export_rings(retained)
        geometry = shape(candidate)
        if not geometry.is_valid:
            raise ValueError('Rejected rounded derivative: ' + explain_validity(geometry))
        candidates[owner], cycles[owner] = candidate, certificates
        summaries[owner] = {'valid_native': True, 'exact_assigned_area': str(assigned_area),
                            'retained_cycles': len(retained),
                            'zero_area_rounded_walks': sum(len(c['zero_area_cycles']) for c in certificates)}
    result = {'version': 1, 'input_commit': INPUT_COMMIT, 'producer': producer, 'inputs': inputs,
              'runtime': {'python': sys.version.split()[0], 'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
              'original_areas': {k: str(v) for k, v in original_areas.items()},
              'component_exact_area': str(component_area), 'noding': noding,
              'segments': len(segments), 'faces': len(records), 'summaries': summaries,
              'unknown_component_faces': [r['face'] for r in records if r['component'] and not r['before'] and not r['after']],
              'lost_face_memberships': sum(len(set(r['before']) - set(r['after'])) for r in records),
              'new_multiple_faces': sum(len(r['after']) > 1 and len(r['before']) <= 1 for r in records),
              'limits': ['Unapproved modern-reference proposal, no installation or territorial/historical assertion.',
                         'Exact rational topology retained; Float64 derivative has explicit rounding/remnant records.',
                         'Source authority, identity/date and physical water remain independently assessed; no nearest fill.']}
    for name, value in [('partition.json', {'records': records, 'cycles': cycles}),
                        ('candidates.json', candidates), ('report.json', result)]:
        raw = encode(value)
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('Output exceeds evidence bound')
        with (output / name).open('xb') as stream:
            stream.write(raw)
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'summaries': summaries,
                      'unknown_faces': result['unknown_component_faces'], 'noding': noding}))


if __name__ == '__main__':
    main()
