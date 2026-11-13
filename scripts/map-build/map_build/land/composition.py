"""Compose assigned land and selected geographic partitions on the native grid."""

import numpy as np

from map_build.core.geometry import rasterize, reject_boundary_centers
from map_build.core.layers import patch_rows, write_layer
from map_build.core.rle import open_grid, row
from map_build.core.wrapping import wrapped_grid_bounds


def partition_rows(partition, components, code, *, rows_per_batch=64):
    """Rasterize a selected geographic polygon, never saved comparison spans."""
    grid = components.grid
    geometry = partition['geometry']
    reject_boundary_centers(
        geometry,
        grid,
        selected=lambda x, y: components.component_at(
            float(grid.longitude(x)), float(grid.latitude(y))
        )
        is not None,
    )
    (x0, x1, y0, y1), _ = wrapped_grid_bounds(geometry, grid.width, grid.height, grid.step)
    for first in range(y0, y1, rows_per_batch):
        last = min(first + rows_per_batch, y1)
        bounds, mask = rasterize(geometry, grid, (x0, x1, first, last))
        values = np.where(mask, code, 0).astype(np.uint32)
        yield from patch_rows(values, bounds, grid)


def compose_land(
    components,
    baseline_directory,
    component_entities,
    bindings,
    directory,
    *,
    partitions=(),
    component_defaults=None
):
    """Apply current component assignments and scoped polygons during composition.

    Partitions contain geographic geometry, a target entity and optionally the
    eligible current ``component_ids``. They cannot assign physical water.
    Component defaults supply inferred distance labels where the mainland seed
    is empty. Explicit affiliations and partitions take precedence over them.
    Conflicting explicit assignments fail instead of depending on order.
    """
    grid = components.grid
    codes = {b['entity_id']: b['code'] for b in bindings if b['physical_class'] == 'land'}
    allowed = set(codes.values())
    if (
        not allowed
        or len(allowed) != len(codes)
        or any(type(code) is not int or not 0 < code < 2**32 for code in allowed)
    ):
        raise ValueError('land entities need distinct nonzero category bindings')
    component_defaults = component_defaults or {}
    if (set(component_entities) | set(component_defaults)) - components.totals().keys():
        raise ValueError('land assignment refers to a missing current component')
    roots = np.array(sorted(component_entities), dtype=np.uint32)
    assigned = np.array([codes[component_entities[int(r)]] for r in roots], dtype=np.uint32)
    default_roots = np.array(sorted(component_defaults), dtype=np.uint32)
    defaults = np.array([codes[component_defaults[int(r)]] for r in default_roots], dtype=np.uint32)
    streams = []
    for partition in partitions:
        stream = iter(partition_rows(partition, components, codes[partition['entity_id']]))
        streams.append([partition, stream, next(stream, None)])

    with open_grid(baseline_directory, grid) as baseline:

        def rows():
            for y in range(grid.height):
                physical = row(components.physical, y, grid.width)
                base = row(baseline, y, grid.width)
                spans = components.row(y)
                active = [
                    (partition, item[1])
                    for partition, _, item in streams
                    if item is not None and item[0] == y
                ]
                cuts = np.unique(
                    np.concatenate(
                        (
                            [0],
                            physical[0],
                            base[0],
                            spans[:, :2].ravel(),
                            *([a, b] for _, values in active for a, b, _ in values),
                        )
                    )
                )
                starts, ends = cuts[:-1], cuts[1:]
                dry = physical[1][np.searchsorted(physical[0], starts, side='right')] == 17
                values = base[1][np.searchsorted(base[0], starts, side='right')].copy()
                if np.any((values != 0) & ~np.isin(values, list(allowed))) or np.any(
                    values[~dry] != 0
                ):
                    raise ValueError(
                        'baseline land differs from the physical mask or entity bindings'
                    )
                component_ids = np.full(len(starts), 2**32 - 1, dtype=np.uint32)
                if len(spans):
                    locations = np.searchsorted(spans[:, 1], starts[dry], side='right')
                    component_ids[dry] = spans[locations, 2]
                if len(default_roots):
                    locations = np.searchsorted(default_roots, component_ids)
                    found = locations < len(default_roots)
                    found[found] &= default_roots[locations[found]] == component_ids[found]
                    if np.any(found & (values != 0)):
                        raise ValueError('component distance default overlaps mainland seeds')
                    values[found] = defaults[locations[found]]
                claims = np.zeros(len(starts), dtype=np.uint32)
                if len(roots):
                    locations = np.searchsorted(roots, component_ids)
                    found = locations < len(roots)
                    found[found] &= roots[locations[found]] == component_ids[found]
                    claims[found] = assigned[locations[found]]
                for partition, ranges in active:
                    eligible = dry.copy()
                    if partition.get('component_ids') is not None:
                        eligible &= np.isin(component_ids, list(partition['component_ids']))
                    for a, b, code in ranges:
                        selected = eligible & (starts >= a) & (starts < b)
                        if np.any(selected & (claims != 0) & (claims != code)):
                            raise ValueError('conflicting land component and partition assignments')
                        claims[selected] = code
                values = np.where(claims != 0, claims, values)
                if np.any(~np.isin(values[dry], list(allowed))):
                    raise ValueError('final land composition leaves physical land unassigned')
                changes = np.r_[True, values[1:] != values[:-1]]
                indices = np.flatnonzero(changes)
                stops = ends[np.r_[indices[1:] - 1, len(ends) - 1]]
                yield y, [
                    (int(starts[i]), int(end), int(values[i]))
                    for i, end in zip(indices, stops)
                    if values[i] != 0
                ]
                for record in streams:
                    if record[2] is not None and record[2][0] == y:
                        record[2] = next(record[1], None)

        return write_layer(directory, grid, rows())
