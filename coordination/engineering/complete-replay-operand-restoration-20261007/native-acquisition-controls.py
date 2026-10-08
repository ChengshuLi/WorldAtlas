"""Tiny synthetic native-frame controls; never a real GSHHG/source acceptance."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import types


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    out = args.out
    if not out.is_absolute() or '..' in out.parts or out.exists() or out.is_symlink() or \
            not out.resolve().is_relative_to(repo / '.cache') or not out.parent.is_dir() or \
            any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('Fresh exclusive owned synthetic-control output required')
    raw = (here / 'native-acquisition.py').read_bytes()
    module = types.ModuleType('native_acquisition_fixture')
    module.__file__ = str(here / 'native-acquisition.py')
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    source_raw = (here / 'source.py').read_bytes()
    source = types.ModuleType('source_fixture')
    source.__file__ = str(here / 'source.py')
    exec(compile(source_raw, source.__file__, 'exec'), source.__dict__)
    header = struct.Struct('>11i')
    points = struct.pack('>8i', 0, 0, 1000000, 0, 1000000, 1000000, 0, 0)
    def record(identity, level, parent):
        return header.pack(identity, 4, level, 0, 1000000, 0, 1000000, 1, 1, parent, -1) + points
    body = record(10, 1, -1) + record(20, 2, 10) + record(30, 3, 20)
    image = io.BytesIO(body)
    index = module.headers(image, header, member_bytes=len(body), expected_headers=3)
    assert set(index) == {10, 20, 30}
    assert module.closure({30}, index) == {10, 20, 30}
    cases = []
    def reject(name, action, expected):
        try:
            action()
        except ValueError as error:
            assert expected in str(error), (name, str(error))
            cases.append({'name': name, 'actual_error': str(error), 'result': 'REJECTED'})
        else:
            raise AssertionError(name + ' did not reject')
    reject('duplicate-native-header-id', lambda: module.headers(
        io.BytesIO(body + record(10, 1, -1)), header, member_bytes=len(body)+76, expected_headers=4), 'Duplicate')
    reject('truncated-native-header', lambda: module.headers(
        io.BytesIO(body[:76]+b'x'), header, member_bytes=77, expected_headers=2), 'Truncated')
    reject('truncated-native-coordinate-body', lambda: module.headers(
        io.BytesIO(body[:-1]), header, member_bytes=len(body)-1, expected_headers=3), 'truncated')
    reject('missing-whole-header-roster', lambda: module.headers(
        io.BytesIO(body), header, member_bytes=len(body), expected_headers=4), 'Incomplete')
    reject('query-source-absent', lambda: module.closure({31}, index), 'absent')
    def decode(raw_header, raw_points, ordinal, offset):
        values = header.unpack(raw_header)
        metadata = {'id': values[0], 'ordinal': ordinal, 'native_offset': offset,
                    'native_record_bytes': 44+len(raw_points), 'n': values[1],
                    'level': values[2] & 255, 'container': values[9],
                    'record_sha256': module.sha(raw_header+raw_points),
                    'decoded_pointset_binary64_sha256': module.sha(raw_points)}
        return metadata, object()
    comparison = types.SimpleNamespace(decode_record=decode)
    offset, size, ordinal, _, _ = index[30]
    metadata, _ = decode(body[offset:offset+44], body[offset+44:offset+size], ordinal, offset)
    query = {'source_id': 30, 'source_level': 3, 'source_container': 20,
             'source_record_sha256': metadata['record_sha256'],
             'source_pointset_sha256': metadata['decoded_pointset_binary64_sha256'],
             'periodic_offset': 0}
    query_rows = {30: [{'query': query}]}
    proof = {'member_sha256': module.sha(body)}
    output = list(module.record_rows(io.BytesIO(body), index, {10,20,30}, query_rows,
                                    comparison, source.query_bind, proof))
    assert [row['source_id'] for row in output] == [10,20,30]
    assert output[-1]['complete_original_metadata'] == metadata
    assert all(len(module.canonical(row)) <= module.ROW_BYTES for row in output)
    bad = dict(query, source_container=10)
    reject('literal-query-parent-binding-drift', lambda: list(module.record_rows(
        io.BytesIO(body), index, {10,20,30}, {30:[{'query':bad}]}, comparison, source.query_bind, proof)), 'binding differs')
    bad = dict(query, source_id=True)
    reject('literal-query-boolean-native-id', lambda: list(module.record_rows(
        io.BytesIO(body), index, {10,20,30}, {30:[{'query':bad}]}, comparison, source.query_bind, proof)), 'binding differs')
    bad = dict(query, source_pointset_sha256='0'*64)
    reject('literal-query-whole-pointset-binding-drift', lambda: list(module.record_rows(
        io.BytesIO(body), index, {10,20,30}, {30:[{'query':bad}]}, comparison, source.query_bind, proof)), 'binding differs')
    fake = types.SimpleNamespace(decode_record=lambda *args:(dict(metadata, id=30), object()))
    reject('whole-record-metadata-identity-drift', lambda: list(module.record_rows(
        io.BytesIO(body), index, {10}, {}, fake, source.query_bind, proof)), 'binding differs')
    oversized = types.SimpleNamespace(decode_record=lambda *args:(dict(metadata, extra='x'*4096), object()))
    reject('complete-row-size-admission', lambda: list(module.record_rows(
        io.BytesIO(body), index, {30}, query_rows, oversized, source.query_bind, proof)), 'row exceeds')
    result = {'status': 'PASS', 'scope': 'synthetic three-record 228-byte fixture only; no real native materialization, scientific decoder, GIS, or global proof',
              'adapter_sha256': module.sha(raw), 'literal_query_binding_source_sha256': module.sha(source_raw),
              'fixture_sha256': module.sha(body), 'fixture_bytes': len(body), 'fixture_headers':3,
              'fixture_complete_parent_records':3, 'fixture_metadata_rows':len(output),
              'controls':cases, 'limits':['Fake decoder is fixture-only; real comparison.decode_record remains unexecuted.']}
    payload = module.canonical(result)
    if len(payload)>16384:
        raise ValueError('Bounded fixture receipt overflow')
    with out.open('xb') as stream:
        stream.write(payload)
    assert out.read_bytes() == payload
    print(json.dumps({'status':'PASS','synthetic_controls':len(cases),'fixture_bytes':len(body)}))


if __name__ == '__main__':
    main()
