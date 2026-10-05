#!/usr/bin/env python3
"""Compare the exact underlying source-entity IDs in the packet to each whole pinned layer."""
import hashlib
import json
from pathlib import Path
from source_bytes import source_bytes, source_parts

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "findings"
records = [json.loads(line) for line in (FINDINGS / "pinned-source-reconciliation.jsonl").read_text().splitlines()]
specs = {"BWA":"ADM2", "LSO":"ADM1", "NAM":"ADM2", "SWZ":"ADM2", "ZAF":"ADM3"}
coverage = []
for country, level in specs.items():
    filename = f"gb-{country}-{level}.geojson"
    raw_source = source_bytes(filename)
    features = json.loads(raw_source)["features"]
    pinned = {f["properties"]["shapeID"] for f in features}
    rows = [r for r in records if r["source_id"] == f"gb:{country}:{level}" or
            (country in {"BWA", "NAM"} and r["source_id"].startswith("resolve:") and
             r["area_id"] == ("framework:area:botswana:9fa5183b68db" if country == "BWA" else "framework:area:namibia:db50c43eb62d"))]
    observed = {str(r["source_original_id"]) for r in rows}
    coverage.append({
        "source_id": f"gb:{country}:{level}",
        "retained_parts": source_parts(filename),
        "reconstructed_source_sha256": hashlib.sha256(raw_source).hexdigest(),
        "pinned_layer_features": len(pinned),
        "scoped_atlas_records_referencing_layer": len(rows),
        "unique_source_original_ids_in_scoped_area": len(observed),
        "missing_source_original_ids": sorted(pinned - observed),
        "unexpected_source_original_ids": sorted(observed - pinned),
        "scope_covers_all_pinned_source_ids": pinned == observed,
        "limitations": "Complete membership of this pinned source layer only; it is not evidence that this vintage is the current or legally complete country roster.",
    })
result = {
    "version": 1,
    "scope_member_ids_sha256": json.loads((ROOT / "source/issue-scope.json").read_text())["member_location_ids_sha256"],
    "source_coverage": coverage,
    "south_africa_neighbor_partition": "See south-africa-neighbor-coverage.json: #435's 17 and #436's 196 disjoint IDs together cover all 213 pinned ZAF ADM3 source IDs.",
}
(FINDINGS / "pinned-source-coverage.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
print(json.dumps([{ "source":x["source_id"],"full_layer":x["pinned_layer_features"],"unique_referenced":x["unique_source_original_ids_in_scoped_area"],"complete":x["scope_covers_all_pinned_source_ids"],"missing":len(x["missing_source_original_ids"])} for x in coverage],indent=2))
