#!/usr/bin/env python3
"""Positive and adverse checks for the actual Madagascar source verifier."""
import argparse
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reproduce


def expect_refusal(fn, expected_fragment):
    try:
        fn()
    except (ValueError, KeyError) as exc:
        if expected_fragment not in str(exc):
            raise AssertionError("unexpected refusal: %s" % exc)
        return str(exc)
    raise AssertionError("adverse input was accepted")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--law-2021", required=True)
    parser.add_argument("--law-2023", required=True)
    parser.add_argument("--portal-html", required=True)
    args = parser.parse_args()
    law1 = Path(args.law_2021).read_bytes()
    law2 = Path(args.law_2023).read_bytes()
    portal_bytes = Path(args.portal_html).read_bytes()
    corrections = json.loads(reproduce.CORRECTIONS.read_text(encoding="utf-8"))
    positive = reproduce.build_report(law1, law2, portal_bytes)
    if positive["scope"] != {"subject_count": 119, "parent_group_count": 22}:
        raise AssertionError("positive report did not retain exact issue scope")

    bad_law = copy.deepcopy(corrections)
    bad_law["legal_sources"][0]["inspection"]["conditional_effect"]["article"] = 7
    wrong_article = expect_refusal(lambda: reproduce.validate_legal_corrections(bad_law), "wrong article references")

    portal_parser = reproduce.PageParser()
    portal_parser.feed(portal_bytes.decode("utf-8"))
    portal_rows = portal_parser.rows[:-1]
    missing_row = expect_refusal(lambda: reproduce.validate_portal_rows(portal_rows), "row count changed")

    changed_portal = portal_bytes + b"\n<!-- changed response -->"
    changed_hash = expect_refusal(lambda: reproduce.validate_portal_html(changed_portal, corrections["portal_observation"]), "bytes/hash")

    csv_path = "data/regional-review/regional-review-4f180b98473f1071/sources/mdg_admpop_adm3_2018.csv"
    csv_bytes = reproduce.git_blob(reproduce.BASELINE, csv_path)
    csv_lines = csv_bytes.decode("utf-8-sig").splitlines()
    namorona_line = next(i for i, line in enumerate(csv_lines) if "Namorona" in line)
    csv_lines[namorona_line] = csv_lines[namorona_line].replace("Mananjary", "Fakeanjary")
    wrong_parent = ("\n".join(csv_lines) + "\n").encode("utf-8")
    rebound_commune = expect_refusal(lambda: reproduce.validate_namorona_rows(wrong_parent), "wrong ADM2_EN")
    raw_lines = csv_bytes.splitlines(keepends=True)
    raw_namorona_line = next(i for i, line in enumerate(raw_lines) if b"Namorona" in line)
    missing_namorona = b"".join(line for i, line in enumerate(raw_lines) if i != raw_namorona_line)
    missing_source_row = expect_refusal(lambda: reproduce.validate_namorona_rows(missing_namorona), "expected one Namorona row")

    part = json.loads(reproduce.git_blob(reproduce.BASELINE, "data/geography/part-13.json"))
    ids = json.loads(reproduce.ISSUE_SNAPSHOT.read_text(encoding="utf-8"))["body"]
    import re
    import json as _json
    contract = _json.loads(re.search(r"<!--\s*worldatlas-work:v1\s*(\{.*?\})\s*-->", ids, re.S).group(1))
    target_id = "gb:MDG:ADM2:10022922B52512193010711"
    target = next(f for f in part["features"] if f["properties"]["id"] == target_id)
    scoped = set(contract["evidence_quality"]["subject_ids"])
    alternate_parent = next(f["properties"]["parent_id"] for f in part["features"] if f["properties"].get("id") in scoped and f["properties"].get("parent_id") != target["properties"]["parent_id"])
    target["properties"]["parent_id"] = alternate_parent
    rebound_parent = expect_refusal(lambda: reproduce.validate_current_roster(json.dumps(part).encode("utf-8"), contract["evidence_quality"]["subject_ids"]), "current identity/parent changed")

    checks = {
        "version": 1,
        "method_id": "madagascar-source-handoff-correction",
        "positive_control": {"outcome": "passed", "exact_issue_scope": positive["scope"], "legal_citations": positive["legal_citations"], "portal_rows": positive["portal"]["table_rows"]},
        "negative_controls": [
            {"case": "wrong statutory conditional-effect article", "outcome": "passed", "observed_refusal": wrong_article},
            {"case": "removed portal table record", "outcome": "passed", "observed_refusal": missing_row},
            {"case": "modified captured portal bytes", "outcome": "passed", "observed_refusal": changed_hash},
            {"case": "rebound historical Namorona parent", "outcome": "passed", "observed_refusal": rebound_commune},
            {"case": "missing historical Namorona row", "outcome": "passed", "observed_refusal": missing_source_row},
            {"case": "rebound current affected-district parent", "outcome": "passed", "observed_refusal": rebound_parent},
        ],
        "limits": ["PDF page interpretation is independently reviewable; script verifies recorded page/article findings, not PDF glyph extraction.", "No commune-level geometry was available; polygon incorporation remains unknown."],
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
