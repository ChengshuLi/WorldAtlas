"""Read selected vector features through GDAL's Python API."""

import json
from pathlib import Path
import time
from typing import Literal, NotRequired
from zipfile import ZipFile

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import FeatureIdentity, NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features


class VectorSelection(FeatureIdentity):
    """Select one provider geometry or the records in a provider collection."""

    collection: NotRequired[bool]
    expected_feature_count: NotRequired[int]
    polygon_containing: NotRequired[tuple[float, float]]
    holes: NotRequired[Literal["preserve", "outer_envelope"]]


def dataset_path(path, member=None):
    """Find the dataset path understood by GDAL.

    Args:
        path: Local vector file or ZIP archive.
        member: Optional dataset path inside the archive.

    Returns:
        A filesystem path or GDAL virtual ZIP path.

    Raises:
        ValueError: The archive selection is missing or ambiguous.
    """
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".zip":
        if member is not None:
            raise ValueError("archive member supplied for a non-archive source")
        return str(path)
    with ZipFile(path) as archive:
        names = archive.namelist()
        if member is None:
            candidates = [name for name in names if name.lower().endswith(".shp")]
            if len(candidates) != 1:
                raise ValueError("select one vector dataset archive member")
            member = candidates[0]
        if names.count(member) != 1:
            raise ValueError("selected vector archive member is missing or duplicated")
    return "/vsizip/" + str(path) + "/" + member


def geojson_geometries(path, member, id_field, wanted):
    """Read original GeoJSON coordinates with their JSON number representation.

    Args:
        path: Local GeoJSON file or ZIP archive.
        member: GeoJSON member name for archived inputs.
        id_field: Provider attribute or ``@fid`` used to identify records.
        wanted: Provider IDs to select, converted to strings.

    Returns:
        Original geometry dictionaries keyed by selected provider ID.
    """
    path = Path(path)
    if member is not None:
        with ZipFile(path) as archive:
            document = json.loads(archive.read(member))
    else:
        document = json.loads(path.read_bytes())
    rows = (
        document["features"] if document["type"] == "FeatureCollection" else [document]
    )
    result = {}
    for ordinal, row in enumerate(rows):
        ident = row.get("id")
        fid = ident if type(ident) is int else ordinal
        key = str(
            fid if id_field == "@fid" else row.get("properties", {}).get(id_field)
        )
        if key in wanted:
            result[key] = row["geometry"] if row["type"] == "Feature" else row
    return result


def polygon_containing(geometry, coordinates):
    """Select an original polygon part by an interior WGS84 point.

    Args:
        geometry: Polygon or multipolygon to search.
        coordinates: Longitude and latitude of the selection point.

    Returns:
        The selected polygon, including its original rings.

    Raises:
        ValueError: The point is invalid or falls inside anything other
            than one polygon interior.
    """
    from shapely.geometry import Polygon

    point = validate_geometry({"type": "Point", "coordinates": coordinates})
    if geometry["type"] not in ("Polygon", "MultiPolygon"):
        raise ValueError("polygon_containing needs polygon geometry")
    parts = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    selected = [
        rings for rings in parts if Polygon(rings[0], rings[1:]).contains(point)
    ]
    if len(selected) != 1:
        raise ValueError("selection point must be strictly inside one source polygon")
    return {"type": "Polygon", "coordinates": selected[0]}


def read_features(path, *, id_field, selections, member=None, layer=None, coordinate_operation=None):
    """Extract selected vector records and convert their geometry to WGS84.

    Args:
        path: Verified local vector dataset or archive.
        id_field: Provider ID attribute or ``@fid`` for the native feature ID.
        selections: Output feature IDs paired with provider records and options.
        member: Optional dataset member inside a ZIP archive.
        layer: Optional dataset layer name.
        coordinate_operation: Optional explicit CRS transformation.

    Returns:
        Selected features with their output IDs, provider IDs, and geometries.

    Raises:
        ValueError: A dataset, selection, CRS, or geometry is invalid.
    """
    from osgeo import ogr, osr

    selected = selections
    wanted = {str(item["source_feature_id"]) for item in selected}
    collections = {
        str(item["source_feature_id"]) for item in selected if item.get("collection")
    }
    identifiers = [item["feature_id"] for item in selected]
    if not wanted or len(set(identifiers)) != len(selected):
        raise ValueError("output feature selections must be unique")
    source = ogr.Open(dataset_path(path, member), 0)
    if source is None:
        raise ValueError("source vector dataset cannot be opened")
    layer_name = layer
    if layer_name is None and source.GetLayerCount() != 1:
        raise ValueError("select one source vector layer")
    layer = source.GetLayerByName(layer_name) if layer_name else source.GetLayer(0)
    if layer is None:
        raise ValueError("selected vector layer is missing")
    if id_field == "@fid":
        fids = {key: [int(key)] for key in wanted}
    else:
        if layer.GetLayerDefn().GetFieldIndex(id_field) < 0:
            raise ValueError("selected provider ID field is missing")
        layer.SetIgnoredFields(["OGR_GEOMETRY"])
        fids = {}
        for row in layer:
            key = str(row.GetField(id_field))
            if key in wanted:
                if key in fids and key not in collections:
                    raise ValueError("selected provider feature is duplicated")
                fids.setdefault(key, []).append(row.GetFID())
        layer.SetIgnoredFields([])
    if fids.keys() != wanted:
        raise ValueError("selected provider feature is missing")
    original = layer.GetSpatialRef()
    if original is None:
        raise ValueError("vector source has no coordinate reference")
    original = original.Clone()
    original.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    reference = "OGC:CRS84"
    if target.SetFromUserInput(reference) != 0:
        raise ValueError("unsupported output coordinate reference")
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    operation = coordinate_operation
    options = osr.CoordinateTransformationOptions()
    if operation:
        options.SetOperation(operation)
    conversion = osr.CreateCoordinateTransformation(original, target, options)
    source_geometries = None
    if (
        source.GetDriver().GetName() == "GeoJSON"
        and not operation
        and not collections
        and original.IsSame(target, ["IGNORE_DATA_AXIS_TO_SRS_AXIS_MAPPING=YES"])
    ):
        source_geometries = geojson_geometries(path, member, id_field, wanted)
    result = []
    for selection in selected:
        key = str(selection["source_feature_id"])
        if selection.get("expected_feature_count", len(fids[key])) != len(fids[key]):
            raise ValueError(
                "source collection does not contain the expected number of features"
            )
        if not selection.get("collection") and len(fids[key]) != 1:
            raise ValueError("selected provider feature is duplicated")
        values = []
        for fid in fids[key]:
            row = layer.GetFeature(fid)
            if row is None:
                raise ValueError("selected provider feature is missing")
            geometry = row.GetGeometryRef()
            if geometry is None:
                raise ValueError("source feature has no geometry")
            geometry = geometry.Clone()
            if source_geometries is None and geometry.Transform(conversion) != 0:
                raise ValueError("source geometry coordinate conversion failed")
            options = (
                ["SIGNIFICANT_FIGURES=17"]
                if source.GetDriver().GetName() == "GeoJSON"
                else []
            )
            value = (
                source_geometries[key]
                if source_geometries is not None
                else json.loads(geometry.ExportToJson(options=options))
            )
            validate_geometry(value)
            values.append(value)
        if selection.get("collection"):
            from shapely.geometry import mapping, shape
            from shapely import union_all

            value = json.loads(
                json.dumps(mapping(union_all([shape(v) for v in values])))
            )
            validate_geometry(value)
        else:
            value = values[0]
        if "polygon_containing" in selection:
            value = polygon_containing(value, selection["polygon_containing"])
        if selection.get("holes", "preserve") == "outer_envelope":
            from shapely import union_all
            from shapely.geometry import Polygon, mapping

            if value["type"] not in ("Polygon", "MultiPolygon"):
                raise ValueError("outer_envelope requires a polygon source")
            parts = (
                [value["coordinates"]]
                if value["type"] == "Polygon"
                else value["coordinates"]
            )
            value = mapping(union_all([Polygon(rings[0]) for rings in parts]))
            value = json.loads(json.dumps(value, allow_nan=False))
            validate_geometry(value)
        result.append(
            {
                "feature_id": selection["feature_id"],
                "source_feature_id": key,
                "geometry": value,
            }
        )
    return result


def selected_vector_features(
    runtime: Runtime,
    *,
    source_id: SourceId,
    id_field: NonEmptyText,
    selections: list[VectorSelection],
    member: NonEmptyText | None = None,
    layer: NonEmptyText | None = None,
    coordinate_operation: NonEmptyText | None = None,
):
    """Import selected vector features as WGS84 GeoJSON.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the vector source.
        id_field: Provider ID attribute or ``@fid``.
        selections: Provider features and their output IDs and options.
        member: Optional dataset member inside a ZIP archive.
        layer: Optional dataset layer name.
        coordinate_operation: Optional explicit CRS transformation.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    features = read_features(path, id_field=id_field, selections=selections, member=member,
                             layer=layer, coordinate_operation=coordinate_operation)
    feature_ids = save_features(runtime, features)
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))
