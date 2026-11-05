"""Approximate western-join overlay on the 1941 IU historical sheet.

The printed-frame fit assumes WGS84 and does not validate the historical datum,
warping, or registration with independent controls. It is not a survey.
"""
import argparse
import hashlib
import json
import numpy as np
import rasterio
from rasterio.windows import Window

PINS = {'image': 'f51b6448d3717ad5e84dfaf145728e1f785d7a4907e94a84a9785d60b78bb635',
        'source': '081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25',
        'candidate': 'f9e4e5da1687f3ffb118e0b621705fe2e6b43a5dc2abbc323699cb56fbf8dcb9'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('image', 'source', 'candidate', 'output'):
        p.add_argument('--' + key, required=True)
    args = p.parse_args()
    for key, expected in PINS.items():
        if digest(getattr(args, key)) != expected:
            raise ValueError('input digest mismatch: ' + key)
    x0, y0, width, height = 5900, 2150, 1500, 1500
    with rasterio.open(args.image) as src:
        if (src.width, src.height) != (10728, 10884):
            raise ValueError('unexpected image dimensions')
        rgb = src.read(window=Window(x0, y0, width, height))[:3].transpose(1, 2, 0)
    def pixel(point):
        lon, lat = point
        return (670.5 + (lon - 38.0) * (10062 - 670.5) / .5 - x0,
                902.9 + (44 + 40/60 - lat) * (9806 - 902.9) / (20/60) - y0)
    def mark(x, y, color, radius=3):
        x, y = round(x), round(y)
        if 0 <= x < width and 0 <= y < height:
            rgb[max(0,y-radius):min(height,y+radius+1), max(0,x-radius):min(width,x+radius+1)] = color
    def draw(coords, color):
        for p1, p2 in zip(coords, coords[1:]):
            x1, y1 = pixel(p1)
            x2, y2 = pixel(p2)
            if max(x1, x2) < -10 or min(x1, x2) > width+10 or max(y1, y2) < -10 or min(y1, y2) > height+10:
                continue
            count = max(1, int(max(abs(x2-x1), abs(y2-y1))))
            for t in np.linspace(0, 1, count + 1):
                mark(x1 + t*(x2-x1), y1 + t*(y2-y1), color)
    with open(args.source) as f:
        source = json.load(f)['coordinates']
    with open(args.candidate) as f:
        candidate = json.load(f)['coordinates']
    draw(source, (255, 40, 40))
    draw(candidate, (20, 80, 255))
    mark(*pixel(candidate[0]), (255, 255, 255), radius=7)
    with rasterio.open(args.output, 'w', driver='PNG', width=width, height=height, count=3, dtype='uint8') as dst:
        dst.write(rgb.transpose(2, 0, 1))


if __name__ == '__main__':
    main()
