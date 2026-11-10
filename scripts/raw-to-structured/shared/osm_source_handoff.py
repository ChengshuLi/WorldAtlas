#!/usr/bin/env python3
"""Verify an archived OSM chain against a selected boundary before use."""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from shared.assemble_osm_ways import assemble


def assemble_archive(archive, archive_sha256):
    """Check an OSM source archive and assemble its manifest's boundary."""
    archive = Path(archive)
    with archive.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if digest != archive_sha256:
        raise ValueError('source archive hash mismatch')
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory() as temp:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or any(
                not n or Path(n).name != n or '\\' in n or n in ('.', '..')
                or i.is_dir() for n, i in zip(names, infos)):
            raise ValueError('duplicate or unsafe archive names')
        manifest = json.loads(z.read('manifest.json'))
        wanted = [e['file'] for e in manifest['ways']]
        if len(wanted) != len(set(wanted)) or set(names) != {'manifest.json', *wanted}:
            raise ValueError('archive manifest does not match members')
        directory = Path(temp)
        for name in wanted:
            (directory / name).write_bytes(z.read(name))
        return assemble(manifest, directory)


def verified_geometry(archive, archive_sha256, selected_geometry_sha256):
    """Reconstruct a boundary and compare it with an expected geometry hash."""
    geom = assemble_archive(archive, archive_sha256)
    encoded = json.dumps(geom, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != selected_geometry_sha256:
        raise ValueError('reconstructed boundary differs from selected boundary')
    return geom
