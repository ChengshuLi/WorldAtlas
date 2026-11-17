"""Uniform-area and multi-face assignment over the same prepared scope."""

from collections import defaultdict
import math
from pathlib import Path

import numpy as np

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.partition import geographic_cuts, divide_regions
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.scope import complete_row, selected


def assign_area(scope, target, directory):
    """Give one child every eligible cell in the supplied scope."""

    def rows():
        for y in scope.query_rows():
            ends, values = scope.query_row(y)
            starts = np.r_[0, ends[:-1]]
            output = np.where(values != 0, target, 0).astype(np.uint32)
            records = spans(starts, ends, output)
            if records:
                yield y, records

    return write_layer(directory, scope.grid, rows())


class Faces:
    def __init__(self, directory, owners, grid):
        self.grid = grid
        self.offsets = np.memmap(Path(directory) / "rows.u64le", dtype="<u8", mode="r")
        self.nodes = np.memmap(
            Path(directory) / "nodes.u32le", dtype="<u4", mode="r"
        ).reshape(-1, 3)
        self.roots = np.asarray(sorted(owners), dtype=np.uint32)
        self.owners = np.asarray(
            [owners[int(root)] for root in self.roots], dtype=np.uint32
        )

    def close(self):
        self.offsets._mmap.close()
        self.nodes._mmap.close()

    def row(self, y):
        nodes = np.asarray(self.nodes[int(self.offsets[y]) : int(self.offsets[y + 1])])
        if not len(nodes):
            return complete_row(self.grid.width, ())
        positions = np.searchsorted(self.roots, nodes[:, 2])
        safe = np.minimum(positions, len(self.roots) - 1)
        matched = (positions < len(self.roots)) & (self.roots[safe] == nodes[:, 2])
        owners = np.where(matched, self.owners[safe], 0)
        return complete_row(
            self.grid.width,
            np.column_stack((nodes[:, :2], owners)),
        )


def component_owners(scope, faces):
    """Require a majority of each eligible whole component in one labelled face."""
    results = {}
    counts = defaultdict(int)
    eligible = scope.eligible_components()
    for y in scope.query_rows():
        face = faces.row(y)
        for kind, roots in eligible.items():
            components = scope.components(kind)
            records = components.row(y)
            chosen = records[selected(records[:, 2], roots)]
            if not len(chosen):
                continue
            component = complete_row(
                scope.grid.width,
                np.column_stack((chosen[:, :2], chosen[:, 2].astype(np.uint64) + 1)),
            )
            starts, ends, (r, owner) = overlay(component, face)
            valid = (r != 0) & (owner != 0)
            keys = ((r[valid].astype(np.uint64) - 1) << 32) | owner[valid].astype(
                np.uint64
            )
            unique, inverse = np.unique(keys, return_inverse=True)
            lengths = np.zeros(len(unique), dtype=np.uint64)
            np.add.at(lengths, inverse, (ends[valid] - starts[valid]).astype(np.uint64))
            for key, n in zip(unique, lengths):
                counts[kind, int(key) >> 32, int(key) & 0xFFFFFFFF] += int(n)
    for kind, roots in eligible.items():
        totals = scope.components(kind).totals()
        by_root = defaultdict(list)
        for (which, root, owner), n in counts.items():
            if which == kind and n * 2 > totals[root]:
                by_root[root].append(owner)
        result = {}
        for root in map(int, roots):
            candidates = by_root[root]
            if len(candidates) != 1:
                raise ValueError(
                    f"rule {scope.rule['id']}: component {root} lacks one majority face"
                )
            result[root] = candidates[0]
        results[kind] = result
    return results


def divide_area(scope, boundaries, targets, directory):
    """Split context first; physical/ownership filters affect emitted cells only."""
    directory = Path(directory)
    directory.mkdir()
    grid = scope.grid
    labels = []
    for target in targets:
        lon, lat = target["point"]["geometry"]["coordinates"]
        labels.append(
            (
                target["entity_id"],
                math.floor((lon - grid.west) / grid.step) % grid.width,
                math.floor((grid.north - lat) / grid.step),
            )
        )
    cuts = geographic_cuts([f["geometry"] for f in boundaries], grid)
    owners = divide_regions(
        scope.context_intervals,
        grid,
        cuts,
        labels,
        directory / "faces",
        rows=scope.context_rows(),
    )
    faces = Faces(directory / "faces", owners, grid)
    try:
        by_component = (
            component_owners(scope, faces)
            if scope.rule["unit"] == "component"
            else None
        )
        compiled = {}
        if by_component is not None:
            for kind, values in by_component.items():
                roots = np.asarray(sorted(values), dtype=np.uint32)
                compiled[kind] = (
                    roots,
                    np.asarray([values[int(r)] for r in roots], dtype=np.uint32),
                )

        def rows():
            for y in scope.query_rows():
                query = scope.query_row(y)
                if by_component is None:
                    proposed = faces.row(y)
                else:
                    records = []
                    for kind, (roots, owners) in compiled.items():
                        pieces = scope.components(kind).row(y)
                        pieces = pieces[selected(pieces[:, 2], roots)]
                        for a, b, root in pieces:
                            entity = int(owners[np.searchsorted(roots, root)])
                            records.append((int(a), int(b), entity))
                    proposed = complete_row(grid.width, sorted(records))
                starts, ends, (eligible, owned) = overlay(query, proposed)
                missing = (eligible != 0) & (owned == 0)
                if missing.any():
                    x = int(starts[np.flatnonzero(missing)[0]])
                    raise ValueError(
                        f"rule {scope.rule['id']}: eligible cell {x},{y} has no face label"
                    )
                result = spans(starts, ends, np.where(eligible != 0, owned, 0))
                if result:
                    yield y, result

        report = write_layer(directory / "claims", grid, rows())
        report["faces"] = len(owners)
        return report
    finally:
        faces.close()
