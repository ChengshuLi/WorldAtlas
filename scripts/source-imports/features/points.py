"""Import selected points from a delimited provider table."""
from contextlib import ExitStack
import csv
import io
from pathlib import Path
from zipfile import ZipFile

from features.geometry import geometry_hash, validate_geometry


def read_points(path, settings):
    """Read provider IDs once; column names and identity checks come from Neon.

    ``columns`` supplies field names for a headerless table. Otherwise the first
    row names the fields. An archive requires an explicit member selection.
    """
    selections = settings['selections']
    wanted = {str(item['source_feature_id']): item for item in selections}
    if not wanted or len(wanted) != len(selections):
        raise ValueError('provider point selections must be unique')
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
        for row in reader:
            key = row[fields[0]]
            if key not in wanted:
                continue
            if key in results:
                raise ValueError('selected provider point is duplicated')
            if None in row or any(value is None for value in row.values()):
                raise ValueError('selected point record has a different number of columns')
            selected = wanted[key]
            if any(row.get(name) != value for name, value in selected.get('expected_properties', {}).items()):
                raise ValueError('source point identity properties do not match')
            try:
                geometry = {'type': 'Point', 'coordinates': [float(row[fields[1]]), float(row[fields[2]])]}
            except ValueError:
                raise ValueError('selected point has invalid coordinates') from None
            validate_geometry(geometry)
            expected = selected.get('expected_geometry_sha256')
            if expected and geometry_hash(geometry) != expected:
                raise ValueError('selected point geometry checksum differs')
            results[key] = {'feature_id': selected['feature_id'], 'source_feature_id': key,
                            'geometry': geometry, 'evidence': {'provider_properties': row,
                            'source_coordinate_reference': settings['coordinate_reference']}}
    if results.keys() != wanted.keys():
        raise ValueError('selected provider point is missing')
    return [results[key] for key in wanted]
