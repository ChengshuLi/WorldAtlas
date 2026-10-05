#!/usr/bin/env python3
"""Compare neighboring West African local administrative tiers at main's pins."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from shapely.geometry import shape

from geometry import VERSION, land_area_m2

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
inventory = json.loads(gzip.decompress((ROOT / "data/macro-foundation/current-membership-inventory.json.gz").read_bytes()))
region = next(row for row in inventory if row.get("id") == "framework:region:west-tropical-africa:ba6e06497098")
region_ids = set(region["member_location_ids"])
target_countries = {"Benin", "Burkina Faso", "Côte d'Ivoire", "Ghana", "Mali", "Niger", "Nigeria", "Togo"}
groups = defaultdict(list)
files = Counter()
source_ids = set()

for relative in json.loads((ROOT / "data/world-index.json").read_text())["parts"]:
    for feature in json.loads((ROOT / "data" / relative).read_text())["features"]:
        props = feature["properties"]
        if props["id"] not in region_ids or props.get("reference_owner") not in target_countries:
            continue
        metadata = props.get("metadata", {})
        source_id = metadata.get("source_id", "")
        if not source_id.startswith("gb:"):
            continue
        owner = props["reference_owner"]
        geometry = shape(feature["geometry"])
        area = land_area_m2(geometry)
        key = (owner, source_id, metadata.get("administrative_level"), metadata.get("reference_year"), metadata.get("source_role"))
        groups[key].append(area)
        files[relative] += 1
        source_ids.add(source_id)

summary = []
for key, areas in sorted(groups.items()):
    owner, source_id, level, year, role = key
    ordered = sorted(areas)
    summary.append({
        "country": owner,
        "source_id": source_id,
        "administrative_level": level,
        "reference_year": year,
        "source_role": role,
        "location_count": len(areas),
        "current_atlas_land_area_m2": {
            "p10": round(ordered[round((len(ordered) - 1) * .10)], 3),
            "median": round(ordered[len(ordered) // 2], 3),
            "p90": round(ordered[round((len(ordered) - 1) * .90)], 3),
        },
    })

result = {
    "version": 1,
    "issue": 467,
    "baseline_commit": "fdab75892d979b995a1d20f311006aeeddb770b5",
    "method": {
        "kind": "measurement",
        "helper_version": VERSION,
        "description": "WGS84 straight-source-edge ellipsoidal area per current atlas location footprint. Groups compare local administrative role, source vintage and scale context only; they are not evidence of semantic correctness or comparable administrative law.",
        "units": "m2",
    },
    "regional_context": {
        "region_id": region["id"],
        "all_region_locations": len(region_ids),
        "neighbor_countries_screened": sorted(target_countries),
        "source_ids": sorted(source_ids),
        "containing_files_for_all_neighbor_inputs": sorted(files),
        "file_feature_counts": dict(sorted(files.items())),
    },
    "country_sources": summary,
    "limits": [
        "Current Atlas polygons are a published reference layer and may include documented border reconciliation; source tags and role statements were not re-reviewed for all comparator countries.",
        "Country-level area distributions conceal local variation and cannot establish territorial purpose, completeness or neighboring semantic compatibility.",
        "The role and source facts for the 224 issue subjects are independently assessed in the subject packet; these other-country counts are contextual screening only.",
    ],
}
out = PACKET / "neighbor-granularity-screen.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"output": str(out.relative_to(ROOT)), "countries": len(summary), "context": result["regional_context"], "country_sources": summary}, ensure_ascii=False, indent=2))
