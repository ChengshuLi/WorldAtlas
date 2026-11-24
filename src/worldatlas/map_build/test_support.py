"""Small input-contract fixtures; no external sources or geographic decisions."""

import io
from contextlib import closing
from unittest.mock import Mock, patch

from worldatlas.shared import r2
from worldatlas.shared.files import sha256_file
from worldatlas.source_assets.cache import SourceCache


def r2_file_pin(path, *, key=None):
    """Describe fixture bytes as an R2 object using their actual size and hash."""
    return {
        "r2_bucket": "test-bucket",
        "r2_key": path.name if key is None else key,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def cache_fixture_file(cache_directory, path, source):
    """Populate a test's real source cache through a fake R2 response."""
    storage = Mock()
    content = path.read_bytes()
    storage.get_object.return_value = {
        "Body": io.BytesIO(content), "ContentLength": len(content)
    }
    with (
        patch.object(r2, "make_r2_client", return_value=r2.R2Client(storage)),
        closing(SourceCache(cache_directory)) as cache,
    ):
        return cache.acquire(source)


def selection():
    return dict(
        schema="worldatlas-input-selection-v4",
        raw_sources=[],
        construction_records=[],
        geography=dict(
            schema="worldatlas-geographic-division-v2",
            levels=[dict(id="world", parent_id=None)],
            entities=[
                dict(
                    id=0,
                    name="World",
                    level_id="world",
                    parent_id=None,
                    physical_class="mixed",
                    color_rgb=None,
                )
            ],
            features=[],
            category_bindings=[],
            rules=[],
            rule_features=[],
            rule_targets=[],
            rule_sources=[],
            construction_sources=[],
            sources=[],
        ),
    )
