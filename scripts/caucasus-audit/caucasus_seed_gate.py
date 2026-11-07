"""Guard a mainland seed request with a source-derived Caucasus comparison.

The caller must authenticate the selected Neon snapshot, recipe and R2 source
pins. This research wrapper does not change the snapshot or selected boundary.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOUNDARY = 'caucasus_blacksea_anapa_to_caspian'
SOURCE_PINS = {
    ('hydrosheds-hydrobasins-europe-level12-standard', 'v1c-21797d53e079'):
        '21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03',
    ('trubetskoy-europe-asia-boundary', 'commit-7aa03ec54a262e8e97e8273f60621c530ec4e998'):
        'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6',
}
SOURCE_LOCATIONS = {
    ('hydrosheds-hydrobasins-europe-level12-standard', 'v1c-21797d53e079'):
        ('worldatlas', 'sources/hydrosheds/hydrobasins/standard/europe/level-12/v1c/hybas_eu_lev12_v1c-21797d53e079.zip', 73934860),
    ('trubetskoy-europe-asia-boundary', 'commit-7aa03ec54a262e8e97e8273f60621c530ec4e998'):
        ('worldatlas', 'sources/trubetskoy/7aa03ec54a262e8e97e8273f60621c530ec4e998/asia_europe_border.geojson', 623503),
}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_pinned(pin):
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'} or digest(pin['path']) != pin['sha256']:
        raise ValueError('invalid input pin')
    return json.loads(Path(pin['path']).read_bytes())


def assembled_region_hash(decision, records):
    """Mirror the region builder's ordered, exact-join ring serialization."""
    ring = []
    for segment in decision['segments']:
        record = records[(segment['kind'], segment['id'])]
        coordinates = record['geometry']['coordinates']
        start, end = segment['start'], segment['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(coordinates) or end - start < 2:
            raise ValueError('invalid region slice')
        pts = [tuple(Decimal(str(v)) for v in p) for p in coordinates[start:end]]
        if any(len(p) != 2 or any(not v.is_finite() for v in p) for p in pts):
            raise ValueError('invalid region coordinate')
        if type(segment['reverse']) is not bool:
            raise ValueError('invalid region direction')
        if segment['reverse']:
            pts.reverse()
        if ring and ring[-1] != pts[0]:
            raise ValueError('region does not join exactly')
        ring.extend(pts if not ring else pts[1:])
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError('region is not explicitly closed')
    geom = {'type': 'Polygon', 'coordinates': [[[float(x), float(y)] for x, y in ring]]}
    return hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def check(request_path, recipe, recipe_sha, hydro, author):
    request = json.loads(Path(request_path).read_bytes())
    snapshot_pin = request['inputs']['snapshot']
    snapshot = read_pinned(snapshot_pin)
    if snapshot.get('schema') != 'worldatlas-geography-decision-draft-evidence-v1' or snapshot.get('source') != 'neon-export':
        raise ValueError('expected pinned selected Neon snapshot')
    matches = [b for b in snapshot['mainland_boundaries'] if b.get('boundary_id') == BOUNDARY]
    if len(matches) != 1 or matches[0].get('execution_status') != 'selected_for_research':
        raise ValueError('selected Caucasus boundary missing or ambiguous')
    boundary = matches[0]
    catalog = {(s['source_id'], s['version']): s for s in snapshot['sources']}
    if len(catalog) != len(snapshot['sources']):
        raise ValueError('duplicate source catalog identity')
    refs = boundary['provenance']['source_refs']
    refset = {(r['source_id'], r['version']) for r in refs}
    for key, expected in SOURCE_PINS.items():
        source = catalog.get(key, {})
        location = (source.get('r2_bucket'), source.get('r2_key'), source.get('size_bytes'))
        if key not in refset or source.get('sha256') != expected or location != SOURCE_LOCATIONS[key]:
            raise ValueError('boundary source reference or source pin missing')
    recipe_sha_before = digest(recipe)
    if recipe_sha_before != recipe_sha:
        raise ValueError('decision recipe digest mismatch')
    decision = boundary['provenance'].get('source_assembly_v1')
    if not isinstance(decision, dict) or decision.get('schema') != 'caucasus-source-assembly-v1' or decision.get('recipe_sha256') != recipe_sha:
        raise ValueError('selected boundary lacks pinned source assembly decision')
    stored_recipe = json.dumps(decision.get('recipe'), sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True, allow_nan=False).encode()
    if hashlib.sha256(stored_recipe).hexdigest() != recipe_sha:
        raise ValueError('snapshot recipe differs from pinned decision bytes')
    source_before = (digest(hydro), digest(author))
    if source_before != tuple(SOURCE_PINS.values()):
        raise ValueError('raw source digest mismatch')
    with tempfile.TemporaryDirectory(prefix='caucasus-gate-') as directory:
        directory = Path(directory)
        guide, output = directory / 'selected.json', directory / 'reconstructed.json'
        guide.write_text(json.dumps(boundary['geometry'], sort_keys=True, separators=(',', ':'), allow_nan=False))
        if sys.flags.isolated and sys.flags.no_site:
            boot = ("import json,runpy,sys; sys.path[:0]=json.loads(sys.argv[1]); "
                    "p=sys.argv[2]; sys.argv=sys.argv[2:]; runpy.run_path(p,run_name='__main__')")
            command = [sys.executable, '-I', '-S', '-B', '-c', boot, json.dumps(sys.path),
                       str(HERE / 'caucasus_source_assembly.py')]
        else:
            command = [sys.executable, '-I', str(HERE / 'caucasus_source_assembly.py')]
        command += ['--decisions', str(recipe),
                   '--decisions-sha256', recipe_sha, '--hydro-zip', str(hydro), '--author', str(author),
                   '--selected', str(guide), '--output', str(output)]
        p = subprocess.run(command, check=True, text=True, capture_output=True)
        report = json.loads(p.stdout.strip().splitlines()[-1])
        derived = json.loads(output.read_text(encoding='utf-8'))
    if digest(recipe) != recipe_sha_before or (digest(hydro), digest(author)) != source_before:
        raise ValueError('source or decisions changed during gate')
    read_pinned(snapshot_pin)
    return {'schema': 'caucasus-source-seed-gate-v1', 'snapshot_sha256': snapshot_pin['sha256'],
            'selected_geometry_sha256': boundary['geometry_sha256'], 'recipe_sha256': recipe_sha,
            'source_sha256': list(source_before), 'assembly': report,
            'reconstruction_inputs': [{'source_id': key[0], 'version': key[1], 'sha256': expected,
                                       'role': 'raw_reconstruction_input'}
                                      for key, expected in SOURCE_PINS.items()],
            'selected_guide': {'boundary_id': BOUNDARY, 'geometry_sha256': boundary['geometry_sha256'],
                               'role': 'guide_and_preservation_guard'},
            'limitations': 'caller authenticates export; source comparisons do not prove watershed correctness'}, derived


def run_guarded_worker(producer_dir, producer_sha256, worker_sha256, request, work, output, derived, report):
    """Use the reviewed worker's resource guard while injecting the effective view.

    The caller must bind these code pins and the resulting report into its own
    trusted execution and resume identity. This function does not do that.
    """
    producer_dir = Path(producer_dir).resolve(strict=True)
    producer_path = (producer_dir / 'seed_producer.py').resolve(strict=True)
    worker_path = (producer_dir / 'seed_worker.py').resolve(strict=True)
    if digest(producer_path) != producer_sha256 or digest(worker_path) != worker_sha256:
        raise ValueError('seed worker or producer digest mismatch')
    # A reused import could point at a different producer. This adapter is an
    # executable entry point, and refuses ambiguous in-process import state.
    if 'seed_producer' in sys.modules:
        raise ValueError('seed producer already imported')
    old_path, old_argv = list(sys.path), list(sys.argv)
    producer = None
    try:
        sys.path.insert(0, str(producer_dir))
        spec = importlib.util.spec_from_file_location('caucasus_gated_seed_worker', worker_path)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        producer = worker.seed_producer
        if Path(producer.__file__).resolve(strict=True) != producer_path:
            raise ValueError('worker imported a different seed producer')
        from caucasus_effective_snapshot import derive
        original_load = producer.load_pinned_snapshot
        def load_effective_snapshot(path, expected_sha256, guard):
            original = original_load(path, expected_sha256, guard)
            effective, trace = derive(original, derived, report, expected_sha256)
            report['effective_snapshot'] = trace
            return effective
        producer.load_pinned_snapshot = load_effective_snapshot
        sys.argv = [str(worker_path), str(request), str(work), str(output)]
        worker.main()
        if digest(producer_path) != producer_sha256 or digest(worker_path) != worker_sha256:
            raise ValueError('seed worker or producer changed during execution')
    finally:
        if producer is not None and 'original_load' in locals():
            producer.load_pinned_snapshot = original_load
        sys.modules.pop('seed_producer', None)
        sys.path[:], sys.argv[:] = old_path, old_argv


def run_producer(producer_dir, producer_sha256, request, work, output, derived, report):
    """Run a pinned producer with the derived view and no extra resource guard.

    This does not change controls implemented by the producer itself. A caller
    choosing a no-limit execution must also use a producer implementing that
    policy and bind its code and this gate into the execution provenance.
    """
    validate_direct_request(request)
    producer_dir = Path(producer_dir).resolve(strict=True)
    producer_path = (producer_dir / 'seed_producer.py').resolve(strict=True)
    if digest(producer_path) != producer_sha256:
        raise ValueError('seed producer digest mismatch')
    if 'seed_producer' in sys.modules:
        raise ValueError('seed producer already imported')
    old_path = list(sys.path)
    producer = None
    try:
        sys.path.insert(0, str(producer_dir))
        spec = importlib.util.spec_from_file_location('caucasus_gated_seed_producer', producer_path)
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        from caucasus_effective_snapshot import derive
        original_load = producer.load_pinned_snapshot
        def load_effective_snapshot(path, expected_sha256, guard):
            original = original_load(path, expected_sha256, guard)
            effective, trace = derive(original, derived, report, expected_sha256)
            report['effective_snapshot'] = trace
            return effective
        producer.load_pinned_snapshot = load_effective_snapshot
        producer.run(request, work, output)
        if digest(producer_path) != producer_sha256:
            raise ValueError('seed producer changed during execution')
    finally:
        if producer is not None and 'original_load' in locals():
            producer.load_pinned_snapshot = original_load
        sys.path[:] = old_path


def validate_direct_request(request):
    """Require the direct v2 producer interface; the producer checks all pins."""
    value = json.loads(Path(request).read_bytes())
    controls = value.get('controls') if isinstance(value, dict) else None
    if (not isinstance(value, dict) or value.get('schema') != 'worldatlas-stage2-seed-direct-request-v2'
            or not isinstance(controls, dict) or set(controls) != {'strip_rows'}
            or type(controls['strip_rows']) is not int or controls['strip_rows'] <= 0):
        raise ValueError('direct seed v2 request required')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'recipe', 'recipe-sha256', 'hydro', 'author', 'report'):
        p.add_argument('--' + name, required=True)
    for name in ('producer-dir', 'producer-sha256', 'worker-sha256', 'work', 'output'):
        p.add_argument('--' + name)
    args = p.parse_args()
    if Path(args.report).exists():
        raise FileExistsError(args.report)
    if digest(args.request) != args.request_sha256:
        raise ValueError('request digest mismatch')
    run_args = (args.producer_dir, args.producer_sha256, args.work, args.output)
    if any(run_args) and not all(run_args):
        raise ValueError('seed producer requires directory, digest, work and output')
    if args.worker_sha256 and not all(run_args):
        raise ValueError('worker digest requires seed execution arguments')
    if all(run_args) and not args.worker_sha256:
        validate_direct_request(args.request)
    report, derived = check(args.request, args.recipe, args.recipe_sha256, args.hydro, args.author)
    report['request_sha256'] = args.request_sha256
    report['seed_producer_executed'] = False
    if all(run_args):
        if args.worker_sha256:
            run_guarded_worker(args.producer_dir, args.producer_sha256, args.worker_sha256,
                               args.request, args.work, args.output, derived, report)
        else:
            run_producer(args.producer_dir, args.producer_sha256,
                         args.request, args.work, args.output, derived, report)
        if digest(args.request) != args.request_sha256:
            raise ValueError('producer or request changed during execution')
        if digest(args.recipe) != args.recipe_sha256 or (digest(args.hydro), digest(args.author)) != tuple(SOURCE_PINS.values()):
            raise ValueError('source or decisions changed during execution')
        report['seed_producer_executed'] = True
        report['seed_producer_sha256'] = args.producer_sha256
        report['seed_worker_sha256'] = args.worker_sha256
    with open(args.report, 'x', encoding='utf-8') as out:
        json.dump(report, out, sort_keys=True, separators=(',', ':'), allow_nan=False)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
