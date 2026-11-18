"""Compare complete grids and retain the exact locations of changed cells."""

from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import time

import numpy as np

from worldatlas.map_build.core.layers import file_hash
from worldatlas.map_build.core.rle import open_grid, row


def reference_lookup(reference_bindings, candidate_bindings):
    """Translate reference codes to candidate codes by entity and physical class."""

    def by_code(bindings):
        return {
            b["code"]: (b["entity_id"], b["physical_class"]) for b in bindings
        }

    reference = by_code(reference_bindings)
    candidate = by_code(candidate_bindings)
    if reference == candidate:
        return None
    candidate_codes = {category: code for code, category in candidate.items()}
    codes = sorted(reference)
    return (
        np.asarray([0, *codes], dtype=np.uint32),
        np.asarray(
            [0, *(candidate_codes.get(reference[c], -1) for c in codes)],
            dtype=np.int64,
        ),
    )


def comparable_codes(codes, lookup):
    if lookup is None:
        return codes
    keys, translated = lookup
    indices = np.searchsorted(keys, codes)
    if np.any(indices == len(keys)) or np.any(keys[indices] != codes):
        raise ValueError("reference grid uses an unknown map category code")
    return translated[indices]


def compare(
    candidate, reference, grid, directory, reference_sha256, *,
    reference_bindings=None, candidate_bindings=None,
):
    candidate, reference, directory = map(Path, (candidate, reference, directory))
    if (reference_bindings is None) != (candidate_bindings is None):
        raise ValueError("both category mappings are required to compare assignments")
    lookup = None
    if reference_bindings is not None:
        lookup = reference_lookup(reference_bindings, candidate_bindings)
    names = ("rows.u32le", "runs.u32le")
    if set(reference_sha256) != set(names):
        raise ValueError("both reference stream checksums are required")
    start = time.monotonic()
    before = {
        label: {name: file_hash(root / name) for name in names}
        for label, root in (("reference", reference), ("candidate", candidate))
    }
    if before["reference"] != reference_sha256:
        raise ValueError("reference stream checksum differs")
    directory.mkdir()
    reference_bytes = (reference / "rows.u32le").stat().st_size
    if reference_bytes % 4 or reference_bytes // 4 - 1 < grid.height:
        raise ValueError("reference must cover the complete candidate northern prefix")
    reference_grid = replace(grid, height=reference_bytes // 4 - 1)
    removed = Counter()
    changed, transitions, offsets = 0, Counter(), [0]
    bounds = None
    with (
        open_grid(candidate, grid) as new,
        open_grid(reference, reference_grid) as old,
        (directory / "changes.u32le").open("xb") as stream,
    ):
        for y in range(grid.height):
            a, b = row(old, y, grid.width), row(new, y, grid.width)
            translated = comparable_codes(a[1], lookup)
            records = []
            if not (np.array_equal(a[0], b[0]) and np.array_equal(translated, b[1])):
                ends = np.union1d(a[0], b[0])
                starts = np.r_[np.uint32(0), ends[:-1]]
                ai = np.searchsorted(a[0], starts, side="right")
                av = a[1][ai]
                bv = b[1][np.searchsorted(b[0], starts, side="right")]
                for i in np.flatnonzero(translated[ai] != bv):
                    left, right, prior, after = map(
                        int, (starts[i], ends[i], av[i], bv[i])
                    )
                    count = right - left
                    changed += count
                    transitions[f"{prior}->{after}"] += count
                    records.append((y, left, right, prior, after))
                    if bounds is None:
                        bounds = [left, right, y, y + 1]
                    else:
                        bounds = [
                            min(bounds[0], left),
                            max(bounds[1], right),
                            bounds[2],
                            y + 1,
                        ]
            np.asarray(records, dtype="<u4").tofile(stream)
            offsets.append(offsets[-1] + len(records))
        for y in range(grid.height, reference_grid.height):
            ends, codes = row(old, y, grid.width)
            for length, code in zip(np.diff(np.r_[0, ends]), codes):
                removed[str(int(code))] += int(length)
    np.asarray(offsets, dtype="<u8").tofile(directory / "change-rows.u64le")
    after = {
        label: {name: file_hash(root / name) for name in names}
        for label, root in (("reference", reference), ("candidate", candidate))
    }
    if after != before:
        raise ValueError("grid input changed during comparison")
    result = {
        "grid": {"width": grid.width, "height": grid.height, "step": grid.step},
        "changed_cells": changed,
        "reference_grid": vars(reference_grid),
        "compared_by": "map_code" if reference_bindings is None else "entity_and_physical_class",
        "removed_cells": sum(removed.values()),
        "removed_cells_by_code": dict(sorted(removed.items())),
        "assignments_identical_on_retained_grid": changed == 0,
        "pair_counts": dict(sorted(transitions.items())),
        "changed_bounds": bounds,
        "byte_identical": before["reference"] == before["candidate"],
        "input_sha256": before,
        "elapsed_seconds": time.monotonic() - start,
        "change_record_fields": ["row", "start", "end", "before_code", "after_code"],
    }
    (directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
