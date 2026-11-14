"""Build the coastal band using the shared complete shoreline index."""

from pathlib import Path
import json
import logging
import time

import numpy as np

from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.water import coastal_core, coastal_rect, shared_nearest


def build_coastal(snapshot, grid, physical, shores, directory, *, rows_per_batch=128):
    """Assign native physical water within the selected nearest-shore band.

    The caller can reuse ``shores`` for named basins. Row batches process the
    complete grid; distances always search the complete supplied shore index.
    """
    if type(rows_per_batch) is not int or rows_per_batch <= 0:
        raise ValueError('row batch must be a positive integer')
    decision, pairs, tolerance, band, bandtol = coastal_core.policy(snapshot)
    if shores.grid != grid or shores.pairs != pairs:
        raise ValueError('coastal policy and shoreline index use different grids or bindings')
    start = time.monotonic()
    totals = {'physical_water_cells': 0, 'bounded_cells': 0, 'exact_cells': 0}

    def rows():
        for first in range(0, grid.height, rows_per_batch):
            last = min(first + rows_per_batch, grid.height)
            water = np.stack(
                [
                    shared_nearest.crop(*physical, y, 0, grid.width, grid.width) == 1
                    for y in range(first, last)
                ]
            )
            assignments, stats = coastal_rect.classify(
                water,
                0,
                first,
                grid.bounds,
                grid.width,
                grid.height,
                grid.step,
                pairs,
                tolerance,
                band,
                bandtol,
                shores.indexes,
            )
            totals['physical_water_cells'] += int(water.sum())
            totals['bounded_cells'] += stats['bounded']
            totals['exact_cells'] += stats['exact']
            yield from patch_rows(assignments, (0, grid.width, first, last), grid)
            logging.getLogger(__name__).info('Coastal rows completed: %s/%s', last, grid.height)

    directory = Path(directory)
    report = write_layer(directory, grid, rows())
    if totals['bounded_cells'] + totals['exact_cells'] != totals['physical_water_cells']:
        raise ValueError('coastal classification counts do not cover physical water')
    report.update(
        policy_id=decision['id'],
        policy_definition=decision['definition'],
        processing_seconds=time.monotonic() - start,
        **totals
    )
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
