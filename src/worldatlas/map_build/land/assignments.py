"""Assign non-mainland components by complete WGS84 minimum-distance search."""

import time
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

import numpy as np

# SciPy publishes the compiled tree without type information.
from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.land import search_engine as engine
from worldatlas.map_build.land.certificates import CertificateIndex
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.exact_search import ExactIndex
from worldatlas.map_build.land.hints import wgs84_nearest_categories
from worldatlas.shared.files import read_json, sha256_file, write_json


def assign_components(
    components: ComponentGrid,
    index_directory: Path | str,
    directory: Path | str,
    *,
    roots: Collection[int],
    priority_codes: Sequence[int] | None = None,
    guard_metres: float = 1000.0,
    chunk_columns: int = 1024,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """Assign each selected component to the owner of its nearest shore.

    Args:
        components: Physical component runs.
        index_directory: Verified reference runs and sampled reference cells.
        directory: New directory for assignments and search statistics.
        roots: Component IDs to assign.
        priority_codes: Optional order for exact distance ties.
        guard_metres: Conservative margin when excluding search candidates.
        chunk_columns: Group size when evaluating long query runs.

    Returns:
        The report and two uint32 arrays of component IDs and matching owners.
    """
    started = time.monotonic()
    grid, index_directory, directory = (
        components.grid,
        Path(index_directory),
        Path(directory),
    )
    metadata = read_json(index_directory / "report.json")
    if metadata["grid"] != vars(grid):
        raise ValueError("seed index grid differs")
    representatives_path = index_directory / "representatives.u32le"
    if sha256_file(representatives_path) != metadata["representatives_sha256"]:
        raise ValueError("representative seed cells differ from their index")
    representatives = np.fromfile(representatives_path, dtype="<u4").reshape(-1, 3)
    tiles = metadata["tiles"]
    exact = ExactIndex(
        index_directory,
        grid.width,
        grid.height,
        grid.step,
        grid.north,
        tiles,
        tile_cells=metadata["tile_cells"],
        guard_m=guard_metres,
    )
    fine = CertificateIndex(
        grid.width,
        grid.height,
        grid.step,
        grid.north,
        exact.certificate_tiles,
        representatives,
        tile_cells=exact.leaf_cells,
        numerical_guard_m=guard_metres,
    )
    certificate = CertificateIndex(
        grid.width,
        grid.height,
        grid.step,
        grid.north,
        [(ty, tx, codes) for ty, tx, codes, count, sha in tiles],
        representatives,
        tile_cells=metadata["tile_cells"],
        numerical_guard_m=guard_metres,
        refinement=fine,
    )
    roots = np.asarray(sorted(roots), dtype=np.uint32)
    if (
        len(np.unique(roots)) != len(roots)
        or set(map(int, roots)) - components.totals().keys()
    ):
        raise ValueError("query roots must identify existing parent components")
    times = dict(index_seconds=time.monotonic() - started)
    codes = np.empty(0, dtype=np.uint32)
    ambiguous, exact_queries, certificate_queries = (
        np.zeros(len(roots), dtype=bool),
        0,
        0,
    )
    if len(roots):
        stamp = time.monotonic()
        # Both the samples and the component coordinates are actual grid cells.
        ys, xs = engine.first_points(
            components.directory / "runs.u32le",
            components.offsets,
            roots,
            grid.width,
        )
        latitude, longitude = (
            grid.latitude(representatives[:, 0]),
            grid.longitude(representatives[:, 1]),
        )
        tree = cKDTree(unit_sphere(latitude, longitude))
        hints = np.empty(len(roots), dtype=np.uint32)
        for first in range(0, len(roots), 8192):
            last = min(len(roots), first + 8192)
            hints[first:last] = wgs84_nearest_categories(
                tree,
                latitude,
                longitude,
                representatives[:, 2],
                grid.latitude(ys[first:last]),
                grid.longitude(xs[first:last]),
            )
        upper = engine.component_witnesses(
            components.directory / "runs.u32le",
            components.offsets,
            roots,
            grid.width,
            certificate,
            hints,
        )
        times["witness_seconds"] = time.monotonic() - stamp
        stamp = time.monotonic()
        ambiguous, certificate_queries = engine.certificate_pass(
            components.directory / "runs.u32le",
            components.offsets,
            roots,
            certificate,
            upper,
            hints,
            ambiguous,
            chunk=chunk_columns,
        )
        times["certificate_seconds"] = time.monotonic() - stamp
        codes = hints
        if ambiguous.any():
            best = np.full((len(roots), len(exact.codes)), np.inf)
            best[np.arange(len(roots)), np.searchsorted(exact.codes, hints)] = upper
            stamp = time.monotonic()
            best, exact_queries = engine.exact_pass(
                components.directory / "runs.u32le",
                components.offsets,
                roots,
                exact,
                hints,
                ambiguous,
                best,
                chunk=chunk_columns,
            )
            codes = engine.finalize(
                hints, ambiguous, best, exact.codes, priority_codes=priority_codes
            )
            times["exact_seconds"] = time.monotonic() - stamp
    directory.mkdir()
    roots.astype("<u4").tofile(directory / "roots.u32le")
    codes.astype("<i8").tofile(directory / "entities.i64le")
    result = dict(
        grid=vars(grid),
        roots=str(directory / "roots.u32le"),
        entities=str(directory / "entities.i64le"),
        assigned_components=len(roots),
        exact_components=int(ambiguous.sum()),
        certificate_queries=certificate_queries,
        exact_queries=exact_queries,
        phase_seconds=times,
        processing_seconds=time.monotonic() - started,
        download_seconds=0.0,
        output_sha256={
            name: sha256_file(directory / name)
            for name in ("roots.u32le", "entities.i64le")
        },
    )
    write_json(directory / "report.json", result)
    return result, roots, codes
