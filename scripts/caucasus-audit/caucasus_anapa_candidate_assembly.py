"""Reproduce the unselected source-backed Anapa coastal candidate.

The baseline is reconstructed from the stored compact decisions and pinned raw
HydroBASINS and author inputs. The coast is intersected with a pinned OSM way.
This is a geographic candidate, not a selected Neon boundary or a map build.
The caller must authenticate Python, explicit dependency paths and this code.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import substring

HERE = Path(__file__).resolve().parent
PINS = {
    'recipe': '59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c',
    'hydro': '21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03',
    'author': 'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6',
    'coast': '66c3c6a36802cf08e70d65c8119c285bf5f88c90b4c8e3320e0c96e352779515',
}
CODE = {'caucasus_compact_selectors.py': '615e5ea1a73f9f918b56fa1f7ac579b73e1974ea16277f1734b2fa2400fb90ea',
        'caucasus_selector_replay.py': 'e671edeceadfad6ef734ea814f2d4359ce60057edaaf2cd64b998e021eac4e23'}
EXPANDED = 'c2107838b8dde06ff65a3ef61a7a15234137dc16a966fe2155edfac50f69a8d0'
BASE = '2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6'
EXPECTED = 'e3dd7f326c0247f4d9f4c4c61b7c31782a5fc1b9e850d164cf46e729cbb60929'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run_script(name, *args):
    boot = ("import json,runpy,sys; sys.path[:0]=json.loads(sys.argv[1]); "
            "p=sys.argv[2]; sys.argv=sys.argv[2:]; runpy.run_path(p,run_name='__main__')")
    subprocess.run([sys.executable, '-I', '-S', '-B', '-c', boot,
                    json.dumps(sys.path), str(HERE / name), *map(str, args)], check=True,
                   stdout=subprocess.DEVNULL)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('recipe', 'hydro', 'author', 'coast', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    if not (sys.flags.isolated and sys.flags.no_site):
        raise ValueError('run under isolated no-site Python with explicit dependencies')
    if Path(a.output).exists():
        raise FileExistsError(a.output)
    for key, expected in PINS.items():
        if sha(getattr(a, key)) != expected:
            raise ValueError('raw source or decision pin mismatch: ' + key)
    for name, expected in CODE.items():
        if sha(HERE / name) != expected:
            raise ValueError('assembly dependency pin mismatch: ' + name)
    with tempfile.TemporaryDirectory(prefix='caucasus-anapa-') as temp:
        tmp = Path(temp)
        with zipfile.ZipFile(a.hydro) as archive:
            matches = [n for n in archive.namelist() if n == 'hybas_eu_lev12_v1c.shp' or n.endswith('/hybas_eu_lev12_v1c.shp')]
            if len(matches) != 1:
                raise ValueError('expected one HydroBASINS shapefile')
            with archive.open(matches[0]) as source, (tmp / 'hydro.shp').open('xb') as out:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    out.write(block)
        expanded, replay = tmp / 'expanded.json', tmp / 'replay.json'
        run_script('caucasus_compact_selectors.py', 'expand', '--input', a.recipe,
                   '--input-sha256', PINS['recipe'], '--output', expanded)
        if sha(expanded) != EXPANDED:
            raise ValueError('expanded recipe mismatch')
        run_script('caucasus_selector_replay.py', '--recipe', expanded, '--recipe-sha256', EXPANDED,
                   '--shp', tmp / 'hydro.shp', '--author', a.author, '--output', replay)
        value = json.loads(replay.read_bytes())
        if value.get('geometry_sha256') != BASE:
            raise ValueError('baseline reconstruction mismatch')
        baseline = LineString(value['geometry']['coordinates'])
        author = LineString(json.loads(Path(a.author).read_bytes())['features'][462]['geometry']['coordinates'])
        root = ET.parse(a.coast).getroot()
        nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
        ways = [w for w in root.findall('way') if w.get('id') == '396539058' and w.get('version') == '2']
        if len(ways) != 1 or {t.get('k'): t.get('v') for t in ways[0].findall('tag')}.get('natural') != 'coastline':
            raise ValueError('expected coastline way unavailable')
        refs = [n.get('ref') for n in ways[0].findall('nd')]
        if len(refs) < 2 or any(n not in nodes for n in refs):
            raise ValueError('incomplete coastline way')
        coastline = LineString([nodes[n] for n in refs])
        coast = author.intersection(coastline)
        if coast.geom_type != 'Point':
            raise ValueError('coastal intersection is not unique')
        hits = baseline.intersection(author)
        points = [hits] if hits.geom_type == 'Point' else list(hits.geoms)
        points = sorted((x for x in points if x.geom_type == 'Point' and author.project(x) < author.project(coast)),
                        key=baseline.project)
        if len(points) <= 4:
            raise ValueError('missing intended source intersection')
        join = points[4]
        if abs(join.x - 37.42406995874469) > 1e-10 or abs(join.y - 44.84168781056519) > 1e-10:
            raise ValueError('fifth intersection changed')
        opening = list(substring(author, author.project(join), author.project(coast)).coords)[::-1]
        retained = list(substring(baseline, baseline.project(join), baseline.length).coords)
        opening[-1] = (join.x, join.y)
        retained[0] = (join.x, join.y)
        first, rest = LineString(opening), LineString(retained)
        hit = first.intersection(rest)
        if hit.geom_type != 'Point' or hit.distance(join) > 1e-10:
            raise ValueError('opening and retained line have extra intersections')
        line = LineString(opening + retained[1:])
        if not line.is_simple:
            raise ValueError('candidate is not simple')
        geometry = {'type': 'LineString', 'coordinates': [[float(x), float(y)] for x, y in line.coords]}
        data = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        if digest != EXPECTED:
            raise ValueError('candidate output hash mismatch: ' + digest)
        for key, expected in PINS.items():
            if sha(getattr(a, key)) != expected:
                raise ValueError('source or decision changed during assembly: ' + key)
        for name, expected in CODE.items():
            if sha(HERE / name) != expected:
                raise ValueError('assembly dependency changed during execution: ' + name)
        with open(a.output, 'xb') as out:
            out.write(data)
        print(json.dumps({'geometry_sha256': digest, 'coordinates': len(line.coords),
                          'coast': [coast.x, coast.y], 'join': [join.x, join.y],
                          'status': 'unselected_candidate'}, sort_keys=True))


if __name__ == '__main__':
    main()
