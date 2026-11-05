#!/usr/bin/env python3
"""Verify an archived OSM chain against a selected boundary before use."""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from assemble_osm_ways import assemble


def verified_geometry(archive, archive_sha256, selected_geometry_sha256):
    archive = Path(archive)
    raw = archive.read_bytes()
    if len(raw) > 16 << 20 or hashlib.sha256(raw).hexdigest() != archive_sha256:
        raise ValueError('source archive size or hash mismatch')
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory() as temp:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or any(Path(n).name != n for n in names):
            raise ValueError('duplicate or unsafe archive names')
        if any(i.file_size > 4 << 20 for i in infos) or sum(i.file_size for i in infos) > 32 << 20:
            raise ValueError('archive expanded size limit')
        manifest = json.loads(z.read('manifest.json'))
        wanted = [e['file'] for e in manifest['ways']]
        if len(wanted) != len(set(wanted)) or set(names) != {'manifest.json', *wanted}:
            raise ValueError('archive manifest does not match members')
        directory = Path(temp)
        for name in wanted:
            (directory / name).write_bytes(z.read(name))
        geom = assemble(manifest, directory)
    encoded = json.dumps(geom, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != selected_geometry_sha256:
        raise ValueError('reconstructed boundary differs from selected boundary')
    return geom
