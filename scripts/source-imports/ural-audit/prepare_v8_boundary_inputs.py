"""Read the V8 Ural recipe from Neon and stage its raw R2 inputs."""
import argparse
import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
import zipfile

import boto3
import psycopg

RECIPE_ID = "v8-ural-construction-recipe"
RECIPE_SHA256 = "1e485322c45a8b135e998845c5aa77d856a6d215cd420504d33a8635e8ebc429"


def verify_bytes(path, pin):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if (path.stat().st_size, digest) != (pin["size_bytes"], pin["sha256"]):
        raise ValueError(f"source bytes differ from pin for {path.name}")


def read_recipe():
    with psycopg.connect(os.environ["NEON_DATABASE_URL"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        row = connection.execute(
            """SELECT sha256,size_bytes,document::text
               FROM atlas.structured_documents WHERE (source_id,version)=(%s,%s)""",
            (RECIPE_ID, "v8.0-" + RECIPE_SHA256[:12]),
        ).fetchone()
        if row is None:
            raise ValueError("V8 Ural construction recipe is missing")
        digest, size, text = row
        raw = text.encode()
        if (digest, size, hashlib.sha256(raw).hexdigest()) != (RECIPE_SHA256, len(raw), RECIPE_SHA256):
            raise ValueError("V8 Ural recipe pin mismatch")
        recipe = json.loads(raw)
        for source in recipe["source_inputs"]:
            for pin in source.get("parts", [source]):
                asset = connection.execute(
                    """SELECT r2_bucket,r2_key,size_bytes,sha256 FROM atlas.source_assets
                       WHERE kind='raw' AND (source_id,version)=(%s,%s)""",
                    (pin["source_id"], pin["version"]),
                ).fetchone()
                if asset != ("worldatlas", pin["r2_key"], pin["size_bytes"], pin["sha256"]):
                    raise ValueError(f"Neon source pin mismatch for {pin['source_id']}")
    return raw, recipe


def stage_source(client, folder, source):
    dest = folder / source["name"]
    if not dest.exists():
        output = NamedTemporaryFile(dir=folder, prefix=dest.name + ".", delete=False)
        partial = Path(output.name)
        try:
            with output:
                for part in source.get("parts", [source]):
                    response = client.get_object(Bucket="worldatlas", Key=part["r2_key"])
                    digest = hashlib.sha256()
                    size = 0
                    with closing(response["Body"]) as stream:
                        while block := stream.read(4 * 1024 * 1024):
                            output.write(block)
                            digest.update(block)
                            size += len(block)
                    if (size, digest.hexdigest()) != (part["size_bytes"], part["sha256"]):
                        raise ValueError(f"R2 input bytes differ from pin for {part['r2_key']}")
            verify_bytes(partial, source)
            partial.rename(dest)
        finally:
            partial.unlink(missing_ok=True)
    verify_bytes(dest, source)


def extract_hydrobasins(folder, area):
    target = folder / f"ural-hydro-{area}"
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(folder / f"ural-hydro-{area}.zip") as archive:
        for extension in ("shp", "shx", "dbf"):
            name = f"hybas_{area}_lev12_v1c.{extension}"
            path = target / name
            if not path.exists():
                output = NamedTemporaryFile(dir=target, prefix=name + ".", delete=False)
                partial = Path(output.name)
                try:
                    with output, archive.open(name) as member:
                        shutil.copyfileobj(member, output)
                    partial.rename(path)
                finally:
                    partial.unlink(missing_ok=True)
            with archive.open(name) as member:
                pin = dict(size_bytes=archive.getinfo(name).file_size,
                           sha256=hashlib.file_digest(member, "sha256").hexdigest())
            verify_bytes(path, pin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r2-endpoint", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    raw, recipe = read_recipe()
    inputs = args.work_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    client = boto3.client("s3", endpoint_url=args.r2_endpoint, region_name="auto")
    for source in recipe["source_inputs"]:
        stage_source(client, inputs, source)
    for area in ("eu", "si"):
        extract_hydrobasins(inputs, area)
    recipe_path = args.work_dir / "recipe.json"
    if recipe_path.exists() and recipe_path.read_bytes() != raw:
        raise ValueError("work directory contains a different Ural recipe")
    if not recipe_path.exists():
        with recipe_path.open("xb") as output:
            output.write(raw)
    print(f"Verified Ural recipe and raw inputs in {args.work_dir}")


if __name__ == "__main__":
    main()
