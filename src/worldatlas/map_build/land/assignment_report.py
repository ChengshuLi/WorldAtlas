"""Review source-area component assignments from the current frozen rule format."""

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import time
import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.division.engine import rule_directory
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


def claim_cells(components, claim_directory):
    """Read saved land claims and identify the components they cover.

    Args:
        components: Land components for the parent that produced the claims.
        claim_directory: Directory containing the rule's row-run streams.

    Returns:
        An array of (start column, end column, row) spans and the claimed
        component IDs.
    """
    grid = components.grid
    bounds = json.loads((claim_directory / "report.json").read_bytes())["assigned_bounds"]
    first, last = bounds[2:] if bounds is not None else (0, 0)
    pieces = []
    roots = set()
    with open_grid(claim_directory, grid) as claims:
        for y in range(first, last):
            ends, owners = row(claims, y, grid.width)
            selected = owners != 0
            starts = np.r_[0, ends[:-1]][selected]
            stops = ends[selected]
            if not len(starts):
                continue
            land = components.row(y)
            indices = np.searchsorted(land[:, 1], starts, side="right")
            if np.any(indices == len(land)):
                raise ValueError("claim falls outside the parent land components")
            matched = land[indices]
            if np.any((starts < matched[:, 0]) | (stops > matched[:, 1])):
                raise ValueError("claim falls outside the parent land components")
            roots.update(map(int, matched[:, 2]))
            pieces.append(np.column_stack((starts, stops, np.full(len(starts), y))))
    spans = np.concatenate(pieces) if pieces else np.empty((0, 3), dtype=np.uint32)
    return spans, roots


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
    y0, y1 = float(ys.min()), float(ys.max())
    if len(spans):
        y0 = min(y0, float(spans[:, 2].min()))
        y1 = max(y1, float(spans[:, 2].max() + 1))
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


def write_report(selection, components, calculation, directory, *, parent_id):
    """Render saved polygon-based land claims for a selected parent.

    Args:
        selection: The build's frozen geography.
        components: The land components used for the parent division.
        calculation: The directory where the parent saved its rule claims.
        directory: Destination for the HTML report and its summary.
        parent_id: ID of the geographic parent to report.

    Returns:
        The reported counts by rule and the report generation time.
    """
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    grid = components.grid
    children, rules = compile_rules(selection["geography"], parent_id)
    selected = []
    for rule in rules:
        if (
            rule["operation"] != "assign_area"
            or rule["unit"] != "component"
            or rule["physical_class"] != "land"
            or not rule["features"].get("scope_area")
        ):
            continue
        pieces, roots = claim_cells(components, rule_directory(calculation, rule["id"]))
        selected.append((rule, pieces, roots))
    supporters = Counter(root for _, _, roots in selected for root in roots)
    for name in ("assignment_report.js", "assignment_report.css"):
        (directory / name).write_text((ASSETS / name).read_text())
    folder = directory / "rules"
    folder.mkdir(exist_ok=True)
    summaries = []
    index = []
    for number, (rule, pieces, roots) in enumerate(selected, 1):
        entity = children[rule["targets"][0]["entity_id"]]
        features = list({
            feature["id"]: feature
            for role in ("scope_area", "scope_component", "connected_to")
            for feature in rule["features"].get(role, ())
        }.values())
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
            cell_count=int((pieces[:, 1] - pieces[:, 0]).sum()),
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
<p>The result shows the cells this rule claimed in the build.</p>
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
        + '</tbody></table></nav>'
        + ('<iframe name="detail" title="Rule details" src="rules/001.html"></iframe>' if selected else '')
        + '</div>'
        + INDEX_SCRIPT
    )
    result = dict(rules=summaries, processing_seconds=time.monotonic() - started)
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--parent", type=int, help="geographic parent ID (defaults to the root)")
    args = parser.parse_args()
    selection = read_saved(args.run / "input-selection.json")
    parent_id = args.parent
    if parent_id is None:
        parent_id = next(
            e["id"] for e in selection["geography"]["entities"] if e["parent_id"] is None
        )
    division = json.loads((args.run / "division/report.json").read_bytes())
    receipt = division["parents"].get(str(parent_id))
    if receipt is None:
        raise ValueError("this run has no division for the selected parent")
    # The land receipt follows the actual producer even after partial reuse.
    calculation = Path(receipt["land"]["directory"]).parent
    physical = calculation / "parent-physical"
    if not physical.is_dir():
        run = json.loads((args.run / "report.json").read_bytes())
        physical = Path(run["physical_directory"])
    grid = Grid(**division["grid"])
    with ComponentGrid(physical, calculation / "land-components", grid) as components:
        result = write_report(
            selection, components, calculation, args.output, parent_id=parent_id
        )
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
