"""Import selected points from a delimited provider table."""
from contextlib import ExitStack
import csv
import io
import math
from pathlib import Path
from zipfile import ZipFile

from worldatlas.source_imports.features.geometry import geometry_hash, validate_geometry


def read_points(path, settings):
    """Read provider IDs once; column names and identity checks come from Neon.

    ``columns`` supplies field names for a headerless table. Otherwise the first
    row names the fields. An archive requires an explicit member selection.
    ``where`` selects additional records by exact property matches, optionally
    limited by ``bounds_lon_lat``. Explicit selections are always retained.
    """
    selections = settings.get('selections', [])
    wanted = {str(item['source_feature_id']): item for item in selections}
    where = settings.get('where')
    if (not wanted and where is None) or len(wanted) != len(selections):
        raise ValueError('provider point selections must be unique')
    if where is not None and (not isinstance(where, dict)
            or any(not isinstance(k, str) or not k or not isinstance(v, str) for k, v in where.items())
            or not isinstance(settings.get('feature_id_prefix'), str) or not settings['feature_id_prefix']):
        raise ValueError('filtered point imports need property matches and an output ID prefix')
    bounds = settings.get('bounds_lon_lat')
    if bounds is not None and (len(bounds) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
            or not -180 <= bounds[0] < bounds[2] <= 180 or not -90 <= bounds[1] < bounds[3] <= 90):
        raise ValueError('invalid point selection bounds')
    columns = settings.get('columns')
    if columns is not None and (not columns or len(columns) != len(set(columns))
                                or any(not isinstance(c, str) or not c for c in columns)):
        raise ValueError('table columns must have unique names')
    if settings.get('coordinate_reference') != 'OGC:CRS84':
        raise ValueError('point table must declare WGS84 longitude/latitude coordinates')
    fields = [settings[name] for name in ('id_field', 'longitude_field', 'latitude_field')]
    results = {}
    path = Path(path)
    with ExitStack() as resources:
        member = settings.get('member')
        if path.suffix.lower() == '.zip':
            archive = resources.enter_context(ZipFile(path))
            if not member or archive.namelist().count(member) != 1:
                raise ValueError('select one existing, unique table archive member')
            raw = resources.enter_context(archive.open(member))
            stream = resources.enter_context(io.TextIOWrapper(raw, encoding=settings.get('encoding', 'utf-8')))
        else:
            if member is not None:
                raise ValueError('archive member supplied for a non-archive source')
            stream = resources.enter_context(path.open(encoding=settings.get('encoding', 'utf-8'), newline=''))
        reader = csv.DictReader(stream, fieldnames=columns, delimiter=settings.get('delimiter', ','))
        names = reader.fieldnames
        if (not names or len(names) != len(set(names)) or not set(fields) <= set(names)):
            raise ValueError('point table is missing required unique columns')
        if where is not None and not set(where) <= set(names):
            raise ValueError('point table is missing selected filter columns')
        for row in reader:
            key = row[fields[0]]
            explicit = key in wanted
            if not explicit and (where is None or any(row.get(k) != v for k, v in where.items())):
                continue
            if None in row or any(value is None for value in row.values()):
                raise ValueError('selected point record has a different number of columns')
            if not key:
                raise ValueError('selected point needs a provider ID')
            selected = wanted[key] if explicit else dict(
                feature_id=settings['feature_id_prefix'] + key, source_feature_id=key)
            if any(row.get(name) != value for name, value in selected.get('expected_properties', {}).items()):
                raise ValueError('source point identity properties do not match')
            try:
                geometry = {'type': 'Point', 'coordinates': [float(row[fields[1]]), float(row[fields[2]])]}
            except (TypeError, ValueError):
                raise ValueError('selected point has invalid coordinates') from None
            validate_geometry(geometry)
            longitude, latitude = geometry['coordinates']
            if (not explicit and bounds is not None
                    and not (bounds[0] <= longitude <= bounds[2] and bounds[1] <= latitude <= bounds[3])):
                continue
            if key in results:
                raise ValueError('selected provider point is duplicated')
            expected = selected.get('expected_geometry_sha256')
            if expected and geometry_hash(geometry) != expected:
                raise ValueError('selected point geometry checksum differs')
            results[key] = {'feature_id': selected['feature_id'], 'source_feature_id': key,
                            'geometry': geometry, 'coordinate_reference': settings['coordinate_reference']}
    if wanted.keys() - results.keys():
        raise ValueError('selected provider point is missing')
    return [results[key] for key in [*wanted, *sorted(results.keys() - wanted.keys())]]
