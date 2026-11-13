"""Import selected source features into existing Neon decision records."""
import time

from worldatlas.source_imports.atlas_sources.catalog import read_recipe, catalog_source, download_source, check_source
from worldatlas.source_imports.features.geometry import save_features
from worldatlas.source_imports.features.vector import read_features


def build_features(database, storage, recipe_id, version, revision, work_dir):
    started = time.monotonic()
    with database.transaction():
        recipe = read_recipe(database, recipe_id, version)
        filtered_points = recipe.get('method') == 'selected_table_points' and 'where' in recipe
        if not recipe.get('basis') or not (recipe.get('selections') or filtered_points):
            raise ValueError('feature construction needs a basis and selections')
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    timing = {}
    path = download_source(storage, source, work_dir, timing=timing)
    method = recipe['method']
    if method == 'selected_vector_features':
        features = read_features(path, recipe)
    elif method == 'selected_table_points':
        from worldatlas.source_imports.features.points import read_points
        features = read_points(path, recipe)
    elif method == 'selected_osm_features':
        from worldatlas.source_imports.osm.features import read_features as read_osm_features
        features = read_osm_features(path, recipe)
    elif method == 's130_areas':
        from worldatlas.source_imports.iho.areas import read_areas
        features = read_areas(path, source, recipe)
    else:
        raise ValueError('unsupported feature construction method')
    check_source(path, source)
    for feature in features:
        feature.update(source_id=source['source_id'], source_version=source['version'])
    hashes = save_features(database, revision, features, recipe)
    elapsed = time.monotonic() - started
    return {'revision': revision, 'geometry_sha256': hashes, 'source': str(path),
            'timing': {'download_seconds': timing.get('download_seconds', 0.),
                       'processing_seconds': elapsed - timing.get('download_seconds', 0.)}}
