#!/usr/bin/env python3
"""Read-only reproduction for the Madagascar source citation erratum.

The original laws and Torolalana response are not redistributed. Supply privately
restored bytes from the exact URLs/digests recorded in source-corrections.json.
This program writes nothing; its JSON report goes to standard output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from typing import List, Optional
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ISSUE_SNAPSHOT = HERE / "issue-1509-api.json"
CORRECTIONS = HERE / "source-corrections.json"
BASELINE = "b765c34077b6d7c5745c7285f08e954edd62144a"
PR1352 = "af355b897c9e3607de610549cfffb890c8e43378"
PR1368 = "839883ae281af7bf012f694698624a7ec77275e1"
RUN14 = "data/regional-review/madagascar-codab-followup-20261003/vintages/2026-10-07-v1-run-14"
PACKET = "data/regional-review/madagascar-codab-followup-20261003"
SCOPE = "data/regional-review/regional-review-4f180b98473f1071"
EXPECTED_LEGAL = {
    "MDG-LAW-2021-012": (4, 5),
    "MDG-LAW-2023-012": (5, 6),
}
EXPECTED_PORTAL_ROWS = {
    ("VATOVAVY", 54, "IFANADIANA"),
    ("FITOVINANY", 55, "IKONGO"),
    ("FITOVINANY", 56, "MANAKARA"),
    ("VATOVAVY", 57, "MANANJARY"),
    ("VATOVAVY", 58, "NOSY VARIKA"),
    ("FITOVINANY", 59, "VOHIPENO"),
    ("ANALANJIROFO", 87, "MANANARA-NORD"),
    ("ANALANJIROFO", 88, "MAROANTSETRA"),
}
MADAGASCAR_IDS = {
    "gb:MDG:ADM2:10022922B52512193010711": ("Mananjary", "framework:province:vatovavy-fitovinany:fd10ec52071e"),
    "gb:MDG:ADM2:10022922B29911348985828": ("Manakara Atsimo", "framework:province:vatovavy-fitovinany:fd10ec52071e"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"])


def parse_contract(issue: dict) -> dict:
    if issue.get("number") != 1509 or issue.get("state") != "open":
        fail("issue snapshot is not the current open #1509 contract")
    found = re.search(r"<!--\s*worldatlas-work:v1\s*(\{.*?\})\s*-->", issue.get("body", ""), re.S)
    if not found:
        fail("issue snapshot has no worldatlas-work:v1 block")
    contract = json.loads(found.group(1))
    if contract.get("mode") != "geography" or contract.get("owned_paths") != [
        "research/geography/madagascar-source-citation-1352-erratum-20261008/"
    ]:
        fail("issue contract mode or exact owned path changed")
    return contract


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self._in_title = False
        self._table_depth = 0
        self._row: Optional[List[str]] = None
        self._cell: Optional[List[str]] = None
        self.rows: List[List[str]] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content") or ""
        if tag == "table":
            self._table_depth += 1
        elif tag == "tr" and self._table_depth:
            self._row = []
        elif tag in ("td", "th") and self._table_depth:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in ("td", "th") and self._cell is not None:
            value = " ".join("".join(self._cell).split())
            if self._row is not None:
                self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._table_depth and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._cell is not None:
            self._cell.append(data)


def validate_legal_corrections(corrections: dict) -> List[dict]:
    by_id = {row.get("source_id"): row for row in corrections.get("legal_sources", [])}
    results = []
    for source_id, expected in EXPECTED_LEGAL.items():
        source = by_id.get(source_id)
        if not source:
            fail(f"missing legal source {source_id}")
        inspection = source.get("inspection", {})
        actual = (
            inspection.get("conditional_effect", {}).get("article"),
            inspection.get("journal_publication", {}).get("article"),
        )
        if actual != expected:
            fail(f"wrong article references for {source_id}: {actual}")
        if inspection.get("exact_broadcast_posting_and_journal_publication_dates") != "unknown":
            fail(f"unsupported effective/publication date claim for {source_id}")
        if "Article 7" in json.dumps(inspection, ensure_ascii=False):
            fail(f"stale Article 7 citation remains in corrected facts for {source_id}")
        results.append({"source_id": source_id, "effect_article": actual[0], "journal_article": actual[1], "passed": True})
    transfer = corrections.get("territorial_trace", {}).get("legal_source", "")
    if transfer != "MDG-LAW-2021-012, Article 1 explanatory text and annex":
        fail("missing exact legal source for Namorona transfer")
    return results


def validate_portal_rows(rows: List[List[str]]) -> dict:
    data_rows = [r for r in rows if len(r) >= 3 and r[1].isdigit()]
    if len(data_rows) != 114:
        fail(f"portal rendered table row count changed: {len(data_rows)}")
    normalized = {(r[0].strip().upper(), int(r[1]), r[2].strip().upper()) for r in data_rows}
    ids = {row[1] for row in normalized}
    missing = sorted(set(range(1, 120)) - ids)
    if missing != [8, 9, 10, 11, 12]:
        fail(f"portal table identifier omissions changed: {missing}")
    if len({row[0] for row in normalized}) != 23:
        fail("portal table region-name roster changed")
    if any("ANTANIMORA" in " ".join(map(str, row)) for row in normalized):
        fail("portal table unexpectedly contains Antanimora")
    if not EXPECTED_PORTAL_ROWS.issubset(normalized):
        fail("portal rows for Vatovavy/Fitovinany or Ambatosoa source handoff changed")
    return {
        "table_rows": len(data_rows),
        "unique_region_names": len({row[0] for row in normalized}),
        "missing_district_ids": missing,
        "antanimora_row_present": False,
        "relevant_rows": [list(row) for row in sorted(EXPECTED_PORTAL_ROWS)],
    }


def validate_portal_html(body: bytes, source: dict) -> dict:
    if len(body) != source["bytes"] or sha256(body) != source["sha256"]:
        fail("portal response bytes/hash do not match the recorded 2026-10-08 vintage")
    parser = PageParser()
    parser.feed(body.decode("utf-8"))
    if "Régions et districts" not in parser.title:
        fail("unexpected portal page title")
    description = parser.description.lower()
    if "23 régions" not in description or "119" not in description:
        fail("portal page description no longer has its 23-region/119-district claim")
    result = validate_portal_rows(parser.rows)
    result["title"] = " ".join(parser.title.split())
    result["description_claimed_regions"] = 23
    result["description_claimed_districts"] = 119
    result["response_bytes"] = len(body)
    result["response_sha256"] = sha256(body)
    return result


def validate_namorona_rows(csv_bytes: bytes) -> tuple[dict, List[dict]]:
    text = csv_bytes.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    matches = [r for r in rows if r.get("ADM3_EN", "").strip().casefold() == "namorona"]
    if len(rows) != 1579 or len(matches) != 1:
        fail(f"expected one Namorona row in the complete 1,579-row 2018 ADM3 file; got {len(matches)} of {len(rows)}")
    row = matches[0]
    expected = {
        "ADM1_PCODE": "MG23",
        "ADM1_EN": "Vatovavy Fitovinany",
        "ADM2_PCODE": "MG23209",
        "ADM2_EN": "Mananjary",
        "ADM3_PCODE": "MG23209490",
        "ADM3_TYPE": "Commune",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            fail(f"Namorona source row has wrong {key}: {row.get(key)!r}")
    return row, rows


def validate_current_roster(part_bytes: bytes, expected_ids: List[str]) -> tuple[dict, dict]:
    part = json.loads(part_bytes)
    features = [f for f in part.get("features", []) if f.get("properties", {}).get("id") in set(expected_ids)]
    by_id = {f["properties"]["id"]: f["properties"] for f in features}
    if len(expected_ids) != 119 or len(set(expected_ids)) != 119 or set(by_id) != set(expected_ids):
        fail("issue's exact 119-subject scope does not resolve one-to-one in pinned geography")
    parents = {p.get("parent_id") for p in by_id.values()}
    if len(parents) != 22:
        fail(f"expected the retained 22 parent groups, got {len(parents)}")
    for subject_id, expected in MADAGASCAR_IDS.items():
        props = by_id.get(subject_id)
        if not props or (props.get("name"), props.get("parent_id")) != expected:
            fail(f"current identity/parent changed for {subject_id}")
    return by_id, {"subject_count": len(by_id), "parent_group_count": len(parents)}


def validate_historical_files(corrections: dict) -> dict:
    expected = corrections["historical_claims"]
    result = {}
    files = {
        "original_1352_readme": (PR1352, f"{PACKET}/README.md"),
        "original_1352_source_restoration": (PR1352, f"{PACKET}/source-restoration.json"),
        "later_1368_readme": (PR1368, f"{PACKET}/README.md"),
        "later_1368_source_restoration": (PR1368, f"{PACKET}/source-restoration.json"),
    }
    for key, (commit, path) in files.items():
        raw = git_blob(commit, path)
        pinned = expected[key]
        if len(raw) != pinned["bytes"] or sha256(raw) != pinned["sha256"]:
            fail(f"historical file no longer matches exact {key} bytes")
        result[key] = {"commit": commit, "path": path, "bytes": len(raw), "sha256": sha256(raw)}
    old_restore = git_blob(PR1352, f"{PACKET}/source-restoration.json").decode("utf-8")
    later_restore = git_blob(PR1368, f"{PACKET}/source-restoration.json").decode("utf-8")
    old_readme = git_blob(PR1352, f"{PACKET}/README.md").decode("utf-8")
    later_readme = git_blob(PR1368, f"{PACKET}/README.md").decode("utf-8")
    for law_year in ("2021", "2023"):
        stale = "Article 7 makes effect contingent"
        if stale not in old_restore or stale not in later_restore:
            fail(f"original Article 7 defect for Law {law_year} is not present in both preserved vintages")
    if "Namorona" in old_readme or "Namorona" in later_readme:
        fail("historical README unexpectedly includes the specific Namorona transfer")
    if "gives older Vatovavy-Fitovinany context" not in later_readme:
        fail("expected contradictory later README portal description was not found")
    result["source_restoration_has_article_7_claim_in_both_vintages"] = True
    result["readmes_omit_namorona_transfer"] = True
    result["later_readme_has_outdated_portal_wording"] = True
    return result


def verify_source_bytes(raw: bytes, label: str, expected_size: int, expected_hash: str) -> bytes:
    if len(raw) != expected_size or sha256(raw) != expected_hash:
        fail(f"restored source does not match recorded full bytes/hash: {label}")
    return raw


def read_verified_source(path: Path, expected_size: int, expected_hash: str) -> bytes:
    return verify_source_bytes(path.read_bytes(), path.name, expected_size, expected_hash)


def build_report(law2021: bytes, law2023: bytes, portal_html: bytes, *, root: Optional[Path] = None) -> dict:
    root = (root or HERE.parents[2]).resolve()
    issue = json.loads(ISSUE_SNAPSHOT.read_text(encoding="utf-8"))
    contract = parse_contract(issue)
    corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    legal = validate_legal_corrections(corrections)
    law_sources = {s["source_id"]: s for s in corrections["legal_sources"]}
    verify_source_bytes(law2021, "Law 2021-012", law_sources["MDG-LAW-2021-012"]["bytes"], law_sources["MDG-LAW-2021-012"]["sha256"])
    verify_source_bytes(law2023, "Law 2023-012", law_sources["MDG-LAW-2023-012"]["bytes"], law_sources["MDG-LAW-2023-012"]["sha256"])
    portal = validate_portal_html(portal_html, corrections["portal_observation"])

    pin_commit = {
        "data/world-index.json": BASELINE,
        "data/geography/part-13.json": BASELINE,
        "data/hierarchy.json": BASELINE,
        f"{SCOPE}/issue-scope.json": BASELINE,
        f"{SCOPE}/sources.json": BASELINE,
        f"{SCOPE}/sources/mdg_admpop_adm3_2018.csv": BASELINE,
        f"{PACKET}/reproduction/reproduce_codab.py": PR1352,
        f"{PACKET}/README.md": PR1368,
        f"{PACKET}/source-restoration.json": PR1368,
    }
    contract_pins = contract["evidence_quality"]["pins"]
    verified_pins = {}
    for path, digest in contract_pins.items():
        commit = pin_commit[path]
        raw = git_blob(commit, path)
        if sha256(raw) != digest:
            fail(f"issue-pinned historical input differs: {path}")
        verified_pins[path] = {"commit": commit, "bytes": len(raw), "sha256": sha256(raw)}

    codps = git_blob(BASELINE, f"{SCOPE}/sources/mdg_admpop_adm3_2018.csv")
    codps_digest = contract_pins[f"{SCOPE}/sources/mdg_admpop_adm3_2018.csv"]
    if sha256(codps) != codps_digest:
        fail("pinned original COD-PS ADM3 bytes changed")
    namorona, all_communes = validate_namorona_rows(codps)
    part = git_blob(BASELINE, "data/geography/part-13.json")
    by_id, scope = validate_current_roster(part, contract["evidence_quality"]["subject_ids"])
    crosswalk = git_blob(PR1352, f"{RUN14}/adm2-crosswalk-and-geometry.csv")
    crosswalk_sha = sha256(crosswalk)
    if crosswalk_sha != corrections["territorial_trace"]["source_comparison"]["sha256"]:
        fail("historical run-14 district comparison bytes changed")
    comparison_rows = list(csv.DictReader(io.StringIO(crosswalk.decode("utf-8-sig"), newline="")))
    selected = {r["source_adm2_name"]: r for r in comparison_rows if r["source_adm2_name"] in {"Mananjary", "Manakara Atsimo"}}
    expected_ids = {"Mananjary": "gb:MDG:ADM2:10022922B52512193010711", "Manakara Atsimo": "gb:MDG:ADM2:10022922B29911348985828"}
    for name, subject_id in expected_ids.items():
        if selected.get(name, {}).get("current_location_id") != subject_id:
            fail(f"historical crosswalk no longer binds {name} to expected stable ID")
    old_data = json.loads(git_blob(PR1352, f"{PACKET}/source-restoration.json"))
    codab = next(s for s in old_data["sources"] if s["source_id"] == "OCHA-HDX-COD-AB-MDG-V01")
    district_metrics = {
        "mananjary_symmetric_difference_percent_of_union": float(selected["Mananjary"]["symmetric_difference_percent_of_union"]),
        "manakara_symmetric_difference_percent_of_union": float(selected["Manakara Atsimo"]["symmetric_difference_percent_of_union"]),
        "source_file": f"{RUN14}/adm2-crosswalk-and-geometry.csv",
        "source_commit": PR1352,
        "source_sha256": crosswalk_sha,
        "interpretation_limit": "These archived whole-district comparisons do not test the Namorona commune transfer.",
    }
    if district_metrics["mananjary_symmetric_difference_percent_of_union"] != 0.741515803 or district_metrics["manakara_symmetric_difference_percent_of_union"] != 1.049105499:
        fail("historical whole-district metric changed")
    summary = {
        "version": 1,
        "issue": 1509,
        "method_id": "madagascar-source-handoff-correction",
        "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "executed_reproducer_sha256": sha256((HERE / "reproduce.py").read_bytes()),
        "source_hashes_verified": {
            "law_2021_sha256": law_sources["MDG-LAW-2021-012"]["sha256"],
            "law_2023_sha256": law_sources["MDG-LAW-2023-012"]["sha256"],
            "portal_sha256": portal["response_sha256"],
        },
        "legal_citations": legal,
        "scope": scope,
        "historical_district_metrics": district_metrics,
        "namorona": {
            "old_commune_code": namorona["ADM3_PCODE"],
            "old_district": namorona["ADM2_EN"],
            "old_district_code": namorona["ADM2_PCODE"],
            "old_region": namorona["ADM1_EN"],
            "old_region_code": namorona["ADM1_PCODE"],
            "legal_new_parent": "Manakara district",
            "old_adm3_file_rows": len(all_communes),
            "old_adm3_matching_records": 1,
            "current_district_ids": list(expected_ids.values()),
            "current_district_parent": by_id[expected_ids["Mananjary"]]["parent_id"],
            "codab_metadata": codab["metadata"],
            "polygon_incorporation_of_transfer": "unknown",
            "post_transfer_commune_code_or_territory_continuity": "unknown",
        },
        "portal": portal,
        "historical_handoff": validate_historical_files(corrections),
        "issue_pins": verified_pins,
        "limits": corrections["scope_and_unknowns"],
        "inherited_followups": corrections["related_inherited_evidence"]["remaining_work"],
    }
    # Preserve the complete verified source row while keeping source PDFs and the
    # portal response out of the repository due unresolved redistribution terms.
    return summary


def reproduce(args: argparse.Namespace) -> dict:
    corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    sources = {s["source_id"]: s for s in corrections["legal_sources"]}
    law2021 = read_verified_source(Path(args.law_2021), sources["MDG-LAW-2021-012"]["bytes"], sources["MDG-LAW-2021-012"]["sha256"])
    law2023 = read_verified_source(Path(args.law_2023), sources["MDG-LAW-2023-012"]["bytes"], sources["MDG-LAW-2023-012"]["sha256"])
    portal = Path(args.portal_html).read_bytes()
    return build_report(law2021, law2023, portal)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law-2021", required=True)
    parser.add_argument("--law-2023", required=True)
    parser.add_argument("--portal-html", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(reproduce(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
