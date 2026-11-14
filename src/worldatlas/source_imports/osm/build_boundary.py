"""Build an editable Neon boundary from an OSM way archive cataloged in Neon."""

from worldatlas.source_imports.contracts import NonEmptyText, Runtime
from worldatlas.source_imports.osm.ways import assemble_archive
from worldatlas.source_imports.atlas_sources.catalog import (
    catalog_source,
    download_source,
)
from worldatlas.source_imports.source_io import save_boundary as save_mainland_boundary


def save_boundary(database, geometry, source, recipe):
    """Save geometry and its construction source together, retaining other evidence."""
    provenance = {"basis": recipe["basis"]}
    return save_mainland_boundary(
        database,
        recipe["boundary_id"],
        geometry,
        provenance,
        [source],
        construction=recipe["recipe_id"],
    )


def osm_way_chain(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    boundary_id: NonEmptyText,
    basis: NonEmptyText,
):
    """Join archived OSM border segments at shared node IDs, preserving coordinates."""
    recipe = runtime.recipe(locals())
    with runtime.connect() as database:
        with database.transaction():
            source = catalog_source(database, source_id)
        archive = download_source(runtime.storage, source, runtime.work_dir)
        geometry = assemble_archive(
            archive, source["sha256"], runtime.expected_geometry_sha256
        )
        with runtime.saving(database):
            digest = save_boundary(database, geometry, source, recipe)
    return {
        "boundary_id": boundary_id,
        "vertices": len(geometry["coordinates"]),
        "sha256": digest,
        "archive": str(archive),
    }
