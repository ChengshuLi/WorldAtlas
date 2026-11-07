"""Preview an OSM headwater network on the historic K-38-108 sheet.

The grid fit is provisional: its datum operation, field controls, feature
identity and hydrography over time are not independently validated. The 1978
map's named river supports a regional lead, not a surveyed divide.
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
from rasterio.windows import Window
from pyproj import Transformer

PINS = ('5c6dcf630fb1297a8a4ca8ff9a2eeaf87a50554fd5b657de549ece15d7391edd',
        '6e81b2c20a4a805039ef10e764e9b132c322c8ba755eb44bc720593d960aa11d',
        '081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25')
GCPS = [(1903,1087,8740000,4566000), (2021,1089,8742000,4566000),
        (2139,1091,8744000,4566000), (1901,1207,8740000,4564000),
        (2019,1209,8742000,4564000), (2137,1211,8744000,4564000)]


def main(image, osm, selected, output):
    for path, expected in zip((image, osm, selected), PINS):
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('source hash mismatch')
    x0, y0, width, height = 1550, 800, 900, 550
    with rasterio.open(image) as src:
        if (src.width, src.height) != (2698, 2592):
            raise ValueError('unexpected map dimensions')
        pixels = src.read(window=Window(x0, y0, width, height))[:3]
    root = ET.parse(osm).getroot()
    nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
    ways = {}
    for wid in ('1244882606', '1244882638'):
        way = root.find("way[@id='" + wid + "']")
        if way is None:
            raise ValueError('mapped way missing')
        ids = [n.get('ref') for n in way.findall('nd')]
        ways[wid] = (ids, [nodes[i] for i in ids])
    if set(ways['1244882606'][0]) & set(ways['1244882638'][0]) != {'11572559585'}:
        raise ValueError('expected mapped confluence missing')
    grid = from_gcps([GroundControlPoint(row=y, col=x, x=e, y=n) for x,y,e,n in GCPS])
    project = Transformer.from_crs(4326, 28408, always_xy=True)
    def pixel(pt):
        x, y = (~grid) * project.transform(*pt)
        return x - x0, y - y0
    def mark(x, y, color):
        x, y = round(x), round(y)
        if 1 <= x < width - 1 and 1 <= y < height - 1:
            pixels[:, y-1:y+2, x-1:x+2] = np.array(color)[:, None, None]
    def draw(points, color):
        for a, b in zip(points, points[1:]):
            if not all(47.75 <= p[0] <= 48.05 and 41.1 <= p[1] <= 41.3 for p in (a, b)):
                continue
            (x,y), (u,v) = pixel(a), pixel(b)
            steps = max(1, int(max(abs(u-x), abs(v-y))))
            for t in np.linspace(0, 1, steps + 1):
                mark(x+(u-x)*t, y+(v-y)*t, color)
    draw(json.loads(Path(selected).read_bytes())['coordinates'], (255, 255, 0))
    draw(ways['1244882606'][1], (0, 180, 0))
    draw(ways['1244882638'][1], (255, 0, 255))
    with rasterio.open(output, 'w', driver='PNG', width=width, height=height,
                       count=3, dtype='uint8') as dst:
        dst.write(pixels)
    print(json.dumps({'shared_node': '11572559585', 'map_projection': 'provisional EPSG:28408',
                      'legend': {'green': 'OSM 1244882606', 'magenta': 'OSM 1244882638',
                                 'yellow': 'selected Caucasus line'},
                      'warning': 'Map datum, independent controls and mapped feature identities unverified.'}))


if __name__ == '__main__':
    main(*sys.argv[1:])
