"""Four-neighbor, longitude-wrapped components of canonical physical RLE.

The sequential union-by-size order is deliberately identical to the original
builder, including equal-size ties. Component IDs are generation-local, but
preserving them allows byte-for-byte comparison with existing evidence.
"""

from array import array
from pathlib import Path
import os
import sys


def _read(path):
    path = Path(path)
    if path.stat().st_size % 4:
        raise ValueError('misaligned u32 stream')
    values = array('I')
    if values.itemsize != 4:
        raise RuntimeError('32-bit unsigned array elements required')
    with path.open('rb') as stream:
        values.fromfile(stream, path.stat().st_size // 4)
    if sys.byteorder != 'little':
        values.byteswap()
    return values


def _write(path, values):
    if sys.byteorder != 'little':
        values = array('I', values)
        values.byteswap()
    with Path(path).open('xb') as stream:
        values.tofile(stream)
        stream.flush()
        os.fsync(stream.fileno())


def build(
    width, height, physical_rows, physical_runs, output_rows, output_runs, *, guard=lambda: None
):
    """Build complete run-level components in-process, without a dense grid."""
    if (
        type(width) is not int
        or type(height) is not int
        or not 0 < width <= 0xFFFFFFFF
        or not 0 < height <= 0xFFFFFFFF
    ):
        raise ValueError('invalid dimensions')
    rows, runs = _read(physical_rows), _read(physical_runs)
    if len(rows) != height + 1 or rows[0] != 0 or len(runs) % 2 or rows[-1] != len(runs) // 2:
        raise ValueError('invalid stream lengths')
    parents, sizes = array('I'), array('I')
    outrows, spans = array('I', [0]), array('I')
    previous = []
    cells = 0

    def find(node):
        while parents[node] != node:
            parents[node] = parents[parents[node]]
            node = parents[node]
        return node

    def unite(a, b):
        a, b = find(a), find(b)
        if a == b:
            return
        if sizes[a] < sizes[b]:
            a, b = b, a
        parents[b] = a
        sizes[a] += sizes[b]

    for y in range(height):
        guard()
        if not rows[y] <= rows[y + 1] <= len(runs) // 2:
            raise ValueError('nonmonotonic row offsets')
        current = []
        x = last_code = 0
        for i in range(rows[y] * 2, rows[y + 1] * 2, 2):
            end, code = runs[i], runs[i + 1]
            if not x < end <= width or code not in (1, 17) or code == last_code:
                raise ValueError('invalid or noncanonical physical run')
            if code == 17:
                node = len(parents)
                if node == 0xFFFFFFFF:
                    raise ValueError('too many component runs')
                parents.append(node)
                sizes.append(1)
                current.append((x, end, node))
                spans.extend((x, end, node))
                cells += end - x
            x, last_code = end, code
        if x != width:
            raise ValueError('incomplete physical row')
        i = j = 0
        while i < len(previous) and j < len(current):
            a, b = previous[i], current[j]
            if a[0] < b[1] and b[0] < a[1]:
                unite(a[2], b[2])
            if a[1] < b[1]:
                i += 1
            else:
                j += 1
        if current and current[0][0] == 0 and current[-1][1] == width:
            unite(current[0][2], current[-1][2])
        outrows.append(len(parents))
        previous = current
    # Resolve roots only after the whole graph is known. This retains seam and
    # bridge unions that occur after an earlier row has already been scanned.
    components = 0
    for node in range(len(parents)):
        if node % 65536 == 0:
            guard()
        root = find(node)
        spans[3 * node + 2] = root
        components += root == node
    _write(output_rows, outrows)
    _write(output_runs, spans)
    return {'runs': len(parents), 'components': components, 'land_cells': cells}


def build_components(grid, physical_directory, directory):
    """Return current components and their measured output record."""
    import json
    import time
    from map_build.core.layers import file_hash

    started = time.monotonic()
    physical_directory, directory = Path(physical_directory), Path(directory)
    directory.mkdir()
    result = build(
        grid.width,
        grid.height,
        physical_directory / 'rows.u32le',
        physical_directory / 'runs.u32le',
        directory / 'rows.u32le',
        directory / 'runs.u32le',
    )
    report = dict(
        result,
        grid=vars(grid),
        output_sha256={name: file_hash(directory / name) for name in ('rows.u32le', 'runs.u32le')},
        processing_seconds=time.monotonic() - started,
    )
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
