"""Fail-closed guards shared by the erratum generator and its negative controls."""
import hashlib
from pathlib import Path


def verify_bound_input(descriptor, committed_bytes, working_bytes):
    """Refuse any change from a whole-file input pinned to the evaluation vintage."""
    expected = descriptor['sha256']
    expected_bytes = descriptor['bytes']
    for label, raw in (('historical', committed_bytes), ('working', working_bytes)):
        if len(raw) != expected_bytes or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f'{label} input differs from pinned vintage: {descriptor["path"]}')


def require_new_output(path):
    """Refuse output collisions before creating any run artifact."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f'Immutable erratum output already exists: {path}')
