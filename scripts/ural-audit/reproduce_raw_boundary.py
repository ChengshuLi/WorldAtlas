#!/usr/bin/env python3
"""Reproduce the Ural research boundary in a fresh staging directory.

The input directory contains the reassembled pinned ArcticDEM tiles, EU/SI
HydroBASINS ZIPs and extracted shapefiles, Copernicus tile, OSM capture and
Neon export, under the names used below. Helpers are the pinned audited files
from PR4. Only local derived files are written; nothing is published.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HELPERS = {'terrain_basin_screen.py': '4b5acd6a6d0039b125bc9299b2f1007cf2432903762a49def9ee54fc4263a731',
           'priority_d8.py': 'b7e8deef7289a1cd5cf38c16270e6ab32dd04c3141f0589a8ff364605497fc24',
           'spring_connector_graph.py': 'be147977fa1102b2578146a17724188f22de3a26c1f6e2f34061c9f093169579',
           'spring_triple_route.py': 'fe1acd1d9e7bc7d83120f5b8244d6454594fa166b75d58f953f566a5c2fbf287',
           'projected_route.py': '3cd363d478be84697c269a42463af6c50a3cd2fa659e3c443ee92393ed45703c'}
PR4_HELPERS = {'terrain_basin_screen.py': '26a81f00180f2007cf8fdf0af796662eeaa3b057a1665392207054855cf001df',
               'priority_d8.py': '884ce9f0d84a193ba82fa85dbd10b2d0894c2b6e389a6df05099146f1db8dd79',
               'spring_connector_graph.py': '86204b914bce4fdf0ee03f71d169acb8d10e301e562ae5e49ef6a48ac42211e5',
               'spring_triple_route.py': 'a553215f79cd64d11d2e67998977ced8be5f878cb4a5acd8ee7650841da1da9f',
               'projected_route.py': 'e3c9ac7465fc5f14e9442f206e9cc9301f2630f3446feea9802797dcb3fce4ef'}
INPUTS = ['ural-arctic-gap00.tif', 'ural-arctic-gap02a.tif', 'ural-arctic-gap02b.tif',
          'ural-hydro-eu.zip', 'ural-hydro-si.zip', 'ural-hydro-eu', 'ural-hydro-si',
          'ural-copernicus-dem.tif', 'ural-river-r2.osm', 'review_snapshot.json']
SCRIPTS = ['construct_arctic_gap_paths.py', 'construct_cop_spring_flow.py',
           'trace_gap_raw_crossings.py', 'check_raw_chord_coverage.py',
           'verify_raw_north_candidate.py', 'assemble_raw_backed_candidate.py']
OUTPUT_SHA = 'c7e8476d10d0ab95da6dc717e0b5aa3852d967a9c1a19ea6932a460b0a31a2d4'
BOOTSTRAP = ("import json,runpy,sys; paths=json.loads(sys.argv[1]); "
             "script=sys.argv[2]; sys.argv=sys.argv[2:]; "
             "sys.path[:0]=paths; runpy.run_path(script,run_name='__main__')")


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--helpers', type=Path, required=True)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--dependency-dir', type=Path, action='append', required=True)
    parser.add_argument('--python-sha256', required=True)
    a = parser.parse_args()
    inputs, helpers, work = a.inputs.resolve(), a.helpers.resolve(), a.workdir.resolve()
    scripts = Path(__file__).resolve().parent
    dependency_dirs = [str(p.resolve(strict=True)) for p in a.dependency_dir]
    if not all(Path(p).is_dir() for p in dependency_dirs) or sha(Path(sys.executable)) != a.python_sha256:
        raise ValueError('invalid dependency directory or Python executable pin')
    runtime_home = work / 'runtime-home'
    clean_env = {'PATH': os.defpath, 'LC_ALL': 'C', 'HOME': str(runtime_home),
                 'XDG_CONFIG_HOME': str(runtime_home), 'XDG_CACHE_HOME': str(runtime_home), 'OPENBLAS_NUM_THREADS': '1',
                 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
    if work.exists():
        raise FileExistsError('workdir must not exist: ' + str(work))
    for name in INPUTS:
        if not (inputs / name).exists():
            raise FileNotFoundError(inputs / name)
    observed = {}
    for name, expected in HELPERS.items():
        observed[name] = sha(helpers / name)
        if observed[name] not in (expected, PR4_HELPERS[name]):
            raise ValueError('helper hash mismatch: ' + name)
    work.mkdir(parents=True)
    runtime_home.mkdir()
    for name in INPUTS:
        (work / name).symlink_to(inputs / name, target_is_directory=(inputs / name).is_dir())
    (work / 'landed-1b494125').symlink_to(helpers, target_is_directory=True)
    staged_code = {}
    for name in SCRIPTS:
        # These audited research scripts use /tmp paths; confine every output
        # to this new workdir while retaining their pinned input checks.
        code = (scripts / name).read_text().replace('/tmp/', str(work) + '/')
        data = code.encode('utf-8')
        (work / name).write_bytes(data)
        staged_code[work / name] = data
    shutil.copyfile(scripts / 'reconstruct_hybrid_osm.py', work / 'ural-reconstruct-hybrid.py')
    staged_code[work / 'ural-reconstruct-hybrid.py'] = (scripts / 'reconstruct_hybrid_osm.py').read_bytes()

    def verify_staged():
        if any(path.read_bytes() != data for path, data in staged_code.items()):
            raise ValueError('staged Ural recipe code changed during construction')

    def run(script, *args, output=None):
        verify_staged()
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                                 json.dumps(dependency_dirs), str(script), *map(str, args)],
                                cwd=work, env=clean_env, check=True, stdout=subprocess.PIPE)
        verify_staged()
        if output:
            (work / output).write_bytes(result.stdout)

    run(scripts / 'extract_watershed_selector.py', '--snapshot', work / 'review_snapshot.json',
        '--selector', work / 'ural-watershed-first4954.json',
        '--template', work / 'ural-raw-chord-template.json', output='selector.log')
    run(scripts / 'reproduce_arctic_gap_rasters.py', '--source-dir', work, '--output-dir', work,
        output='rasters.log')
    for script, output in [('construct_arctic_gap_paths.py', 'gaps.log'),
                           ('construct_cop_spring_flow.py', 'ural-spring-cop-flow-reproduced.jsonl'),
                           ('trace_gap_raw_crossings.py', 'ural-gap-raw-edge-crossings.jsonl'),
                           ('check_raw_chord_coverage.py', 'ural-raw-chord-coverage.json'),
                           ('verify_raw_north_candidate.py', 'north.log'),
                           ('assemble_raw_backed_candidate.py', 'boundary.log')]:
        run(work / script, output=output)
    output = work / 'ural-raw-backed-continuous-cop-only.geometry.json'
    if sha(output) != OUTPUT_SHA:
        raise ValueError('reproduced boundary file hash mismatch')
    for name, expected in observed.items():
        if sha(helpers / name) != expected:
            raise ValueError('helper changed during construction: ' + name)
    if sha(Path(sys.executable)) != a.python_sha256:
        raise ValueError('Python executable changed during construction')
    print(json.dumps({'geometry': str(output), 'file_sha256': OUTPUT_SHA,
                      'canonical_geometry_sha256': '68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66',
                      'status': 'research-selected; no map built'}, sort_keys=True))


if __name__ == '__main__':
    main()
