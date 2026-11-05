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
        command = [sys.executable, str(HERE / 'caucasus_source_assembly.py'), '--decisions', str(recipe),
                   '--decisions-sha256', recipe_sha, '--hydro-zip', str(hydro), '--author', str(author),
                   '--selected', str(guide), '--output', str(output)]
        p = subprocess.run(command, check=True, text=True, capture_output=True)
        report = json.loads(p.stdout.strip().splitlines()[-1])
    if digest(recipe) != recipe_sha_before or (digest(hydro), digest(author)) != source_before:
        raise ValueError('source or decisions changed during gate')
    read_pinned(snapshot_pin)
    return {'schema': 'caucasus-source-seed-gate-v1', 'snapshot_sha256': snapshot_pin['sha256'],
            'selected_geometry_sha256': boundary['geometry_sha256'], 'recipe_sha256': recipe_sha,
            'source_sha256': list(source_before), 'assembly': report,
            'limitations': 'caller authenticates export; source comparisons do not prove watershed correctness'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'request-sha256', 'recipe', 'recipe-sha256', 'hydro', 'author', 'report'):
        p.add_argument('--' + name, required=True)
    for name in ('producer-dir', 'producer-sha256', 'work', 'output'):
        p.add_argument('--' + name)
    args = p.parse_args()
    if Path(args.report).exists():
        raise FileExistsError(args.report)
    if digest(args.request) != args.request_sha256:
        raise ValueError('request digest mismatch')
    run_args = (args.producer_dir, args.producer_sha256, args.work, args.output)
    if any(run_args) and not all(run_args):
        raise ValueError('seed producer requires directory, digest, work and output')
    report = check(args.request, args.recipe, args.recipe_sha256, args.hydro, args.author)
    report['request_sha256'] = args.request_sha256
    report['seed_producer_executed'] = False
    if all(run_args):
        producer_path = (Path(args.producer_dir).resolve(strict=True) / 'seed_producer.py').resolve(strict=True)
        if digest(producer_path) != args.producer_sha256:
            raise ValueError('seed producer digest mismatch')
        # The existing producer performs its own input and resource checks.
        sys.path.insert(0, str(producer_path.parent))
        spec = importlib.util.spec_from_file_location('caucasus_gated_seed_producer', producer_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run(args.request, args.work, args.output, lambda: None)
        if digest(producer_path) != args.producer_sha256 or digest(args.request) != args.request_sha256:
            raise ValueError('producer or request changed during execution')
        if digest(args.recipe) != args.recipe_sha256 or (digest(args.hydro), digest(args.author)) != tuple(SOURCE_PINS.values()):
            raise ValueError('source or decisions changed during execution')
        report['seed_producer_executed'] = True
        report['seed_producer_sha256'] = args.producer_sha256
    with open(args.report, 'x', encoding='utf-8') as out:
        json.dump(report, out, sort_keys=True, separators=(',', ':'), allow_nan=False)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
