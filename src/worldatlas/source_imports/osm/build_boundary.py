"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""

from worldatlas.source_imports.contracts import NonEmptyText, Runtime
from worldatlas.source_imports.osm.ways import assemble_archive
from worldatlas.source_imports.atlas_sources.catalog import catalog_source, download_source
from worldatlas.source_imports.source_io import save_boundary as save_mainland_boundary


def save_boundary(database, revision, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    provenance = {'basis': recipe['basis']}
    return save_mainland_boundary(database, revision, recipe['boundary_id'], geometry,
                                  provenance, [source],
                                  construction=(recipe['recipe_id'], recipe['recipe_version']))


def osm_way_chain(runtime: Runtime, *, source_id: NonEmptyText, source_version: NonEmptyText,
                  boundary_id: NonEmptyText, basis: NonEmptyText):
    """Join archived OSM border segments at shared node IDs, preserving coordinates."""
    recipe = runtime.recipe(locals())
    with runtime.connect() as database:
        with database.transaction():
            if database.execute('SELECT 1 FROM atlas.decision_revisions WHERE revision=%s',
                                (runtime.revision,)).fetchone() is None:
                raise ValueError('destination decision revision does not exist')
            source = catalog_source(database, source_id, source_version)
        archive = download_source(runtime.storage, source, runtime.work_dir)
        geometry = assemble_archive(archive, source['sha256'], runtime.expected_geometry_sha256)
        digest = save_boundary(database, runtime.revision, geometry, source, recipe)
    return {'revision': runtime.revision, 'boundary_id': boundary_id,
            'vertices': len(geometry['coordinates']), 'sha256': digest, 'archive': str(archive)}
