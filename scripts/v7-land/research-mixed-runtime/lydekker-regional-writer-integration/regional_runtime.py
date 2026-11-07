"""Explicit, run-scoped accelerators for the unchanged reviewed regional rule."""
from types import FunctionType


def bind(function, **dependencies):
    """Bind equivalent query functions without altering reviewed module state."""
    result = FunctionType(function.__code__, {**function.__globals__, **dependencies},
                          function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def prepare(modules, inputs, grid, code):
    index = modules['component_index'].ComponentIndex(inputs['component_rows'], inputs['component_runs'], grid)
    workflow = modules['regional_workflow']
    scan, collect, point = index.scan, index.collect_runs, index.component_at
    satellite = modules['satellite_index'].apply_satellites
    boo = bind(workflow.require_boo_east, component_at=point)
    research = bind(workflow.research, scan=scan, collect_runs=collect,
                    component_at=point, require_boo_east=boo, apply_satellites=satellite)
    return {'dependencies': {'research': research, 'scan': scan, 'collect_runs': collect,
                             'component_at': point, 'apply_satellites': satellite},
            'verify': index.verify,
            'provenance': {'schema': 'regional-equivalent-runtime-v1', 'code': code,
                           'numpy_version': modules['component_index'].np.__version__,
                           'substitutions': {'component_scan': 'authenticated-vectorized-run-index',
                                             'satellite_geodesic': 'conservative-row-interval-index'},
                           'geographic_policy_changed': False,
                           'wgs84_solver_changed': False}}
