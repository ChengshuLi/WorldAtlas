"""Bounded exact compact-geometry comparison; retain only verified source areas."""
import gzip
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

import numpy
import shapely
from shapely.geometry import shape

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from ellipsoidal_area import area

MAX = 32 * 1024 * 1024
config = json.load(sys.stdin)
assert pathlib.Path(config['root']).resolve() == ROOT
assert shapely.__version__ == '2.1.2' and numpy.__version__ == '2.3.5'
head = config['commit']
pins = {}


def read(name, pin=None):
    assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
    spec = head + ':' + name
    tree = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', head, '--', name]).decode()
    assert tree.startswith('100644 blob ') and tree.split('\t', 1)[1] == name + '\0'
    size = int(subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-s', spec]))
    assert size <= MAX
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', spec])
    digest = hashlib.sha256(raw).hexdigest()
    assert len(raw) == size
    if pin:
        assert digest == pin['sha256'] and size == pin['bytes']
    pins[spec] = {'commit': head, 'path': name, 'bytes': size, 'sha256': digest}
    assert sum(p['bytes'] for p in pins.values()) + 131072 <= 256 * 1024 * 1024
    assert len(pins) + 16 <= 512
    return raw


def decode(raw):
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        result = stream.read(MAX + 1)
    assert len(result) <= MAX
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


for name in [config['helper'], 'scripts/ellipsoidal_area.py', 'requirements.txt']:
    assert (ROOT / name).read_bytes() == read(name), 'Executed source differs from committed producer'
before = json.loads(read(config['before']))
after = json.loads(read(config['after']))
assert isinstance(before['parts'], list) and isinstance(after['parts'], list)
assert len(before['parts']) <= 128 and len(after['parts']) <= 128
old = json.loads(read(config['old_pixel']))
assert old['footprints_sha256'] == before['footprints_sha256']
assert before['owner_sha256'] == after['owner_sha256']
assert len(before['parts']) == len(after['parts'])
old_records = {r['id']: r for r in old['records']}
assert len(old_records) == old['locations'] == 49625
targets = set(config['targets'])
changed = set()
rows = []
seen = set()
for a, b in zip(before['parts'], after['parts']):
    assert a['owners'] == b['owners'] and a['first_owner'] == b['first_owner'] == len(rows) + 1
    aa = decode(read(str(pathlib.PurePosixPath(config['before']).parent / a['path']), a))
    bb = decode(read(str(pathlib.PurePosixPath(config['after']).parent / b['path']), b))
    for raw, pin in [(aa, a), (bb, b)]:
        assert len(raw) == pin['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest() == pin['uncompressed_sha256']
    original, successor = json.loads(aa), json.loads(bb)
    assert len(original) == len(successor) == a['owners']
    for f, g in zip(original, successor):
        identity = f['id']
        assert identity not in seen and identity in old_records
        assert f['pixelIndex'] == g['pixelIndex'] == len(rows) + 1
        assert f['id'] == g['id'] and canonical(f['properties']) == canonical(g['properties'])
        seen.add(identity)
        previous_area = old_records[identity]['source_wgs84_area_m2']
        assert previous_area > 0
        if canonical(f['geometry']) == canonical(g['geometry']):
            assert canonical(f) == canonical(g)
            source_area = previous_area
        else:
            assert identity in targets
            assert canonical({k: v for k, v in f.items() if k != 'geometry'}) == canonical({k: v for k, v in g.items() if k != 'geometry'})
            geometry = shape(g['geometry'])
            assert geometry.is_valid and not geometry.is_empty
            source_area = area(geometry)
            assert source_area > 0
            changed.add(identity)
        rows.append([identity, f['pixelIndex'], source_area, f['properties']['parent_id']])
assert changed == targets and len(rows) == 49625 and seen == set(old_records)
def runtime_file(filename):
    digest = hashlib.sha256()
    with open(filename, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(pathlib.Path(filename).resolve()), 'sha256': digest.hexdigest()}

result = {'rows': rows, 'changed_ids': sorted(changed), 'unchanged_geometry_count': len(rows) - len(changed),
          'before_footprints_sha256': before['footprints_sha256'], 'after_footprints_sha256': after['footprints_sha256'],
          'owner_sha256': after['owner_sha256'], 'inputs': list(pins.values()),
          'runtime': {'python': platform.python_version(), 'executable': runtime_file(sys.executable),
                      'numpy': numpy.__version__, 'shapely': shapely.__version__,
                      'numpy_entry': runtime_file(numpy.__file__), 'shapely_entry': runtime_file(shapely.__file__),
                      'numpy_native': runtime_file(numpy._core._multiarray_umath.__file__),
                      'shapely_native': runtime_file(shapely.lib.__file__)},
          'area_policy': 'Exact unchanged compact geometry retains prior source WGS84 area; two changed valid source polygons use committed ellipsoidal_area.area.'}
encoded = json.dumps(result, separators=(',', ':')).encode()
assert len(encoded) <= MAX
sys.stdout.buffer.write(encoded)
