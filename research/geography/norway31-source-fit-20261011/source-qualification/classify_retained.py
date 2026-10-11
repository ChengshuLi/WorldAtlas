"""Authenticate the complete historical Norway comparison rows; no new GIS."""
import collections
import gzip
import hashlib
import io
import json
import pathlib
import resource
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.parent.relative_to(ROOT).as_posix()
BASE = '6a99a7606b9c2d11ac8cd093610653d4cd5d1382'
PACKAGE = 'coordination/engineering/global-source-comparisons-b-20261006/source-comparisons-b-package2/'
REPORT = PACKAGE + 'verification/run-one-actual-report.json.gz'
CAP = 128 * 1024 ** 2
sha = lambda b: hashlib.sha256(b).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def classify(row):
    residual = row.get('component_minus_source_union')
    positive = [x for x in row.get('feature_intersections', [])
                if x.get('intersection', {}).get('planar_area_coordinate_units_squared', 0) > 0]
    targets = sorted({s['id'] for x in positive for s in x['binding'].get('recorded_stable_subjects', [])})
    if row['status'] == 'one-compatible-recorded-subject-uniquely-covers-component':
        disposition = 'provisional-single-owner-full-cover-needs-physical-and-current-gates'
    elif residual is None:
        disposition = 'missing-retained-union-observation'
    elif residual.get('is_empty') is False:
        disposition = 'not-fully-covered-by-retained-source-union'
    elif residual.get('is_empty') is True and len(targets) > 1:
        disposition = 'collectively-full-covered-multiple-source-subjects-needs-bounded-construction'
    elif residual.get('is_empty') is True:
        disposition = 'full-union-cover-but-single-owner-binding-unresolved'
    else:
        disposition = 'unknown-retained-union-observation'
    return {'component_id': row['component'], 'original_source_status': row['status'],
            'disposition': disposition, 'retained_union_residual_is_empty': None if residual is None else residual.get('is_empty'),
            'positive_area_source_subject_ids': targets,
            'positive_area_feature_count': len(positive),
            'unique_cover_subject': row.get('uniquely_covering_compatible_recorded_subject'),
            'cause_status': row.get('cause_status'), 'surface_status': row.get('surface_status'),
            'unknowns': row.get('unknowns', []), 'scientific_acceptance': False}

def main():
    started = time.monotonic()
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Require exact committed execution HEAD')
    control = (HERE / 'classify_retained.py').relative_to(ROOT).as_posix()
    roster_path = (HERE / 'roster.json').relative_to(ROOT).as_posix()
    pins = []
    for name in [control, roster_path, 'scripts/evidence/immutable.py']:
        raw = (ROOT / name).read_bytes()
        if raw != git('show', head + ':' + name):
            raise ValueError('Unfrozen execution input: ' + name)
        pins.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'})
    helper = git('show', head + ':scripts/evidence/immutable.py')
    ns = {'__name__': 'cohort_immutable', '__file__': str(ROOT / 'scripts/evidence/immutable.py')}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, pins)
    base.pinned_bytes(control)
    roster = json.loads(base.pinned_bytes(roster_path))
    destination = ns['NewVintage'](base, OWN + '/', vintage, ['original-comparison-rows.json', 'dispositions.json', 'receipt.json'])
    inputs = []
    def read(name, expected=None, decode=False):
        tree = git('ls-tree', '-z', BASE, '--', name).decode().rstrip('\0')
        fields, actual = tree.split('\t'); mode, kind, oid = fields.split()
        if mode != '100644' or kind != 'blob' or actual != name:
            raise ValueError('Nonordinary source product')
        size = int(git('cat-file', '-s', oid)); base.admit(BASE + ':' + name, size)
        raw = git('cat-file', 'blob', oid)
        if expected and (len(raw) != expected['bytes'] or sha(raw) != expected['sha256']):
            raise ValueError('Whole encoded comparison product changed')
        desc = {'commit': BASE, 'path': name, 'mode': mode, 'blob': oid, 'bytes': len(raw), 'sha256': sha(raw)}
        if decode:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(32 * 1024 ** 2 + 1)
            base.admit('decoded:' + BASE + ':' + name, len(raw))
            if expected and (len(raw) != expected['decoded_bytes'] or sha(raw) != expected['decoded_sha256']):
                raise ValueError('Whole decoded comparison product changed')
            desc.update(decoded_bytes=len(raw), decoded_sha256=sha(raw))
        inputs.append(desc)
        if sum(base.consumed.values()) > CAP - 4 * 1024 ** 2:
            raise ValueError('Complete metadata input/output reservation exceeded')
        return raw, desc
    raw, report_pin = read(REPORT, decode=True)
    report = json.loads(raw)
    wanted = set(roster['candidate_ids'])
    if len(wanted) != 31 or wanted.intersection(roster['previously_selected_excluded_ids']):
        raise ValueError('Wrong new-work scope')
    found = {}; source_products = {p['key']: p for p in report['source_input_products']}
    for key, expected_hash in roster['whole_source_sha256'].items():
        if source_products[key]['original_sha256'] != expected_hash:
            raise ValueError('Original product edition mismatch')
    for p in report['outputs']:
        name = pathlib.PurePosixPath(p['path']).name
        if PACKAGE + 'scientific/' + name not in roster['comparison_products']:
            continue
        raw, pin = read(PACKAGE + 'scientific/' + name, p, True)
        rows = json.loads(raw)
        if len(rows) != p['rows'] or len({r['component'] for r in rows}) != len(rows):
            raise ValueError('Wrong whole-product row coverage')
        for ordinal, row in enumerate(rows):
            cid = row['component']
            if cid not in wanted:
                continue
            if cid in found or sorted(row['source_products']) != roster['source_keys']:
                raise ValueError('Duplicate component or incompatible source product')
            membership = next(x for x in roster['original_gap_membership'] if x['component_id'] == cid)
            if row['family'] != membership['original_family_id']:
                raise ValueError('Original family identity drift')
            found[cid] = {'comparison': row, 'original_product': pin, 'ordinal': ordinal,
                          'comparison_sha256': sha(ns['canonical_json'](row)), 'original_membership': membership}
    if set(found) != wanted:
        raise ValueError('Incomplete original component comparison inventory')
    original_rows = [found[cid] for cid in roster['candidate_ids']]
    dispositions = [{**classify(r['comparison']), 'original_membership': r['original_membership'],
                     'comparison_sha256': r['comparison_sha256'], 'original_product': r['original_product'],
                     'ordinal': r['ordinal']} for r in original_rows]
    receipt = {'execution_head': head, 'baseline': BASE, 'phase': 'whole-original-administrative-row-authentication',
               'report': report_pin, 'whole_source_products': [source_products[key] for key in roster['source_keys']],
               'components': len(dispositions), 'status_counts': dict(collections.Counter(r['original_source_status'] for r in dispositions)),
               'disposition_counts': dict(collections.Counter(r['disposition'] for r in dispositions)),
               'inputs': inputs, 'logical_input_bytes': sum(base.consumed.values()),
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               'elapsed_seconds': time.monotonic() - started,
               'limits': ['No new GIS, native operator or scientific acceptance.',
                          'Recorded mixed/partial or multi-owner source observations are not irreparability claims.',
                          'Original source observation dates, physical/legal/current truth and processing cause remain unapproved.']}
    if receipt['peak_rss_bytes'] > 256 * 1024 ** 2:
        raise ValueError('Metadata process reservation exceeded')
    destination.publish({'original-comparison-rows.json': original_rows, 'dispositions.json': dispositions, 'receipt.json': receipt})
    print(json.dumps({k: receipt[k] for k in ['components', 'status_counts', 'disposition_counts', 'logical_input_bytes', 'peak_rss_bytes', 'elapsed_seconds']}))

if __name__ == '__main__':
    main()
