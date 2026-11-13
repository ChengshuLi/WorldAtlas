"""Render each basin replacement with identical before/after map extents."""

from collections import Counter
from contextlib import ExitStack
import html
import json
import math
from pathlib import Path
import time

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
import numpy as np
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from map_build.core.rle import open_grid, row
from map_build.water.basins import physical_water, rasterize
from map_build.core.wrapping import wrapped_grid_bounds


def union(geometries):
    if not geometries:
        return None
    return json.loads(json.dumps(mapping(unary_union([shape(value) for value in geometries]))))


def view_bounds(geometry, grid):
    (x0, x1, y0, y1), _ = wrapped_grid_bounds(geometry, grid.width, grid.height, grid.step)
    pad = max(2, math.ceil(max(x1 - x0, y1 - y0) * 0.025))
    if x1 - x0 + 2 * pad >= grid.width:
        left, right = 0, grid.width
    else:
        left = (x0 - pad) % grid.width
        right = left + x1 - x0 + 2 * pad
    return left, right, max(0, y0 - pad), min(grid.height, y1 + pad)


def sample(data, grid, xs, ys):
    result = np.empty((len(ys), len(xs)), dtype=np.uint32)
    for i, y in enumerate(ys):
        ends, codes = row(data, int(y), grid.width)
        result[i] = codes[np.searchsorted(ends, xs % grid.width, side='right')]
    return result


def colors(values, palette):
    keys = np.asarray(sorted(palette), dtype=np.uint32)
    positions = np.searchsorted(keys, values)
    if np.any(positions >= len(keys)) or not np.array_equal(keys[positions], values):
        raise ValueError('image palette lacks a map category')
    return np.asarray([palette[int(key)] for key in keys], dtype=np.uint8)[positions]


def changes_in_window(changes, offsets, bounds, grid, footprint, image_shape):
    x0, x1, y0, y1 = bounds
    height, width = image_shape
    heat = np.zeros((height, width), dtype=bool)
    counts = Counter()
    bins = Counter()
    windows = [(x0, min(x1, grid.width))]
    if x1 > grid.width:
        windows.append((0, x1 - grid.width))
    for y in range(y0, y1):
        for _, first, last, before, after in changes[int(offsets[y]) : int(offsets[y + 1])]:
            for a, b in windows:
                left, right = max(int(first), a), min(int(last), b)
                if left >= right:
                    continue
                start = (left - x0) % grid.width
                stop = start + right - left
                n = int(np.count_nonzero(footprint[y - y0, start:stop]))
                if n:
                    counts[f'{before}->{after}'] += n
                    bins[(y // 256, (left + right) // 2 // 256)] += n
                    iy = min(height - 1, (y - y0) * height // (y1 - y0))
                    selected = np.flatnonzero(footprint[y - y0, start:stop]) + start
                    pixels = np.unique(selected * width // (x1 - x0))
                    heat[iy, pixels] = True
    return heat, dict(counts), bins


def render(
    path, label, bounds, before, after, grid, palette, heat, coverage, titles, changed, legend
):
    x0, x1, y0, y1 = bounds
    xs = np.linspace(x0, x1 - 1, heat.shape[1], dtype=np.int64)
    ys = np.linspace(y0, y1 - 1, heat.shape[0], dtype=np.int64)
    old, new = colors(sample(before, grid, xs, ys), palette), colors(
        sample(after, grid, xs, ys), palette
    )
    extent = [
        -180 + x0 * grid.step,
        -180 + x1 * grid.step,
        90 - y1 * grid.step,
        90 - y0 * grid.step,
    ]
    aspect = 1 / max(0.05, math.cos(math.radians((extent[2] + extent[3]) / 2)))
    fig, axes = plt.subplots(1, 3, figsize=(17, 7))
    fig.subplots_adjust(left=0.05, right=0.99, bottom=0.18, top=0.85, wspace=0.18)
    longitude = FuncFormatter(
        lambda value, _: f'{abs((value+180)%360-180):g}°'
        + ('W' if (value + 180) % 360 - 180 < 0 else 'E')
    )
    for ax, image, title in zip(axes, [old, new, new], [*titles, 'Coverage and changed cells']):
        ax.imshow(image, extent=extent, origin='upper', aspect=aspect, interpolation='nearest')
        ax.set_title(title, fontsize=12)
        ax.xaxis.set_major_formatter(longitude)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _: f'{abs(value):g}°' + ('S' if value < 0 else 'N'))
        )
        ax.tick_params(labelsize=8)
    overlay = np.zeros((*heat.shape, 4), dtype=np.uint8)
    overlay[coverage == 1] = [0, 170, 105, 140]
    overlay[coverage == 2] = [240, 130, 20, 160]
    overlay[heat] = [190, 0, 155, 230]
    axes[2].imshow(overlay, extent=extent, origin='upper', aspect=aspect, interpolation='nearest')
    axes[2].legend(
        handles=[
            Patch(color='#00aa69', label='Inside new basin only'),
            Patch(color='#f08214', label='Inside old basin only'),
            Patch(color='#be009b', label='Changed assignment'),
        ],
        loc='lower left',
        fontsize=8,
    )
    entries = {}
    for code in np.unique(
        np.r_[sample(before, grid, xs, ys).ravel(), sample(after, grid, xs, ys).ravel()]
    ):
        entries[legend[int(code)]] = palette[int(code)]
    fig.legend(
        handles=[Patch(color=np.asarray(rgb) / 255, label=label) for label, rgb in entries.items()],
        loc='lower center',
        bbox_to_anchor=(0.5, 0.025),
        ncol=4,
        fontsize=8,
    )
    fig.suptitle(label, fontsize=14, y=0.98)
    fig.text(
        0.5,
        0.925,
        f'{changed:,} changed water cells in the compared basin areas',
        ha='center',
        fontsize=11,
    )
    fig.text(
        0.01,
        0.012,
        'Water colors show assigned entities; gray is land, blue is ocean. Each pink pixel marks at least one changed cell.',
        fontsize=8,
    )
    fig.savefig(path, dpi=130, facecolor='white')
    plt.close(fig)


def generate(
    rows,
    before_features,
    after_features,
    grid,
    physical_directory,
    before_directory,
    after_directory,
    changes_directory,
    directory,
    palette,
    titles,
    legend,
):
    """Write an overview and measured coverage report for every mapping row."""
    directory, changes_directory = Path(directory), Path(changes_directory)
    directory.mkdir()
    offsets = np.memmap(changes_directory / 'change-rows.u64le', dtype='<u8', mode='r')
    change_path = changes_directory / 'changes.u32le'
    changes = (
        np.memmap(change_path, dtype='<u4', mode='r').reshape(-1, 5)
        if change_path.stat().st_size
        else np.empty((0, 5), dtype=np.uint32)
    )
    if (
        len(offsets) != grid.height + 1
        or offsets[0] != 0
        or offsets[-1] != len(changes)
        or np.any(offsets[1:] < offsets[:-1])
    ):
        raise ValueError('invalid changed-cell row offsets')
    results, started = [], time.monotonic()
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        before = resources.enter_context(open_grid(before_directory, grid))
        after = resources.enter_context(open_grid(after_directory, grid))
        for number, item in enumerate(rows, 1):
            old = union([before_features[ident] for ident in item['before_feature_ids']])
            new = union([after_features[ident] for ident in item['after_feature_ids']])
            geometry = union([g for g in (old, new) if g is not None])
            bounds = view_bounds(geometry, grid)
            x0, x1, y0, y1 = bounds
            masks = []
            for value in (old, new):
                mask = (
                    rasterize(value, grid, bounds)[1]
                    if value
                    else np.zeros((y1 - y0, x1 - x0), dtype=bool)
                )
                masks.append(physical_water(mask, bounds, physical, grid))
            union_mask = masks[0] | masks[1]
            width = 650
            ratio = (y1 - y0) / (
                (x1 - x0) * max(0.05, math.cos(math.radians(90 - (y0 + y1) * grid.step / 2)))
            )
            height = max(180, min(800, round(width * ratio)))
            heat, counts, bins = changes_in_window(
                changes, offsets, bounds, grid, union_mask, (height, width)
            )
            xs = np.linspace(0, x1 - x0 - 1, width, dtype=np.int64)
            ys = np.linspace(0, y1 - y0 - 1, height, dtype=np.int64)
            old_sample, new_sample = [mask[np.ix_(ys, xs)] for mask in masks]
            coverage = np.where(
                new_sample & ~old_sample, 1, np.where(old_sample & ~new_sample, 2, 0)
            )
            filename = f'{number:02d}.png'
            count = sum(counts.values())
            render(
                directory / filename,
                item['label'],
                bounds,
                before,
                after,
                grid,
                palette,
                heat,
                coverage,
                titles,
                count,
                legend,
            )
            result = dict(
                item,
                image=filename,
                changed_cells=count,
                pair_counts=counts,
                newly_covered_water_cells=int(np.count_nonzero(masks[1] & ~masks[0])),
                retired_coverage_water_cells=int(np.count_nonzero(masks[0] & ~masks[1])),
                bounds=bounds,
                closeups=[],
            )
            centers = []
            if max(x1 - x0, y1 - y0) > 4096:
                for (by, bx), _ in sorted(bins.items(), key=lambda item: -item[1]):
                    cy, cx = by * 256 + 128, bx * 256 + 128
                    cx += math.ceil((x0 - cx) / grid.width) * grid.width
                    if any(abs(cy - y) < 1024 and abs(cx - x) < 1024 for y, x in centers):
                        continue
                    centers.append((cy, cx))
                    if len(centers) == 3:
                        break
            for closeup, (cy, cx) in enumerate(centers, 1):
                sub = (max(x0, cx - 512), min(x1, cx + 512), max(y0, cy - 512), min(y1, cy + 512))
                a, b, c, d = sub
                if a >= b or c >= d:
                    continue
                local_masks = [mask[c - y0 : d - y0, a - x0 : b - x0] for mask in masks]
                local_heat, local_counts, _ = changes_in_window(
                    changes, offsets, sub, grid, local_masks[0] | local_masks[1], (650, 650)
                )
                xx = np.linspace(0, b - a - 1, 650, dtype=np.int64)
                yy = np.linspace(0, d - c - 1, 650, dtype=np.int64)
                old_sample, new_sample = [mask[np.ix_(yy, xx)] for mask in local_masks]
                local_coverage = np.where(
                    new_sample & ~old_sample, 1, np.where(old_sample & ~new_sample, 2, 0)
                )
                image = f'{number:02d}-closeup-{closeup}.png'
                render(
                    directory / image,
                    item['label'] + f' · close-up {closeup}',
                    sub,
                    before,
                    after,
                    grid,
                    palette,
                    local_heat,
                    local_coverage,
                    titles,
                    sum(local_counts.values()),
                    legend,
                )
                result['closeups'].append(image)
            results.append(result)
            print(
                f'Image {number}/{len(rows)}: {item["label"]}, {count:,} changed cells', flush=True
            )
    (directory / 'rows.json').write_text(json.dumps(results, indent=2) + '\n')
    sections = [
        '<!doctype html><meta charset="utf-8"><title>Basin comparisons</title>',
        '<style>body{font:16px system-ui;max-width:1500px;margin:2rem auto;padding:0 1rem}img{width:100%}section{margin:3rem 0}table{border-collapse:collapse}td,th{padding:.5rem;border:1px solid #ddd}</style>',
        '<h1>Named-basin comparisons</h1><p>Every image uses the same physical land and final land assignments. Water shows its assigned entity.</p>',
        '<p><b>Final map label changes</b> counts cells assigned to a different continent or ocean. '
        '<b>Inside new basin only</b> and <b>inside old basin only</b> describe changes to basin outlines. '
        'Those outline changes often leave the final map label unchanged. All cells remain on the map.</p>',
    ]
    for number, result in enumerate(results, 1):
        sections.append(
            f'<section id="row-{number}"><h2>{number}. {html.escape(result["label"])}</h2>'
            f'<p>{html.escape(result["reason"])}</p><table><tr><th>Final map label changes</th>'
            f'<th>Inside new basin only</th><th>Inside old basin only</th></tr><tr>'
            f'<td>{result["changed_cells"]:,}</td><td>{result["newly_covered_water_cells"]:,}</td>'
            f'<td>{result["retired_coverage_water_cells"]:,}</td></tr></table>'
            f'<a href="{result["image"]}"><img loading="lazy" src="{result["image"]}"></a></section>'
        )
        for image in result['closeups']:
            sections.append(f'<a href="{image}"><img loading="lazy" src="{image}"></a>')
    (directory / 'index.html').write_text('\n'.join(sections))
    return {'rows': len(results), 'elapsed_seconds': time.monotonic() - started}
