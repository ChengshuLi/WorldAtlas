"""Test reference for crop wrapping and exhaustive full-shore fallback."""

import math

from worldatlas.map_build.core.wrapping import wrapped_grid_bounds


class StreamedWrappedClassifier:
    """Use certified WGS84 narrow results, scanning every full shore on fallback."""

    def __init__(
        self,
        classifier,
        stream_one,
        narrow_bounds,
        full_bounds,
        width,
        height,
        step,
        pairs,
        tolerance,
        narrow_indexes,
        full_blocks,
    ):
        self.classifier = classifier
        self.stream_one = stream_one
        self.narrow_bounds = narrow_bounds
        self.full_bounds = full_bounds
        self.width = width
        self.height = height
        self.step = step
        self.pairs = pairs
        self.tolerance = tolerance
        self.narrow = narrow_indexes
        self.full_blocks = full_blocks
        self.narrow_cells = 0
        self.fallback_cells = 0

    def classify(self, lat, lon):
        import numpy as np

        recoverable = (
            'query lies outside crop',
            'crop cannot certify nearest shore; increase halo',
            'crop cannot certify coastal band; increase halo',
            'crop cannot certify; increase halo',
            'missing participant shore',
        )
        if self.narrow:
            try:
                result = self.classifier(
                    lat,
                    lon,
                    self.narrow_bounds,
                    self.width,
                    self.height,
                    self.step,
                    self.pairs,
                    self.tolerance,
                    self.narrow,
                )
                self.narrow_cells += len(lat)
                return result
            except ValueError as exc:
                if str(exc) not in recoverable:
                    raise
        out = np.empty(len(lat), dtype=np.uint32)
        certified = exact = 0
        for i in range(len(lat)):
            try:
                if not self.narrow:
                    raise ValueError('missing participant shore')
                z, nc, ne = self.classifier(
                    lat[i : i + 1],
                    lon[i : i + 1],
                    self.narrow_bounds,
                    self.width,
                    self.height,
                    self.step,
                    self.pairs,
                    self.tolerance,
                    self.narrow,
                )
                out[i] = z[0]
                certified += nc
                exact += ne
                self.narrow_cells += 1
            except ValueError as exc:
                if str(exc) not in recoverable:
                    raise
                out[i] = self.stream_one(
                    float(lat[i]),
                    float(lon[i]),
                    self.full_bounds,
                    self.width,
                    self.height,
                    self.step,
                    self.pairs,
                    self.tolerance,
                    self.full_blocks,
                    self.narrow,
                )
                exact += 1
                self.fallback_cells += 1
        return out, certified, exact


def shore_blocks(shared, physical, land, bounds, width, height, step, code, rows_per_chunk=64):
    """Enumerate the complete full crop in row chunks with original neighbor halos."""
    if type(rows_per_chunk) is not int or rows_per_chunk <= 0:
        raise ValueError('invalid row chunk')
    xa, xb, ya, yb = bounds
    for first in range(ya, yb, rows_per_chunk):
        try:
            yield shared.centers_for_crop(
                physical,
                land,
                (xa, xb, first, min(first + rows_per_chunk, yb)),
                width,
                height,
                step,
                [code],
            )
        except ValueError as exc:
            if str(exc) != 'no participant shorelines in crop':
                raise


def baseline_shore_order(centers, full_bounds, width, step):
    """Match full-crop row/column enumeration before constructing a wrapped tree."""
    import numpy as np

    lon = centers['lon']
    lat = centers['lat']
    if (
        lon.shape != lat.shape
        or lat.ndim != 1
        or width <= 0
        or not math.isfinite(step)
        or step <= 0
    ):
        raise ValueError('invalid shoreline centers')
    cols = np.rint((lon + 180) / step - 0.5).astype(np.int64) % width
    offset = (cols - full_bounds[0]) % width
    order = np.lexsort((offset, -lat))
    return {key: value[order] for key, value in centers.items()}
