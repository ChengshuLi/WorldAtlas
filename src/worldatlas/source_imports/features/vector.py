"""Read selected vector features through GDAL's Python API."""
import json
from pathlib import Path
from zipfile import ZipFile

from osgeo import ogr, osr

from worldatlas.source_imports.features.geometry import validate_geometry


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


def geojson_geometries(path, member, id_field, wanted):
    """Preserve source coordinate values, including integer JSON numbers."""
    path = Path(path)
    if member is not None:
        with ZipFile(path) as archive:
            document = json.loads(archive.read(member))
    else:
        document = json.loads(path.read_bytes())
    rows = document['features'] if document['type'] == 'FeatureCollection' else [document]
    result = {}
    for ordinal, row in enumerate(rows):
        ident = row.get('id')
        fid = ident if type(ident) is int else ordinal
        key = str(fid if id_field == '@fid' else row.get('properties', {}).get(id_field))
        if key in wanted:
            result[key] = row['geometry'] if row['type'] == 'Feature' else row
    return result


def read_features(path, settings):
    """Extract requested provider IDs once; no continent or grid decisions."""
    selected = settings['selections']
    wanted = {str(item['source_feature_id']) for item in selected}
    collections = {str(item['source_feature_id']) for item in selected if item.get('collection')}
    identifiers = [item['feature_id'] for item in selected]
    if not wanted or len(set(identifiers)) != len(selected):
        raise ValueError('output feature selections must be unique')
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
        fids = {key: [int(key)] for key in wanted}
    else:
        if layer.GetLayerDefn().GetFieldIndex(id_field) < 0:
            raise ValueError('selected provider ID field is missing')
        layer.SetIgnoredFields(['OGR_GEOMETRY'])
        fids = {}
        for row in layer:
            key = str(row.GetField(id_field))
            if key in wanted:
                if key in fids and key not in collections:
                    raise ValueError('selected provider feature is duplicated')
                fids.setdefault(key, []).append(row.GetFID())
        layer.SetIgnoredFields([])
    if fids.keys() != wanted:
        raise ValueError('selected provider feature is missing')
    original = layer.GetSpatialRef()
    if original is None:
        raise ValueError('vector source has no coordinate reference')
    original = original.Clone()
    original.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = osr.SpatialReference()
    reference = 'OGC:CRS84'
    if target.SetFromUserInput(reference) != 0:
        raise ValueError('unsupported output coordinate reference')
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    operation = settings.get('coordinate_operation')
    options = osr.CoordinateTransformationOptions()
    if operation:
        options.SetOperation(operation)
    conversion = osr.CreateCoordinateTransformation(original, target, options)
    source_geometries = None
    if (source.GetDriver().GetName() == 'GeoJSON' and not operation
            and not collections and original.IsSame(target, ['IGNORE_DATA_AXIS_TO_SRS_AXIS_MAPPING=YES'])):
        source_geometries = geojson_geometries(path, settings.get('member'), id_field, wanted)
    result = []
    for selection in selected:
        key = str(selection['source_feature_id'])
        if selection.get('expected_feature_count', len(fids[key])) != len(fids[key]):
            raise ValueError('source collection does not contain the expected number of features')
        if not selection.get('collection') and len(fids[key]) != 1:
            raise ValueError('selected provider feature is duplicated')
        values = []
        for fid in fids[key]:
            row = layer.GetFeature(fid)
            if row is None:
                raise ValueError('selected provider feature is missing')
            geometry = row.GetGeometryRef()
            if geometry is None:
                raise ValueError('source feature has no geometry')
            geometry = geometry.Clone()
            if source_geometries is None and geometry.Transform(conversion) != 0:
                raise ValueError('source geometry coordinate conversion failed')
            options = ['SIGNIFICANT_FIGURES=17'] if source.GetDriver().GetName() == 'GeoJSON' else []
            value = (source_geometries[key] if source_geometries is not None
                     else json.loads(geometry.ExportToJson(options=options)))
            validate_geometry(value)
            values.append(value)
        if selection.get('collection'):
            from shapely.geometry import mapping, shape
            from shapely import union_all
            value = json.loads(json.dumps(mapping(union_all([shape(v) for v in values]))))
            validate_geometry(value)
        else:
            value = values[0]
        result.append({'feature_id': selection['feature_id'], 'source_feature_id': key,
                       'geometry': value})
    return result
