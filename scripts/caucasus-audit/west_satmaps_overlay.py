"""Provisional visual overlay on the unregistered L-37-126 scan.

The pixel fit uses two printed 2 km grid spacings and assumes the Soviet
Pulkovo 1942 / Gauss-Kruger zone 7 grid. No independent ground controls or
scan-deformation correction were applied. It is a research screen only.
"""
import argparse
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--candidate', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
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
        return (224 + (e - 7462000) * 159 / 2000 - x0,
                406 + (4944000 - n) * 156 / 2000 - y0)
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
