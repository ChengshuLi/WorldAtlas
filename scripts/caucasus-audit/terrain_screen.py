#!/usr/bin/env python3
"""Screen line samples against source DSM and quality masks; no selection changes."""
import argparse
import json
import math
from pathlib import Path
from osgeo import gdal, osr

OFFSETS = (-1000, -500, -250, -100, 0, 100, 250, 500, 1000)


def classify(a, center, b):
    if any(value is None for value in (a, center, b)):
        return 'excluded'
    if center > a and center > b:
        return 'higher_than_both'
    if center < a and center < b:
        return 'lower_than_both'
    if a < center < b or a > center > b:
        return 'monotonic'
    return 'tie'


def raster_point(ds, longitude, latitude):
    transform = ds.GetGeoTransform()
    inv = gdal.InvGeoTransform(transform)
    col, row = gdal.ApplyGeoTransform(inv, longitude, latitude)
    col, row = math.floor(col), math.floor(row)
    if not (0 <= col < ds.RasterXSize and 0 <= row < ds.RasterYSize):
        return None
    return int(ds.GetRasterBand(1).ReadAsArray(col, row, 1, 1)[0, 0])


def read_tiles(specs):
    tiles = {}
    for spec in specs:
        name, dsm_path, mask_path = spec.split(':', 2)
        if len(name) != 7 or name[0] != 'N' or name[3] != 'E':
            raise ValueError('tile name must be NddEddd')
        key = (int(name[1:3]), int(name[4:7]))
        if key in tiles:
            raise ValueError('duplicate tile ' + name)
        dsm, mask = gdal.Open(dsm_path), gdal.Open(mask_path)
        if dsm is None or mask is None:
            raise ValueError('could not open both rasters for ' + name)
        if (dsm.RasterXSize, dsm.RasterYSize, dsm.GetGeoTransform()) != (mask.RasterXSize, mask.RasterYSize, mask.GetGeoTransform()):
            raise ValueError('DSM and mask grids differ for ' + name)
        gt = dsm.GetGeoTransform()
        if not (abs(gt[0] - key[1]) < 1e-7 and abs(gt[3] - (key[0] + 1)) < 1e-7 and abs(gt[2]) < 1e-12 and abs(gt[4]) < 1e-12 and gt[1] > 0 and gt[5] < 0 and abs(gt[1] * dsm.RasterXSize - 1) < 1e-7 and abs(gt[5] * dsm.RasterYSize + 1) < 1e-7):
            raise ValueError('raster bounds do not match named 1-degree tile ' + name)
        tiles[key] = (dsm, mask)
    return tiles


def sample_point(tiles, longitude, latitude):
    key = (math.floor(latitude), math.floor(longitude))
    if key not in tiles:
        return {'status': 'missing_tile', 'tile': list(key)}
    dsm, mask = tiles[key]
    value = raster_point(dsm, longitude, latitude)
    quality = raster_point(mask, longitude, latitude)
    valid = quality == 0 and value is not None and value != -9999
    return {'status': 'valid_mask_0' if valid else 'excluded_mask_or_nodata',
            'tile': list(key), 'longitude': longitude, 'latitude': latitude,
            'height_m': value, 'mask': quality}


def transformer(epsg):
    geographic = osr.SpatialReference()
    geographic.ImportFromEPSG(4326)
    geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(epsg)
    if not projected.IsProjected() or abs(projected.GetLinearUnits() - 1.0) > 1e-9:
        raise ValueError('offset CRS must be projected and measured in metres')
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return osr.CoordinateTransformation(geographic, projected), osr.CoordinateTransformation(projected, geographic)


def screen(features, vertices, tiles, section, epsg):
    forward, reverse = transformer(epsg)
    output = []
    for feature in features:
        properties = feature['properties']
        if properties['section'] != section:
            continue
        lon, lat = feature['geometry']['coordinates']
        x, y = forward.TransformPoint(lon, lat)[:2]
        idx = properties['source_edge_index']
        ax, ay = forward.TransformPoint(*vertices[idx])[:2]
        bx, by = forward.TransformPoint(*vertices[idx + 1])[:2]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        if not norm:
            raise ValueError(f'zero-length source edge at index {idx}')
        dx, dy = dx / norm, dy / norm
        offsets = {}
        for offset in OFFSETS:
            lon2, lat2 = reverse.TransformPoint(x - dy * offset, y + dx * offset)[:2]
            offsets[str(offset)] = sample_point(tiles, lon2, lat2)
        output.append({'distance_m': properties['distance_along_section_m'],
                       'coordinates': [lon, lat], 'offsets': offsets})
    return output


def summary(results, distance):
    counts = {'higher_than_both': 0, 'lower_than_both': 0, 'monotonic': 0, 'tie': 0, 'excluded': 0}
    for result in results:
        entries = [result['offsets'][str(k)] for k in (-distance, 0, distance)]
        values = [entry.get('height_m') if entry['status'] == 'valid_mask_0' else None for entry in entries]
        counts[classify(*values)] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', required=True, help='Input GeoJSON point features with section and source_edge_index properties')
    parser.add_argument('--line', required=True, help='Input GeoJSON LineString geometry')
    parser.add_argument('--tile', action='append', required=True, help='NddEddd:DSM.tiff:MSK.tiff; repeat for each tile')
    parser.add_argument('--section', type=int, required=True)
    parser.add_argument('--epsg', type=int, required=True, help='Suitable local projected CRS for metric offsets')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    features = json.loads(Path(args.samples).read_text())['features']
    line = json.loads(Path(args.line).read_text())
    if line.get('type') != 'LineString':
        raise ValueError('line must be a GeoJSON LineString geometry')
    results = screen(features, line['coordinates'], read_tiles(args.tile), args.section, args.epsg)
    output = {'method': 'Point samples and nearest raster pixels, not proof of watershed or continuous alignment. Mask 0 only; surface model may include vegetation and buildings.',
              'section': args.section, 'projected_epsg': args.epsg,
              'summary': {str(d): summary(results, d) for d in (250, 500, 1000)}, 'samples': results}
    Path(args.output).write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    gdal.UseExceptions()
    main()
