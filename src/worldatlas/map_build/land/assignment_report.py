"""Show numbered geographic rules, source geometry and their actual assigned cells."""

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import time

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.inputs.selection import geographic_domain, read_saved
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.geographic_assignments import resolve_assignments

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


def _selected_rules(selection):
    domain = geographic_domain(selection, "regional")
    return domain, domain["assignments"] if "assignments" in domain else domain[
        "affiliations"
    ]


def write_report(selection, components, directory, *, previous=None):
    """Write a local interactive report and machine-readable coverage inventory."""
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("assignment_report.js", "assignment_report.css"):
        (directory / name).write_text((ASSETS / name).read_text())
    groups = [("current", selection)] + ([("previous", previous)] if previous else [])
    resolved = []
    for label, frozen in groups:
        domain, rules = _selected_rules(frozen)
        result = resolve_assignments(
            rules, domain["features"], components, domain["category_bindings"]
        )
        resolved.append((label, domain, rules, result))
    all_roots = {
        root for _, _, _, result in resolved for root in result["component_entities"]
    }
    spans = cell_spans(components, all_roots)
    totals = components.totals()
    current = resolved[0][3]["component_entities"]
    summaries = []
    index = []
    for label, domain, rules, result in resolved:
        features = {f["feature_id"]: f for f in domain["features"]}
        entities = {e["id"]: e for e in domain.get("entities", [])}
        supporters = Counter(
            root for c in result["claims"] for root in c["component_ids"]
        )
        claims = {
            c.get("assignment_id", c.get("affiliation_id")): c for c in result["claims"]
        }
        section = []
        folder = directory / label
        folder.mkdir(exist_ok=True)
        for number, rule in enumerate(rules, 1):
            ident = rule.get("assignment_id", rule.get("affiliation_id"))
            claim = claims[ident]
            roots = claim["component_ids"]
            selected = np.concatenate([spans[root] for root in roots])
            legacy = rule.get(
                "component_selection",
                rule.get("evidence", {}).get("component_selection"),
            )
            conditions = (
                [rule["selection"]] if "selection" in rule else legacy["conditions"]
            )
            geometries = [features[c["feature_id"]]["geometry"] for c in conditions]
            bounds = view_bounds(geometries, selected, components.grid)
            background, stride = context_spans(components, bounds)
            entity = entities.get(rule["entity_id"], {})
            record = dict(
                number=number,
                assignment_id=ident,
                entity_id=rule["entity_id"],
                entity=entity.get("name", str(rule["entity_id"])),
                component_count=len(roots),
                cell_count=sum(totals[r] for r in roots),
                unique_component_count=sum(supporters[r] == 1 for r in roots),
                other_assignments=sorted(
                    k
                    for k, c in claims.items()
                    if k != ident and set(roots) & set(c["component_ids"])
                ),
                matched_current_components=sum(
                    current.get(r) == rule["entity_id"] for r in roots
                ),
                conditions=conditions,
                combine="all" if "selection" in rule else legacy["combine"],
                current_rule_numbers=[
                    n
                    for n, c in enumerate(resolved[0][3]["claims"], 1)
                    if c["entity_id"] == rule["entity_id"]
                    and set(roots) & set(c["component_ids"])
                ],
            )
            summaries.append(dict(section=label, **record))
            payload = dict(
                **record,
                grid=vars(components.grid),
                bounds=bounds,
                geometries=geometries,
                cells=selected.tolist(),
                context=background,
                context_stride=stride,
                color=entity.get("color_rgb") or "#3769a0",
            )
            content = json.dumps(
                payload, separators=(",", ":"), ensure_ascii=False
            ).replace("<", "\\u003c")
            heading = f"{number}. {ident}"
            html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>{escape(heading)}</title><link rel="stylesheet" href="../assignment_report.css">
<body><h1>{escape(heading)}</h1><p>{escape(rule.get("rationale", ""))}</p>
<p><strong>{escape(record["entity"])}</strong> · {len(roots):,} components · {record["cell_count"]:,} cells ·
{record["unique_component_count"]:,} components uniquely selected by this rule</p>
<pre>{escape(json.dumps(rule["selection"] if "selection" in rule else legacy, indent=2))}</pre>
<p>Left: source geometry. Right: actual assigned land cells in the entity color.
Blue outlines/markers show source polygons/points. Gray is background land.
Drag to pan; scroll to zoom. Both views move together.</p>
<button id="reset">Reset view</button><button id="save">Save comparison image</button>
<div class="maps"><canvas id="source"></canvas><canvas id="result"></canvas></div>
<p id="extent"></p><p>Selected cells retain the full grid resolution. Background land is sampled for orientation.</p>
<p>Current rules covering these components: {escape(", ".join("#" + str(n) for n in record["current_rule_numbers"]))}.</p>
<p>Other rules sharing selected components: {escape(", ".join(record["other_assignments"]) or "none")}.</p>
<script id="data" type="application/json">{content}</script><script src="../assignment_report.js"></script></body></html>"""
            (folder / f"{number:03d}.html").write_text(html)
            section.append(
                f'<tr><td>{number}</td><td><a target="detail" href="{label}/{number:03d}.html">{escape(ident)}</a></td>'
                f"<td>{escape(record['entity'])}</td><td>{len(roots):,}</td><td>{record['cell_count']:,}</td>"
                f"<td>{record['unique_component_count']:,}</td></tr>"
            )
        index.append(
            f"<h2>{label.title()} rules ({len(rules)})</h2><table><thead><tr><th>#</th><th>Rule</th><th>Entity</th><th>Components</th><th>Cells</th><th>Unique components</th></tr></thead><tbody>"
            + "".join(section)
            + "</tbody></table>"
        )
    changed = None
    if previous:
        before = resolved[1][3]["component_entities"]
        changed_roots = {
            r for r in set(before) | set(current) if before.get(r) != current.get(r)
        }
        changed = sum(totals[r] for r in changed_roots)
    summary = dict(
        rules=summaries,
        changed_assignment_cells=changed,
        processing_seconds=time.monotonic() - started,
    )
    (directory / "coverage.json").write_text(json.dumps(summary, indent=2) + "\n")
    (directory / "index.html").write_text(
        """<!doctype html><html lang="en"><meta charset="utf-8"><title>Geographic assignment review</title>
<link rel="stylesheet" href="assignment_report.css"><body><h1>Geographic assignment review</h1>
<p>Each numbered row opens its source geometry and actual assigned cells. Unique components are selected by no other rule in that section.
This report covers whole-component assignments; mainland partitions and regional line/group policies are separate inputs.</p>"""
        + (
            f"<p><strong>{changed:,} assignment cells changed.</strong></p>"
            if changed is not None
            else ""
        )
        + '<input id="search" placeholder="Filter rules by name, entity or number"><div class="layout"><nav>'
        + "".join(index)
        + '</nav><iframe name="detail" title="Rule details" src="current/001.html"></iframe></div>'
        + INDEX_SCRIPT

    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--previous-selection", type=Path)
    parser.add_argument("--physical", required=True, type=Path)
    parser.add_argument("--components", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    grid = Grid(**json.loads((args.components / "report.json").read_text())["grid"])
    with ComponentGrid(args.physical, args.components, grid) as components:
        result = write_report(
            read_saved(args.selection),
            components,
            args.output,
            previous=read_saved(args.previous_selection)
            if args.previous_selection
            else None,
        )
    print(json.dumps({k: v for k, v in result.items() if k != "rules"}))


if __name__ == "__main__":
    main()
