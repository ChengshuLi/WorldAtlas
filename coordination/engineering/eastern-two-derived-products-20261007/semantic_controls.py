"""Coherently rehashed adverse records against actual unchanged stock consumers."""
import contextlib
import copy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile

import restore


def module(index, path, root):
    binding = next(b for b in index['bindings'] if b['group'] == 'existing_caller_and_helper_code' and b['path'] == path)
    raw = restore.member_bytes(index, index['members'][binding['member_id']])
    restore.original_guard(binding, raw)
    file = root / Path(path).name
    file.write_bytes(raw)
    spec = importlib.util.spec_from_file_location(file.stem.replace('-', '_'), file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main():
    index = json.loads((restore.PREFIX / 'source-index.json').read_text())
    controls = []
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        runtime = module(index, 'scripts/prepare-ownership-runtime.py', root)
        validator = module(index, 'scripts/validate-ownership-runtime.py', root)
        for operation in ('positive', 'evidence', 'shortened', 'missing', 'identity', 'dictionary', 'source', 'gap', 'reversed'):
            folder = root / operation
            source = folder / 'source'
            output = folder / 'runtime'
            source.mkdir(parents=True)
            evidence = [[0, .6, .6, [[0, .6]], [0], 0], [None, 0, 0, [], [], 0]]
            subjects = ['atlas:physical:CAN-103:QUE', 'atlas:physical:CAN-114:NFL']
            rows = [[subjects[0], [[-2, 3, 0, 0, 0]]], [subjects[1], [[-2, 1, None, 1, 1], [1, 3, 1, 0, 0]]]]
            for path, values in [('evidence.json.gz', evidence), ('ownership.json.gz', rows)]:
                (source / path).write_bytes(gzip.compress(json.dumps(values, separators=(',', ':')).encode(), mtime=0))
            manifest = {'version': 2, 'valid_from': -2, 'valid_to': 3,
                        'parts': [{'path': 'ownership.json.gz', 'sha256': validator.sha(source / 'ownership.json.gz')}],
                        'evidence_parts': [{'path': 'evidence.json.gz', 'sha256': validator.sha(source / 'evidence.json.gz')}],
                        'evidence_records': 2, 'locations': 2, 'intervals': 3, 'footprints_sha256': 'fixture',
                        'owner_ids': subjects, 'labels': subjects, 'source_ids': ['fixture-source'],
                        'statuses_order': ['derived', 'no-majority']}
            (source / 'index.json').write_text(json.dumps(manifest, separators=(',', ':')))
            with contextlib.redirect_stdout(io.StringIO()):
                runtime.prepare(source, output)
            m = validator.read(output / 'index.json')
            first = m['buckets'][0]
            path = output / first['path']
            data = validator.read(path)
            if operation == 'evidence':
                data['evidence'][0][1] = .7
            elif operation == 'shortened':
                data['parts'][0][0][1][0][1] = 1
            elif operation == 'missing':
                data['parts'][0][0][1].pop()
            elif operation == 'identity':
                data['parts'][0][0][0] = 'different-existing-identity'
            elif operation == 'dictionary':
                m['shared']['owner_ids'].reverse()
            elif operation == 'source':
                m['source_index_sha256'] = '0' * 64
            elif operation == 'gap':
                m['buckets'][0]['valid_to'] -= 1
            elif operation == 'reversed':
                m['buckets'].reverse()
            path.write_bytes(gzip.compress(json.dumps(data, separators=(',', ':')).encode(), mtime=0))
            first['sha256'] = validator.sha(path)
            (output / 'index.json').write_text(json.dumps(m, separators=(',', ':')))
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = validator.validate(source, output)
            except ValueError as error:
                if operation == 'positive':
                    raise
                controls.append({'case': operation, 'actual_rejection': str(error), 'all_asset_hashes_rebound': True})
            else:
                if operation != 'positive':
                    raise AssertionError('Actual semantic mutation passed: ' + operation)
                assert result['source_intervals'] == 3 and result['transport_intervals'] == 4
                controls.append({'case': operation, 'status': 'PASS'})
        bomb = gzip.compress(b'x' * (restore.MAX + 1), mtime=0)
        try:
            restore.gunzip(bomb)
        except ValueError as error:
            assert 'Decoded body exceeds cap' in str(error)
            controls.append({'case': 'small-encoded-overbound-decoded', 'actual_rejection': str(error), 'encoded_bytes': len(bomb)})
        else:
            raise AssertionError('Decoded overbound accepted')
    print(json.dumps({'status': 'PASS', 'actual_controls': controls,
                      'source': 'actual pinned original stock prepare and validator modules',
                      'fixture_does_not_claim_geographic_or_political_authority': True}))


if __name__ == '__main__':
    main()
