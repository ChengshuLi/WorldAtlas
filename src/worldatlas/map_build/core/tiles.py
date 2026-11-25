"""Split horizontal cell runs into the columns of a regular tile grid."""

import numpy as np


def split_runs_into_tile_columns(
    left: np.ndarray, right: np.ndarray, tile_cells: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Clip each run to every tile column it crosses.

    Args:
        left: One-dimensional array of inclusive start columns.
        right: Matching array of exclusive end columns, with right > left.
        tile_cells: Number of columns per tile.

    Returns:
        (source indices, tile columns, clipped starts, clipped ends). For a
        tile width of 100, [95, 105) yields [95, 100) in tile column 0 and
        [100, 105) in tile column 1. Both pieces have the same source index.
    """
    first_tiles, last_tiles = left // tile_cells, (right - 1) // tile_cells
    lengths = (last_tiles - first_tiles + 1).astype(np.int64)
    source = np.repeat(np.arange(len(left)), lengths)
    offsets = np.repeat(np.cumsum(lengths) - lengths, lengths)
    tile_columns = np.repeat(first_tiles, lengths) + np.arange(len(source)) - offsets
    starts = np.maximum(left[source], tile_columns * tile_cells)
    ends = np.minimum(right[source], (tile_columns + 1) * tile_cells)
    return source, tile_columns, starts, ends
