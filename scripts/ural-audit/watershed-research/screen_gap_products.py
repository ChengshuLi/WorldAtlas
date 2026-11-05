#!/usr/bin/env python3
"""Cross-screen provisional gap interfaces; this never selects a boundary."""
import argparse, collections, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, 'landed-1b494125')
from smoothed_transect_screen import screen

BASINS = [
    ('/tmp/ural-hydro-eu.zip', '21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03', '/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),
    ('/tmp/ural-hydro-si.zip', '67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd', '/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp'),
]
DEM = {
    '00': [('arctic', '/tmp/ural-gap00-12km-nearest.tif', '3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b'),
           ('cop', '/tmp/ural-gap00-cop-30m-bilinear.tif', 'd661fee6218f9198f48cf3505a5303a4942cec602747fb82af3571c9548e4a86')],
    '02': [('arctic', '/tmp/ural-gap02-16km-nearest.tif', 'dc04a55cdc1b742a21dfdb1f050f493c621a6ae0f3f66f7cdd0042c2cb893635'),
           ('cop', '/tmp/ural-gap02-cop-30m-bilinear.tif', 'b35eff9756b70096e6ea2f1090249b6a60a31d4b7cc47dfd9d72eec646a0e169')],
}
LINE = {
    '00': [('arctic', 'd6960d47fd084c4dfdc73bebfef1f379d2fa83205a9e3f017fa321c11f436bec'),
           ('cop', 'ddba931464360ea7b19adc2f01bf3f6610e8bb570b81c2d87036b49c561f02ad')],
    '02': [('arctic', '91192a2a44966bc37f01ac646d70ed72cab97e58cff5a0ccc4f495f61d5474ae'),
           ('cop', 'a661593eaaa405d29c7e13c740121ffc643b13cffc96a464c28886f181d6304f')],
}


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('gap', choices=['00', '02'])
    p.add_argument('output_directory', type=Path)
    a = p.parse_args()
    a.output_directory.mkdir(parents=True, exist_ok=False)
    implementation = Path('landed-1b494125/smoothed_transect_screen.py')
    code_sha = file_sha(implementation)
    reports = []
    for line, line_sha in LINE[a.gap]:
        line_path = f'/tmp/ural-gap{a.gap}-{line}-intersection-line.json'
        for dem, dem_path, dem_sha in DEM[a.gap]:
            result = screen(dem_path, dem_sha, BASINS, line_path, line_sha, 100., [50.], [50.,100.,200.])
            counts = {}
            for offset in (50,100,200):
                c = collections.Counter()
                for station in result['stations']:
                    d = next(x for x in station['directions'] if x['mode'] == '50.0' and x['offset_wgs84_m'] == offset)
                    x,y = d['samples']
                    if not x or not y or len(x['main_basins']) != 1 or len(y['main_basins']) != 1:
                        category = 'unknown'
                    elif {x['main_basins'][0],y['main_basins'][0]} == {2120043720,3120001840}:
                        category = 'opposite'
                    else:
                        category = 'same_or_other'
                    c[f"{d['crossing_count']}:{category}"] += 1
                counts[str(offset)] = dict(c)
            target = a.output_directory / f'{line}-screen-{dem}.json'
            with target.open('x') as f: json.dump(result, f, sort_keys=True, allow_nan=False)
            reports.append({'line':line,'dem':dem,'stations':len(result['stations']),'counts':counts,'output_sha256':file_sha(target)})
    if file_sha(implementation) != code_sha: raise ValueError('screen implementation changed')
    summary = {'status':'research-not-selected','gap':a.gap,'screen_code_sha256':code_sha,'reports':reports,
               'limitations':['D8 outlet crosswalk and grid resolution are shared model assumptions.',
                              'Cross-sections at neighboring stations are spatially correlated.',
                              'Terrain products are surface models and the interface source is not a complete raw-source boundary.',
                              'Results do not establish the surveyed divide or select a boundary.']}
    with (a.output_directory/'summary.json').open('x') as f: json.dump(summary, f, indent=2, sort_keys=True, allow_nan=False)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__': main()
