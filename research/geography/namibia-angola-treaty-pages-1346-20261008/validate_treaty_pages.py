#!/usr/bin/env python3
"""Bounded additive audit of historical No. 2960 page locators; never runs GIS."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.evidence.immutable import Baseline, NewVintage, sha256

OWNED = "research/geography/namibia-angola-treaty-pages-1346-20261008/"
MANIFEST = ROOT / OWNED / "evidence-quality.json"
PAGE_MAP = ROOT / OWNED / "historical-to-corrected-locators.json"
ISSUE_IDS = [
    "gb:AGO:ADM2:16411231B14510444140190",
    "gb:AGO:ADM2:16411231B28551746118834",
    "gb:AGO:ADM2:16411231B36562728226085",
    "gb:NAM:ADM2:8085530B15355770078360",
    "gb:NAM:ADM2:8085530B25496891828693",
    "gb:NAM:ADM2:8085530B32015186497374",
    "gb:NAM:ADM2:8085530B43563455443088",
    "gb:NAM:ADM2:8085530B54610932550654",
    "gb:NAM:ADM2:8085530B8620298556926",
    "gb:NAM:ADM2:8085530B94702234009846",
]
PDF_PATH = "research/geography/gap-source-namibia-angola-20261006/sources/historical-boundary/lon-treaty-series-vol-129-1932.pdf"
ASSESSMENTS = [
    "research/geography/gap-source-namibia-angola-20261006/historical-boundary-contact-water-assessment.json",
    "research/geography/gap-source-namibia-angola-20261006/vintages/kakeri-final-1/historical-boundary-contact-water-assessment.json",
    "research/geography/gap-source-namibia-angola-20261006/vintages/kakeri-final-2/historical-boundary-contact-water-assessment.json",
]
PRODUCER = "research/geography/gap-source-namibia-angola-20261006/reproduce_1928_boundary_contact_water.py"
EXPECTED_PDF_SHA = "a8790efad550c33786a75e26466a241a1858fac902678d8d2a7c2ffb02b0903f"
EXPECTED_PDF_BYTES = 7_801_132


def fail(message: str) -> None:
    raise ValueError(message)


def text_page(reader: PdfReader, number: int) -> str:
    return " ".join((reader.pages[number - 1].extract_text() or "").split())


def scan_historical_record(report: dict) -> list[str]:
    """Return the specific false bindings required to be exposed by this audit."""
    findings = []
    beacon = report["beacon_47"]
    if beacon.get("source_printed_page") != 166:
        findings.append("beacon_47_wrong_printed_page")
    act = report["boundary_sources"]["primary_final_act"]
    pdf_pages = act.get("pdf_pages", [])
    printed_pages = act.get("printed_pages", [])
    if not set((158, 159, 160)).issubset(pdf_pages):
        findings.append("exchange_claim_missing_pages_158_160")
    if 166 not in printed_pages:
        findings.append("beacon_47_page_missing_from_printed_range")
    return findings


def verify_page_map(page_map: dict, reader: PdfReader) -> dict:
    if page_map["source_pdf"]["sha256"] != EXPECTED_PDF_SHA:
        fail("Candidate page map points to a different Treaty Series source")
    if len(reader.pages) != page_map["source_pdf"]["pdf_pages"] or len(reader.pages) != 478:
        fail("Treaty source page count differs from authenticated volume")
    by_id = {row["claim_id"]: row for row in page_map["claims"]}
    if len(by_id) != len(page_map["claims"]):
        fail("Duplicate claim IDs in corrected locator map")
    required = {
        "exchange_acceptance": ([158, 159, 160], [158, 159, 160]),
        "final_act_body": ([160, 161, 162, 163], [160, 161, 162, 163]),
        "main_beacons_english_1_35": ([164], [164]),
        "main_beacons_portuguese_1_35": ([165], [165]),
        "main_beacons_english_36_47": ([166], [166]),
        "main_beacons_portuguese_36_47": ([167], [167]),
        "intermediate_beacons_english": ([168], [168]),
        "intermediate_beacons_portuguese": ([169], [169]),
        "french_translation": ([170, 171, 172, 173, 174, 175, 176], [170, 171, 172, 173, 174, 175, 176]),
    }
    if set(by_id) != set(required):
        fail("Corrected map omits or adds a claim binding")
    for claim_id, (pdf_pages, printed_pages) in required.items():
        row = by_id[claim_id]
        if row["correct_pdf_pages"] != pdf_pages or row["correct_printed_pages"] != printed_pages:
            fail("Incorrect corrected page binding: " + claim_id)
    beacon = page_map["beacon_47"]
    if (beacon["historical_pdf_page"], beacon["historical_printed_page"],
            beacon["correct_pdf_page"], beacon["correct_printed_page"]) != (166, 165, 166, 166):
        fail("Beacon 47 erratum does not correct the historical false locator")
    if (beacon["latitude_dms"], beacon["longitude_dms"]) != ("17 23 23.7 S", "18 25 06.2 E"):
        fail("Erratum changed the historical coordinate")

    # Extracted text is an automated structural check, not the visual inspection.
    pages = {n: text_page(reader, n) for n in range(157, 179)}
    for n in range(158, 177):
        if not re.search(rf"\b{n}\b", pages[n][:180]):
            fail(f"Printed header not found near top of physical PDF page {n}")
    if not all(word in pages[158].upper() for word in ("EXCHANGE", "NOTES", "1931")):
        fail("PDF page 158 does not support the exchange-of-notes locator")
    if "prepared to accept the boundary" not in pages[159].lower():
        fail("PDF page 159 does not contain the acceptance exchange text")
    if "SCHEDULE CONTAINING" not in pages[164].upper() or "MAIN BEACONS" not in pages[164].upper():
        fail("PDF page 164 is not the English main-beacon schedule")
    if "DOCUMENTO" not in pages[165].upper() or "MARCOS PRINCIPAIS" not in pages[165].upper():
        fail("PDF page 165 is not the Portuguese main-beacon schedule")
    if not re.search(r"17\s+23\s+23[.,]7", pages[166]) or not re.search(r"18\s+25\s+06[.,]2", pages[166]):
        fail("PDF page 166 lacks beacon 47's two printed coordinate values")
    if "47" not in pages[166] or "astronomically" not in pages[166].lower():
        fail("PDF page 166 lacks the last beacon and method footnote")
    if "18 25 06.2" in pages[165]:
        fail("PDF page 165 incorrectly appears to contain beacon 47")
    if "DESCRIPTION OF EIGHT INTERMEDIATE BEACONS" not in pages[168].upper():
        fail("PDF page 168 is not the English intermediate-beacon schedule")
    if "MARCOS SECUNDARIOS" not in pages[169].upper():
        fail("PDF page 169 is not the Portuguese intermediate-beacon schedule")
    if "2960" not in pages[170] or "BRITISH COMMONWEALTH MERCHANT SHIPPING AGREEMENT" not in pages[178].upper():
        fail("No. 2960 boundary or following No. 2961 boundary was not located")
    return {
        "volume_bytes": EXPECTED_PDF_BYTES,
        "volume_sha256": EXPECTED_PDF_SHA,
        "pdf_page_count": len(reader.pages),
        "checked_physical_pages": list(range(157, 179)),
        "printed_header_pages": list(range(158, 177)),
        "beacon_47_pdf_page": 166,
        "beacon_47_printed_page": 166,
        "page_165_excludes_beacon_47": True,
        "visual_inspection": "Researcher visually inspected the retained volume's rendered pages 157–178; local review images were discarded and are not included because no separate reuse license was captured.",
        "text_extraction_note": "pypdf extraction is a reproducible locator check; visual page inspection independently established the rendered headers and bilingual schedule layout.",
    }


def extract_producer_beacon(source: bytes) -> dict:
    tree = ast.parse(source.decode("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BEACON_47" for t in node.targets):
            if not isinstance(node.value, ast.Dict):
                fail("Historical producer BEACON_47 is not a literal dictionary")
            wanted = {"number", "latitude_dms", "longitude_dms", "description", "source_pdf_page", "source_printed_page"}
            value = {}
            for key_node, value_node in zip(node.value.keys, node.value.values):
                if isinstance(key_node, ast.Constant) and key_node.value in wanted:
                    value[key_node.value] = ast.literal_eval(value_node)
            if set(value) != wanted:
                fail("Historical producer BEACON_47 lacks required literal citation fields")
            return value
    fail("Historical producer BEACON_47 binding not found")


def context_findings(baseline: Baseline) -> list[dict]:
    features, containing = baseline.subjects(ISSUE_IDS)
    hierarchy = json.loads(baseline.pinned_bytes("data/hierarchy.json"))
    nodes = {row["id"]: row for row in hierarchy}
    rows = []
    for identity in sorted(ISSUE_IDS):
        feature = features[identity]
        props = feature["properties"]
        meta = props["metadata"]
        parent_id = props["parent_id"]
        parent = nodes[parent_id]
        semantic = parent["metadata"]["semantic_review"]
        rows.append({
            "id": identity,
            "name": props["name"],
            "country": identity.split(":")[1],
            "source": meta["source_name"],
            "source_id": meta["source_id"],
            "source_url": meta["source_url"],
            "source_role": meta["source_role"],
            "source_vintage": meta["reference_year"],
            "source_license": meta["license"],
            "administrative_level": meta["administrative_level"],
            "parent_id": parent_id,
            "parent_name": parent["name"],
            "parent_kind": parent["metadata"]["kind"],
            "parent_framework_status": parent["metadata"]["framework_status"],
            "parent_semantic_review": semantic["action"],
            "parent_review_reasons": semantic["remaining_reasons"],
            "source_feature_sha256": sha256(json.dumps(feature, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
            "indexed_containing_file": containing[identity]["path"],
            "scope_limit": "Identity, source metadata and retained parent reference only; no geometry, current administration, boundary, or legal status validated by this citation packet.",
        })
    if len(rows) != 10 or {r["country"] for r in rows} != {"NAM", "AGO"}:
        fail("Issue's exact ten subject identities did not resolve")
    if {r["source_vintage"] for r in rows if r["country"] == "AGO"} != {"2018"}:
        fail("Angola subject source vintage/role differs from inspected records")
    if {r["source_vintage"] for r in rows if r["country"] == "NAM"} != {"2007"}:
        fail("Namibia subject source vintage/role differs from inspected records")
    if any(r["parent_semantic_review"] != "open" for r in rows):
        fail("Parent source-grouping review status changed")
    return rows


def destination_preservation_check(baseline: Baseline, run_id: str) -> dict:
    sentinel_root = ROOT / OWNED / "vintages" / ("preserve-" + run_id)
    sentinel_root.mkdir(parents=True, exist_ok=False)
    sentinel = sentinel_root / "keep.txt"
    original = b"pre-existing evidence sentinel\n"
    with sentinel.open("xb") as stream:
        stream.write(original)
    before = sha256(sentinel.read_bytes())
    rejected = False
    try:
        NewVintage(baseline, OWNED, "preserve-" + run_id, ["findings.json"])
    except FileExistsError:
        rejected = True
    after_raw = sentinel.read_bytes()
    after = sha256(after_raw)
    sentinel.unlink()
    sentinel_root.rmdir()
    if not rejected or before != after or after_raw != original:
        fail("NewVintage did not reject the occupied destination without changing its sentinel")
    return {"occupied_destination_rejected": rejected, "sentinel_before_sha256": before,
            "sentinel_after_sha256": after, "sentinel_preserved": before == after}


def run(run_id: str) -> Path:
    spec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline_spec = spec["baseline"]
    baseline = Baseline(ROOT, baseline_spec["commit"], baseline_spec["files"])
    helper = "scripts/evidence/immutable.py"
    if baseline.materialized_bytes(helper) != Path(ROOT / helper).read_bytes():
        fail("Shared immutable helper bytes drifted from pinned baseline")
    baseline.pinned_bytes(helper)
    context = context_findings(baseline)

    page_map = json.loads(PAGE_MAP.read_text(encoding="utf-8"))
    pdf_bytes = baseline.pinned_bytes(PDF_PATH)
    if len(pdf_bytes) != EXPECTED_PDF_BYTES or sha256(pdf_bytes) != EXPECTED_PDF_SHA:
        fail("Full treaty volume does not match its original size/hash")
    reader = PdfReader(io.BytesIO(pdf_bytes), strict=True)
    source_observations = verify_page_map(page_map, reader)

    historical = []
    for path in ASSESSMENTS:
        original = json.loads(baseline.pinned_bytes(path))
        errors = scan_historical_record(original)
        if errors != ["beacon_47_wrong_printed_page", "exchange_claim_missing_pages_158_160",
                      "beacon_47_page_missing_from_printed_range"]:
            fail("Expected historical locator/range defect not reproduced in " + path + ": " + repr(errors))
        historical.append({"path": path, "sha256": baseline.pins[path]["sha256"],
                           "detected_findings": errors})

    producer = baseline.pinned_bytes(PRODUCER)
    producer_beacon = extract_producer_beacon(producer)
    if (producer_beacon.get("source_pdf_page"), producer_beacon.get("source_printed_page")) != (166, 165):
        fail("Expected producer beacon-47 false printed page was not reproduced")
    producer_finding = {"path": PRODUCER, "sha256": baseline.pins[PRODUCER]["sha256"],
                        "source_pdf_page": producer_beacon["source_pdf_page"],
                        "historical_source_printed_page": producer_beacon["source_printed_page"],
                        "detected": "beacon_47_wrong_printed_page"}

    # A fresh normalized record with distinct claim/page roles must pass.
    fixture = {row["claim_id"]: row for row in page_map["claims"]}
    for claim_id, row in fixture.items():
        actual = sorted(set(row["correct_pdf_pages"]))
        printed = sorted(set(row["correct_printed_pages"]))
        if actual != printed or not actual:
            fail("Fresh correctly mapped fixture has missing or wrong page binding: " + claim_id)
        for n in actual:
            if n < 157 or n > 176 or not text_page(reader, n):
                fail("Fresh correct fixture points outside No. 2960 or to an empty page: " + claim_id)
    if fixture["main_beacons_english_36_47"]["correct_pdf_pages"] != [166]:
        fail("Fresh fixture fails to map English beacons 36–47")

    # Both modified and truncated bytes must be rejected by the real hash/size gate.
    def authenticate(raw: bytes | None) -> None:
        if raw is None or len(raw) != EXPECTED_PDF_BYTES or sha256(raw) != EXPECTED_PDF_SHA:
            raise ValueError("treaty source bytes failed pinned size/hash")
    altered = pdf_bytes[:-1] + bytes([pdf_bytes[-1] ^ 1])
    truncated = pdf_bytes[:-1]
    rejects = []
    for label, candidate in (("source_absent", None), ("one_byte_changed", altered), ("one_byte_missing", truncated)):
        try:
            authenticate(candidate)
        except ValueError:
            rejects.append(label)
    if rejects != ["source_absent", "one_byte_changed", "one_byte_missing"]:
        fail("Source-byte drift control did not reject absent, altered and truncated source inputs")

    preservation = destination_preservation_check(baseline, run_id)
    method_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {
        "version": 1,
        "issue": 1499,
        "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": baseline.commit,
        "method": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": method_hash,
                   "shared_helper_path": helper, "shared_helper_sha256": baseline.pins[helper]["sha256"]},
        "source_observations": source_observations,
        "historical_report_findings": historical,
        "historical_producer_finding": producer_finding,
        "correct_fixture": {"claim_count": len(fixture), "status": "passed",
                             "beacon_47_pdf_page": 166, "beacon_47_printed_page": 166,
                             "citation_claims_separated": True},
        "source_drift_controls": {"rejected": rejects, "status": "passed"},
        "destination_preservation": preservation,
        "subject_context": context,
        "limitations": [
            "This bounded audit does not rerun the prior full raster CLI or certify its 21 candidates, 49 positive-area pairs among 210 comparisons, or water summaries.",
            "Historical treaty coordinates have no modern datum; beacon 47 latitude was not astronomically observed; no present river-bank or thalweg geometry was inspected.",
            "The ten context IDs resolve in the pinned world index, but their source roles and parent semantic reviews do not establish present administrative status or territorial assignment.",
            "Text extraction supports reproducible page discovery. Human inspection of rendered pages 157–178 remains the independent check of page layout and printed labels.",
        ],
        "status": "passed-locator-controls-only",
    }
    stable = {key: value for key, value in result.items() if key not in ("run_id", "started_at_utc")}
    semantic_hash = sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":"), allow_nan=False).encode("utf-8"))
    result["semantic_result_sha256"] = semantic_hash
    positive = {"method_id": "treaty-page-locator-audit", "kind": "positive-control",
                "outcome": "passed", "run_id": run_id,
                "correct_fixture": result["correct_fixture"],
                "page_166_beacon_47": source_observations["beacon_47_pdf_page"] == 166}
    negative = {"method_id": "treaty-page-locator-audit", "kind": "negative-control",
                "outcome": "passed", "run_id": run_id,
                "historical_findings": historical,
                "producer_finding": producer_finding,
                "source_bytes_rejected": rejects,
                "occupied_destination_preserved": preservation}
    new_run = NewVintage(baseline, OWNED, run_id,
                         ["findings.json", "positive-control.json", "negative-control.json"])
    files = new_run.publish({"findings.json": result, "positive-control.json": positive,
                             "negative-control.json": negative})
    by_name = {Path(row["path"]).name: row for row in files}
    output = ROOT / by_name["findings.json"]["path"]
    print(json.dumps({"run_id": run_id, "outputs": files,
                      "semantic_result_sha256": semantic_hash, "subjects": len(context),
                      "historical_records": len(historical), "status": result["status"]}, indent=2))
    return output


def compare_runs(run_one: str, run_two: str) -> Path:
    """Admit a new receipt first, then authenticate and compare two fresh runs."""
    spec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline_spec = spec["baseline"]
    baseline = Baseline(ROOT, baseline_spec["commit"], baseline_spec["files"])
    helper = "scripts/evidence/immutable.py"
    baseline.materialized_bytes(helper)
    if run_one == run_two:
        fail("Two distinct fresh run IDs are required")
    output_vintage = "treaty-page-audit-repro-1"
    destination = NewVintage(baseline, OWNED, output_vintage, ["reproducibility.json"])
    runs = []
    for run_id in (run_one, run_two):
        folder = ROOT / OWNED / "vintages" / run_id
        receipt = json.loads((folder / "publication.json").read_text(encoding="utf-8"))
        if receipt.get("version") != 1 or receipt.get("status") != "complete":
            fail("Run lacks a complete exclusive publication receipt: " + run_id)
        outputs = {Path(row["path"]).name: row for row in receipt["outputs"]}
        if set(outputs) != {"findings.json", "positive-control.json", "negative-control.json"}:
            fail("Run output inventory incomplete: " + run_id)
        products = {}
        for name, descriptor_row in outputs.items():
            raw = (ROOT / descriptor_row["path"]).read_bytes()
            if len(raw) != descriptor_row["bytes"] or sha256(raw) != descriptor_row["sha256"]:
                fail("Run output changed after its publication receipt: " + run_id + "/" + name)
            products[name] = json.loads(raw)
        finding = products["findings.json"]
        if finding.get("run_id") != run_id or finding.get("method", {}).get("sha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
            fail("Run did not execute this exact validator source: " + run_id)
        for kind in ("positive-control", "negative-control"):
            control = products[kind + ".json"]
            if (control.get("method_id"), control.get("kind"), control.get("outcome"), control.get("run_id")) != (
                    "treaty-page-locator-audit", kind, "passed", run_id):
                fail("Run lacks its real-format control receipt: " + run_id + "/" + kind)
        runs.append({"run_id": run_id, "semantic_result_sha256": finding["semantic_result_sha256"],
                     "publication_sha256": sha256((folder / "publication.json").read_bytes()),
                     "findings_sha256": outputs["findings.json"]["sha256"]})
    if runs[0]["semantic_result_sha256"] != runs[1]["semantic_result_sha256"]:
        fail("Independent bounded executions disagree")
    value = {"method_id": "treaty-page-locator-audit", "kind": "reproducibility",
             "outcome": "passed", "run_one_sha256": runs[0]["semantic_result_sha256"],
             "run_two_sha256": runs[1]["semantic_result_sha256"], "runs": runs,
             "baseline_commit": baseline.commit,
             "note": "Hashes bind each run to its complete exclusive publication receipt and this exact validator source; equal semantic-result hashes exclude only run ID and start timestamp."}
    files = destination.publish({"reproducibility.json": value})
    print(json.dumps({"outputs": files, "runs": [row["run_id"] for row in runs],
                      "semantic_result_sha256": value["run_one_sha256"], "status": value["outcome"]}, indent=2))
    return ROOT / files[0]["path"]


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", help="Fresh, unused evidence vintage name")
    group.add_argument("--compare-runs", nargs=2, metavar=("RUN_ONE", "RUN_TWO"),
                       help="Authenticate two completed independent runs and publish a reproducibility receipt")
    args = parser.parse_args()
    if args.run_id:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.run_id):
            fail("Unsafe run ID")
        run(args.run_id)
    else:
        if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id) for run_id in args.compare_runs):
            fail("Unsafe run ID")
        compare_runs(*args.compare_runs)


if __name__ == "__main__":
    main()
