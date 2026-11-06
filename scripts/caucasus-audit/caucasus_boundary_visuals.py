"""Create standalone side-by-side research maps from pinned local sources.

Elevation and OSM are contextual; these figures do not compute cell impacts,
prove flow direction, select a boundary, or rebuild a map product.
"""
import argparse
import base64
import html
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds
from shapely.geometry import LineString, Polygon, box, shape


def line(path):
    geom = shape(json.loads(Path(path).read_bytes()))
    if geom.geom_type != 'LineString' or geom.is_empty:
        raise ValueError('expected nonempty line')
    return geom


def bounds_for(a, b):
    x0 = min(a.bounds[0], b.bounds[0]); y0 = min(a.bounds[1], b.bounds[1])
    x1 = max(a.bounds[2], b.bounds[2]); y1 = max(a.bounds[3], b.bounds[3])
    xc, yc = (x0+x1)/2, (y0+y1)/2
    dx, dy = (x1-x0)*1.15, (y1-y0)*1.15
    ratio = 540 / 440
    coslat = math.cos(math.radians(yc))
    if dx*coslat/dy < ratio:
        dx = dy*ratio/coslat
    else:
        dy = dx*coslat/ratio
    return xc-dx/2, yc-dy/2, xc+dx/2, yc+dy/2


def terrain_image(path, bounds):
    with rasterio.open(path) as d:
        if not d.crs or d.crs.to_epsg() != 4326:
            raise ValueError('elevation grid must use EPSG:4326')
        window = from_bounds(*bounds, transform=d.transform)
        z = d.read(1, window=window, out_shape=(440, 540), boundless=True,
                   masked=True, resampling=Resampling.bilinear)
    values = np.asarray(z.astype(float).filled(np.nan), dtype=float)
    invalid = ~np.isfinite(values)
    valid = values[~invalid]
    if not valid.size:
        raise ValueError('no valid elevation in requested bounds')
    lo, hi = np.percentile(valid, [2, 98])
    norm = np.clip((values - lo) / max(1., hi-lo), 0, 1)
    norm[invalid] = 0
    # Soft relief palette; data gaps are neutral gray, not classified water.
    rgb = np.stack([245-70*norm, 244-65*norm, 239-55*norm]).astype('uint8')
    rgb[:, invalid] = np.array([225, 228, 229], dtype='uint8')[:, None]
    with MemoryFile() as mem:
        with mem.open(driver='PNG', width=540, height=440, count=3, dtype='uint8') as out:
            out.write(rgb)
        return base64.b64encode(mem.read()).decode('ascii')


def water_features(files, extent):
    seen = set(); result = []; clip = box(*extent)
    for name in files:
        root = ET.parse(name).getroot()
        nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
        for w in root.findall('way'):
            tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
            if not (tags.get('waterway') in {'river', 'stream', 'riverbank', 'canal'} or tags.get('natural') == 'water'):
                continue
            ident = (w.get('id'), w.get('version'))
            refs = [n.get('ref') for n in w.findall('nd')]
            if ident in seen or len(refs) < 2 or any(n not in nodes for n in refs):
                continue
            seen.add(ident); coords = [nodes[n] for n in refs]
            geom = LineString(coords); area = False
            if len(refs) >= 4 and refs[0] == refs[-1] and (tags.get('natural') == 'water' or tags.get('waterway') == 'riverbank'):
                poly = Polygon(coords)
                if poly.is_valid:
                    geom, area = poly, True
            if geom.intersects(clip):
                result.append((geom.intersection(clip), area))
    return result


def paths(geom, bounds, xoff, yoff):
    x0,y0,x1,y1 = bounds
    def xy(p):
        return (xoff+(p[0]-x0)/(x1-x0)*540, yoff+(y1-p[1])/(y1-y0)*440)
    def one(coords):
        points = [xy(p) for p in coords]
        return 'M' + ' L'.join('%.2f,%.2f' % q for q in points)
    if geom.is_empty:
        return []
    if geom.geom_type in ('LineString', 'LinearRing'):
        return [one(geom.coords)]
    if geom.geom_type == 'Polygon':
        return [one(geom.exterior.coords) + ' Z']
    if hasattr(geom, 'geoms'):
        return [v for g in geom.geoms for v in paths(g, bounds, xoff, yoff)]
    return []


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('selected', 'candidate', 'elevation', 'title', 'source-label', 'output'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--water', action='append', default=[])
    a = p.parse_args(); old, new = line(a.selected), line(a.candidate)
    bounds = bounds_for(old, new); image = terrain_image(a.elevation, bounds)
    water = water_features(a.water, bounds)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="655" viewBox="0 0 1200 655" role="img">',
           '<rect width="1200" height="655" fill="#f5f7f8"/>',
           '<text x="30" y="38" font-family="Arial" font-size="27" font-weight="bold" fill="#192c3a">'+html.escape(a.title)+'</text>',
           '<text x="30" y="63" font-family="Arial" font-size="14" fill="#415869">Same extent in both panels; proposed route is not selected.</text>']
    for index, (label, geom, color) in enumerate((('BEFORE · current line',old,'#d1493f'), ('AFTER · proposed line',new,'#006f78'))):
        xoff = 30 + index*600; yoff = 102
        out += [f'<text x="{xoff}" y="91" font-family="Arial" font-size="16" font-weight="bold" fill="{color}">{label}</text>',
                f'<image x="{xoff}" y="{yoff}" width="540" height="440" href="data:image/png;base64,{image}"/>']
        for geom0, area in water:
            for path in paths(geom0, bounds, xoff, yoff):
                fill = '#94cde1' if area else 'none'
                out.append(f'<path d="{path}" fill="{fill}" stroke="#5aaac5" stroke-width="1.2" opacity=".85"/>')
        for path in paths(geom, bounds, xoff, yoff):
            out += [f'<path d="{path}" fill="none" stroke="white" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>',
                    f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>']
        out += [f'<rect x="{xoff}" y="{yoff}" width="540" height="440" fill="none" stroke="#9dadb4"/>',
                f'<text x="{xoff+8}" y="{yoff+20}" font-family="Arial" font-size="13" font-weight="bold" fill="#263f4c">N ↑</text>',
                f'<text x="{xoff}" y="{yoff+460}" font-family="Arial" font-size="11" fill="#50636d">{bounds[0]:.3f}°E</text>',
                f'<text x="{xoff+475}" y="{yoff+460}" font-family="Arial" font-size="11" fill="#50636d">{bounds[2]:.3f}°E</text>',
                f'<text x="{xoff+5}" y="{yoff+435}" font-family="Arial" font-size="11" fill="#50636d">{bounds[1]:.3f}°N</text>',
                f'<text x="{xoff+5}" y="{yoff+35}" font-family="Arial" font-size="11" fill="#50636d">{bounds[3]:.3f}°N</text>']
    out += ['<text x="30" y="596" font-family="Arial" font-size="13" fill="#314957">Blue: mapped OSM water; shaded background: '+html.escape(a.source_label)+'. Gray means missing elevation.</text>',
            '<text x="30" y="618" font-family="Arial" font-size="13" fill="#314957">Mapped water is incomplete; terrain shading does not prove drainage. Cell counts require the current land mask.</text>',
            '</svg>']
    Path(a.output).write_text('\n'.join(out), encoding='utf-8')


if __name__ == '__main__':
    main()
