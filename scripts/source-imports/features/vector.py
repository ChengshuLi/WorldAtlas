"""Read selected vector features through GDAL's Python API."""
import json
from pathlib import Path
from zipfile import ZipFile

from osgeo import ogr, osr

from features.geometry import geometry_hash, validate_geometry


def dataset_path(path, member=None):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != '.zip':
        if member is not None:
            raise ValueError('archive member supplied for a non-archive source')
        return str(path)
    with ZipFile(path) as archive:
        names = archive.namelist()
        if member is None:
            candidates = [name for name in names if name.lower().endswith('.shp')]
            if len(candidates) != 1:
                raise ValueError('select one vector dataset archive member')
            member = candidates[0]
        if names.count(member) != 1:
            raise ValueError('selected vector archive member is missing or duplicated')
    return '/vsizip/' + str(path) + '/' + member


def read_features(path, settings):
    """Extract requested provider IDs once; no continent or grid decisions."""
    selected = settings['selections']
    wanted = {str(item['source_feature_id']): item for item in selected}
    if not wanted or len(wanted) != len(selected):
        raise ValueError('provider feature selections must be unique')
    source = ogr.Open(dataset_path(path, settings.get('member')), 0)
    if source is None:
        raise ValueError('source vector dataset cannot be opened')
    layer_name = settings.get('layer')
    if layer_name is None and source.GetLayerCount() != 1:
        raise ValueError('select one source vector layer')
    layer = source.GetLayerByName(layer_name) if layer_name else source.GetLayer(0)
    if layer is None:
        raise ValueError('selected vector layer is missing')
    id_field = settings['id_field']
    if id_field == '@fid':
        fids = {key: int(key) for key in wanted}
    else:
        if layer.GetLayerDefn().GetFieldIndex(id_field) < 0:
            raise ValueError('selected provider ID field is missing')
        layer.SetIgnoredFields(['OGR_GEOMETRY'])
        fids = {}
        for row in layer:
            key = str(row.GetField(id_field))
            if key in wanted:
                if key in fids:
                    raise ValueError('selected provider feature is duplicated')
                fids[key] = row.GetFID()
        layer.SetIgnoredFields([])
    if fids.keys() != wanted.keys():
        raise ValueError('selected provider feature is missing')
    original = layer.GetSpatialRef()
    if original is None:
        raise ValueError('vector source has no coordinate reference')
    original = original.Clone()
    original.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    target.SetFromUserInput('OGC:CRS84')
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    operation = settings.get('coordinate_operation')
    options = osr.CoordinateTransformationOptions()
    if operation:
        options.SetOperation(operation)
    conversion = osr.CreateCoordinateTransformation(original, target, options)
    result = []
    for key, selection in wanted.items():
        row = layer.GetFeature(fids[key])
        if row is None:
            raise ValueError('selected provider feature is missing')
        properties = row.items()
        if any(properties.get(name) != value for name, value in
               selection.get('expected_properties', {}).items()):
            raise ValueError('source feature identity properties do not match')
        geometry = row.GetGeometryRef()
        if geometry is None:
            raise ValueError('source feature has no geometry')
        geometry = geometry.Clone()
        if geometry.Transform(conversion) != 0:
            raise ValueError('source geometry coordinate conversion failed')
        value = json.loads(geometry.ExportToJson(options=['COORDINATE_PRECISION=15']))
        validate_geometry(value)
        expected = selection.get('expected_geometry_sha256')
        if expected and geometry_hash(value) != expected:
            raise ValueError('selected source geometry checksum differs')
        result.append({'feature_id': selection['feature_id'], 'source_feature_id': key,
                       'geometry': value,
                       'evidence': {'source_coordinate_reference': original.ExportToWkt(),
                                    'provider_properties': properties}})
    return result
