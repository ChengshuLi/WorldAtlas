"""Assemble one geographic area from its contributing structured source features."""

import json
import time
from typing import Literal

from shapely import union_all
from shapely.geometry import mapping, shape

from worldatlas.source_imports.contracts import NonEmptyText, Runtime
from worldatlas.source_imports.features.geometry import feature_footprint, save_features


def composed_area(
    runtime: Runtime,
    *,
    feature_id: NonEmptyText,
    input_feature_ids: list[NonEmptyText],
    basis: NonEmptyText,
    footprint: Literal["source", "bounding_box"] = "source",
):
    """Union a geographic family's source areas; retain every contributing input."""
    recipe = runtime.recipe(locals())
    if (
        not input_feature_ids
        or len(set(input_feature_ids)) != len(input_feature_ids)
        or feature_id in input_feature_ids
    ):
        raise ValueError(
            "a composed area needs distinct input features and a separate output"
        )
    started = time.monotonic()
    with runtime.connect() as database, runtime.saving(database):
        rows = database.execute(
            "SELECT feature_id,source_id,source_feature_id,geometry FROM atlas.source_features "
            "WHERE feature_id=ANY(%s) ORDER BY feature_id FOR SHARE",
            (input_feature_ids,),
        ).fetchall()
        inputs = {r[0]: r for r in rows}
        if set(inputs) != set(input_feature_ids):
            raise ValueError("composed area refers to a missing source feature")
        values = []
        for ident in input_feature_ids:
            value = shape(inputs[ident][3])
            if (
                value.is_empty
                or not value.is_valid
                or value.geom_type not in ("Polygon", "MultiPolygon")
            ):
                raise ValueError("a composed area needs valid polygon inputs")
            values.append(value)
        geometry = feature_footprint(
            json.loads(json.dumps(mapping(union_all(values)))), footprint
        )
        # The first input supplies the primary provider identity; the construction
        # retains every additional input and its own raw-source relationship.
        primary = inputs[input_feature_ids[0]]
        hashes = save_features(
            database,
            [
                dict(
                    feature_id=feature_id,
                    source_id=primary[1],
                    source_feature_id=primary[2],
                    geometry=geometry,
                )
            ],
            recipe,
        )
    return dict(
        geometry_sha256=hashes,
        input_feature_ids=input_feature_ids,
        timing=dict(
            download_seconds=0.0, processing_seconds=time.monotonic() - started
        ),
    )
