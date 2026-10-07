#!/usr/bin/env python3
"""Build the issue-bound evidence manifest from the pinned local packet."""

from __future__ import annotations

import hashlib
import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
MANIFEST = PACKAGE / "evidence-quality.json"
WORKER = "01a112b9-e2b7-7d03-8000-eb2890649612"
PIN_FILES = {
    "current_batch_report": "coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json",
    "current_lineage_report": "coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json",
    "source_registry": "data/administrative-sources.json",
    "source_catalogue": "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json",
}
SUBJECT_PARTS = [8, 19, 20, 28, 29]


def descriptor(path: str, vintage: str = "candidate", *, original_source: bool = False,
               baseline_commit: str | None = None) -> dict:
    if vintage == "baseline":
        if not baseline_commit:
            raise ValueError("baseline_commit is required for baseline descriptors")
        raw = subprocess.run(["git", "show", f"{baseline_commit}:{path}"], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout
    else:
        raw = (ROOT / path).read_bytes()
    row = {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"}
    if original_source:
        row["role"] = "original-source"
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-commit", required=True,
                        help="exact commit used as the issue/PR baseline")
    args = parser.parse_args()
    baseline_commit = args.baseline_commit
    subprocess.run(["git", "cat-file", "-e", f"{baseline_commit}^{{commit}}"], cwd=ROOT, check=True)
    index_path = PACKAGE / "inputs/complete-input-index.json"
    index = json.loads(index_path.read_text())
    contacts = index["scope"]["contact_ids"]
    if len(contacts) != 57 or len(set(contacts)) != 57:
        raise SystemExit("exact 57-contact scope failed")
    baseline_paths = set(PIN_FILES.values())
    baseline_paths.update(f"data/geography/part-{number}.json" for number in SUBJECT_PARTS)
    product_descriptors = index["source_product_payload_descriptors"]
    for row in product_descriptors:
        baseline_paths.add(row["descriptor"]["path"])
    baseline_files = [descriptor(path, "baseline", original_source=path in {row["descriptor"]["path"] for row in product_descriptors},
                                 baseline_commit=baseline_commit)
                      for path in sorted(baseline_paths)]
    baseline_by_path = {row["path"]: row for row in baseline_files}

    pins = {
        "current_batch_report": "3527014045c5aedc2b26be8bb5dff97e3e34097b7d4cb66a9b2fe3fcf33a6856",
        "current_lineage_report": "3d95a15d3797943290997c9a16fede48e6eb6e0941b0071a5fcd410375c49d46",
        "source_registry": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
        "source_catalogue": "d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9",
    }
    for key, path in PIN_FILES.items():
        if baseline_by_path[path]["sha256"] != pins[key]:
            raise SystemExit(f"issue baseline pin differs: {key}")

    subject_files = {}
    remaining = set(contacts)
    for part in SUBJECT_PARTS:
        path = f"data/geography/part-{part}.json"
        collection = json.loads(subprocess.run(["git", "show", f"{baseline_commit}:{path}"], cwd=ROOT, check=True,
                                               stdout=subprocess.PIPE).stdout)
        for feature in collection["features"]:
            identity = feature.get("id") or feature.get("properties", {}).get("id")
            if identity in remaining:
                subject_files[identity] = path
                remaining.remove(identity)
    if remaining:
        raise SystemExit(f"scope contacts absent from pinned geometry features: {sorted(remaining)}")

    geoboundaries_sources = []
    for item, license_name in zip(product_descriptors, ("CC BY 4.0", "CC0 1.0"), strict=True):
        source_id = item["source_key"]
        product = next(row for row in index["selected_source_products"] if row["key"] == source_id)
        part = item["part"]
        row = descriptor(part["path"], original_source=True)
        row["uncompressed_bytes"] = part["uncompressed_bytes"]
        row["uncompressed_sha256"] = part["uncompressed_sha256"]
        geoboundaries_sources.append({
            "id": f"geoboundaries-{source_id.replace(':', '-')}-simplified",
            "url": product["recorded_consumed_url"],
            "role": "Exact simplified administrative product recorded as consumed by Atlas",
            "vintage": f"Represented-year claim {product['source_represented_year_claim']}; original simplified release product",
            "retrieved_at": "2026-10-07",
            "license": {"status": "redistributable", "terms": f"{license_name}; preserve source attribution and original metadata"},
            "retention": "retained", "verification": "verified", "temporal_status": "reference",
            "files": [row],
        })

    jrc_capture = json.loads((PACKAGE / "sources/jrc/monthlyhistory-v1_5-2024-capture.json").read_text())
    jrc_files = [descriptor(f"research/geography/portugal-spain-gap-source-families-20261007/sources/jrc/monthlyhistory-v1_5-2024/{asset['filename']}")
                 for asset in jrc_capture["assets"]]
    sources = geoboundaries_sources + [{
        "id": "mapa-current-comarcas-snapshot",
        "url": "https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2",
        "role": "Recent current-service target-feature snapshot; not a recovered historical import",
        "vintage": "Undated current MapServer snapshot retrieved 2026-10-07",
        "retrieved_at": "2026-10-07",
        "license": {"status": "unknown", "terms": "Layer metadata leaves copyright and use-terms fields blank; reuse rights for geometry are not established."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Use the recorded official MapServer URL with bounded target ObjectID queries; historical Atlas-imported response bytes were not recovered.",
        "limit": "All 18 historical MAPA originals remain absent; 17 current features are diagnostic context only, and source license/use terms are unknown.",
    }, {
        "id": "apa-wfd-river-network",
        "url": "https://sniamb.apambiente.pt/geoportal/catalog/search/resource/details.page?uuid=6543c7f7b801ee975665fca5",
        "role": "Official Portuguese WFD planning river-line source and captured bounded WFS response",
        "vintage": "Planning source context 2015–2021; WFS captured 2026-10-07",
        "retrieved_at": "2026-10-07",
        "license": {"status": "unknown", "terms": "Current official catalog API says notspecified; a related catalog record reports CC BY 4.0 and an older record also says notspecified. Fees/access constraints are not a reuse license."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Use the captured official APA WFS service URL, complete envelope query, pagination metadata, and exact schema/capabilities retained in sources/apa-wfd/.",
        "limit": "Line features do not measure wetted width and are not a complete land/water inventory; separate requests were not transactional; reuse terms remain unresolved.",
    }, {
        "id": "miteco-phc-2022-2027",
        "url": "https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/masas-de-agua-phc-2022-2027.html",
        "role": "Official Spanish water-planning data access record and documented unavailable vector retrieval",
        "vintage": "Planning cycle 2022–2027; official page and challenge responses captured 2026-10-07",
        "retrieved_at": "2026-10-07",
        "license": {"status": "redistributable", "terms": "The official page permits free use with attribution to the Ministry; no vector data were acquired."},
        "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
        "restoration": "Retry the official dataset links under the published access conditions when the vector endpoints are available without bypassing their challenge.",
        "limit": "The linked .lyr files are styles, while data endpoints returned an HTML challenge form; no vectors were acquired or used.",
    }, {
        "id": "jrc-global-surface-water-monthly-history-v1-5-2024",
        "url": "https://global-surface-water.appspot.com/download",
        "role": "Contemporary monthly surface-water reference; 24 exact 2024 assets for two tiles",
        "vintage": "2024 Monthly History v1.5; product period 2022–2024",
        "retrieved_at": "2026-10-07",
        "license": {"status": "redistributable", "terms": "Official product page permits use without restrictions; attribute Source: EC JRC/Google and cite the JRC paper."},
        "retention": "retained", "verification": "verified", "temporal_status": "reference",
        "files": jrc_files,
    }]

    source_paths = {row["path"] for source in sources for row in source.get("files", [])}
    output_files = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file() or path == MANIFEST or str(path.relative_to(ROOT)) in source_paths:
            continue
        output_files.append(descriptor(str(path.relative_to(ROOT))))

    method_specs = [
        ("admin-gb-ESP-ADM3", "Compare every scoped geometry with all ESP ADM3 simplified source features using EPSG:6933 equal-area overlay.", "positive-control", "negative-control"),
        ("admin-gb-PRT-ADM2", "Compare every scoped geometry with all PRT ADM2 simplified source features using EPSG:6933 equal-area overlay.", "positive-control", "negative-control"),
        ("apa-wfd-lines", "Intersect every scoped geometry with all 1,428 captured APA WFD planning line features after GML axis-order handling and equal-area projection.", "positive-control", "negative-control"),
        ("mapa-current-snapshot", "Compare every scoped geometry with all 17 unique current MAPA target features after applying documented Esri ring winding.", "positive-control", "negative-control"),
        ("jrc-monthly-history", "Decode only selected source-grid TIFF internal tiles, apply Zstandard and Predictor 2, and count strict-inside pixel centers for each month.", "positive-control", "negative-control"),
    ]
    methods = [{"id": identity, "kind": "measurement", "description": description,
                "software": "Python 3.12.14; NumPy 2.3.5; Shapely 2.1.2/GEOS 3.13.1; pyproj 3.7.2/PROJ 9.5.1; Pillow 12.3.0; Zstandard CLI 1.4.5",
                "units": "EPSG:6933 square metres and line metres; JRC source-grid pixel centers and monthly code counts"}
               for identity, description, _, _ in method_specs]
    validation = []
    for identity, _, positive_kind, negative_kind in method_specs:
        for kind in (positive_kind, negative_kind):
            path = f"research/geography/portugal-spain-gap-source-families-20261007/outputs/control-{identity}-{kind}.json"
            validation.append({"method_id": identity, "kind": kind, "outcome": "passed", "evidence_path": path})

    changed_paths = sorted(str(path.relative_to(ROOT)) for path in PACKAGE.rglob("*") if path.is_file())
    changed_paths.append(str(MANIFEST.relative_to(ROOT)))
    change_receipts = [{"path": path, "status": "added", "previous_path": None} for path in sorted(set(changed_paths))]

    manifest = {
        "version": 1, "issue": 1274, "lane": "geography", "worker_id": WORKER,
        "subject_ids": contacts,
        "subject_ids_sha256": hashlib.sha256(json.dumps(sorted(contacts), separators=(",", ":")).encode()).hexdigest(),
        "baseline": {"commit": baseline_commit, "files": baseline_files, "pins": pins,
                     "pin_files": PIN_FILES, "subject_files": subject_files},
        "sources": sources,
        "outputs": output_files,
        "change_receipts": change_receipts,
        "methods": methods,
        "metrics": [], "metric_bindings": [], "summaries": [],
        "conclusions": [
            {"text": "The exact simplified geoBoundaries products recorded as consumed by Atlas were reassembled from pinned shards, byte-verified, and compared against every scoped component; no individual component is fully covered by either complete source union.",
             "status": "supported", "source_ids": ["geoboundaries-gb-ESP-ADM3-simplified", "geoboundaries-gb-PRT-ADM2-simplified"]},
            {"text": "The current MAPA snapshot, APA lines, and 2024 JRC detections provide bounded reference context but do not resolve whole-component water status, historical ownership, cause, or boundary changes; unavailable and unresolved source results remain unknown.",
             "status": "unresolved", "source_ids": ["mapa-current-comarcas-snapshot", "apa-wfd-river-network", "jrc-global-surface-water-monthly-history-v1-5-2024", "miteco-phc-2022-2027"]},
        ],
        "validation": validation,
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3 research/geography/portugal-spain-gap-source-families-20261007/scripts/run-complete-analysis.py run-1",
            "python3 research/geography/portugal-spain-gap-source-families-20261007/scripts/run-complete-analysis.py run-2",
            "python3 research/geography/portugal-spain-gap-source-families-20261007/scripts/finalize-evidence-lock.py",
            "node scripts/evidence-quality.mjs research/geography/portugal-spain-gap-source-families-20261007/evidence-quality.json",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"subject_count": len(contacts), "baseline_files": len(baseline_files),
                      "source_files": sum(len(s.get("files", [])) for s in sources),
                      "output_files": len(output_files), "methods": len(methods),
                      "sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
