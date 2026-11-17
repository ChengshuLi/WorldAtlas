"""Reuse an aligned northern prefix of verified physical row-run outputs."""

import json
from pathlib import Path
import time

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import file_hash
from worldatlas.map_build.core.rle import open_grid, row


def crop_physical(source, grid, directory):
    started = time.monotonic()
    source = Path(source)
    directory = Path(directory)
    original = json.loads((source / "report.json").read_text())
    old = Grid(**original["grid"])
    if (
        any(
            getattr(grid, k) != getattr(old, k)
            for k in ("width", "step", "west", "north")
        )
        or grid.height > old.height
    ):
        raise ValueError("physical reuse requires an aligned northern prefix")
    directory.mkdir()
    removed_land = 0
    with open_grid(source, old) as physical:
        offsets, runs = physical
        stop = int(offsets[grid.height]) * 2
        for y in range(grid.height, old.height):
            ends, kinds = row(physical, y, grid.width)
            removed_land += int(np.diff(np.r_[0, ends])[kinds == 17].sum())
        offsets[: grid.height + 1].tofile(directory / "rows.u32le")
        with (directory / "runs.u32le").open("xb") as output:
            for first in range(0, stop, 1 << 20):
                runs[first : min(stop, first + (1 << 20))].tofile(output)
    result = dict(
        status="candidate-only",
        grid=vars(grid),
        candidate_dry_cells=original["candidate_dry_cells"] - removed_land,
        source_directory=str(source.resolve()),
        source_grid=vars(old),
        removed_cells=old.width * (old.height - grid.height),
        removed_land_cells=removed_land,
        output_sha256={
            name: file_hash(directory / name) for name in ("rows.u32le", "runs.u32le")
        },
        processing_seconds=time.monotonic() - started,
        download_seconds=0.0,
    )
    (directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
