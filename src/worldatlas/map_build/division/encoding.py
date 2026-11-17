"""Encode entity ownership and physical class only when packaging a map grid."""

from contextlib import ExitStack
import numpy as np

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.intervals import overlay, spans


def encode(grid, physical_directory, ownership_directory, bindings, directory):
    pairs = sorted(
        ((b["entity_id"] << 1) | (b["physical_class"] == "land"), b["code"])
        for b in bindings
    )
    keys = np.asarray([k for k, _ in pairs], dtype=np.uint64)
    codes = np.asarray([c for _, c in pairs], dtype=np.uint32)
    if not len(keys) or np.any(keys[1:] == keys[:-1]):
        raise ValueError("ambiguous map category bindings")
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        ownership = resources.enter_context(open_grid(ownership_directory, grid))

        def rows():
            for y in range(grid.height):
                starts, ends, (kind, entity) = overlay(
                    row(physical, y, grid.width), row(ownership, y, grid.width)
                )
                lookup = (entity.astype(np.uint64) << 1) | (kind == 17).astype(
                    np.uint64
                )
                positions = np.searchsorted(keys, lookup)
                safe = np.minimum(positions, len(keys) - 1)
                valid = (positions < len(keys)) & (keys[safe] == lookup)
                if np.any((entity != 0) & ~valid):
                    raise ValueError("missing entity/physical-class map binding")
                values = np.where(entity != 0, codes[safe], 0)
                records = spans(starts, ends, values)
                if records:
                    yield y, records

        return write_layer(directory, grid, rows())
