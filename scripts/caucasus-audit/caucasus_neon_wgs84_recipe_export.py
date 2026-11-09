"""Export the pinned Caucasus WGS84 construction recipe."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_neon_recipe(expected_sha):
    import psycopg

    with psycopg.connect(os.environ["NEON_DATABASE_URL"]) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        row = connection.execute(
            """
            SELECT sha256, size_bytes, document::text
            FROM atlas.structured_documents
            WHERE source_id='v8-caucasus-construction-recipe' AND version=%s
            """,
            ("v8.0-" + expected_sha[:12],),
        ).fetchone()
    if row is None:
        raise ValueError("Caucasus construction recipe is missing")
    digest, size, text = row
    raw = text.encode()
    if digest != expected_sha or size != len(raw) or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("stored Caucasus recipe pin mismatch")
    return text


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-neon", action="store_true")
    source.add_argument("--recipe-text", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = read_neon_recipe(args.sha256) if args.from_neon else args.recipe_text.read_text()
    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict) or value.get("schema") != "caucasus-approved-wgs84-recipe-v2":
        raise ValueError("wrong recipe schema")
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ValueError("Neon recipe hash mismatch")
    with args.output.open("xb") as output:
        output.write(raw)
    print("recipe_sha256", args.sha256, "bytes", len(raw))


if __name__ == "__main__":
    main()
