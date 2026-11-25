"""Find every pair of labels within a fixed distance on the flat map."""

from collections import deque
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import combinations, groupby
from math import isqrt
from pathlib import Path

import numpy as np
from numba import njit

from worldatlas.map_build.core.distances import wrapped_column_gap
from worldatlas.map_build.core.grid import Grid, column_windows
from worldatlas.map_build.core.rle import merge_adjacent_runs, open_grid, row
from worldatlas.map_build.core.tiles import split_runs_into_tile_columns
from worldatlas.map_build.execution.control import check_cancelled

NEIGHBOR_DISTANCE_DEGREES = 2


@dataclass(frozen=True)
class LabelRuns:
    """Hold one tile's runs for a label and the bounds of those runs.

    Bounds include both end rows. The right column bound is exclusive.
    """

    records: np.ndarray
    left: int
    right: int
    top: int
    bottom: int


def display_row(
    streams: tuple[np.ndarray, np.ndarray], grid: Grid, y: int, land: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Read a row, representing all water with code zero.

    Args:
        streams: Row offsets and run data for the final grid.
        grid: Dimensions of the final grid.
        y: Row index from the north edge.
        land: Sorted uint32 array of land codes, with at least one entry.

    Returns:
        Matching uint32 arrays of exclusive run ends and display codes.
    """
    ends, codes = row(streams, y, grid.width)
    matching = land.take(land.searchsorted(codes), mode="clip")
    display_codes = np.where(matching == codes, codes, np.uint32(0))
    return merge_adjacent_runs(ends, display_codes)


@njit(cache=True)
def row_boundary_runs(
    current: tuple[np.ndarray, np.ndarray],
    north: tuple[np.ndarray, np.ndarray],
    south: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    """Find cells in the middle row with a different code across a cell edge.

    Args:
        current: Exclusive run ends and display codes for the middle row.
        north: Same arrays for the row above. Use current at the north edge.
        south: Same arrays for the row below. Use current at the south edge.

    Returns:
        N-by-3 uint32 records of (start, exclusive end, display code).
    """
    ends, codes = current
    north_ends, north_codes = north
    south_ends, south_codes = south
    # Advancing to a run end in any row creates at most one interval.
    # Each current run can also contribute its first and last cells.
    records = np.empty(
        (3 * len(ends) + len(north_ends) + len(south_ends), 3), dtype=np.uint32
    )
    count = above = below = left = 0
    for run, end_value in enumerate(ends):
        start, end = left, int(end_value)
        code = codes[run]
        different_on_left = codes[run - 1] != code
        different_on_right = codes[(run + 1) % len(codes)] != code
        while left < end:
            right = min(end, int(north_ends[above]), int(south_ends[below]))
            if code != north_codes[above] or code != south_codes[below]:
                records[count, 0] = left
                records[count, 1] = right
                records[count, 2] = code
                count += 1
            else:
                if left == start and different_on_left:
                    records[count, 0] = left
                    records[count, 1] = left + 1
                    records[count, 2] = code
                    count += 1
                if right == end and different_on_right:
                    records[count, 0] = right - 1
                    records[count, 1] = right
                    records[count, 2] = code
                    count += 1
            above += int(right == north_ends[above])
            below += int(right == south_ends[below])
            left = right
    return records[:count]


def boundary_rows(
    streams: tuple[np.ndarray, np.ndarray], grid: Grid, land: np.ndarray
) -> Iterator[tuple[int, np.ndarray]]:
    """Read runs on both sides of every change from one display code to another.

    At least one closest pair of cells between any two distinct codes lies on
    their boundaries. An interior cell could take one grid step toward the
    other cell while keeping its code, which would make the pair closer.

    Args:
        streams: Row offsets and run data for the final grid.
        grid: Dimensions of the final grid. Only longitude wraps.
        land: Sorted nonempty uint32 array of land codes.

    Yields:
        (row index, N-by-3 uint32 array) for rows with boundary cells. Each
        record is (start column, exclusive end column, display code).
    """
    north = current = display_row(streams, grid, 0, land)
    for y in range(grid.height):
        south = (
            display_row(streams, grid, y + 1, land) if y + 1 < grid.height else current
        )
        records = row_boundary_runs(current, north, south)
        if len(records):
            yield y, records
        north, current = current, south


def group_tile_runs(
    parts: list[np.ndarray], side: int
) -> dict[int, dict[int, LabelRuns]]:
    """Group the clipped runs in a tile row by tile column and display code.

    Args:
        parts: Arrays in row order with (row, start, end, code).
        side: Width of a tile in cells.

    Returns:
        Tile column mapped to the runs and bounds for each code in that tile.
    """
    rows, starts, ends, codes = np.concatenate(parts).T
    source, columns, starts, ends = split_runs_into_tile_columns(starts, ends, side)
    # Sort by tile then code, keeping row order within each group.
    keys = (columns.astype(np.uint64) << 32) | codes[source]
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    records = np.column_stack((rows[source[order]], starts[order], ends[order]))
    cuts = np.r_[0, np.flatnonzero(keys[:-1] != keys[1:]) + 1, len(keys)]
    tiles: dict[int, dict[int, LabelRuns]] = {}
    for first, last in zip(cuts[:-1], cuts[1:]):
        key = int(keys[first])
        cells = records[first:last]
        tiles.setdefault(key >> 32, {})[key & 0xFFFFFFFF] = LabelRuns(
            cells,
            int(cells[:, 1].min()),
            int(cells[:, 2].max()),
            int(cells[0, 0]),
            int(cells[-1, 0]),
        )
    return tiles


def boundary_tile_rows(
    streams: tuple[np.ndarray, np.ndarray], grid: Grid, land: np.ndarray, side: int
) -> Iterator[tuple[int, dict[int, dict[int, LabelRuns]]]]:
    """Collect boundary runs in bands of one tile height.

    Args:
        streams: Row offsets and run data for the final grid.
        grid: Dimensions of the final grid.
        land: Sorted nonempty uint32 array of land codes.
        side: Length of a tile side in cells.

    Yields:
        (tile row, mapping of tile columns to runs by code) from north to south.
    """
    rows = boundary_rows(streams, grid, land)
    for band, band_rows in groupby(rows, key=lambda item: item[0] // side):
        parts = [
            np.column_stack((np.full(len(records), y, dtype=np.uint32), records))
            for y, records in band_rows
        ]
        yield band, group_tile_runs(parts, side)


@njit(cache=True)
def runs_within_distance(
    first: np.ndarray, second: np.ndarray, width: int, radius: int, radius_squared: int
) -> bool:
    """Find whether any two runs contain cell centers within the cutoff.

    Args:
        first: First N-by-3 array of (row, start, exclusive end), sorted by row.
        second: Matching run format for the other label.
        width: Number of columns in one full turn.
        radius: Largest possible absolute row gap in cells.
        radius_squared: Squared cutoff in cell spacings, rounded down.

    Returns:
        True if a pair qualifies. Only the candidate rows within radius are read.
    """
    start = 0
    for y, left, right in first:
        while start < len(second) and second[start, 0] < y - radius:
            start += 1
        for index in range(start, len(second)):
            other_y, other_left, other_right = second[index]
            dy = int(other_y) - int(y)
            if dy > radius:
                break
            dx = wrapped_column_gap(left, right, other_left, other_right, width)
            if dx * dx + dy * dy <= radius_squared:
                return True
    return False


def add_tile_neighbors(
    pairs: set[tuple[int, int]],
    first: dict[int, LabelRuns],
    second: dict[int, LabelRuns],
    width: int,
    radius: int,
    radius_squared: int,
) -> None:
    """Add previously unconfirmed pairs that have a match across two tiles.

    Args:
        pairs: Confirmed pairs in ascending code order. Updated in place.
        first: Runs grouped by display code in the first tile.
        second: Runs grouped by display code in the second tile.
        width: Number of columns in one full turn.
        radius: Largest possible row gap in cells.
        radius_squared: Squared cutoff in cell spacings, rounded down.
    """
    for code, runs in first.items():
        for other_code, other in second.items():
            pair = (min(code, other_code), max(code, other_code))
            if code == other_code or pair in pairs:
                continue
            dy = max(0, runs.top - other.bottom, other.top - runs.bottom)
            dx = wrapped_column_gap(
                runs.left, runs.right, other.left, other.right, width
            )
            # Bounds can rule out a pair. Confirm the others using actual runs.
            if dx * dx + dy * dy <= radius_squared and runs_within_distance(
                runs.records, other.records, width, radius, radius_squared
            ):
                pairs.add(pair)


def scan_color_neighbors(
    directory: Path,
    grid: Grid,
    land_codes: Sequence[int],
    *,
    distance_degrees: int = NEIGHBOR_DISTANCE_DEGREES,
) -> tuple[set[tuple[int, int]], set[int]]:
    """Find all labels with a pair of cell centers within the flat-map cutoff.

    Args:
        directory: Finished grid directory containing the decoded row runs.
        grid: Grid dimensions. Columns wrap at the antimeridian.
        land_codes: Map codes with physical class land.
        distance_degrees: Nonnegative radius in degrees along the grid axes.

    Returns:
        (Ascending land-code pairs, land codes near water). All water counts
        as one label. A single qualifying cell is enough to confirm a pair.
    """
    # Each squared distance is an integer in cell spacings. Convert the cutoff
    # exactly using width / 360, including pairs that fall right on the cutoff.
    radius_squared = (grid.width * distance_degrees) ** 2 // 360**2
    if not land_codes or not radius_squared:
        return set(), set()
    radius = isqrt(radius_squared)
    side = isqrt(radius_squared // 2) + 1
    land = np.array(sorted(land_codes), dtype=np.uint32)
    pairs: set[tuple[int, int]] = set()
    bands: deque[tuple[int, dict[int, dict[int, LabelRuns]]]] = deque()
    with open_grid(directory, grid) as streams:
        for y, tiles in boundary_tile_rows(streams, grid, land, side):
            check_cancelled()
            while bands and y * side - ((bands[0][0] + 1) * side - 1) > radius:
                bands.popleft()
            bands.append((y, tiles))
            for codes in tiles.values():
                # Even opposite corners fit inside the cutoff for one tile.
                pairs.update(combinations(sorted(codes), 2))
            for x, codes in tiles.items():
                left, right = (
                    x * side - radius,
                    min((x + 1) * side, grid.width) + radius,
                )
                windows = column_windows(
                    left, min(right, left + grid.width), grid.width
                )
                nearby_columns = {
                    column
                    for start, stop in windows
                    for column in range(start // side, (stop - 1) // side + 1)
                }
                for other_y, other_tiles in bands:
                    for other_x in nearby_columns:
                        if (
                            other_y == y and other_x >= x
                        ) or other_x not in other_tiles:
                            continue
                        add_tile_neighbors(
                            pairs,
                            codes,
                            other_tiles[other_x],
                            grid.width,
                            radius,
                            radius_squared,
                        )
    return (
        {(first, second) for first, second in pairs if first != 0},
        {second for first, second in pairs if first == 0},
    )
