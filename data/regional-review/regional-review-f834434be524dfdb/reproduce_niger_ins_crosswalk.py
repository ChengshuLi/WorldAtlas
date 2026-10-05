#!/usr/bin/env python3
"""Recreate the 2012 INS census-row crosswalk from private NER source bytes."""
import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import unicodedata

PACKET = Path("data/regional-review/regional-review-f834434be524dfdb")
INS_SHA256 = "a8833e9460c1fb42c0647c42b99b518144ca34923e8e1de3296bae1ee153b6a7"
NER_SHA256 = "9e51e9033ff65c867faa8d741a5b39522d448fa15ae75e0bf5b1da68cb7bc5fa"


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = self.in_cell = False
        self.text = ""
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.text = ""

    def handle_data(self, data):
        if self.in_cell:
            self.text += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.row.append(" ".join(self.text.split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.row)
            self.in_row = False


def normalize(value):
    return "".join(ch for ch in unicodedata.normalize("NFKD", value.upper())
                   if not unicodedata.combining(ch) and ch.isalnum())


def baseline_json(path, commit):
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ins-html", required=True, help="private-cache historical official INS HTML matching the captured hash")
    parser.add_argument("--adm3", required=True, help="private-cache pinned NER ADM3 GeoJSON")
    parser.add_argument("--output", default=str(PACKET / "niger-ins-crosswalk.json"))
    args = parser.parse_args()
    raw = Path(args.ins_html).read_bytes()
    if hashlib.sha256(raw).hexdigest() != INS_SHA256:
        raise SystemExit("INS source hash mismatch")
    raw_ner = Path(args.adm3).read_bytes()
    if hashlib.sha256(raw_ner).hexdigest() != NER_SHA256:
        raise SystemExit("NER ADM3 source hash mismatch")
    parser = Table()
    parser.feed(raw.decode("utf-8", errors="replace"))
    official = [row[:3] for row in parser.rows if len(row) >= 3]
    scope = json.loads((PACKET / "issue-scope.json").read_text())
    ids = {value for value in scope["member_location_ids"] if value.startswith("gb:NER:ADM3:")}
    atlas = {}
    baseline = json.loads((PACKET / "baseline-inputs.json").read_text())
    commit = "0c6232db2b2f9531a479f0c752f66c4d12013f3b"
    if baseline["baseline_commit"] != commit:
        raise SystemExit("Unexpected baseline commit")
    for entry in baseline["files"]:
        if entry["path"].startswith("data/geography/") and entry["path"].endswith(".json"):
            for feat in baseline_json(entry["path"], commit).get("features", []):
                props = feat["properties"]
                if props.get("id") in ids:
                    atlas[props["id"]] = props
    if set(atlas) != ids:
        raise SystemExit("Pinned Atlas scope not found")

    aliases = {
        "SARKIN YAMA": "SARKIN YAMMA",
        "MARADI I": "MARADI ARRONDISSEMENT 1",
        "MARADI II": "MARADI ARRONDISSEMENT 2",
        "MARADI III": "MARADI ARRONDISSEMENT 3",
        "TAHOUA I": "TAHOUA ARRONDISSEMENT 1",
        "TAHOUA II": "TAHOUA ARRONDISSEMENT 2",
        "MATAMÉYE": "MATAMEY",
    }
    rows = []
    for feature in json.loads(raw_ner)["features"]:
        props = feature["properties"]
        identity = "gb:NER:ADM3:" + props["shapeID"]
        if identity not in ids:
            continue
        name = props["shapeName"].strip()
        parent = atlas[identity]["parent_id"].split(":")[2].replace("-", " ")
        if name == "Tibiri" and parent == "guidan roumdji":
            target = "TIBIRI (MARADI)"
        elif name == "Tibiri":
            target = "TIBIRI (DOUTCHI)"
        elif name == "Gangara" and parent == "tanout":
            target = "GANGARA (TANOUT)"
        elif name == "Gangara":
            target = "GANGARA (AGUIE)"
        else:
            target = aliases.get(name.upper(), name)
        candidates = [row for row in official if normalize(row[2]) == normalize(target)]
        project_parent = normalize(parent.replace("tahoua ville", "tahoua"))

        def parent_matches(row):
            department = normalize(row[1])
            return department == project_parent or (
                row[1].startswith("VILLE DE ") and
                project_parent == normalize(row[1].replace("VILLE DE ", "")))

        matches = [row for row in candidates if parent_matches(row)]
        if len(matches) == 1:
            resolution = ("official-spelling-or-role-alias-confirmed" if target != name
                          else "exact-normalized-official-name-and-parent")
            selected = matches[0]
        elif candidates:
            resolution, selected = "official-name-candidate-parent-unresolved", candidates
        else:
            resolution, selected = "unresolved-official-roster-match", []
        rows.append({"id": identity, "source_name": name,
                     "atlas_parent": atlas[identity]["parent_id"],
                     "official_INS_2012_row": selected, "resolution": resolution,
                     "official_role_limit": "INS 2012 census/projection table; not a current legal gazetteer or independent polygon boundary"})
    if len(rows) != 204 or len({row["id"] for row in rows}) != len(rows):
        raise SystemExit("Scoped row count/uniqueness failed")
    counts = {}
    for row in rows:
        counts[row["resolution"]] = counts.get(row["resolution"], 0) + 1
    output = {"version": 1,
              "source": {"title": "INS Niger Projections démographiques 2012–2026",
                         "url": "https://www.stat-niger.org/projections/",
                         "sha256": INS_SHA256, "extracted_rows": len(official),
                         "retrieval_limit": "Verify the exact body hash; the older nested routes currently return non-table content."},
              "method": "Python standard-library HTMLParser extracts three source columns. Normalize Unicode accents/punctuation and join source feature name plus Atlas parent slug to INS commune and department; apply explicit spelling and special-city arrondissement aliases. Duplicate names use the parent label.",
              "summary": counts, "scoped_rows": sorted(rows, key=lambda row: row["id"])}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"official_rows": len(official), "scoped_rows": len(rows), "resolutions": counts,
                      "limits": "census statistical labels are not a current legal gazetteer"}, indent=2))


if __name__ == "__main__":
    main()
