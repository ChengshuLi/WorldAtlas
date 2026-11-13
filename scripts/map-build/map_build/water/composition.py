"""Compose water layers by declared precedence while preserving physical land."""

import numpy as np

from map_build.core.layers import write_layer
from map_build.core.rle import row


def compose(
    physical,
    land,
    groups,
    grid,
    directory,
    land_codes,
    water_codes,
    *,
    complete=False,
    prefill=None,
):
    """Earlier groups win; conflicting assignments within one group fail.

    Each group contains complete row-run layers. These can be cached layers or
    current calculations. Zero means that a layer makes no assignment.
    """
    land_codes, water_codes = set(land_codes), set(water_codes)
    if not land_codes or land_codes & water_codes or 0 in land_codes | water_codes:
        raise ValueError('land and water bindings must be distinct and nonzero')

    def rows():
        for y in range(grid.height):
            p, land_row = row(physical, y, grid.width), row(land, y, grid.width)
            base = row(prefill, y, grid.width) if prefill is not None else None
            selected = []
            for group in groups:
                layers = [row(layer, y, grid.width) for layer in group]
                selected.append(
                    [(ends, codes) for ends, codes in layers if len(codes) != 1 or codes[0] != 0]
                )
            cuts = np.unique(
                np.concatenate(
                    (
                        [0],
                        p[0],
                        land_row[0],
                        *([base[0]] if base is not None else []),
                        *(ends for group in selected for ends, _ in group),
                    )
                )
            )
            starts, ends = cuts[:-1], cuts[1:]

            def values(data):
                stops, codes = data
                return codes[np.searchsorted(stops, starts, side='right')]

            pv, lv = values(p), values(land_row)
            if np.any(~np.isin(pv, [1, 17])) or np.any((pv == 17) & ~np.isin(lv, list(land_codes))):
                raise ValueError(f'invalid physical or assigned land at row {y}')
            result = np.where(pv == 17, lv, 0).astype(np.uint32)
            if base is not None:
                v = values(base)
                if np.any((pv == 17) & (v != lv)) or np.any(
                    (pv == 1) & ~np.isin(v, [0, *water_codes])
                ):
                    raise ValueError(
                        f'prefill changes physical land or uses an unbound code at row {y}'
                    )
                result = v.copy()
            for group in selected:
                combined = np.zeros(len(starts), dtype=np.uint32)
                for layer in group:
                    v = values(layer)
                    if np.any((v != 0) & ((pv != 1) | ~np.isin(v, list(water_codes)))):
                        raise ValueError(
                            f'water layer changes physical land or uses an unbound code at row {y}'
                        )
                    if np.any((combined != 0) & (v != 0) & (combined != v)):
                        raise ValueError(f'conflicting equal-priority water assignments at row {y}')
                    combined = np.where(v != 0, v, combined)
                result = np.where(result == 0, combined, result)
            if complete and np.any(result == 0):
                raise ValueError(f'unassigned final cells at row {y}')
            changes = np.r_[True, result[1:] != result[:-1]]
            indices = np.flatnonzero(changes)
            final_ends = ends[np.r_[indices[1:] - 1, len(ends) - 1]]
            yield y, [
                (int(starts[i]), int(stop), int(result[i]))
                for i, stop in zip(indices, final_ends)
                if result[i] != 0
            ]

    return write_layer(directory, grid, rows())
