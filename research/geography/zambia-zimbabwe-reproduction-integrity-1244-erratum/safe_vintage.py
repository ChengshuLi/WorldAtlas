"""Read-only validation of completed fresh output vintages."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat

from evidence_core import HERE, OWNED, ROOT, sha


def read_complete(vintage: str, expected_names: set[str]) -> tuple[dict, dict[str, bytes]]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        raise ValueError("Unsafe vintage name")
    directory = ROOT / OWNED / "vintages" / vintage
    for ancestor in [directory, *directory.parents]:
        if ancestor == ROOT.parent:
            break
        if ancestor.is_symlink():
            raise ValueError("Symlink in completed-vintage path")
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Missing ordinary completed vintage")
    dfd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        pubfd = os.open("publication.json", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=dfd)
        try:
            with os.fdopen(pubfd, "rb", closefd=False) as stream:
                receipt_raw = stream.read(64 * 1024)
        finally:
            os.close(pubfd)
        receipt = json.loads(receipt_raw)
        outputs = receipt.get("outputs")
        names = {Path(row["path"]).name for row in outputs or []}
        if receipt.get("version") != 1 or receipt.get("status") != "complete" or names != expected_names or len(outputs) != len(expected_names):
            raise ValueError("Incomplete or unexpected publication receipt")
        if set(os.listdir(dfd)) != expected_names | {"publication.json"}:
            raise ValueError("Vintage directory contains unreceipted, missing or partial outputs")
        files = {}
        for row in outputs:
            name = Path(row["path"]).name
            if row["path"] != OWNED + "vintages/" + vintage + "/" + name:
                raise ValueError("Output receipt path escaped its owned vintage")
            fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=dfd)
            try:
                st = os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or st.st_size != row.get("bytes"):
                    raise ValueError("Published file type/size changed")
                if st.st_size > 32 * 1024 * 1024:
                    raise ValueError("Published output exceeds 32 MiB")
                chunks = []
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
            finally:
                os.close(fd)
            if sha(raw) != row.get("sha256"):
                raise ValueError("Published output hash changed: " + name)
            if name.endswith(".gz"):
                import gzip
                decoded_size = 0
                with gzip.GzipFile(fileobj=__import__("io").BytesIO(raw)) as stream:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        decoded_size += len(chunk)
                        if decoded_size > 32 * 1024 * 1024:
                            raise ValueError("Decoded output exceeds 32 MiB")
            files[name] = raw
        return {"receipt_sha256": sha(receipt_raw), "receipt": receipt}, files
    finally:
        os.close(dfd)
