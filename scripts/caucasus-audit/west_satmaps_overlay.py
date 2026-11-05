"""Provisional visual overlay on the unregistered L-37-126 scan.

The pixel fit uses two printed 2 km grid spacings and assumes the Soviet
Pulkovo 1942 / Gauss-Kruger zone 7 grid. No independent ground controls or
scan-deformation correction were applied. It is a research screen only.
"""
import argparse
import hashlib
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer


PINS = {'image': 'e78a58145a9b47c8f0dffab9855fbd6a8c04858586378feeff6bce2fdb5af1a2',
        'source': '081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25',
        'candidate': 'f9e4e5da1687f3ffb118e0b621705fe2e6b43a5dc2abbc323699cb56fbf8dcb9'}


def map_pixel(easting, northing):
    # Locally measured grid lines: 7472/7474 km at x=1027/1187 and
    # 4930/4932 km at y=1498/1341, near the eastern join.
    return (1027 + (easting - 7472000) * 160 / 2000,
            1498 + (4930000 - northing) * 157 / 2000)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as src:
        for block in iter(lambda: src.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--candidate', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    for key in PINS:
        if file_hash(getattr(a, key)) != PINS[key]:
            raise ValueError('input digest mismatch: ' + key)
    x0, y0, width, height = 650, 1050, 1000, 1000
    with rasterio.open(a.image) as src:
        if (src.width, src.height) != (3322, 3081):
            raise ValueError('unexpected image dimensions')
        lut = np.asarray([src.colormap(1).get(i, (0, 0, 0, 255))[:3]
                          for i in range(256)], dtype='uint8')
        rgb = lut[src.read(1, window=Window(x0, y0, width, height))]
    transformer = Transformer.from_crs('EPSG:4326', 'EPSG:28407', always_xy=True)
    def screen(point):
        e, n = transformer.transform(*point)
        x, y = map_pixel(e, n)
        return (x - x0, y - y0)
    def mark(x, y, color, radius=2):
        x, y = round(x), round(y)
        if 0 <= x < width and 0 <= y < height:
            rgb[max(0,y-radius):min(height,y+radius+1), max(0,x-radius):min(width,x+radius+1)] = color
    def draw(coords, color):
        for p1, p2 in zip(coords, coords[1:]):
            a1, a2 = screen(p1), screen(p2)
            count = max(1, int(max(abs(a2[0]-a1[0]), abs(a2[1]-a1[1]))))
            for t in np.linspace(0, 1, count + 1):
                mark(a1[0] + t*(a2[0]-a1[0]), a1[1] + t*(a2[1]-a1[1]), color)
    source = json.load(open(a.source))['coordinates']
    candidate = json.load(open(a.candidate))['coordinates']
    draw(source, (255, 40, 40))
    draw(candidate, (20, 80, 255))
    mark(*screen(candidate[-1]), (255, 255, 255), radius=5)
    with rasterio.open(a.output, 'w', driver='PNG', width=width, height=height,
                       count=3, dtype='uint8') as dst:
        dst.write(rgb.transpose(2, 0, 1))


if __name__ == '__main__':
    main()
