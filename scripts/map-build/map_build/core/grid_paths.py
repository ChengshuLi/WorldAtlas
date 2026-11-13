"""Exact closed-cell contacts along selected geographic line segments."""

from fractions import Fraction


def interval_cells(a, b):
    lo, hi = sorted((a, b))
    return range(
        lo.numerator // lo.denominator - (lo.denominator == 1), hi.numerator // hi.denominator + 1
    )


def touched_segment(x0, y0, x1, y1):
    """Yield every closed grid square intersecting a rational segment."""
    for y in interval_cells(y0, y1):
        dy = y1 - y0
        if dy == 0:
            xa, xb = x0, x1
        else:
            t0 = max(Fraction(0), min((Fraction(y) - y0) / dy, (Fraction(y + 1) - y0) / dy))
            t1 = min(Fraction(1), max((Fraction(y) - y0) / dy, (Fraction(y + 1) - y0) / dy))
            if t0 > t1:
                continue
            xa, xb = x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1
        for x in interval_cells(xa, xb):
            yield x, y


def grid_points(coordinates, grid):
    step = Fraction(str(grid.step))
    return [
        (
            (Fraction(str(lon)) - Fraction(str(grid.west))) / step,
            (Fraction(str(grid.north)) - Fraction(str(lat))) / step,
        )
        for lon, lat in coordinates
    ]
