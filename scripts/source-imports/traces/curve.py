"""Interpolate and smooth a boundary defined by north-to-south control points."""
import math

import numpy as np
from scipy.ndimage import gaussian_filter1d


def positive_number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a finite positive number')
    return float(value)


def construct(points, step_latitude_degrees, smoothing_latitude_degrees):
    """Return one final line; all geographic choices belong in the input points."""
    step = positive_number(step_latitude_degrees, 'step_latitude_degrees')
    sigma = positive_number(smoothing_latitude_degrees, 'smoothing_latitude_degrees')
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError('at least two control points are required')
    for point in points:
        if (not isinstance(point, list) or len(point) != 2
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in point)
                or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90):
            raise ValueError('invalid longitude/latitude control point')
    if any(a[1] <= b[1] for a, b in zip(points, points[1:])):
        raise ValueError('control points must run strictly north to south')
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(points, points[1:])):
        raise ValueError('antimeridian-crossing traces are unsupported')
    latitudes = np.array([p[1] for p in reversed(points)], dtype=float)
    longitudes = np.array([p[0] for p in reversed(points)], dtype=float)
    ys = np.linspace(latitudes[0], latitudes[-1],
                     math.ceil((latitudes[-1] - latitudes[0]) / step) + 1)
    delta = ys[1] - ys[0]
    raw = np.interp(ys, latitudes, longitudes)
    result = gaussian_filter1d(raw, sigma / delta, mode='nearest')
    t0 = np.clip((ys - ys[0]) / (4 * sigma), 0, 1)
    t1 = np.clip((ys[-1] - ys) / (4 * sigma), 0, 1)
    w0 = 1 - 3 * t0 * t0 + 2 * t0 * t0 * t0
    w1 = 1 - 3 * t1 * t1 + 2 * t1 * t1 * t1
    result += (raw[0] - result[0]) * w0 + (raw[-1] - result[-1]) * w1
    result[0], result[-1] = raw[0], raw[-1]
    return {'type': 'LineString',
            'coordinates': [[float(x), float(y)] for x, y in zip(result[::-1], ys[::-1])]}
