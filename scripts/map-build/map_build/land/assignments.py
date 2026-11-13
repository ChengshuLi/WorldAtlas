"""Assign non-mainland components by complete WGS84 minimum-distance search."""

import json
from pathlib import Path
import time

import numpy as np
from scipy.spatial import cKDTree

from map_build.core.layers import file_hash
from map_build.land.certificates import CertificateIndex
from map_build.land.exact_search import ExactIndex
from map_build.land.hints import _xyz, wgs84_nearest_categories
from map_build.land import search_engine as engine


def assign_components(
    components,
    seed_report,
    index_directory,
    bindings,
    directory,
    *,
    tie_metres,
    guard_metres=1000.0,
    chunk_columns=1024
):
    """Return stable entity assignments; component IDs remain run-local data."""
    started = time.monotonic()
    grid, index_directory, directory = components.grid, Path(index_directory), Path(directory)
    metadata = json.loads((index_directory / 'report.json').read_text())
    if metadata['grid'] != vars(grid) or not np.isfinite(tie_metres) or tie_metres < 0:
        raise ValueError('distance policy or seed index grid differs')
    representatives_path = index_directory / 'representatives.u32le'
    if file_hash(representatives_path) != metadata['representatives_sha256']:
        raise ValueError('representative seed cells differ from their index')
    representatives = np.fromfile(representatives_path, dtype='<u4').reshape(-1, 3)
    tiles = metadata['tiles']
    exact = ExactIndex(
        index_directory,
        grid.width,
        grid.height,
        grid.step,
        grid.north,
        tiles,
        tile_cells=metadata['tile_cells'],
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
        tile_cells=metadata['tile_cells'],
        numerical_guard_m=guard_metres,
        refinement=fine,
    )
    mainland = {
        g['component_id'] for g in seed_report['groups'].values() if g['role'] == 'mainland'
    }
    roots = np.array(sorted(components.totals().keys() - mainland), dtype=np.uint32)
    times = dict(index_seconds=time.monotonic() - started)
    codes = np.empty(0, dtype=np.uint32)
    ambiguous, exact_queries, certificate_queries, ties = np.zeros(len(roots), dtype=bool), 0, 0, []
    if len(roots):
        stamp = time.monotonic()
        # Both the samples and the component coordinates are actual grid cells.
        ys, xs = engine.first_points(
            components.directory / 'runs.u32le',
            components.offsets,
            roots,
            list(mainland),
            grid.width,
        )
        latitude, longitude = grid.latitude(representatives[:, 0]), grid.longitude(
            representatives[:, 1]
        )
        tree = cKDTree(_xyz(latitude, longitude))
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
            components.directory / 'runs.u32le',
            components.offsets,
            roots,
            list(mainland),
            grid.width,
            certificate,
            hints,
        )
        times['witness_seconds'] = time.monotonic() - stamp
        stamp = time.monotonic()
        ambiguous, certificate_queries, _ = engine.certificate_pass(
            components.directory / 'runs.u32le',
            components.offsets,
            roots,
            list(mainland),
            certificate,
            upper,
            hints,
            ambiguous,
            chunk=chunk_columns,
            tolerance=tie_metres,
        )
        times['certificate_seconds'] = time.monotonic() - stamp
        best = np.full((len(roots), len(exact.codes)), np.inf)
        best[np.arange(len(roots)), np.searchsorted(exact.codes, hints)] = upper
        stamp = time.monotonic()
        best, exact_queries, _ = engine.exact_pass(
            components.directory / 'runs.u32le',
            components.offsets,
            roots,
            list(mainland),
            exact,
            hints,
            ambiguous,
            best,
            chunk=chunk_columns,
            tolerance=tie_metres,
        )
        codes, ties = engine.finalize(hints, ambiguous, best, exact.codes, tolerance=tie_metres)
        times['exact_seconds'] = time.monotonic() - stamp
    entities = {b['code']: b['entity_id'] for b in bindings if b['physical_class'] == 'land'}
    directory.mkdir()
    roots.astype('<u4').tofile(directory / 'roots.u32le')
    np.array([entities[int(code)] for code in codes], dtype='<i8').tofile(
        directory / 'entities.i64le'
    )
    result = dict(
        grid=vars(grid),
        roots=str(directory / 'roots.u32le'),
        entities=str(directory / 'entities.i64le'),
        assigned_components=len(roots),
        exact_components=int(ambiguous.sum()),
        certificate_queries=certificate_queries,
        exact_queries=exact_queries,
        ties=ties,
        phase_seconds=times,
        processing_seconds=time.monotonic() - started,
        download_seconds=0.0,
        output_sha256={
            name: file_hash(directory / name) for name in ('roots.u32le', 'entities.i64le')
        },
    )
    (directory / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def read_assignments(report):
    roots, entities = Path(report['roots']), Path(report['entities'])
    for path in (roots, entities):
        if file_hash(path) != report['output_sha256'][path.name]:
            raise ValueError('component assignment file differs')
    a, b = np.fromfile(roots, dtype='<u4'), np.fromfile(entities, dtype='<i8')
    if len(a) != len(b) or len(a) != report['assigned_components'] or np.any(a[1:] <= a[:-1]):
        raise ValueError('component assignments need unique ordered roots and entity IDs')
    return dict(zip(map(int, a), map(int, b)))
