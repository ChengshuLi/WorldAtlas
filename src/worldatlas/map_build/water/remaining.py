"""Fill ocean and enclosed water after coastal and named-basin assignment."""
from worldatlas.map_build.inputs.selection import geographic_domain, selection_domains


from contextlib import ExitStack
import hashlib
from pathlib import Path
import time

from worldatlas.map_build.core.layers import file_hash, layer_rows, write_layer
from worldatlas.map_build.core.rle import open_grid
from worldatlas.map_build.inputs.selection import canonical_bytes, validate_bindings
from worldatlas.map_build.water.composition import compose
from worldatlas.map_build.water.ocean import engine as ocean
from worldatlas.map_build.water import streaming_closed_water as enclosed


def water_snapshot(selection):
    validate_bindings(selection_domains(selection))
    water, oceans = (geographic_domain(selection, name) for name in ('water', 'ocean'))
    return {
        'source': 'saved-selection',
        'category_bindings': water['category_bindings'],
        'endpoints': oceans['endpoints'],
        'routes': oceans['routes'],
        'ocean_seeds': oceans['ocean_seeds'],
        'policies': [p for p in water['policies'] if p['kind'] != 'ocean_fill']
        + [p for p in oceans['policies'] if p['kind'] == 'ocean_fill'],
    }


def build_remaining(
    snapshot, grid, physical_directory, land_directory, prefill_directory, directory, *, shores=None
):
    """Calculate and compose residual water; return paths, counts and timings."""
    directory = Path(directory)
    directory.mkdir()
    physical_directory, land_directory, prefill_directory = map(
        Path, (physical_directory, land_directory, prefill_directory)
    )
    digest = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
    (directory / 'water-selection.json').write_bytes(canonical_bytes(snapshot))
    inputs = {
        kind + '_' + stream + '_sha256': file_hash(root / (stream + '.u32le'))
        for kind, root in (('physical', physical_directory), ('prefill', prefill_directory))
        for stream in ('rows', 'runs')
    }
    inputs['prefill_audit_sha256'] = file_hash(prefill_directory / 'report.json')
    timings = {}
    start = time.monotonic()
    ocean_directory = directory / 'ocean'
    ocean.run(
        snapshot,
        digest,
        physical_directory / 'rows.u32le',
        physical_directory / 'runs.u32le',
        prefill_directory / 'rows.u32le',
        prefill_directory / 'runs.u32le',
        ocean_directory,
        grid.width,
        grid.height,
        inputs,
    )
    timings['ocean_seconds'] = time.monotonic() - start
    inputs['source_cut_edges_sha256'] = file_hash(ocean_directory / 'barrier_edges.u32le')
    land_codes = {b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'}
    water_codes = {
        b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'water'
    }
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        land = resources.enter_context(open_grid(land_directory, grid))
        prefill = resources.enter_context(open_grid(prefill_directory, grid))
        start = time.monotonic()
        closed = enclosed.run(
            snapshot,
            digest,
            physical,
            prefill,
            land,
            ocean_directory / 'partition/manifest.json',
            ocean_directory / 'partition/unseeded_rows.u64le',
            ocean_directory / 'partition/unseeded_component_spans.u32le',
            ocean_directory / 'barrier_edges.u32le',
            directory / 'enclosed',
            grid.width,
            grid.height,
            8.0,
            inputs,
            shores=shores,
        )
        timings['enclosed_seconds'] = time.monotonic() - start
        if closed['pending_cells']:
            raise ValueError(
                f"{closed['pending_cells']} enclosed-water cells need geographic evidence"
            )
        residual = []
        for name, manifest in [
            ('ocean-layer', ocean_directory / 'ocean-layer-manifest.json'),
            ('enclosed-layer', directory / 'enclosed/manifest.json'),
        ]:
            start = time.monotonic()
            path = directory / name
            write_layer(path, grid, layer_rows(manifest, grid, water_codes))
            residual.append(resources.enter_context(open_grid(path, grid)))
            timings[name + '_conversion_seconds'] = time.monotonic() - start
        start = time.monotonic()
        # Prefill already contains physical land; compose consumes only its
        # water assignments as a water layer, keeping land separately.
        result = compose(
            physical,
            land,
            [residual],
            grid,
            directory / 'final',
            land_codes,
            water_codes,
            complete=True,
            prefill=prefill,
        )
        timings['composition_seconds'] = time.monotonic() - start
    return {'final': str(directory / 'final'), 'counts': result['counts'], 'timings': timings}
