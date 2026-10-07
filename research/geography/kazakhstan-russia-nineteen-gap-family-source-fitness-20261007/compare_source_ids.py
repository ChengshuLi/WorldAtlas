#!/usr/bin/env python3
"""Compare feature identity sets in pinned full and simplified geoBoundaries files."""

import argparse
import hashlib
import json
from pathlib import Path

RELEASE = "9469f09592ced973a3448cf66b6100b741b64c0d"
RUS_SHA256 = "74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(path: Path) -> tuple[int, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [feature["properties"]["shapeID"] for feature in data["features"]]
    return len(ids), sorted(ids)


def id_digest(ids: list[str]) -> str:
    payload = "".join(value + "\n" for value in ids).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compare(
    country: str,
    full: Path,
    simplified: Path,
    full_retention: str,
    full_packet_path: str | None,
    simplified_packet_path: str,
) -> dict:
    full_count, full_ids = inspect(full)
    simple_count, simple_ids = inspect(simplified)
    full_set, simple_set = set(full_ids), set(simple_ids)
    if len(full_set) != len(full_ids) or len(simple_set) != len(simple_ids):
        raise ValueError(f"{country} source contains duplicate shapeID values")
    full_sha, simple_sha = sha256(full), sha256(simplified)
    if country == "RUS" and full_sha != RUS_SHA256:
        raise ValueError(f"RUS full source digest mismatch: {full_sha}")
    return {
        "full_feature_count": full_count,
        "full_unique_id_count": len(full_set),
        "full_id_list_sha256": id_digest(full_ids),
        "full_source_bytes": full.stat().st_size,
        "full_source_preservation": full_retention,
        "full_source_path_in_packet": full_packet_path,
        "full_source_sha256": full_sha,
        "same_id_set": full_set == simple_set,
        "full_only_count": len(full_set - simple_set),
        "simplified_only_count": len(simple_set - full_set),
        "simplified_feature_count": simple_count,
        "simplified_unique_id_count": len(simple_set),
        "simplified_id_list_sha256": id_digest(simple_ids),
        "simplified_source_bytes": simplified.stat().st_size,
        "simplified_source_path_in_packet": simplified_packet_path,
        "simplified_source_sha256": sha256(simplified),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--rus-full", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    inputs = args.packet / "inputs"
    entries = {
        "KAZ": compare(
            "KAZ",
            inputs / "geoboundaries-kaz-adm2-2017-full-source.geojson",
            inputs / "geoboundaries-kaz-adm2-2017-simplified-full-source.geojson",
            "included in packet",
            "inputs/geoboundaries-kaz-adm2-2017-full-source.geojson",
            "inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson",
        ),
        "RUS": compare(
            "RUS",
            args.rus_full,
            inputs / "geoboundaries-rus-adm2-2017-simplified-full-source.geojson",
            "local restoration cache; omitted from ordinary packet because of per-file size cap",
            None,
            "inputs/geoboundaries-rus-adm2-2017-simplified-full-source.geojson",
        ),
    }
    entries["RUS"]["full_source_url"] = (
        "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/"
        f"{RELEASE}/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson"
    )
    entries["RUS"]["advertised_feature_count"] = 2328
    result = {
        "comparison": "sorted unique feature properties.shapeID values; identity set only, no geometry equality claim",
        "id_list_digest": "sha256 of UTF-8 concatenation of each sorted shapeID followed by LF",
        "release_commit": RELEASE,
        "method": "Parsed both GeoJSON FeatureCollections, extracted properties.shapeID, sorted values, counted duplicates, and compared exact sets. SHA-256 fingerprints were calculated over the sorted IDs with one LF after each ID.",
        "results": entries,
        "scope_note": "A matching ID set does not establish geometry equivalence, positional accuracy, completeness of the underlying territorial source, temporal applicability, or legal authority. RUS count mismatch remains unresolved.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
