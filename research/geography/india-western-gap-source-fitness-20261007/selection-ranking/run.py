#!/usr/bin/env python3
"""Reconstruct the source-fitness family denominator and rank from pinned outputs."""
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
BASELINE = '64770c1a8c82c3626344d3d5ce322cdcb839ea2e'
ROUTING = 'coordination/engineering/global-actionability-routing-20261007/results/'
SOURCE_SLICE = ROUTING + 'land-source-fitness-000.bin.gz'
ROUTING_REPORT = ROUTING + 'report.json'
PRIORITY_CODE = 'scripts/physical_gap_priority.py'
TARGET = 'gap-source-batch:ff84042d9e10553c98925ed5'
ORDER = ('source_locator_readiness', 'coordination_complexity', 'measured_impact')
SHARDS = [ROUTING + 'families-%03d.bin.gz' % i for i in range(14)]
SUBJECTS = [
    'physical-component:000f8ceae5d2a99223959081d563a10b524519680b495e98e0ab26acf5feafe7',
    'physical-component:0b0f4f8da263777fd7e59ebfd90ba6545811dd8014832cf1a91fc10ad2a78194',
    'physical-component:158d29fe97181ce35bcbee0548005905634f6dfae7083fde2346a0f8a1d88bf5',
    'physical-component:16a15562778f813213a723286dc05b997683ea5d6c88e421bd533dda812875da',
    'physical-component:300746aaaeeeaf86e3782f48d123d367aab071fabc57d87028d897ed444184b5',
    'physical-component:36ffb10735d8d7d402912f989ff500524a686e86a2f636efc100acc56b9d2ba0',
    'physical-component:4c9fc7c98e4c74fba00b685e964f1082726a32488d14987811702efabc6947ac',
    'physical-component:777631d5e6656693b99bbebff66787db117ac0e7595fb8b80d5d032ac0659038',
    'physical-component:87d5810b83156c3f47cd05e5221d064dbf80622f98706a593ec08548d1588364',
    'physical-component:9bfcc12c85f301e0745895e459345d8f81a1abe87b317188d1fc4c82c5989477',
    'physical-component:9db43066a4445eede1df1316d18dd6ff40393734a09a720207c5f14685487a2c',
    'physical-component:a1238cf0d19f4b0a045b41418061764b2ffa076128c4d7718a4a0b6693be1d7c',
    'physical-component:a5caa084567455808fecd8aec8f98eff8eb24e41498c28eff9b740962c505401',
    'physical-component:c9ab9d9b1f31057510a02095d979ec7126cd62fd780793d5c2bba7a775759989',
    'physical-component:d5085885c61def27a4994e0603af5328dc208c342ad9787a1b4d1f98e45cfb0b',
    'physical-component:d8a7c45330ea4f423c70a95cd8bb8a510225b04bcea292ffb5574e19d323d1ca',
    'physical-component:e547c85631bb512b40659a4fbb669c704379bd7a2422ac1cf6ed837c2af171b9',
    'physical-component:f39a89a7d4dd30b99fcd8f6f98b0394c5a17d4e406144262e63c2d0b549df746',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':'), allow_nan=False) + '\n').encode()


def git_blob(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', BASELINE + ':' + path])


def descriptor(path):
    raw = git_blob(path)
    d = {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}
    if path.endswith('.gz'):
        unpacked = gzip.decompress(raw)
        d['uncompressed_bytes'] = len(unpacked)
        d['uncompressed_sha256'] = sha(unpacked)
    return d, raw


def main():
    priority_desc, priority_raw = descriptor(PRIORITY_CODE)
    family_parts, raw_map = [], {}
    for path in SHARDS:
        d, raw = descriptor(path)
        family_parts.append(d)
        raw_map[path] = gzip.decompress(raw)
    slice_desc, slice_raw = descriptor(SOURCE_SLICE)
    route_desc, route_raw = descriptor(ROUTING_REPORT)
    files = [priority_desc, route_desc, slice_desc] + family_parts
    pins = {'priority_order_code': priority_desc['sha256'],
            'routing_report': route_desc['sha256'],
            'source_fit_slice': slice_desc['sha256']}
    pin_files = {'priority_order_code': PRIORITY_CODE,
                 'routing_report': ROUTING_REPORT,
                 'source_fit_slice': SOURCE_SLICE}
    for i, d in enumerate(family_parts):
        key = 'routing_families_%03d' % i
        pins[key] = d['sha256']
        pin_files[key] = d['path']

    # Authenticate the order directly from the pinned source code's declared constant.
    code = priority_raw.decode('utf-8')
    expected = "ORDER_NAMES = ('source_locator_readiness', 'coordination_complexity', 'measured_impact')"
    if expected not in code:
        raise ValueError('Pinned priority code ordering differs from the selection rule')

    source_rows = json.loads(gzip.decompress(slice_raw))
    if not isinstance(source_rows, list) or not all(isinstance(row, dict) for row in source_rows):
        raise ValueError('Source-fitness routing slice is not a JSON array of rows')
    families = {row.get('family') for row in source_rows}
    if None in families or len(families) != 711 or len(source_rows) != 1005:
        raise ValueError('Unexpected source-fitness slice size or family universe')
    target_rows = [row for row in source_rows if row.get('family') == TARGET]
    if len(target_rows) != 2 or len({row.get('component') for row in target_rows}) != 2:
        raise ValueError('Selected family source-fitness prerequisite roster mismatch')

    all_bytes = b''.join(raw_map[path] for path in SHARDS)
    records = [json.loads(line) for line in all_bytes.splitlines() if line.strip()]
    rank_fields = {}
    for record in records:
        family = record.get('id')
        fine = record.get('original_fine_family')
        if family in families and isinstance(fine, dict):
            rank = fine.get('best_rank')
            if not isinstance(rank, dict) or not all(isinstance(rank.get(k), int) for k in ORDER):
                raise ValueError('Missing family-best priority tuple: ' + str(family))
            if family in rank_fields:
                raise ValueError('Duplicate family record: ' + family)
            rank_fields[family] = rank
    if set(rank_fields) != families:
        raise ValueError('Family records do not cover the complete source-fitness universe')
    tuples = {family: tuple(rank_fields[family][key] for key in ORDER) for family in families}
    if len(set(tuples.values())) != len(families):
        raise ValueError('Family-best priority tuple ties need an explicit tie-break policy')
    ordered = sorted(families, key=lambda family: tuples[family])
    selected_rank = ordered.index(TARGET) + 1
    if selected_rank != 8:
        raise ValueError('Selected family reconstructed rank differs from issue selection claim')
    if len(target_rows) != 2 or {row['component'] for row in target_rows} != set(SUBJECTS).intersection({row['component'] for row in source_rows}):
        raise ValueError('Selected family witness roster does not match pinned issue subjects')

    input_set = {'baseline_commit': BASELINE,
                 'priority_order': list(ORDER),
                 'source_fit_slice_sha256': slice_desc['sha256'],
                 'family_shard_sha256': {d['path']: d['sha256'] for d in family_parts},
                 'priority_order_code_sha256': priority_desc['sha256'],
                 'routing_report_sha256': route_desc['sha256']}
    selection_sha = sha(canonical(input_set))
    report = {
        'version': 1,
        'status': 'complete-family-rank-reconstruction',
        'baseline_commit': BASELINE,
        'target_family_id': TARGET,
        'target_component_count_in_source_slice': len(target_rows),
        'source_fit_slice_row_count': len(source_rows),
        'ranked_source_fitness_family_count': len(families),
        'selected_family_rank': selected_rank,
        'selected_family_best_rank_tuple': list(tuples[TARGET]),
        'rank_order': list(ORDER),
        'sort_direction': 'ascending lexicographic, matching the pinned priority ORDER_NAMES',
        'family_tuple_tie_count': 0,
        'selection_input_sha256': selection_sha,
        'selection_inputs': files,
        'producer_sha256': sha(pathlib.Path(__file__).read_bytes()),
        'runtime': {'python': sys.version.split()[0]},
        'limits': ['This reproduces the preselection ordinal among the pinned source-fitness slice; it does not establish physical source fitness, authority, or geography approval.']
    }
    report_path = HERE / 'report.json'
    report_path.write_bytes(canonical(report))
    output_files = []
    for path in [pathlib.Path(__file__), report_path]:
        raw = path.read_bytes()
        output_files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes','role':'generated-evidence' if path==report_path else 'method-code'})
    publication = {'version':1,'status':'complete','outputs':[{k:f[k] for k in ('path','bytes','sha256','hash_kind')} for f in output_files if f['path'].endswith('report.json')]}
    publication_path = HERE / 'publication.json'
    publication_path.write_bytes(canonical(publication))
    raw=publication_path.read_bytes(); output_files.append({'path':str(publication_path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes','role':'generated-evidence'})

    source_id='pinned-routing-rank-inputs'
    metric_rows=[
      {'id':'ranked_source_fitness_family_count','value':len(families),'unit':'families','vintage':'baseline','input_sha256':slice_desc['sha256'],'input_set_sha256':selection_sha,'evaluation_commit':BASELINE,'title':'Unique complete families in pinned source-fitness slice'},
      {'id':'selected_family_rank','value':selected_rank,'unit':'rank','vintage':'baseline','input_sha256':next(d['sha256'] for d in family_parts if d['path'].endswith('families-013.bin.gz')),'input_set_sha256':selection_sha,'evaluation_commit':BASELINE,'title':'Selected family rank by pinned priority tuple'},
    ]
    evidence={
      'version':1,'issue':1432,'lane':'source-only','worker_id':'01a11522-1da9-75a1-8ecb-765bae224f1c',
      'subject_ids':SUBJECTS,'subject_ids_sha256':'37dd61b45ab3a5b85e65456f3f9b8e1aa0544ab026118de72e213ca91c14cde5',
      'baseline':{'commit':BASELINE,'files':files,'pins':pins,'pin_files':pin_files},
      'sources':[{'id':source_id,'url':'https://github.com/ChengshuLi/WorldAtlas/tree/64770c1a8c82c3626344d3d5ce322cdcb839ea2e/coordination/engineering/global-actionability-routing-20261007/results','role':'Pinned complete family ranking outputs and source-fitness slice','vintage':'2026-10-07 actionability routing snapshot','retrieved_at':'2026-10-08','license':{'status':'unknown','terms':'Internal repository evidence; redistribution terms are not assessed in this source-ranking packet.'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'Restore the exact pinned Git blobs from the baseline commit listed in this manifest.','limit':'This source packet verifies selection accounting only; it does not establish geographic source fitness or physical surface.'}],
      'outputs':output_files,
      'methods':[{'id':'complete-family-rank-reconstruction','kind':'source','description':'Count unique families in the complete source-fitness slice; retrieve each family best-rank tuple from the complete immutable family shards; sort by the pinned ORDER_NAMES in ascending lexicographic order and locate the selected family.','software':'Python '+sys.version.split()[0]+'; gzip; standard-library JSON and SHA-256','units':'families and one-based ordinal rank'}],
      'commands':['python3 research/geography/india-western-gap-source-fitness-20261007/selection-ranking/run.py','node scripts/evidence-quality.mjs research/geography/india-western-gap-source-fitness-20261007/selection-ranking/evidence-quality.json'],
      'metrics':metric_rows,
      'summaries':[{'metric_id':m['id'],'value':m['value'],'unit':m['unit']} for m in metric_rows],
      'metric_bindings':[{'metric_id':'ranked_source_fitness_family_count','path':str(report_path.relative_to(ROOT)),'json_pointer':'/ranked_source_fitness_family_count'},{'metric_id':'selected_family_rank','path':str(report_path.relative_to(ROOT)),'json_pointer':'/selected_family_rank'}],
      'conclusions':[{'status':'supported','text':'The selected family is rank 8 among 711 families in the pinned source-fitness slice under the pinned priority tuple order.','source_ids':[source_id]}],
      'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'}
    }
    (HERE/'evidence-quality.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'families':len(families),'rank':selected_rank,'tuple':list(tuples[TARGET]),'selection_input_sha256':selection_sha,'rows':len(source_rows),'ties':0},indent=2))


if __name__ == '__main__':
    main()
