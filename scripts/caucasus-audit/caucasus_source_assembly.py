"""Reconstruct the selected Caucasus research boundary from source decisions.

This is an explicit, guide-derived reconstruction, not historic provenance or
independent watershed verification. The guard comparison is mandatory.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from pyproj import Geod

HERE = Path(__file__).resolve().parent
HYDRO_ZIP_SHA = '21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03'
AUTHOR_SHA = 'c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6'


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('decisions', 'decisions-sha256', 'hydro-zip', 'author', 'selected', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--feature-id', help='wrap as a FeatureCollection for build_regions.py')
    parser.add_argument('--exact-overrides', help='explicit binary64 preservation decisions')
    parser.add_argument('--exact-overrides-sha256', help='trusted digest of override decisions')
    a = parser.parse_args()
    if sha(a.decisions) != a.decisions_sha256:
        raise ValueError('decision bytes do not match the pinned digest')
    if sha(a.hydro_zip) != HYDRO_ZIP_SHA or sha(a.author) != AUTHOR_SHA:
        raise ValueError('source bytes do not match R2 source pins')
    if os.path.exists(a.output):
        raise FileExistsError(a.output)
    if bool(a.exact_overrides) != bool(a.exact_overrides_sha256):
        raise ValueError('override file and digest must be supplied together')
    if a.exact_overrides and sha(a.exact_overrides) != a.exact_overrides_sha256:
        raise ValueError('override digest mismatch')
    with tempfile.TemporaryDirectory(prefix='caucasus-source-assembly-') as tmp:
        tmp = Path(tmp)
        shp = tmp / 'hydro.shp'
        with zipfile.ZipFile(a.hydro_zip) as archive:
            matches = [x for x in archive.namelist() if x.endswith('/hybas_eu_lev12_v1c.shp') or x == 'hybas_eu_lev12_v1c.shp']
            if len(matches) != 1:
                raise ValueError('expected exactly one named HydroBASINS shapefile')
            with archive.open(matches[0]) as source, shp.open('xb') as dest:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    dest.write(block)
        recipe = tmp / 'expanded.json'
        result = tmp / 'replay.json'
        subprocess.run([sys.executable, str(HERE / 'caucasus_compact_selectors.py'), 'expand', '--input', a.decisions,
                        '--input-sha256', a.decisions_sha256, '--output', str(recipe)], check=True)
        subprocess.run([sys.executable, str(HERE / 'caucasus_selector_replay.py'), '--recipe', str(recipe),
                        '--recipe-sha256', sha(recipe), '--shp', str(shp), '--author', a.author,
                        '--compare', a.selected, '--output', str(result)], check=True)
        value = json.loads(result.read_text(encoding='utf-8'))
        c = value['comparison']
        if c['possible_changed_centers'] != 0 or c['maximum_wgs84_vertex_displacement_m'] > 0.0002:
            raise ValueError('reconstruction does not satisfy preservation guard')
        # build_regions.py consumes a pinned FeatureCollection feature selector.
        geometry = value['geometry']
        if a.exact_overrides:
            decisions = json.loads(Path(a.exact_overrides).read_bytes())
            if decisions.get('schema') != 'caucasus-binary64-preservation-v1':
                raise ValueError('unsupported override schema')
            seen = set()
            for item in decisions['overrides']:
                i, coordinate = item['index'], item['coordinate']
                if type(i) is not int or not 0 <= i < len(geometry['coordinates']) or i in seen:
                    raise ValueError('invalid or duplicate override index')
                if not isinstance(coordinate, list) or len(coordinate) != 2 or any(
                    type(v) not in (int, float) or not math.isfinite(v) for v in coordinate
                ):
                    raise ValueError('invalid override coordinate')
                distance = Geod(ellps='WGS84').inv(*geometry['coordinates'][i], *coordinate)[2]
                if not 0 <= distance <= 0.0002:
                    raise ValueError('override exceeds preservation tolerance')
                seen.add(i)
                geometry['coordinates'][i] = [float(coordinate[0]), float(coordinate[1])]
            canonical = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            if hashlib.sha256(canonical).hexdigest() != decisions['target_geometry_sha256']:
                raise ValueError('overridden geometry digest mismatch')
            value['geometry_sha256'] = decisions['target_geometry_sha256']
        if a.feature_id is not None:
            if not a.feature_id.strip():
                raise ValueError('feature ID must not be empty')
            output_value = {'type': 'FeatureCollection', 'features': [{
                'type': 'Feature', 'properties': {'cut_id': a.feature_id}, 'geometry': geometry}]}
        else:
            output_value = geometry
        with open(a.output, 'x', encoding='utf-8') as out:
            json.dump(output_value, out, sort_keys=True, separators=(',', ':'), allow_nan=False)
        print(json.dumps({'output_sha256': sha(a.output), 'geometry_sha256': value['geometry_sha256'],
                          'comparison': c}, sort_keys=True))


if __name__ == '__main__':
    main()
