"""Review source-area component assignments from the current frozen rule format."""

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import time
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.inputs.selection import read_saved
from worldatlas.map_build.land.components import ComponentGrid

ASSETS = Path(__file__).parent


INDEX_SCRIPT = r"""<script>
document.querySelector('#search').oninput = event => {
  const query = event.target.value.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(row => {
    row.hidden = !row.textContent.toLowerCase().includes(query);
  });
};
for (const table of document.querySelectorAll('table')) {
  const body = table.tBodies[0], headers = [...table.tHead.rows[0].cells];
  headers.forEach((header, column) => {
    const label = header.textContent, button = document.createElement('button');
    button.textContent = label + ' ↕';
    header.replaceChildren(button);
    button.onclick = () => {
      const rows = [...body.rows];
      const value = row => row.cells[column].textContent.trim();
      const numeric = rows.every(row => /^[\d,]+$/.test(value(row)));
      const descending = header.hasAttribute('aria-sort')
        ? header.getAttribute('aria-sort') === 'ascending' : numeric && column !== 0;
      rows.sort((a, b) => {
        const comparison = numeric
          ? Number(value(a).replaceAll(',', '')) - Number(value(b).replaceAll(',', ''))
          : value(a).localeCompare(value(b), undefined, {numeric: true, sensitivity: 'base'});
        return (descending ? -comparison : comparison) || Number(a.cells[0].textContent) - Number(b.cells[0].textContent);
      });
      body.append(...rows);
      headers.forEach(other => {
        other.removeAttribute('aria-sort');
        other.firstChild.textContent = other.firstChild.textContent.replace(/ [↑↓↕]$/, '') + ' ↕';
      });
      header.setAttribute('aria-sort', descending ? 'descending' : 'ascending');
      button.textContent = label + (descending ? ' ↓' : ' ↑');
    };
  });
}
</script></body></html>"""


def cell_spans(components, roots):
    """Index only requested components; keep every selected native-grid cell."""
    positions = np.flatnonzero(np.isin(components.runs[:, 2], list(roots)))
    positions = positions[np.argsort(components.runs[positions, 2], kind="stable")]
    selected = components.runs[positions]
    rows = np.searchsorted(components.offsets, positions, side="right") - 1
    values = np.column_stack((selected[:, :2], rows)).astype(np.uint32)
    ids, first = np.unique(selected[:, 2], return_index=True)
    ends = np.r_[first[1:], len(selected)]
    return {int(root): values[a:b] for root, a, b in zip(ids, first, ends)}


def view_bounds(geometries, spans, grid):
    """Include complete input geometry and selected cells, with room around points."""
    points = []

    def visit(value):
        if isinstance(value[0], (int, float)):
            points.append(
                (
                    (value[0] - grid.west) / grid.step,
                    (grid.north - value[1]) / grid.step,
                )
            )
        else:
            for child in value:
                visit(child)

    for geometry in geometries:
        visit(geometry["coordinates"])
    xs, ys = np.array(points).T
    # Choose a continuous longitude view by removing the largest empty gap.
    intervals = [(float(x), float(x)) for x in xs]
    intervals.extend((float(a), float(b)) for a, b, _ in spans)
    intervals.sort()
    merged = []
    for a, b in intervals:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    gaps = [
        (
            merged[(i + 1) % len(merged)][0]
            + (grid.width if i == len(merged) - 1 else 0)
            - b,
            i,
        )
        for i, (_, b) in enumerate(merged)
    ]
    _, i = max(gaps)
    x0 = merged[(i + 1) % len(merged)][0]
    x1 = merged[i][1]
    if x1 < x0:
        x1 += grid.width
    y0 = min(float(ys.min()), float(spans[:, 2].min()))
    y1 = max(float(ys.max()), float(spans[:, 2].max() + 1))
    padding = max(4, max(x1 - x0, y1 - y0) * 0.06)
    return [
        x0 - padding,
        max(0, y0 - padding),
        min(grid.width, x1 - x0 + 2 * padding),
        min(grid.height, y1 + padding) - max(0, y0 - padding),
    ]


def context_spans(components, bounds):
    """Thin background rows for orientation; assigned cells remain full resolution."""
    x0, y0, width, height = bounds
    stride = max(1, int(height / 450))
    result = []
    for y in range(
        max(0, int(y0)), min(components.grid.height, int(y0 + height) + 1), stride
    ):
        spans = components.row(y)
        for a, b, _ in spans:
            a, b = int(a), int(b)
            if any(
                a + shift < x0 + width and b + shift > x0
                for shift in (-components.grid.width, 0, components.grid.width)
            ):
                result.append([a, b, y])
    return result, stride


def write_report(
    selection, components, directory, *, parent_id=None, parent_membership=None
):
    """Use the same scope/majority calculation as production assignment."""
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    geography = selection["geography"]
    grid = components.grid
    if parent_id is None:
        roots = [e["id"] for e in geography["entities"] if e["parent_id"] is None]
        if len(roots) != 1:
            raise ValueError("select one geographic parent")
        parent_id = roots[0]
    children, rules = compile_rules(geography, parent_id)
    parent = parent_membership
    if parent is None:
        entity = next(e for e in geography["entities"] if e["id"] == parent_id)
        if entity["parent_id"] is not None:
            raise ValueError("a non-root report needs its parent membership")
        parent = (
            np.arange(grid.height + 1, dtype=np.uint32),
            np.tile([grid.width, 1], grid.height).astype(np.uint32),
        )
    snapshot = (
        np.arange(grid.height + 1, dtype=np.uint32),
        np.tile([grid.width, 0], grid.height).astype(np.uint32),
    )
    selected = []
    for rule in rules:
        if (
            rule["operation"] != "assign_area"
            or rule["unit"] != "component"
            or rule["physical_class"] != "land"
            or not rule["features"].get("scope_area")
        ):
            continue
        scope = Scope(
            rule, grid, components.physical, parent, snapshot, lambda kind: components
        )
        roots = set(map(int, scope.eligible_components()["land"]))
        selected.append((rule, roots))
    spans = cell_spans(components, set().union(*(roots for _, roots in selected)))
    totals = components.totals()
    supporters = Counter(root for _, roots in selected for root in roots)
    for name in ("assignment_report.js", "assignment_report.css"):
        (directory / name).write_text((ASSETS / name).read_text())
    folder = directory / "rules"
    folder.mkdir(exist_ok=True)
    summaries = []
    index = []
    for number, (rule, roots) in enumerate(selected, 1):
        if not roots:
            raise ValueError(
                "selected area rule has no current land components: " + rule["id"]
            )
        entity = children[rule["targets"][0]["entity_id"]]
        pieces = np.concatenate([spans[root] for root in sorted(roots)])
        features = rule["features"]["scope_area"]
        geometries = [f["geometry"] for f in features]
        bounds = view_bounds(geometries, pieces, grid)
        background, stride = context_spans(components, bounds)
        record = dict(
            number=number,
            assignment_id=rule["id"],
            entity_id=entity["id"],
            entity=entity["name"],
            feature_count=len(features),
            component_count=len(roots),
            cell_count=sum(totals[r] for r in roots),
            unique_component_count=sum(supporters[r] == 1 for r in roots),
        )
        payload = dict(
            **record,
            grid=vars(grid),
            bounds=bounds,
            geometries=geometries,
            conditions=[dict(feature_ids=[f["id"] for f in features])],
            cells=pieces.tolist(),
            context=background,
            context_stride=stride,
            color=entity["color_rgb"],
            entity_colors={e: child["color_rgb"] for e, child in children.items()},
        )
        content = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")
        page = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>{number}. {escape(rule["id"])}</title><link rel="stylesheet" href="../assignment_report.css">
<h1>{number}. {escape(rule["id"])}</h1><p>{escape(rule["rationale"])}</p>
<p>{escape(entity["name"])}: {record["cell_count"]:,} cells; {len(roots):,} components; {len(features)} source features.</p>
<p>The union of these source areas selects components by strict majority of their land cells.</p>
<button id="reset">Reset view</button><button id="save">Save image</button>
<div class="maps"><canvas id="source"></canvas><canvas id="result"></canvas></div>
<div id="feature-legend" class="feature-legend"></div><p id="extent"></p>
<script id="data" type="application/json">{content}</script><script src="../assignment_report.js"></script></html>"""
        (folder / f"{number:03d}.html").write_text(page)
        summaries.append(record)
        index.append(
            f'<tr><td>{number}</td><td><a target="detail" href="rules/{number:03d}.html">{escape(rule["id"])}</a></td>'
            f"<td>{escape(entity['name'])}</td><td>{len(features)}</td><td>{len(roots):,}</td><td>{record['cell_count']:,}</td><td>{record['unique_component_count']:,}</td></tr>"
        )
    (directory / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><link rel="stylesheet" href="assignment_report.css">'
        '<title>Geographic area assignments</title><h1>Geographic area assignments</h1><input id="search" placeholder="Filter rules">'
        '<div class="review-layout"><nav><table><thead><tr><th>#</th><th>Rule</th><th>Entity</th><th>Features</th><th>Components</th><th>Cells</th><th>Unique components</th></tr></thead><tbody>'
        + "".join(index)
        + '</tbody></table></nav><iframe name="detail" title="Rule details" src="rules/001.html"></iframe></div>'
        + INDEX_SCRIPT
    )
    result = dict(rules=summaries, processing_seconds=time.monotonic() - started)
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("selection", "physical", "components", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    grid = Grid(**json.loads((args.components / "report.json").read_text())["grid"])
    with ComponentGrid(args.physical, args.components, grid) as components:
        result = write_report(read_saved(args.selection), components, args.output)
    print(
        json.dumps(
            dict(
                rule_count=len(result["rules"]),
                processing_seconds=result["processing_seconds"],
            )
        )
    )


if __name__ == "__main__":
    main()
