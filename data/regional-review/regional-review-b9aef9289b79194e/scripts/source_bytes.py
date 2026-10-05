"""Read original source streams, including exact ordered byte-partitioned inputs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
PARTITIONS = {
    "gb-ZAF-ADM3.geojson": (
        "gb-ZAF-ADM3.geojson.part-001",
        "gb-ZAF-ADM3.geojson.part-002",
    ),
}

def source_bytes(filename: str) -> bytes:
    """Return original source bytes. Partitions are concatenated without transformation."""
    names = PARTITIONS.get(filename)
    if names:
        return b"".join((SOURCES / name).read_bytes() for name in names)
    return (SOURCES / filename).read_bytes()

def source_parts(filename: str) -> list[dict]:
    """Describe retained part paths, raw byte lengths and hashes."""
    import hashlib
    names = PARTITIONS.get(filename, (filename,))
    rows = []
    for name in names:
        path = SOURCES / name
        raw = path.read_bytes()
        rows.append({"path": "sources/" + name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return rows
