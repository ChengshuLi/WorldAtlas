#!/usr/bin/env python3
"""Exact-name lookup in the pinned, undated identity/migration archive.

Reads one immutable Git blob, never writes archive data or candidate geometry.
This is an identity/name search only; a miss is not proof of absence.
"""
import gzip
import json
import re
import subprocess
import unicodedata

BASELINE = "8b6835dfa645cf763137374c3730401d5ac2f732"
ARCHIVE = "data/geographic-migration-archive.json.gz"
ALIASES = [
    "Makin", "Butaritari", "Marakei", "Abaiang", "Tarawa", "Maiana",
    "Abemama", "Kuria", "Aranuka", "Nonouti", "Tabiteuea", "Beru",
    "Nikunau", "Onotoa", "Tamana", "Arorae", "Banaba",
    "Kanton", "Canton", "Birnie", "Enderbury", "Manra", "Sydney",
    "McKean", "Nikumaroro", "Gardner", "Orona", "Hull", "Rawaki",
    "Phoenix", "Teraina", "Washington", "Tabuaeran", "Fanning",
    "Kiritimati", "Christmas", "Malden", "Starbuck", "Vostok", "Flint",
    "Millennium", "Caroline",
]


def normalized(value):
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", ascii_text.casefold())


def main():
    raw = subprocess.check_output(["git", "show", f"{BASELINE}:{ARCHIVE}"])
    archive = json.loads(gzip.decompress(raw))
    aliases = {normalized(name): name for name in ALIASES}
    hits = {name: [] for name in ALIASES}
    for collection in ("locations", "units"):
        for index, row in enumerate(archive[collection]):
            name = row.get("name")
            if isinstance(name, str) and normalized(name) in aliases:
                hits[aliases[normalized(name)]].append({
                    "collection": collection,
                    "index": index,
                    "id": row.get("id"),
                    "name": name,
                    "level": row.get("level"),
                    "parent_id": row.get("parent_id"),
                })
    result = {
        "baseline_commit": BASELINE,
        "archive_path": ARCHIVE,
        "search": "Unicode NFKD ASCII casefold; remove non-alphanumeric characters; exact normalized equality on each row name in locations and units",
        "physical_name_aliases": ALIASES,
        "archive_collection_counts": {key: len(archive[key]) for key in ("locations", "units")},
        "hits": {name: rows for name, rows in hits.items() if rows},
        "limits": [
            "The archive is undated and has no geometry; names and ID parents alone are identity clues.",
            "An exact-name miss may reflect another label, an ID without a physical island name, or omitted history; it is not proof of absence.",
            "A hit is not assigned to Kiribati without independent parent/source context.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
