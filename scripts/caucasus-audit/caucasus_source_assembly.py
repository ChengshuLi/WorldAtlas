"""Reconstruct the selected Caucasus research boundary from source decisions.

This is an explicit, guide-derived reconstruction, not historic provenance or
independent watershed verification. The guard comparison is mandatory.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

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
    a = parser.parse_args()
    if sha(a.decisions) != a.decisions_sha256:
        raise ValueError('decision bytes do not match the pinned digest')
    if sha(a.hydro_zip) != HYDRO_ZIP_SHA or sha(a.author) != AUTHOR_SHA:
        raise ValueError('source bytes do not match R2 source pins')
    if os.path.exists(a.output):
        raise FileExistsError(a.output)
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
        # Preserve a GeoJSON-only output usable by the existing line consumer.
        with open(a.output, 'x', encoding='utf-8') as out:
            json.dump(value['geometry'], out, sort_keys=True, separators=(',', ':'), allow_nan=False)
        print(json.dumps({'output_sha256': sha(a.output), 'geometry_sha256': value['geometry_sha256'],
                          'comparison': c}, sort_keys=True))


if __name__ == '__main__':
    main()
