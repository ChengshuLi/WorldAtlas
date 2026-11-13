"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""

from osm.ways import assemble_archive
from atlas_sources.catalog import read_recipe, catalog_source, download_source
from source_io import save_boundary as save_mainland_boundary


def save_boundary(database, revision, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    provenance = {'basis': recipe['basis']}
    return save_mainland_boundary(database, revision, recipe['boundary_id'], geometry,
                                  provenance, [source],
                                  construction=(recipe['recipe_id'], recipe['recipe_version']))


def build_boundary(database, client, recipe_id, recipe_version, revision,
                   work_dir, expected_geometry_sha256=None):
    """Look up, download, assemble, and save one boundary in the requested revision."""
    with database.transaction():
        if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                            (revision,)).fetchone() is None:
            raise ValueError('destination decision revision does not exist')
        recipe = read_recipe(database, recipe_id, recipe_version)
        fields = {'method', 'source_id', 'source_version', 'boundary_id', 'basis',
                  'recipe_id', 'recipe_version'}
        if (set(recipe) != fields
                or any(not isinstance(value, str) or not value.strip() for value in recipe.values())):
            raise ValueError('invalid OSM construction record')
        if recipe['method'] != 'osm_way_chain':
            raise ValueError('unsupported construction method')
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
    archive = download_source(client, source, work_dir)
    geometry = assemble_archive(archive, source['sha256'], expected_geometry_sha256)
    digest = save_boundary(database, revision, geometry, source, recipe)
    return {'revision': revision, 'boundary_id': recipe['boundary_id'],
            'vertices': len(geometry['coordinates']), 'sha256': digest,
            'archive': str(archive)}
