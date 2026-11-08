"""Public-Python WGS84 search wiring, independent of build/publication drivers."""
from certificate import CertificateIndex
from exact_index import ExactIndex

CODE_NAMES=('land_runtime.py','contracts.py','baseline_runner.py','certificate.py','checkpoints.py',
    'engine.py','exact_index.py','point_prototype.py','preflight.py','run_pair.py',
    'verify_inputs.py','write_land_stream.py','ural_delta.py')


def search_indexes(directory, grid, tiles, representatives, controls):
    """Refine only still-possible categories, using public SciPy/PyProj APIs."""
    width,height=grid['width'],grid['height'];step,north=grid['step'],grid['north']
    guard=controls['numerical_guard_metres']
    exact=ExactIndex(directory,width,height,step,north,tiles,tile_cells=1024,guard_m=guard)
    fine=CertificateIndex(width,height,step,north,exact.certificate_tiles,representatives[:,2:5],
        tile_cells=exact.leaf_cells,numerical_guard_m=guard)
    coarse=CertificateIndex(width,height,step,north,
        [(ty,tx,codes) for ty,tx,codes,count,sha in tiles],representatives[:,2:5],
        tile_cells=1024,numerical_guard_m=guard,refinement=fine)
    return coarse,exact
