"""Read selected vector features through GDAL's Python API."""

import json
from pathlib import Path
import time
from typing import NotRequired
from zipfile import ZipFile

from osgeo import gdal, ogr, osr
from shapely import union_all
from shapely.geometry import Polygon, mapping

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import FeatureIdentity, NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features


class VectorSelection(FeatureIdentity):
    """Select one provider geometry and optionally refine its polygon."""

    polygon_containing: NotRequired[tuple[float, float]]
    fill_holes: NotRequired[bool]


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
            # The .shp is the entry point. GDAL finds its companion files in the ZIP.
            candidates = [name for name in names if name.lower().endswith(".shp")]
            if len(candidates) != 1:
                raise ValueError("select one vector dataset archive member")
            member = candidates[0]
        if names.count(member) != 1:
            raise ValueError("selected vector archive member is missing or duplicated")
    return "/vsizip/" + str(path) + "/" + member


def native_geojson_geometry(feature, path, member):
    """Read original coordinates for the feature GDAL selected.

    Args:
        feature: Feature from a GeoJSON dataset opened with native data enabled.
        path: Local GeoJSON file or ZIP archive.
        member: GeoJSON member name for archived inputs.

    Returns:
        The original geometry dictionary for this feature.
    """
    native = feature.GetNativeData()
    if native is not None:
        return json.loads(native)["geometry"]

    # For a file containing just a geometry, GDAL supplies a feature with no
    # native data. The entire original JSON document is the selected geometry.
    path = Path(path)
    if member is not None:
        with ZipFile(path) as archive:
            return json.loads(archive.read(member))
    return json.loads(path.read_bytes())


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


def read_features(path, *, id_field, selections, member=None, layer=None):
    """Extract selected vector records and convert their geometry to WGS84.

    Args:
        path: Verified local vector dataset or archive.
        id_field: Provider ID attribute or ``@fid`` for the native feature ID.
        selections: Output feature IDs paired with provider records and options.
        member: Optional dataset member inside a ZIP archive.
        layer: Optional dataset layer name.

    Returns:
        Selected features with their output IDs and geometries.

    Raises:
        ValueError: A dataset, selection, CRS, or geometry is invalid.
    """
    wanted = {str(item["source_feature_id"]) for item in selections}
    identifiers = [item["feature_id"] for item in selections]
    # A source record can be saved under several IDs. Each output ID is unique.
    if not wanted or len(set(identifiers)) != len(selections):
        raise ValueError("output feature selections must be unique")
    # Request each GeoJSON feature's original JSON. The @ makes the option
    # optional for drivers that do not support it.
    # Use return codes here regardless of GDAL's exception setting elsewhere.
    with gdal.ExceptionMgr(useExceptions=False):
        source = gdal.OpenEx(
            dataset_path(path, member), gdal.OF_VECTOR, open_options=["@NATIVE_DATA=YES"]
        )
    if source is None:
        raise ValueError("source vector dataset cannot be opened")
    layer_name = layer
    if layer_name is None and source.GetLayerCount() != 1:
        raise ValueError("select one source vector layer")
    layer = source.GetLayerByName(layer_name) if layer_name else source.GetLayer(0)
    if layer is None:
        raise ValueError("selected vector layer is missing")
    if id_field == "@fid":
        fids = {key: int(key) for key in wanted}
    else:
        if layer.GetLayerDefn().GetFieldIndex(id_field) < 0:
            raise ValueError("selected provider ID field is missing")
        # Match the requested attribute values exactly, then ask GDAL for
        # geometry only when fetching the matched records by their native IDs.
        layer.SetIgnoredFields(["OGR_GEOMETRY"])
        fids = {}
        for row in layer:
            key = str(row.GetField(id_field))
            if key in wanted:
                if key in fids:
                    raise ValueError("selected provider feature is duplicated")
                fids[key] = row.GetFID()
        layer.SetIgnoredFields([])
    if fids.keys() != wanted:
        raise ValueError("selected provider feature is missing")
    original = layer.GetSpatialRef()
    if original is None:
        raise ValueError("vector source has no coordinate reference")
    original = original.Clone()
    # GeoJSON requires longitude first even when a CRS declares latitude first.
    original.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    reference = "OGC:CRS84"
    with osr.ExceptionMgr(useExceptions=False):
        status = target.SetFromUserInput(reference)
    if status != 0:
        raise ValueError("unsupported output coordinate reference")
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    is_geojson = source.GetDriver().ShortName == "GeoJSON"
    # Skip coordinate conversion when the source already has the required values.
    use_native_coordinates = (
        is_geojson
        and original.IsSame(target, ["IGNORE_DATA_AXIS_TO_SRS_AXIS_MAPPING=YES"])
    )
    if not use_native_coordinates:
        with osr.ExceptionMgr(useExceptions=False):
            conversion = osr.CreateCoordinateTransformation(original, target)
        if conversion is None:
            raise ValueError("source coordinate reference cannot be converted to WGS84")
    export_options = ["SIGNIFICANT_FIGURES=17"] if is_geojson else []

    result = []
    for selection in selections:
        key = str(selection["source_feature_id"])
        row = layer.GetFeature(fids[key])
        if row is None:
            raise ValueError("selected provider feature is missing")
        geometry = row.GetGeometryRef()
        if geometry is None:
            raise ValueError("source feature has no geometry")
        if use_native_coordinates:
            value = native_geojson_geometry(row, path, member)
        else:
            geometry = geometry.Clone()
            with ogr.ExceptionMgr(useExceptions=False):
                status = geometry.Transform(conversion)
            if status != 0:
                raise ValueError("source geometry coordinate conversion failed")
            value = json.loads(geometry.ExportToJson(options=export_options))
        validate_geometry(value)
        # Test containment against the original holes before filling any of them.
        if "polygon_containing" in selection:
            value = polygon_containing(value, selection["polygon_containing"])
        if selection.get("fill_holes", False):
            if value["type"] not in ("Polygon", "MultiPolygon"):
                raise ValueError("fill_holes requires a polygon source")
            parts = (
                [value["coordinates"]]
                if value["type"] == "Polygon"
                else value["coordinates"]
            )
            # Build from exterior rings only. A union also merges parts that
            # overlap once their holes are filled.
            value = mapping(union_all([Polygon(rings[0]) for rings in parts]))
            value = json.loads(json.dumps(value, allow_nan=False))
            validate_geometry(value)
        result.append(
            {
                "feature_id": selection["feature_id"],
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
):
    """Import selected vector features as WGS84 GeoJSON.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the vector source.
        id_field: Provider ID attribute or ``@fid``.
        selections: Provider features and their output IDs and options.
        member: Optional dataset member inside a ZIP archive.
        layer: Optional dataset layer name.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    features = read_features(path, id_field=id_field, selections=selections,
                             member=member, layer=layer)
    feature_ids = save_features(runtime, features)
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))
