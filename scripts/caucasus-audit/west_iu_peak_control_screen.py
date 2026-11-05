"""Screen two mapped summits against the 1941 Abin sheet, without registering it."""
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET

EXPECTED = 'c447f5d1e7da385c7ca13b3d119d2c1b260b29315974a6f9b3db08f9c4fe35c8'


def main(path):
    with open(path, 'rb') as f:
        data = f.read()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError('wrong OSM input')
    root = ET.fromstring(data)
    # Visual estimate of the triangle marked 896.3 m, crop origin (5900,2150).
    symbol = (632, 690)
    for identifier in ('13276920139', '785474093'):
        n = root.find("node[@id='" + identifier + "']")
        if n is None:
            raise ValueError('expected peak missing')
        lon, lat = float(n.get('lon')), float(n.get('lat'))
        x = 670.5 + (lon - 38.0) * 9391.5 / .5 - 5900
        y = 902.9 + (44 + 40/60 - lat) * 8903.1 / (20/60) - 2150
        tags = {t.get('k'): t.get('v') for t in n.findall('tag')}
        print(json.dumps({'node': identifier, 'lon': lon, 'lat': lat,
                          'ele_tag_m': tags.get('ele'), 'pixel': [x, y],
                          'separation_from_estimated_symbol_pixels': math.hypot(x-symbol[0], y-symbol[1]),
                          'warning': 'Approximate frame fit and unverified feature identity; not a control.'}, sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1])
