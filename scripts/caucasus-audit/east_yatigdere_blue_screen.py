"""Screen historic blue ink near mapped streams; not a drainage classifier.

The coordinates use a provisional six-point SK42 grid fit. Blue pixels can be
glaciers, labels, rivers or other symbols; mapper source and map accuracy are
unknown. Small shifts are correlated controls, not statistical independence.
"""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.transform import from_gcps
from scipy.ndimage import maximum_filter
from pyproj import Transformer

PINS = ('5c6dcf630fb1297a8a4ca8ff9a2eeaf87a50554fd5b657de549ece15d7391edd',
        '6e81b2c20a4a805039ef10e764e9b132c322c8ba755eb44bc720593d960aa11d')
GCPS = [(1903,1087,8740000,4566000), (2021,1089,8742000,4566000),
        (2139,1091,8744000,4566000), (1901,1207,8740000,4564000),
        (2019,1209,8742000,4564000), (2137,1211,8744000,4564000)]
SHIFTS = [(0,0),(10,0),(-10,0),(0,10),(0,-10),(20,0),(-20,0),(0,20),(0,-20)]


def main(image, osm):
    for path, pin in zip((image, osm), PINS):
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != pin:
            raise ValueError('source hash mismatch')
    with rasterio.open(image) as src:
        if (src.width, src.height) != (2698, 2592):
            raise ValueError('unexpected map dimensions')
        arr = src.read()[:3].astype('int16')
    r, g, b = arr
    blue = maximum_filter((b-r >= 15) & (b-g >= 4) & (b > 70) & (r < 220), size=5)
    root = ET.parse(osm).getroot()
    nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
    grid = from_gcps([GroundControlPoint(row=y, col=x, x=e, y=n) for x,y,e,n in GCPS])
    project = Transformer.from_crs(4326, 28408, always_xy=True)
    results = {}
    for wid in ('1244882606', '1244882638'):
        way = root.find("way[@id='" + wid + "']")
        if way is None:
            raise ValueError('expected way missing')
        pts = [(~grid) * project.transform(*nodes[n.get('ref')]) for n in way.findall('nd')]
        samples = []
        for (x,y), (u,v) in zip(pts, pts[1:]):
            count = max(1, int(np.hypot(x-u, y-v)))
            samples.extend((int(round(x+(u-x)*t)), int(round(y+(v-y)*t)))
                           for t in np.linspace(0, 1, count, endpoint=False))
        xs, ys = np.asarray(samples).T
        if min(xs) < 20 or min(ys) < 20 or max(xs) >= blue.shape[1]-20 or max(ys) >= blue.shape[0]-20:
            raise ValueError('offset samples exceed map')
        results[wid] = {'samples': len(xs), 'blue_hit_fraction_by_offset_pixels':
                        {str((dx,dy)): float(blue[ys+dy, xs+dx].mean()) for dx,dy in SHIFTS}}
    print(json.dumps({'result': results,
                      'warning': 'Blue ink is not a verified stream; projections and source independence are unverified.'},
                     sort_keys=True, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
