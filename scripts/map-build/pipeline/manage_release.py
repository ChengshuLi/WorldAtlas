"""Stage, approve, and publish the same immutable map and viewer files."""

import argparse
from contextlib import closing
import gzip
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from map_build.execution.runtime import digest, json_bytes, pin, verify_pins
from run_pipeline import SCRIPTS, stage_module

STREAMS = ('rows', 'runs')
CANDIDATE = re.compile(r'(?P<version>v[0-9]+\.[0-9]+)-rc\.?[1-9][0-9]*')
HOMEPAGE = 'review/index.html'


def version(candidate):
    match = CANDIDATE.fullmatch(candidate)
    if not match:
        raise ValueError('candidate must look like v9.0-rc1')
    return match['version']


def prefix(candidate):
    return f'review/releases/{candidate}'


def read(path):
    return json.loads(path.read_bytes())


def category_snapshot(request, identity):
    draft = identity.get('land_draft')
    if draft is not None:
        snapshot = draft['snapshot']
    else:
        source = request['sources']['land_snapshot']
        if 'json' in source:
            return source['json']
        snapshot = next((item for item in identity['source_pins']
                         if item['sha256'] == source['sha256']), None)
        if snapshot is None:
            raise ValueError('build identity is missing its geographic snapshot')
    verify_pins([snapshot])
    return read(Path(snapshot['path']))


def release_categories(db, snapshot):
    names = {entity['id']: entity['name'] for entity in snapshot['entities']}
    bindings = snapshot['category_bindings']
    land_ids = sorted({b['entity_id'] for b in bindings if b['physical_class'] == 'land'})
    colors = {entity_id: list(bytes.fromhex(color[1:])) for entity_id, color in db.execute(
        'SELECT id, color_rgb FROM atlas.geographic_entity_ids WHERE id = ANY(%s) AND color_rgb IS NOT NULL',
        (land_ids,),
    )}
    if missing := sorted(set(land_ids) - colors.keys()):
        raise ValueError(f'Neon colors are missing for land entities {missing}')
    categories = []
    for binding in sorted(bindings, key=lambda b: b['code']):
        entity_id = binding['entity_id']
        physical_class = binding['physical_class']
        category = {'id': binding['code'], 'entity_id': entity_id, 'name': names[entity_id],
                    'physical_class': physical_class}
        if physical_class == 'land':
            category['rgb'] = colors[entity_id]
        categories.append(category)
    return categories


def build_bundle(candidate, run, viewer, bundle, db):
    report = read(run / 'report.json')
    if (report.get('schema') != 'worldatlas-end-to-end-report-v1'
            or report.get('status') != 'complete'
            or any(not report['stages'].get(name, {}).get('outputs_complete')
                   for name in ('physical', 'mainland', 'water', 'verification'))):
        raise ValueError('a completed map build is required')
    identity_pin = report['original_run_identity']
    if identity_pin != pin(run / 'run-identity.json'):
        raise ValueError('build identity does not match the report')
    identity = read(run / 'run-identity.json')
    request_pin = report['request']
    if request_pin != identity['request']:
        raise ValueError('build configuration does not match the run')
    final = report['final']
    verify_pins([request_pin, *final.values()])
    for name, filename in (('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json')):
        if Path(final[name]['path']) != (run / 'final' / filename).resolve():
            raise ValueError('expected final outputs inside the build directory')

    request = read(Path(request_pin['path']))
    grid = request['sources']['land_config']['json']['grid']
    summary = read(run / 'final/report.json')
    counts = summary['counts']
    if sum(counts.values()) != grid['width'] * grid['height']:
        raise ValueError('the output counts must cover the entire grid')
    categories = release_categories(db, category_snapshot(request, identity))
    if {code for code, count in counts.items() if count} - {str(c['id']) for c in categories}:
        raise ValueError('geographic snapshot is missing categories used by the map')

    for source in sorted(viewer.rglob('*')):
        rel = source.relative_to(viewer)
        if source.is_symlink() or not all(re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', part) for part in rel.parts):
            raise ValueError(f'invalid viewer asset path: {rel}')
        if source.is_dir() or source.suffix == '.md':
            continue
        destination = bundle / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    index = bundle / 'index.html'
    html = index.read_text()
    if html.count('<head>') != 1 or re.search(r'<base\b', html, re.I):
        raise ValueError('the viewer homepage must have a single head and no base URL')
    index.write_text(html.replace('<head>', f'<head><base href="/{prefix(candidate)}/">', 1))

    combined = hashlib.sha256()
    grid_config = {'run_count': summary['run_count']}
    decoded = {}
    for stream in STREAMS:
        output = bundle / f'{stream}.u32le.gz'
        raw = Path(final[stream]['path'])
        checksum = hashlib.sha256()
        with raw.open('rb') as src, output.open('xb') as dst, gzip.GzipFile(
                filename='', fileobj=dst, mode='wb', mtime=0) as compressed:
            while chunk := src.read(4 << 20):
                checksum.update(chunk)
                combined.update(chunk)
                compressed.write(chunk)
        if checksum.hexdigest() != final[stream]['sha256']:
            raise ValueError(f'{stream} changed while preparing the release')
        decoded[stream] = checksum.hexdigest()
        grid_config[stream] = output.name
        grid_config[stream + '_sha256'] = decoded[stream]

    config = bundle / 'config.json'
    viewer_config = read(config)
    legend = {}
    for category in categories:
        entity_id = category['entity_id']
        entry = legend.setdefault(entity_id, {
            'id': entity_id, 'name': category['name'],
            'color': viewer_config['water_rgb'], 'count': 0,
        })
        entry['count'] += counts.get(str(category['id']), 0)
        if category['physical_class'] == 'land':
            entry['color'] = category['rgb']
    legend_path = bundle / 'legend' / 'continents.json'
    legend_path.parent.mkdir(exist_ok=True)
    legend_path.write_bytes(json_bytes(list(legend.values())))
    viewer_config.update(width=grid['width'], height=grid['height'], step=grid['step'],
                         map_version=version(candidate), local_grid=grid_config,
                         combined_sha256=combined.hexdigest(), legend='legend/continents.json',
                         categories=[{key: category[key] for key in ('id', 'entity_id', 'physical_class')}
                                     for category in categories])
    config.write_bytes(json_bytes(viewer_config))

    inputs = {'configuration': request, 'run': identity, 'report_sha256': digest(run / 'report.json')}
    if 'land_draft' in identity:
        snapshot = identity['land_draft']['snapshot']
        verify_pins([snapshot])
        inputs['mainland_snapshot'] = Path(snapshot['path']).read_text()
    if 'regional_decisions' in identity:
        snapshot = identity['regional_decisions']
        verify_pins([snapshot])
        inputs['regional_snapshot'] = Path(snapshot['path']).read_text()
    if report['comparison']:
        verify_pins([report['comparison']])
        inputs['comparison'] = read(Path(report['comparison']['path']))

    objects = {
        path.relative_to(bundle).as_posix(): {
            'sha256': digest(path), 'size_bytes': path.stat().st_size,
            'content_type': 'application/gzip' if path.suffix == '.gz' else
                            mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
        }
        for path in sorted(bundle.rglob('*')) if path.is_file()
    }
    return {'inputs': inputs, 'decoded_sha256': decoded, 'objects': objects}


def verify_object(storage, bucket, key, expected, *, return_bytes=False):
    response = storage.get_object(Bucket=bucket, Key=key)
    with closing(response['Body']) as body:
        if response['ContentLength'] != expected['size_bytes'] or response.get('ContentEncoding'):
            raise ValueError(f'wrong size or encoding for {key}')
        if response.get('ContentType') != expected['content_type']:
            raise ValueError(f'wrong content type for {key}')
        data = body.read() if return_bytes else None
        checksum = hashlib.sha256(data) if return_bytes else hashlib.file_digest(body, 'sha256')
    if checksum.hexdigest() != expected['sha256']:
        raise ValueError(f'published bytes differ from the candidate: {key}')
    return data


def upload_bundle(storage, bucket, candidate, bundle, manifest):
    from botocore.exceptions import ClientError

    for name, asset in manifest['objects'].items():
        key = f'{prefix(candidate)}/{name}'
        with (bundle / name).open('rb') as body:
            try:
                storage.put_object(Bucket=bucket, Key=key, Body=body, IfNoneMatch='*',
                                   ContentType=asset['content_type'])
            except ClientError as exc:
                if exc.response['ResponseMetadata']['HTTPStatusCode'] != 412:
                    raise
        verify_object(storage, bucket, key, asset)


def put_homepage(storage, bucket, key, html, **condition):
    storage.put_object(Bucket=bucket, Key=key, Body=html,
                       ContentType='text/html', CacheControl='no-cache', **condition)


def homepage_condition(storage, bucket):
    from botocore.exceptions import ClientError

    try:
        return {'IfMatch': storage.head_object(Bucket=bucket, Key=HOMEPAGE)['ETag']}
    except ClientError as exc:
        if exc.response['ResponseMetadata']['HTTPStatusCode'] != 404:
            raise
        return {'IfNoneMatch': '*'}


def stage(db, storage, bucket, candidate, bundle, manifest):
    from psycopg.types.json import Jsonb

    row = db.execute(
        'SELECT r2_bucket,manifest FROM atlas.map_release_candidates WHERE candidate_id=%s',
        (candidate,),
    ).fetchone()
    if row is not None and row != (bucket, manifest):
        raise ValueError('that candidate already exists with different contents')
    upload_bundle(storage, bucket, candidate, bundle, manifest)
    if row is None:
        db.execute('INSERT INTO atlas.map_release_candidates (candidate_id,r2_bucket,manifest) VALUES (%s,%s,%s)',
                   (candidate, bucket, Jsonb(manifest)))


def approve(db, candidate, reviewer):
    if not reviewer.strip():
        raise ValueError('reviewer name is required')
    row = db.execute(
        'UPDATE atlas.map_release_candidates SET approved_by=%s,approved_at=now() '
        'WHERE candidate_id=%s AND approved_at IS NULL RETURNING candidate_id',
        (reviewer, candidate),
    ).fetchone()
    if row is None:
        raise ValueError('candidate is missing or already approved')


def publish(db, storage, candidate):
    row = db.execute(
        'SELECT map_version,r2_bucket,manifest FROM atlas.map_release_candidates '
        'WHERE candidate_id=%s AND approved_at IS NOT NULL', (candidate,),
    ).fetchone()
    if row is None:
        raise ValueError('approve this exact candidate before publishing')
    map_version, bucket, manifest = row
    condition = homepage_condition(storage, bucket)
    expected = []
    for stream in STREAMS:
        name = f'{stream}.u32le.gz'
        asset = manifest['objects'][name]
        expected.append((map_version, stream, bucket, f'{prefix(candidate)}/{name}',
                         asset['size_bytes'], asset['sha256'], manifest['decoded_sha256'][stream], candidate))
    with db.transaction():
        rows = db.execute(
            'SELECT map_version,stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256,candidate_id '
            'FROM atlas.map_release_objects WHERE map_version=%s ORDER BY stream', (map_version,),
        ).fetchall()
        if rows and rows != expected:
            raise ValueError('this map version already points to a different release')
        html = None
        for name, asset in manifest['objects'].items():
            data = verify_object(storage, bucket, f'{prefix(candidate)}/{name}', asset,
                                 return_bytes=name == 'index.html')
            if name == 'index.html':
                html = data
        if not rows:
            for entry in expected:
                db.execute(
                    'INSERT INTO atlas.map_release_objects '
                    '(map_version,stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256,candidate_id) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', entry,
                )
    # This single write is the switch. A failed write can be retried using the same candidate.
    put_homepage(storage, bucket, HOMEPAGE, html, **condition)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    stage_args = actions.add_parser('stage')
    stage_args.add_argument('candidate')
    stage_args.add_argument('run', type=Path)
    stage_args.add_argument('--viewer', type=Path, required=True)
    stage_args.add_argument('--bucket', default='worldatlas')
    approve_args = actions.add_parser('approve')
    approve_args.add_argument('candidate')
    approve_args.add_argument('--reviewer', required=True)
    publish_args = actions.add_parser('publish')
    publish_args.add_argument('candidate')
    args = parser.parse_args()
    version(args.candidate)
    if not (connection := os.environ.get('NEON_DATABASE_URL')):
        parser.error('set NEON_DATABASE_URL to the release catalog database')

    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    if '-pooler.' in conninfo_to_dict(connection).get('host', ''):
        parser.error('use a direct Neon connection for the release lock')

    with tempfile.TemporaryDirectory() as temp:
        bundle = Path(temp)
        with psycopg.connect(connection, autocommit=True) as db:
            if args.action == 'stage':
                manifest = build_bundle(args.candidate, args.run.resolve(), args.viewer.resolve(), bundle, db)
            db.execute("SELECT pg_advisory_lock(hashtext('atlas.release_publication'))")
            if args.action == 'approve':
                approve(db, args.candidate, args.reviewer)
                print(f'Approved {args.candidate}')
                return
            from map_build.physical import build as physical
            if args.action == 'stage':
                endpoint = manifest['inputs']['configuration']['physical_controls']['source_staging']['endpoint_url']
            else:
                row = db.execute(
                    "SELECT manifest#>>'{inputs,configuration,physical_controls,source_staging,endpoint_url}' "
                    'FROM atlas.map_release_candidates WHERE candidate_id=%s AND approved_at IS NOT NULL',
                    (args.candidate,),
                ).fetchone()
                if row is None:
                    raise ValueError('approve this exact candidate before publishing')
                endpoint = row[0]
            with closing(physical.make_r2_client(endpoint)) as storage:
                if args.action == 'stage':
                    stage(db, storage, args.bucket, args.candidate, bundle, manifest)
                    print(f'Preview: /{prefix(args.candidate)}/index.html')
                else:
                    publish(db, storage, args.candidate)
                    print(f'Published {args.candidate} at /')


if __name__ == '__main__':
    main()
