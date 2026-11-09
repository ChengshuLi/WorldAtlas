"""Model the Copernicus drainage path into the mapped Ural spring."""

import numpy as np
from pyproj import Geod, Transformer
import rasterio
from rasterio.transform import rowcol
from rasterio.warp import Resampling, reproject

from priority_d8 import drainage
from spring_connector_graph import basin_labels


def model_spring(dem, dem_sha256, basins, spring):
    geod = Geod(ellps="WGS84")
    labels, t, geo, _ = basin_labels(
        dem, dem_sha256, None, None, basins, [59.31, 54.6, 59.56, 54.81],
        [2120068680, 2120067740, 3120001840], 30,
    )
    z = np.full(labels.shape, np.nan, dtype=np.float32)
    with rasterio.open(dem) as ds:
        reproject(
            rasterio.band(ds, 1), z, src_transform=ds.transform, src_crs=ds.crs,
            src_nodata=ds.nodata, dst_transform=t, dst_crs='EPSG:32640',
            dst_nodata=np.nan, resampling=Resampling.nearest,
        )
    valid = np.isfinite(z)
    _, _, flow = drainage(z.astype('float64'), valid, t, 'EPSG:32640')
    height, width = z.shape
    proj = Transformer.from_crs(4326, 'EPSG:32640', always_xy=True)
    r0, c0 = rowcol(t, *proj.transform(*spring))
    near = np.zeros(labels.shape, dtype=bool)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rs = slice(max(0, dr), min(height, height + dr))
        cs = slice(max(0, dc), min(width, width + dc))
        rt = slice(max(0, -dr), min(height, height - dr))
        ct = slice(max(0, -dc), min(width, width - dc))
        near[rs, cs] |= labels[rt, ct] == 1
    boundary = (labels == 2) & near
    out = {}
    for radius in (0, 1, 2, 3):
        seen = set()
        stack = []
        for r in range(max(0, r0 - radius), min(height, r0 + radius + 1)):
            for c in range(max(0, c0 - radius), min(width, c0 + radius + 1)):
                if valid[r, c] and labels[r, c] == 2:
                    stack.append((r, c))
                    seen.add(r * width + c)
        seed_count = len(stack)
        seed_ids = set(seen)
        hit = []
        hit_cells = []
        while stack:
            r, c = stack.pop()
            i = r * width + c
            if boundary[r, c]:
                lon, lat = geo.transform(*t * (c + 0.5, r + 0.5))
                hit.append(geod.inv(*spring, lon, lat)[2])
                hit_cells.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = (r + dr, c + dc)
                    if (dr or dc) and 0 <= rr < height and (0 <= cc < width):
                        j = rr * width + cc
                        if j not in seen and flow[rr, cc] == i:
                            seen.add(j)
                            stack.append((rr, cc))
        out[str(radius)] = {'seed_cells': seed_count, 'upstream_cells': len(seen), 'interface_adjacent_upstream_cells': len(hit), 'nearest_interface_cell_center_wgs84_m': min(hit) if hit else None}
        if hit_cells and radius == 0:

            def center(r, c):
                return geo.transform(*t * (c + 0.5, r + 0.5))
            candidates = []
            for rr, cc in hit_cells:
                trail = [(rr, cc)]
                current = rr * width + cc
                while current not in seed_ids:
                    current = int(flow[current // width, current % width])
                    if current < 0 or len(trail) > height * width:
                        raise ValueError('flow path fails to reach seed')
                    trail.append(divmod(current, width))
                line = [center(*v) for v in trail]
                join = geod.inv(*line[-1], *spring)[2]
                length = sum((geod.inv(*a, *b)[2] for a, b in zip(line, line[1:])))
                candidates.append((join + length, join, length, rr, cc, line))
            total, join, length, rr, cc, line = min(candidates, key=lambda x: (x[0], x[1], x[3], x[4]))
            neighbors = [(rr + dr, cc + dc) for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)) if 0 <= rr + dr < height and 0 <= cc + dc < width and (labels[rr + dr, cc + dc] == 1)]
            neighbors.sort()
            nr, nc = neighbors[0]
            edge = geo.transform(*t * ((cc + nc + 1) / 2, (rr + nr + 1) / 2))
            out[str(radius)]['candidate'] = {'flow_length_wgs84_m': length, 'spring_snap_wgs84_m': join, 'interface_half_cell_wgs84_m': geod.inv(*edge, *line[0])[2], 'interface_edge_midpoint': list(edge), 'interface_cells': [[int(rr), int(cc)], [int(nr), int(nc)]], 'method': 'minimum WGS84 flow-path plus direct spring snap among reachable interface-adjacent Ural cells; coordinate-linear edge/center lengths approximate the modeled flow', 'terrain_centers': line, 'seed_radius_cells': radius, 'status': 'research-not-selected'}
    return {'dem': 'cop', 'spring_grid_row_col': [int(r0), int(c0)], 'spring_label': int(labels[r0, c0]), 'resolution_m': 30, 'radius_cell_square': out, 'limitations': 'D8 on reprojected surface model, selected spring coordinate and local domain. Reverse connectivity of local modeled flow only; seed radius is raster pixels, not a geographic distance. No boundary selection.'}, labels, t, geo
