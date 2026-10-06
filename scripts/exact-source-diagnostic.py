"""Read-only exact source-point/crossing diagnostic; immutable output, no repair."""
import argparse
import hashlib
import json
from pathlib import Path
from evidence.exact_predicates import MAX_FILE_BYTES, DiagnosticError, diagnose, segment_certificate, read_inputs, original_segment, unique_json_object


def run(root, request_path, output):
    request_path, output = Path(request_path), Path(output)
    if not request_path.is_file() or request_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('Missing or oversized request')
    raw = request_path.read_bytes()
    request = json.loads(raw, object_pairs_hook=unique_json_object)
    if not isinstance(request, dict) or request.get('version') != 1:
        raise ValueError('Expected version 1 request')
    certificates = request.get('crossings', [])
    if not isinstance(certificates, list) or len(certificates) > 512:
        raise ValueError('Crossing descriptor budget exceeded')
    result = diagnose(Path(root), request)
    result['request_sha256'] = hashlib.sha256(raw).hexdigest()
    result['crossings'] = []
    try:
        prepared, _ = read_inputs(Path(root), request)
    except DiagnosticError:
        prepared = None
    for crossing in certificates:
        try:
            if not isinstance(crossing, dict) or prepared is None:
                raise DiagnosticError('unknown', 'crossing-original-source-closure-unavailable')
            first = original_segment(prepared, crossing.get('first'), request['context'])
            second = original_segment(prepared, crossing.get('second'), request['context'])
            certificate = segment_certificate(first, second, crossing.get('exported'))
            certificate['original_source_references'] = [first['source_reference'], second['source_reference']]
            certificate['original_source_paths'] = [first['source_path'], second['source_path']]
            result['crossings'].append(certificate)
        except DiagnosticError as error:
            result['crossings'].append({'status': error.status, 'reason': error.reason, 'geometry_acceptance': 'not-assessed'})
    encoded = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if output.is_symlink():
        raise ValueError('Symlink output refused')
    # No replacement or auto-repair of a previously failed receipt.
    with output.open('xb') as handle:
        handle.write(encoded)
    return {'output_bytes': len(encoded), 'output_sha256': hashlib.sha256(encoded).hexdigest(), 'status': result['status']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.request, args.output), sort_keys=True))
