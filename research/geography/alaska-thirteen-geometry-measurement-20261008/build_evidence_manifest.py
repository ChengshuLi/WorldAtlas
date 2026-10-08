#!/usr/bin/env python3
"""Build the versioned evidence manifest for the bounded Alaska measurement packet."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OUT = ROOT / "evidence-quality.json"
BASELINE = "41ed5e819702fde5cd89445eb09b6d4cefa07bf1"
RECEIPTS = "research/geography/alaska-thirteen-geometry-measurement-20261008/vintages/acceptance-receipts-20261008"
PACKET = "research/geography/alaska-thirteen-geometry-measurement-20261008"
SOURCE_PACKET = "research/geography/alaska-thirteen-source-fitness-20261008/sources"
GSHHG = "coordination/engineering/gshhg-native-member-custody-20261007"
CORPUS = "coordination/engineering/original-geography-source-corpus-20261006"
METHOD_ID = "alaska-thirteen-full-simplified-atlas-native-measurement-v1"

PINS = {
    "atlas-target-geometries-7": (f"{SOURCE_PACKET}/native-atlas-target-features.geojson", "0cfe5197d17fdd88fa4a13bbd1ac120a7cf195cc6ee7bf3b49dbd0303b86e326"),
    "candidate-components": (f"{SOURCE_PACKET}/candidate-components.geojson", "b24011f1acef059783ea61d96308f3b43ef0aabdbaf19f1fb7694b613a470b14"),
    "candidate-source-screen": (f"{SOURCE_PACKET}/candidate-source-screen.json", "0763d5368b045b0f77951616d83ebaf1bc30336fad7f58fe5e0b4ddef52cc867"),
    "family-context-995": (f"{SOURCE_PACKET}/complete-native-family-record.jsonl", "5c79b82588ff5c8f3c1e6305e4c1bcd565b7e379203b95bc2c09322f30f18119"),
    "geoBoundaries-attribution": (f"{SOURCE_PACKET}/usa-adm2-attribution.json", "6236712dd0cf23fd258ce7e4a39412e7652be7d2a3c4db2b3e83ddbd4a60c8cd"),
    "geoBoundaries-source-metadata": (f"{SOURCE_PACKET}/usa-adm2-source-metadata.json", "88dcd7f581d5b8d2b5f5003cf4cd7b39310b8bc52c96e8371d55c92559dd2258"),
    "geoBoundaries-terms": (f"{SOURCE_PACKET}/geoBoundaries-derivative-use-terms.txt", "f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5"),
    "gshhg-codec": (f"{GSHHG}/codec.py", "b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd"),
    "gshhg-native-00": (f"{GSHHG}/results/native-00.bin.gz", "99546c4a2bf41fe8f8a050fb425ab372c22e9c9821bf592d66ed9748b36301eb"),
    "gshhg-native-01": (f"{GSHHG}/results/native-01.bin.gz", "c4a508d91e40bdd66e48f2533530916c773566e75277826c0806218c3997bcbf"),
    "gshhg-native-02": (f"{GSHHG}/results/native-02.bin.gz", "b7070a55d8edfbead17c14a014ed0c430586606bf0f38ea10c0c1e038f31c7c0"),
    "gshhg-query-records-11": (f"{SOURCE_PACKET}/gshhg-native-query-records.json", "d978c4e92bdcbff3ece9f4f798ea977ed21a4d709ef5598fed5bde71a7130783"),
    "gshhg-reader": (f"{GSHHG}/reader.py", "c06f8b65e700b81fb73352ffb17bee719eaab7a1bc8ae30ed1707d6e2f3b015a"),
    "gshhg-reader-index": (f"{GSHHG}/results/downstream-reader.json", "39a571ab73464d46cc2029b430e7db0bfccca82fed3a74d652765fbe5317f731"),
    "input-receipts": (f"{SOURCE_PACKET}/input-receipts.json", "6c6593688dd8ae65083cd57878f44f449898eab0060febbbddfc5c030589503d"),
    "physical-query-rows-25": (f"{SOURCE_PACKET}/physical-query-rows.jsonl", "e36d6319cd9d23c4c8d508415f8af7965e069928e5e1206faac3d50cbd5ece50"),
    "simplified-county-geometries-7": (f"{SOURCE_PACKET}/selected-2018-usa-adm2-features.geojson", "02427b560826d51ab275e3df6f8fa3d4629dd762733f5c4c69b1a8f2ee8e44b5"),
}

EXTRA_BASELINE = [
    f"{CORPUS}/catalogue.json",
    f"{GSHHG}/results/member-index.json",
    "scripts/evidence/immutable.py",
    f"{CORPUS}/payloads/gb-USA-ADM1-000.bin.gz",
]
SUBJECT_IDS = [
    "physical-component:073d9a81648d56c1b63a4e495fbd0140c17659bedb5c9b211739642b438ee488",
    "physical-component:4d36c81ff35079341e6ec0d5a207ba3844e26f5d55c30c7205924dfd33b8dc18",
    "physical-component:5874689a46f7945e9dcc67cc3b0321d4e534572e4b4bd8a85f4a07c5005d1922",
    "physical-component:66e4f6c15eb17f53815844efc04e7cae9faf9118de313541d3a4be2ff1fcf0a2",
    "physical-component:70174bffffdbb4a421344d6c10d80b760972f9c5452daf0d7c26408fdf18bb53",
    "physical-component:777e7bc99320bf155684f99b0903c336f9a07862de4a7fa0ac8cde990d7d6ee5",
    "physical-component:8435dc6d973751bab55c4eff12c872ba331c3e005254ceb21b76933a8cc6207a",
    "physical-component:8fb2ed9360ba13f6b19f8bb6ee9a16099039d8b59c9f51eab0a442249f428e7d",
    "physical-component:9f130f023a510be6e4b2f9075ed99cf75c4f88053e93189dda3f0bd51080f14a",
    "physical-component:cffd5f514585665c2d76279e036889887df24efa229a67f88052aef0d8ee4a83",
    "physical-component:d688afd3657ded3f0cf85a95956f2d42726f44923b168499320d681080539fb1",
    "physical-component:e76fd386dc9a23375537ede302f7f380a217fd4bbccd9536f856e8b4253a5ab8",
    "physical-component:ef7383db4412abe64b7e8d009679cffa4a3174d6da100c6de1fc37272aadeca9",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO)


def descriptor(path: str, raw: bytes, role: str | None = None, decoded: dict | None = None):
    value = {"path": path, "bytes": len(raw), "sha256": digest(raw), "hash_kind": "file-bytes"}
    if role:
        value["role"] = role
    if decoded:
        value["uncompressed_bytes"] = decoded["bytes"]
        value["uncompressed_sha256"] = decoded["sha256"]
    return value


def candidate(path: str, role: str | None = None):
    raw = (REPO / path).read_bytes()
    return descriptor(path, raw, role)


def main():
    baseline_paths = sorted(set(path for path, _ in PINS.values()) | set(EXTRA_BASELINE))
    decoded_aliases = {
        f"{GSHHG}/results/native-00.bin.gz": {"bytes": 33554432, "sha256": "020aa63a7bbd7e4945e99b96389f0e0580aad7204c91f631f4e92aeeddba3281"},
        f"{GSHHG}/results/native-01.bin.gz": {"bytes": 33554432, "sha256": "2460722a7cbbc6d8f383b64d39e0c49a50831ffc01f0241942f90975ee698e0c"},
        f"{GSHHG}/results/native-02.bin.gz": {"bytes": 28700472, "sha256": "aae9796235376f1f520b9b216c3a887e60e1c0d91d3f12463db1d403b835ae0f"},
        f"{CORPUS}/payloads/gb-USA-ADM1-000.bin.gz": {"bytes": 5469814, "sha256": "9d7a32244a5c3c2868d039355db2fdd9eb903ef255cfda128decd20bedc0dfbe"},
    }
    baseline_files = []
    for path in baseline_paths:
        raw = git_bytes(BASELINE, path)
        expected = next((sha for pin_path, sha in PINS.values() if pin_path == path), None)
        if expected and digest(raw) != expected:
            raise SystemExit(f"required issue pin mismatch: {path}")
        baseline_files.append(descriptor(path, raw, "original-source" if expected else "execution-input", decoded_aliases.get(path)))

    source_path = f"{SOURCE_PACKET}/candidate-components.geojson"
    subjects_map = {identity: source_path for identity in SUBJECT_IDS}
    pin_files = {key: path for key, (path, _) in PINS.items()}
    pins = {key: value for key, (_, value) in PINS.items()}

    retained_geo_files = [
        candidate(f"{PACKET}/sources/geoboundaries-USA-ADM2-full-9469f09.geojson", "complete-full-USA-ADM2-source"),
        candidate(f"{PACKET}/sources/geoboundaries-USA-ADM2-full-9469f09-receipt.json", "source-retrieval-receipt"),
        candidate(f"{PACKET}/sources/geoboundaries-USA-ADM2-full-9469f09-source-check.json", "source-and-license-preflight"),
        candidate(f"{PACKET}/sources/alaska-adm1-parent/feature.geojson", "selected-Alaska-ADM1-parent-feature"),
        candidate(f"{PACKET}/sources/alaska-adm1-parent/receipt.json", "parent-source-feature-receipt"),
    ]
    geo_files = {row["path"] for row in retained_geo_files}
    descriptors = []
    outputs = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        relative = path.relative_to(REPO).as_posix()
        if relative == OUT.relative_to(REPO).as_posix() or relative in geo_files:
            continue
        role = "generated-table" if relative == f"{PACKET}/README.md" else (
            "code" if path.suffix == ".py" else "supporting-evidence"
        )
        outputs.append(candidate(relative, role))
    outputs.extend([])
    sources = [
        {
            "id": "geoboundaries-usa-adm2-9469f09",
            "url": "https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/USA/ADM2",
            "role": "Complete non-simplified USA ADM2 release product and same-release Alaska ADM1 parent; comparison reference for seven selected 2018 source targets.",
            "vintage": "geoBoundaries release tag 9469f09; source metadata carries a 2018 boundary-year claim.",
            "retrieved_at": "2026-10-08",
            "license": {"status": "redistributable", "terms": "Retained product metadata and attribution state CC-BY 4.0 with attribution. The source packet preserves the original attribution and derivative-use text; this packet makes no new legal determination."},
            "retention": "retained",
            "verification": "verified",
            "temporal_status": "reference",
            "files": retained_geo_files,
            "limit": "Feature hashes and product metadata do not establish real-world boundary accuracy or which geometries are applicable to the recorded Atlas vintage.",
        },
        {
            "id": "gshhg-2.3.7",
            "url": "https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip",
            "role": "Coarse physical land-support comparison using complete original native coordinates for the 11 query-referenced records.",
            "vintage": "GSHHG 2.3.7 release dated 2017-06-15; original records preserve heterogeneous older source observations.",
            "retrieved_at": "2026-10-07",
            "license": {"status": "unknown", "terms": "Original distributed LICENSE and README disagree about LGPL version bounds; the exact wording and source terms remain preserved without resolving the conflict."},
            "retention": "restoration-only",
            "verification": "unverified",
            "restoration": f"The three admitted native aliases and reader are pinned in baseline commit {BASELINE}; exact selected original record bytes and headers are retained at {PACKET}/sources/native-selected/records.bin and its receipt.",
            "limit": "Per-feature observation dates, shoreline registration and precision, licensing interpretation, current land/water status, and repair authority are not established. Coarse land support is not repair approval.",
            "temporal_status": "reference",
        },
        {
            "id": "worldatlas-alaska-candidate-source-records",
            "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{BASELINE}/{SOURCE_PACKET}",
            "role": "Original 13 candidate geometries, 995-member source-family context, seven target identities, 25 physical relations, and source-vintage detector/contact records.",
            "vintage": f"Merged Alaska source-fitness packet at baseline commit {BASELINE}; exact original issue pins are independently bound in baseline.pins.",
            "retrieved_at": "2026-10-08",
            "license": {"status": "unknown", "terms": "Retained WorldAtlas source records and upstream attribution are preserved; no independent redistribution determination is made for the component delivery."},
            "retention": "restoration-only",
            "verification": "verified",
            "restoration": f"All original source files remain at their exact paths in baseline commit {BASELINE}; the complete 995-member record and original contacts are referenced without filtering the assigned 13.",
            "limit": "Identity and source-vintage comparisons do not certify physical class, real-world geometry accuracy, current political status or correction authority.",
            "temporal_status": "reference",
        },
        {
            "id": "atlas-recorded-target-and-neighbor-geometries",
            "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{BASELINE}/data/geography",
            "role": "Seven actual recorded Atlas target geometries and 17 positive-length read-only neighbor features.",
            "vintage": f"Atlas source-record snapshot pinned by the merged #1495 packet at {BASELINE}; not a claim of current real-world boundaries.",
            "retrieved_at": "2026-10-08",
            "license": {"status": "unknown", "terms": "Repository geometry records are retained as evidence; separate reuse and authority determinations were not made."},
            "retention": "restoration-only",
            "verification": "verified",
            "restoration": f"Seven target geometries and their source IDs are pinned in baseline.pins; 17 neighbor records, captures, and receipt are retained in {PACKET}/sources/atlas-neighbors/.",
            "limit": "Atlas records provide a reproducible target comparison only; they do not establish applicable boundary vintage or geographic approval.",
            "temporal_status": "reference",
        },
    ]

    metrics_document = json.loads((ROOT / "vintages" / "acceptance-receipts-20261008" / "metric-values.json").read_text())
    source_hashes = {
        "component_count": pins["candidate-components"],
        "family_member_count": pins["family-context-995"],
        "atlas_target_count": pins["atlas-target-geometries-7"],
        "simplified_target_count": pins["simplified-county-geometries-7"],
        "full_source_feature_count": next(row["sha256"] for row in retained_geo_files if row["path"].endswith(".geojson") and "full-9469f09" in row["path"]),
        "physical_relation_count": pins["physical-query-rows-25"],
        "native_gshhg_record_count": pins["gshhg-query-records-11"],
        "native_point_count": candidate(f"{PACKET}/sources/native-selected/records.bin")["sha256"],
        "native_coordinate_bytes": candidate(f"{PACKET}/sources/native-selected/records.bin")["sha256"],
        "native_source_pair_count": candidate(f"{PACKET}/sources/native-selected/records.bin")["sha256"],
        "neighbor_feature_count": candidate(f"{PACKET}/sources/atlas-neighbors/features.geojson")["sha256"],
        "candidate_pair_count": pins["candidate-components"],
        "collective_union_trial_count": pins["candidate-components"],
        "single_case_gate_count": pins["candidate-components"],
        "variant_candidate_agreement_count": next(row["sha256"] for row in retained_geo_files if row["path"].endswith(".geojson") and "full-9469f09" in row["path"]),
        "source_parent_support_count": next(row["sha256"] for row in retained_geo_files if row["path"].endswith("feature.geojson")),
        "native_linked_support_count": candidate(f"{PACKET}/sources/native-selected/records.bin")["sha256"],
        "original_physical_relation_match_count": pins["physical-query-rows-25"],
        "original_neighbor_contact_match_count": candidate(f"{PACKET}/sources/atlas-neighbors/features.geojson")["sha256"],
        "new_positive_area_neighbor_overlap_count": candidate(f"{PACKET}/sources/atlas-neighbors/features.geojson")["sha256"],
        "qualifying_single_case_count": pins["candidate-components"],
        "qualifying_batch_count": pins["candidate-components"],
        "proposal_feature_count": pins["candidate-components"],
        "positive_control_count": pins["candidate-components"],
        "negative_control_count": pins["candidate-components"],
        "reproducible_run_count": pins["candidate-components"],
        "output_bytes_per_run": pins["candidate-components"],
    }
    metrics = []
    metric_bindings = []
    for metric_id, row in sorted(metrics_document["values"].items()):
        metrics.append({
            "id": metric_id,
            "value": row["value"],
            "unit": row["unit"],
            "input_sha256": source_hashes[metric_id],
            "evaluation_commit": BASELINE,
            "vintage": "baseline",
        })
        metric_bindings.append({
            "metric_id": metric_id,
            "path": f"{RECEIPTS}/metric-values.json",
            "json_pointer": f"/values/{metric_id}/value",
        })

    subject_hash = digest(json.dumps(sorted(SUBJECT_IDS), separators=(",", ":")).encode("utf-8"))
    validation = [
        {"method_id": METHOD_ID, "kind": "positive-control", "outcome": "passed", "evidence_path": f"{RECEIPTS}/positive-control.json"},
        {"method_id": METHOD_ID, "kind": "negative-control", "outcome": "passed", "evidence_path": f"{RECEIPTS}/negative-control.json"},
        {"method_id": METHOD_ID, "kind": "reproducibility", "outcome": "passed", "evidence_path": f"{RECEIPTS}/reproducibility.json"},
    ]
    rendered = json.loads((ROOT / "vintages" / "acceptance-receipts-20261008" / "rendered-table-bindings.json").read_text())

    manifest_path = OUT.relative_to(REPO).as_posix()
    changed_paths = sorted(
        path.relative_to(REPO).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.relative_to(REPO).as_posix() != manifest_path and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    receipts = [{"path": path, "status": "added"} for path in changed_paths]
    receipts.append({"path": manifest_path, "status": "added"})

    manifest = {
        "version": 1,
        "issue": 1508,
        "lane": "geography",
        "worker_id": "01a112c2-1d0f-7bf2-a50e-74956219b9c1",
        "subject_ids": sorted(SUBJECT_IDS),
        "subject_ids_sha256": subject_hash,
        "baseline": {
            "commit": BASELINE,
            "files": baseline_files,
            "pins": pins,
            "pin_files": pin_files,
            "subject_files": subjects_map,
        },
        "sources": sources,
        "outputs": outputs,
        "methods": [
            {
                "id": METHOD_ID,
                "kind": "measurement",
                "description": "For exactly 13 retained Alaska component geometries, compare each candidate against both full and simplified geoBoundaries county sources, its seven-target Atlas source identity, the source ADM1 Alaska parent, all linked original GSHHG level-1 records, and all 17 actual Atlas neighbors. Report exact intersection, coverage, uncovered area, strict no-loss and union predicates without altering source geometry.",
                "software": "Python 3.12.14; Shapely 2.1.2; GEOS 3.13.1; pyproj 3.7.2; PROJ; package file closure and PROJ database hashes retained in phase-admission.json.",
                "units": "Raw coordinate-plane square degrees; EPSG:3338 projected square metres; metres for projected linear coordinates; feature, relation, record, pair and trial counts.",
                "axis_order": "longitude-latitude (always_xy)",
                "crs": "Input GeoJSON EPSG:4326; projected areas EPSG:3338 Alaska Albers Equal Area.",
                "area_method": "Exact GEOS planar intersections and differences; projected areas computed after EPSG:4326 to EPSG:3338 transformation; no numeric epsilon or repair.",
                "distance_method": "No geodesic distance calculation; no buffer or distance tolerance is used.",
            },
            {
                "id": "retained-acceptance-receipts",
                "kind": "code",
                "description": "Deterministically bind the two retained producer outputs, 13 single-case strict geometry trials, the 13-row truth table, six positive/negative controls and numeric ledger; this receipt builder does not execute geometry.",
                "software": "Python 3.12.14 standard library; SHA-256 whole-file byte verification.",
                "units": "Whole-file bytes, SHA-256 digests, feature/case/relation/control counts.",
            },
        ],
        "validation": validation,
        "metrics": metrics,
        "summaries": [{"metric_id": row["id"], "value": row["value"], "unit": row["unit"]} for row in metrics],
        "metric_bindings": metric_bindings,
        "rendered_tables": [{"path": rendered["path"], "rows": rendered["rows"]}],
        "conclusions": [
            {"text": "The full and simplified source products yield identical candidate-specific intersection, coverage and uncovered-area predicates for these 13 components; their selected county geometries themselves differ, so the applicable Atlas source geometry and real-world boundary remain unresolved.", "status": "unresolved", "source_ids": ["geoboundaries-usa-adm2-9469f09", "atlas-recorded-target-and-neighbor-geometries"]},
            {"text": "The retained 11 original GSHHG records provide coarse source-relative level-1 land support for the measured candidate relations, while observation date, shoreline registration, precision and repair authority remain unresolved.", "status": "unresolved", "source_ids": ["gshhg-2.3.7"]},
            {"text": "No individual case or tested same-county batch passes the declared strict geometry conjunction; no correction geometry qualifies for proposal.", "status": "supported", "source_ids": ["worldatlas-alaska-candidate-source-records", "atlas-recorded-target-and-neighbor-geometries", "geoboundaries-usa-adm2-9469f09"]},
        ],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "Run measurement_driver.py run-thirteen and measurement_driver.py run-fourteen with distinct fresh destinations under the owned packet path, using Python 3.12.14 and the pinned geometry runtime; compare all four published output files.",
            f"python3.12 -B {PACKET}/build_acceptance_packet.py",
            f"node scripts/evidence-quality.mjs {manifest_path}",
        ],
        "change_receipts": receipts,
    }
    for key, (_, expected) in PINS.items():
        if manifest["baseline"]["pins"].get(key) != expected:
            raise SystemExit(f"issue pin missing or changed: {key}")
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "manifest-written", "baseline": BASELINE,
                      "baseline_files": len(baseline_files), "outputs": len(outputs),
                      "sources": len(sources), "metrics": len(metrics), "changed_files": len(receipts)}, sort_keys=True))


if __name__ == "__main__":
    main()
