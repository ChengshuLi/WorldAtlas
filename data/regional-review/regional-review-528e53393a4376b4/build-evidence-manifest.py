#!/usr/bin/env python3
"""Build the versioned whole-file evidence manifest for issue #428."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASELINE = "bfa1c56ef72c1bc3a9d1fcf8263d073a966bf46f"
WORKER = "worldatlas-geography-431-20261005-r1-7fca"
OUT = ROOT / "evidence-quality.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def descriptor(path: str, role: str | None = None) -> dict:
    raw = (REPO / path).read_bytes()
    result = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if role:
        result["role"] = role
    if path.endswith(".gz"):
        uncompressed = gzip.decompress(raw)
        result["uncompressed_bytes"] = len(uncompressed)
        result["uncompressed_sha256"] = sha(uncompressed)
    return result


def baseline_descriptor(path: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=REPO)
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def issue_scope(body: str) -> dict:
    start = body.find("```json\n")
    if start < 0:
        raise ValueError("Issue body has no JSON scope block")
    raw = body[start + len("```json\n"):].split("\n```", 1)[0]
    value = json.loads(raw)
    if value.get("location_count") != 279 or value.get("member_location_ids_sha256") != "3ca1e40285884fca1e3ac8a23868e9a49e6d7c706c5c1106f560ffcede075dbc":
        raise ValueError("Scope differs from exact issue #428 member pin")
    return value


def candidate_descriptor(relative: str, role: str) -> dict:
    return descriptor(f"data/regional-review/regional-review-528e53393a4376b4/{relative}", role)


def main() -> None:
    scope = json.loads((ROOT / "scope.json").read_bytes())
    ids = scope["member_location_ids"]
    snapshot = json.loads((ROOT / "issue-snapshot.json").read_bytes())
    issue_scope(snapshot["body"])
    if len(ids) != 279 or len(set(ids)) != 279:
        raise ValueError("Issue scope is not the exact unique roster")

    baseline_paths = [
        "data/world-index.json", "data/hierarchy.json", "data/geographic-releases/current-manifest.json",
        "data/administrative-sources.json", "data/macro-foundation/current-membership-inventory.json.gz",
        "data/macro-foundation/review-index.json", "data/macro-foundation/regional-handoffs.json.gz",
        "data/macro-foundation/macro-certificate.json", "data/macro-foundation/approved-boundary-decisions.json",
        "data/geography/part-25.json", "data/geography/part-26.json", "data/geography/part-27.json",
        "data/geography/part-28.json", "data/geography/part-29.json",
    ]
    baseline_files = [baseline_descriptor(path) for path in baseline_paths]
    base_data = {row["path"]: row for row in baseline_files}
    pins = {
        "world-index": base_data["data/world-index.json"]["sha256"],
        "hierarchy": base_data["data/hierarchy.json"]["sha256"],
        "source-catalog": base_data["data/administrative-sources.json"]["sha256"],
        "current-membership-inventory": base_data["data/macro-foundation/current-membership-inventory.json.gz"]["sha256"],
        "review-index": base_data["data/macro-foundation/review-index.json"]["sha256"],
        "current-release-manifest": base_data["data/geographic-releases/current-manifest.json"]["sha256"],
    }
    pin_files = {
        "world-index": "data/world-index.json", "hierarchy": "data/hierarchy.json",
        "source-catalog": "data/administrative-sources.json",
        "current-membership-inventory": "data/macro-foundation/current-membership-inventory.json.gz",
        "review-index": "data/macro-foundation/review-index.json",
        "current-release-manifest": "data/geographic-releases/current-manifest.json",
    }

    part_rows = {}
    for path in [row["path"] for row in baseline_files if row["path"].startswith("data/geography/part-")]:
        raw = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=REPO)
        for feature in json.loads(raw)["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in ids:
                if identity in part_rows:
                    raise ValueError(f"Duplicate baseline subject: {identity}")
                part_rows[identity] = path
    if set(part_rows) != set(ids):
        raise ValueError("Baseline containing files do not exactly cover the issue subjects")

    gb_receipt = json.loads((ROOT / "source/geoBoundaries-restoration.json").read_bytes())
    tiger18 = json.loads((ROOT / "source/census-2018/retrieval.json").read_bytes())
    tiger25 = json.loads((ROOT / "source/census-2025/retrieval.json").read_bytes())
    cbf_receipt = json.loads((ROOT / "source/census-2018/cb_2018_us_county_500k-retrieval.json").read_bytes())
    source_specs = [
        {
            "id": "geoboundaries-usa-adm2-2018",
            "url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2.geojson",
            "role": "USA ADM2 counties; 2018 county boundaries and identity source",
            "vintage": "2018 boundary release; source object commit 9469f09592ced973a3448cf66b6100b741b64c0d",
            "retrieved_at": gb_receipt["retrieved_completed_at"],
            "license": {"status": "redistributable", "terms": "Upstream geoBoundaries metadata declares Public Domain and cites the US Census MAF/TIGER database."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "limit": "Source metadata and identity agreement do not establish legal boundary accuracy.",
            "files": [
                "source/geoBoundaries-USA-ADM2.geojson", "source/geoBoundaries-USA-ADM2-metaData.json",
                "source/geoBoundaries-USA-ADM2.geojson.lfs-pointer", "source/geoBoundaries-USA-ADM2-metaData.json.lfs-pointer",
                "source/geoBoundaries-commit.json", "source/geoBoundaries-restoration.json",
            ],
        },
        {
            "id": "census-tigerweb-2018",
            "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer/84",
            "role": "Georgia and Kentucky county/equivalent geometry and attributes",
            "vintage": "January 1, 2018; Census TIGERweb layer 84",
            "retrieved_at": tiger18["retrieval_completed_at"],
            "license": {"status": "redistributable", "terms": "U.S. Census Bureau federal reference data; see retained Census public-access policy."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "limit": "Statistical/reference geometry; not legal adjudication. Three Georgia rings are invalid.",
            "files": ["source/census-2018/georgia-kentucky-counties.geojson", "source/census-2018/counties-layer-metadata.json", "source/census-2018/retrieval.json"],
        },
        {
            "id": "census-tigerweb-2025",
            "url": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/39",
            "role": "Georgia and Kentucky county/equivalent geometry and attributes",
            "vintage": "January 1, 2025; Census TIGERweb layer 39",
            "retrieved_at": tiger25["retrieval_completed_at"],
            "license": {"status": "redistributable", "terms": "U.S. Census Bureau federal reference data; see retained Census public-access policy."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "limit": "Statistical/reference geometry; not legal adjudication. Three Georgia rings are invalid.",
            "files": ["source/census-2025/georgia-kentucky-counties.geojson", "source/census-2025/counties-layer-metadata.json", "source/census-2025/retrieval.json"],
        },
        {
            "id": "census-2018-cartographic-boundaries",
            "url": "https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html",
            "role": "Generalized 1:500,000 county cartographic comparator",
            "vintage": "2018 CBF",
            "retrieved_at": cbf_receipt["retrieved_at_utc"],
            "license": {"status": "redistributable", "terms": "U.S. Census Bureau federal cartographic reference; see retained Census public-access policy."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "limit": "Generalized cartographic comparator only; not a legal boundary adjudication.",
            "files": ["source/census-2018/cb_2018_us_county_500k.zip", "source/census-2018/cb_2018_us_county_500k-retrieval.json"],
        },
        {
            "id": "census-geographic-authorities",
            "url": "https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html",
            "role": "Official Census division/state purpose, functional-status codes, source-vintage and reuse guidance",
            "vintage": "Guidance pages retained/retrieved 2026-10-05; state/local guides describe 2010 geography and were revised in 2021",
            "retrieved_at": "2026-10-05T14:22:00Z",
            "license": {"status": "redistributable", "terms": "U.S. federal Census publications and reference materials; consult retained access policy."},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "limit": "State/local guides are dated and do not adjudicate current boundaries.",
            "files": [
                "source/authorities/census-2018-boundary-vintage.html.gz", "source/authorities/census-2018-boundary-vintage.retrieval.json",
                "source/authorities/census-2018-cartographic-boundaries.html.gz", "source/authorities/census-2018-cartographic-boundaries.retrieval.json",
                "source/authorities/census-functional-status-codes.html.gz", "source/authorities/census-functional-status-codes.retrieval.json",
                "source/authorities/census-geography-levels.html.gz", "source/authorities/census-geography-levels.retrieval.json",
                "source/authorities/census-georgia-state-local-guide.html.gz", "source/authorities/census-georgia-state-local-guide.retrieval.json",
                "source/authorities/census-kentucky-state-local-guide.html.gz", "source/authorities/census-kentucky-state-local-guide.retrieval.json",
                "source/authorities/census-public-access-policy.pdf", "source/authorities/census-public-access-policy.pdf.retrieval.json",
                "source/authorities/census-tiger-2018-user-note.html.gz", "source/authorities/census-tiger-2018-user-note.html.retrieval.json",
                "source/authorities/census-us-regions-divisions.pdf", "source/authorities/census-us-regions-divisions.pdf.retrieval.json",
            ],
        },
    ]

    # Original official state source bodies are not distributed without explicit reuse terms.
    retrieval = {
        "georgia-sos-roster": "source/authorities/georgia-sos-county-roster.retrieval.json",
        "kentucky-constitution": "source/authorities/kentucky-constitution.retrieval.json",
        "kentucky-statutes-chapter-67": "source/authorities/kentucky-revised-statutes-chapter-67.retrieval.json",
    }
    state_restoration = [
        ("georgia-sos-roster", "Georgia Secretary of State county roster", "https://mvp.sos.ga.gov/resource/1674861955000/County_Number_List"),
        ("kentucky-constitution", "Kentucky Constitution", "https://apps.legislature.ky.gov/law/constitution"),
        ("kentucky-statutes-chapter-67", "Kentucky Revised Statutes chapter 67", "https://apps.legislature.ky.gov/law/statutes/chapter.aspx?id=37377"),
        ("georgia-constitution-2025", "Georgia Constitution revised July 2025", "https://sos.ga.gov/sites/default/files/forms/Georgia%20Constitution.pdf"),
    ]
    sources = []
    for spec in source_specs:
        row = {key: value for key, value in spec.items() if key != "files"}
        row["files"] = [candidate_descriptor(path, "original-source") for path in spec["files"]]
        sources.append(row)
    for source_id, role, url in state_restoration:
        receipt_path = retrieval.get(source_id)
        receipt = json.loads((ROOT / receipt_path).read_bytes()) if receipt_path else json.loads((ROOT / "source/authorities/georgia-constitution-restoration.json").read_bytes())
        sources.append({
            "id": source_id, "url": url, "role": role,
            "vintage": receipt.get("document_revision_visible_in_official_pdf_view", "Official state source; page/document vintage not established in retained bytes"),
            "retrieved_at": receipt.get("retrieved_completed_at", "2026-10-05"),
            "license": {"status": "unknown", "terms": "No explicit redistribution terms established; full response body is not included."},
            "retention": "restoration-only", "verification": "unverified" if source_id == "georgia-constitution-2025" else "verified",
            "temporal_status": "reference",
            "restoration": "Use the exact official URL and the adjacent retrieval receipt/restoration instructions; verify the response SHA-256 and source_bytes before reliance or redistribution.",
            "limit": "No source body is retained; Kentucky and Georgia roster body hashes/dates are in their retrieval sidecars. The Georgia Constitution direct response returned HTTP 403 and no source-body hash is available.",
        })

    source_paths = {file["path"] for source in sources for file in source.get("files", [])}
    all_candidates = sorted(
        path.relative_to(REPO).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.resolve() != OUT.resolve()
    )
    outputs = []
    for path in all_candidates:
        if path in source_paths:
            continue
        role = "generated-result" if "/runs/" in path and path.endswith((".json", ".jsonl")) else "research-output"
        if "/runs/archived-" in path or "/runs/initial-" in path or "/runs/verified-" in path or "/runs/review-" in path:
            role = "archived-result"
        outputs.append(descriptor(path, role))

    rows_path = "data/regional-review/regional-review-528e53393a4376b4/runs/packet-nine/county-assessments.json"
    rows_raw = (REPO / rows_path).read_bytes()
    summary_path = "data/regional-review/regional-review-528e53393a4376b4/runs/packet-nine/comparison-summary.json"
    summary = json.loads((REPO / summary_path).read_bytes())
    metrics, bindings = [], []

    def unit_for(pointer: str, value: int | float) -> str:
        key = pointer.rsplit("/", 1)[-1]
        if key in {"minimum", "maximum", "median", "mean", "threshold"} or "equal_area_iou" in pointer:
            return "IoU fraction"
        if "bytes" in key.lower():
            return "bytes"
        if "vertex" in key.lower():
            return "vertices"
        if "area" in key.lower() and "count" not in key.lower():
            return "area km2"
        if "length" in key.lower() or "perimeter" in key.lower():
            return "length km"
        if key == "version":
            return "version"
        return "count"

    def add_metric(metric_id: str, value: int | float, unit: str, path: str, pointer: str, input_hash: str) -> None:
        metrics.append({"id": metric_id, "value": value, "unit": unit, "vintage": "current",
                        "evaluation_commit": BASELINE, "input_sha256": input_hash})
        bindings.append({"metric_id": metric_id, "path": path, "json_pointer": pointer})

    def walk(value: object, pointer: str = "") -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                escaped = key.replace("~", "~0").replace("/", "~1")
                walk(value[key], pointer + "/" + escaped)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, pointer + "/" + str(index))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            metric_id = "summary:" + pointer
            add_metric(metric_id, value, unit_for(pointer, value), summary_path, pointer, sha(rows_raw))

    walk(summary)
    result_rows = json.loads(rows_raw)
    coastal_names = {"Chatham", "Glynn", "McIntosh", "Camden", "Liberty"}
    for index, row in enumerate(result_rows):
        if row["name"] not in coastal_names:
            continue
        for metric_id, key in [
            ("coast:" + row["name"] + ":atlas-to-tiger-2018", "atlas_v6_to_census_2018_tiger"),
            ("coast:" + row["name"] + ":atlas-to-cbf-2018", "atlas_v6_to_census_2018_cbf"),
        ]:
            pointer = f"/{index}/equal_area_iou/{key}"
            add_metric(metric_id, row["equal_area_iou"][key], "IoU fraction", rows_path, pointer, sha(rows_raw))

    summaries = [{"metric_id": metric["id"], "value": metric["value"], "unit": metric["unit"]} for metric in metrics]
    source_ids = [source["id"] for source in sources]
    conclusions = [
        {"text": "The exact 279 county IDs, county role, state crosswalk, and parent assignment are reproducible against the retained source and the two Census county vintages.", "status": "supported", "source_ids": ["geoboundaries-usa-adm2-2018", "census-tigerweb-2018", "census-tigerweb-2025"]},
        {"text": "The two area labels and state memberships match Census division groupings; the 1,422-member Atlas region is a custom grouping and its interior remains unapproved.", "status": "supported", "source_ids": ["census-geographic-authorities"]},
        {"text": "Five coastal county geometry signals, three invalid Census TIGER references, and the repository catalog/raw-source hash discrepancy remain unresolved and require bounded follow-up.", "status": "unresolved", "source_ids": ["geoboundaries-usa-adm2-2018", "census-tigerweb-2018", "census-tigerweb-2025", "census-2018-cartographic-boundaries"]},
        {"text": "The available statistical/cartographic references do not establish the legal correctness or complete shoreline/island coverage of the Atlas county boundaries.", "status": "unresolved", "source_ids": ["census-tigerweb-2018", "census-tigerweb-2025", "census-2018-cartographic-boundaries"]},
    ]

    changed_paths = all_candidates + [OUT.relative_to(REPO).as_posix()]
    change_receipts = [{"path": path, "status": "added"} for path in changed_paths]
    manifest = {
        "version": 1, "issue": 428, "lane": "geography", "worker_id": WORKER,
        "owned_path": "data/regional-review/regional-review-528e53393a4376b4/",
        "subject_ids": sorted(ids), "subject_ids_sha256": hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest(),
        "baseline": {
            "commit": BASELINE, "files": baseline_files, "pins": pins, "pin_files": pin_files,
            "subject_files": part_rows,
            "issue_scope_release": scope["release"],
            "issue_original_scope_release": scope.get("original_scope_release"),
        },
        "sources": sources, "outputs": outputs,
        "change_receipts": change_receipts,
        "metric_bindings": bindings, "metrics": metrics, "summaries": summaries,
        "methods": [
            {"id": "issue-scope-and-source-identities", "kind": "source", "description": "Match the exact issue roster to national GeoBoundaries shapeIDs, Census 2018/2025 county GEOIDs, source vintage/role, and current state parent IDs.", "software": "Python 3.12.14; standard library JSON/hashlib/subprocess", "units": "county records"},
            {"id": "equal-area-geometry-screen", "kind": "geography", "description": "Compare unmodified source geometries using intersection-over-union after EPSG:6933 equal-area transformation; threshold is triage only. Invalid Census rings are retained and repaired only in-memory for comparison.", "software": "Python 3.12.14, Shapely 2.1.2, pyproj 3.7.2, NumPy 2.3.5, pyshp 2.3.1", "units": "dimensionless IoU fraction", "helper_version": "worldatlas-evidence-geometry-v1", "axis_order": "longitude-latitude", "crs": "EPSG:4326 input to EPSG:6933 equal-area projection", "area_method": "Planar equal-area intersection / union; helper's WGS84 transform/area positive and negative controls also run", "distance_method": "Not measured; no distances or adjacency are inferred"},
            {"id": "packet-generator-reproducibility", "kind": "generator", "description": "Generate canonical result JSON and summaries in a fresh output directory; verify exact roster, no overwrite, and byte-identical repeated runs.", "software": "Python 3.12.14, NumPy 2.3.5, Shapely 2.1.2, pyproj 3.7.2, pyshp 2.3.1", "units": "279 scoped county records and seven IoU comparisons per county"},
        ],
        "validation": [
            {"method_id": "issue-scope-and-source-identities", "kind": "source", "outcome": "passed", "evidence_path": "data/regional-review/regional-review-528e53393a4376b4/runs/validation-source.json"},
            {"method_id": "equal-area-geometry-screen", "kind": "geography", "outcome": "passed", "evidence_path": "data/regional-review/regional-review-528e53393a4376b4/runs/validation-geography.json"},
            {"method_id": "packet-generator-reproducibility", "kind": "generator", "outcome": "passed", "evidence_path": "data/regional-review/regional-review-528e53393a4376b4/runs/validation-generator.json"},
        ],
        "conclusions": conclusions,
        "stages": {"research": "complete", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            ".geo-review-venv/bin/python data/regional-review/regional-review-528e53393a4376b4/reproduce.py --output-dir runs/packet-nine",
            ".geo-review-venv/bin/python data/regional-review/regional-review-528e53393a4376b4/reproduce.py --output-dir runs/packet-ten",
            ".geo-review-venv/bin/python data/regional-review/regional-review-528e53393a4376b4/verify-reproduction.py",
            "node scripts/evidence-quality.mjs data/regional-review/regional-review-528e53393a4376b4/evidence-quality.json",
        ],
    }
    # Ensure every declared source/output candidate path is within this worker-owned prefix.
    for row in outputs + [file for source in sources for file in source.get("files", [])]:
        if not row["path"].startswith("data/regional-review/regional-review-528e53393a4376b4/"):
            raise ValueError("Manifest candidate escapes issue-owned path")
    OUT.write_bytes(canonical(manifest))
    print(json.dumps({"manifest": str(OUT.relative_to(REPO)), "source_count": len(sources),
                      "baseline_files": len(baseline_files), "candidate_outputs": len(outputs),
                      "metrics": len(metrics), "subject_mappings": len(part_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
