"""Import selected source features into existing Neon decision records."""
import time

from atlas_sources.catalog import read_recipe, catalog_source, download_source, check_source
from features.geometry import save_features
from features.vector import read_features


def build_features(database, storage, recipe_id, version, revision, work_dir):
    started = time.monotonic()
    with database.transaction():
        recipe = read_recipe(database, recipe_id, version)
        if not recipe.get('basis') or not recipe.get('selections'):
            raise ValueError('feature construction needs a basis and selections')
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    timing = {}
    path = download_source(storage, source, work_dir, timing=timing)
    method = recipe['method']
    if method == 'selected_vector_features':
        features = read_features(path, recipe)
    elif method == 's130_areas':
        from iho.areas import read_areas
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
