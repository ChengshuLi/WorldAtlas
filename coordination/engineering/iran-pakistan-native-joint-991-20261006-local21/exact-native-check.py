"""Independent Fraction scanlines: exact partition versus native Float64 cells."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PREFIX = Path(__file__).resolve().parent.relative_to(ROOT).as_posix()


def ceiling(value):
    return -((-value.numerator) // value.denominator)


def spans(rings, latitude, size):
    intersections = []
    ties = []
    for ring in rings:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[1] > b[1]:
                a, b = b, a
            if a[1] < latitude <= b[1]:
                longitude = a[0] + (latitude - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                column = (longitude + 180) * size / 360 - F(1, 2)
                if column.denominator == 1:
                    ties.append(int(column))
                intersections.append(column)
    intersections.sort()
    if len(intersections) % 2:
        raise ValueError('Unpaired exact native scanline')
    output = []
    for a, b in zip(intersections[::2], intersections[1::2]):
        start, end = max(0, ceiling(a)), min(size, ceiling(b))
        if start < end:
            if output and output[-1][1] == start:
                output[-1][1] = end
            else:
                output.append([start, end])
    return output, ties


def selected_spans(row, owner):
    output = []
    for segment in row:
        if owner in segment['owners']:
            if output and output[-1][1] == segment['start']:
                output[-1][1] = segment['end']
            else:
                output.append([segment['start'], segment['end']])
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluation-commit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if len(args.evaluation_commit) != 40 or any(c not in '0123456789abcdef' for c in args.evaluation_commit):
        raise ValueError('Immutable execution pin required')
    inputs = []

    def read(path):
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', args.evaluation_commit + ':' + path])
        inputs.append({'commit': args.evaluation_commit, 'path': path, 'bytes': len(raw),
                       'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'})
        return raw

    producer = read(PREFIX + '/exact-native-check.py')
    if producer != Path(__file__).read_bytes():
        raise ValueError('Producer differs from execution pin')
    partition = json.loads(read(PREFIX + '/results-v1/partition.json'))
    native = json.loads(read(PREFIX + '/native-v1/native-cells.json'))
    table = read(PREFIX + '/native-v1/latitude-bytes.f64le')
    if len(table) != 262166 * 8 or hashlib.sha256(table).hexdigest() != '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23':
        raise ValueError('Normative latitude input differs')
    staged_path = 'coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json'
    staged_raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', '06bf4087bf5aec0e7071830ba61e99105f2c3697:' + staged_path])
    inputs.append({'commit': '06bf4087bf5aec0e7071830ba61e99105f2c3697', 'path': staged_path,
                   'bytes': len(staged_raw), 'sha256': hashlib.sha256(staged_raw).hexdigest(), 'hash_kind': 'file-bytes'})
    staged = json.loads(staged_raw)
    discrepancies, records, ties = [], [], []
    # Each original cycle preserves the complete exact owned boundary. Floating
    # derivatives, reduced vertices and collapsed walks are not the reference.
    for subject, certificates in partition['cycles'].items():
        rings = [[tuple(F(v) for v in p) for p in c['original']] for c in certificates]
        for row in native['rows']:
            y = row['y']
            latitude = F(struct.unpack_from('<d', table, y * 8)[0])
            ideal, row_ties = spans(rings, latitude, staged['size'])
            actual = selected_spans(row['after'], staged['owner_indices'][subject])
            records.append({'subject': subject, 'y': y, 'exact': ideal, 'rounded_native': actual})
            if ideal != actual:
                discrepancies.append(records[-1])
            if row_ties:
                ties.append({'subject': subject, 'y': y, 'columns': row_ties})
    report = {'version': 1, 'inputs': inputs, 'rows_per_subject': len(native['rows']),
              'columns_per_row': staged['size'], 'exact_subject_count': len(partition['cycles']),
              'discrepancy_rows': len(discrepancies), 'discrepancies': discrepancies, 'exact_intersection_ties': ties,
              'records': records, 'limits': ['Independent exact rational scanline check at normative cell latitudes.',
                'Cell equivalence does not assert continuous geometry equality or source/geographic approval.',
                'No new tie assignment is authorized; excluded horizontal/vertex ties need separate synthetic controls.']}
    target = Path(args.out).resolve()
    if not target.is_relative_to(ROOT / PREFIX) or target.exists():
        raise ValueError('Fresh owned output required')
    target.mkdir(parents=True, exist_ok=False)
    with (target / 'exact-native.json').open('x') as stream:
        json.dump(report, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
    print(json.dumps({'rows_per_subject': len(native['rows']), 'discrepancy_rows': len(discrepancies),
                      'exact_intersection_ties': len(ties), 'output': str(target.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
