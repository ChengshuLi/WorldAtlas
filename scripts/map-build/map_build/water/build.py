"""Calculate water assignments from one saved selection and final land grid."""
from contextlib import ExitStack
import json
import logging
from pathlib import Path
import time

from map_build.core.grid import Grid
from map_build.core.layers import file_hash, patch_rows, write_layer
from map_build.core.rle import open_grid
from map_build.inputs.features import selected_basins
from map_build.inputs.selection import canonical_bytes, read_saved
from map_build.water.basins import Shorelines, build_basin
from map_build.water.coastal import build_coastal
from map_build.water.coastal_core import policy
from map_build.water.composition import compose
from map_build.water.remaining import build_remaining, water_snapshot


def build_water(selection, grid, physical_directory, land_directory, directory):
    """Run coastal, basin, ocean and enclosed-water calculations directly.

    The output directory must be new. The main pipeline owns checkpoint reuse;
    this calculation never queries Neon or changes the published release.
    """
    snapshot = water_snapshot(selection)
    coastal_policy, pairs, tolerance, _, _ = policy(snapshot)
    domain = selection['domains']['water']
    basins = selected_basins(domain)
    order = [p['definition']['order'] for p in domain['policies']
             if p['kind'] == 'layer_precedence']
    if order != [['coastal', 'named_basins', 'ocean', 'enclosed_water']]:
        raise ValueError('expected coastal, basin, ocean and enclosed-water precedence')
    for basin, _ in basins:
        if (basin['assignment_method'] != 'nearest_participating_shore'
                or basin['tie_rules'] != {'policy_id': coastal_policy['id']}):
            raise ValueError('basin must use the selected nearest-shore policy')
    directory = Path(directory)
    physical_directory, land_directory = map(Path, (physical_directory, land_directory))
    directory.mkdir()
    (directory / 'input-selection.json').write_bytes(canonical_bytes(selection))
    inputs = {kind: {name: file_hash(root / name) for name in ('rows.u32le', 'runs.u32le')}
              for kind, root in [('physical', physical_directory), ('land', land_directory)]}
    timings, basin_reports = {}, []
    started = time.monotonic()
    land_codes = {p[1] for p in pairs}
    water_codes = {b['code'] for b in snapshot['category_bindings'] if b['physical_class'] == 'water'}
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        land = resources.enter_context(open_grid(land_directory, grid))
        start = time.monotonic()
        shores = Shorelines(physical, land, grid, pairs)
        timings['shore_index_seconds'] = time.monotonic() - start
        coast_report = build_coastal(snapshot, grid, physical, shores, directory / 'coastal')
        timings['coastal_seconds'] = coast_report['processing_seconds']
        coast = resources.enter_context(open_grid(directory / 'coastal', grid))
        layers = []
        start = time.monotonic()
        for number, (basin, feature) in enumerate(basins):
            basin_started = time.monotonic()
            result = build_basin(feature['geometry'], grid, physical, land, shores,
                                 tolerance, coastal=coast)
            target = directory / f'basin-{number:03d}'
            report = write_layer(target, grid, patch_rows(result.assignments, result.bounds, grid))
            report.update(basin_id=basin['id'], feature_id=feature['feature_id'],
                          participant_shore_edges=result.participant_shore_edges,
                          physical_water_cells=int(result.water.sum()),
                          processing_seconds=time.monotonic() - basin_started)
            (target / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            basin_reports.append(report)
            layers.append(resources.enter_context(open_grid(target, grid)))
            logging.getLogger(__name__).info('Basins completed: %s/%s', number + 1, len(basins))
        timings['basins_seconds'] = time.monotonic() - start
        start = time.monotonic()
        compose(physical, land, [[coast], layers], grid, directory / 'prefill', land_codes, water_codes)
        timings['prefill_seconds'] = time.monotonic() - start
    start = time.monotonic()
    result = build_remaining(snapshot, grid, physical_directory, land_directory,
                             directory / 'prefill', directory / 'remaining', shores=shores)
    timings['remaining_seconds'] = time.monotonic() - start
    # Per-basin and residual timings are details of their parent phases, not
    # additional time to add to this measured parent total.
    report = {'final': result['final'], 'counts': result['counts'], 'inputs': inputs,
              'basins': basin_reports, 'timings': timings,
              'remaining_timings': result['timings'],
              'processing_seconds': time.monotonic() - started,
              'download_seconds': 0.0}
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--physical', type=Path, required=True)
    parser.add_argument('--land', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    grid = Grid(**json.loads((args.physical / 'report.json').read_text())['grid'])
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    report = build_water(read_saved(args.selection), grid, args.physical, args.land, args.output)
    print(json.dumps({'final': report['final'], 'processing_seconds': report['processing_seconds']}))


if __name__ == '__main__':
    main()
