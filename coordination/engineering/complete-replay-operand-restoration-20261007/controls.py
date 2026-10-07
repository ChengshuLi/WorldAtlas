"""Small actual counterexamples, executed before complete-source restoration."""
import copy
import types
from shapely.geometry import Polygon, mapping


def run(guard, objects, source):
    checks = []

    def rejected(name, operation):
        try:
            operation()
        except (ValueError, KeyError, AttributeError, TypeError):
            checks.append({'control': name, 'rejected': True})
            return
        raise ValueError('Negative control accepted: ' + name)

    raw = b'def f(x):\n return x\nclass C:\n @staticmethod\n def s(x):\n  return x\n @classmethod\n def c(cls,x):\n  return x\n @property\n def p(self):\n  return 1\n'
    module = types.ModuleType('required_roster_control')
    module.__file__ = '/immutable/required-roster.py'
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    guard.all_callables(module, raw)
    original = module.f
    module.f = len
    rejected('builtin replacement cannot escape required roster', lambda: guard.all_callables(module, raw))
    del module.f
    rejected('deleted function cannot escape required roster', lambda: guard.all_callables(module, raw))
    module.f = original
    original_static = vars(module.C)['s']
    module.C.s = staticmethod(len)
    rejected('static method substitution', lambda: guard.all_callables(module, raw))
    module.C.s = original_static
    module.C.s = original_static.__func__
    rejected('static descriptor removed with same code', lambda: guard.all_callables(module, raw))
    module.C.s = original_static
    original_class = vars(module.C)['c']
    module.C.c = classmethod(lambda cls, x: x)
    rejected('class method substitution', lambda: guard.all_callables(module, raw))
    module.C.c = original_class
    original_property = vars(module.C)['p']
    module.C.p = original_property.fget
    rejected('property descriptor removed with same code', lambda: guard.all_callables(module, raw))
    module.C.p = original_property.setter(lambda self, value: None)
    rejected('undeclared property setter', lambda: guard.all_callables(module, raw))
    module.C.p = original_property
    guard.all_callables(module, raw)
    checks.append({'control': 'genuine complete callable roster restored', 'passed': True})

    class Products:
        def __init__(self):
            self.rows = []
            self.buffers = {}
            self.ordinals = {}
        def emit(self, name, value):
            self.rows.append((name, value))
            self.buffers.setdefault(name, bytearray()).extend(source.canonical(value))
            self.ordinals.setdefault(name, 0)

    # Tiny physical objects exercise exact original/periodic aliases and changed
    # output bodies. They do not claim to validate any geographic source.
    geometry = Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])
    value = mapping(geometry)
    value = __import__('json').loads(source.canonical(value))
    identity = 'tiny-complete-component'
    candidate = {'geometry': value}
    row = {'query_relations': [{'source_id': 7, 'periodic_offset': 0},
                               {'source_id': 7, 'periodic_offset': 360}], 'geometry': value}
    pin = {'whole_row_sha256': source.sha(source.canonical(row)), 'ordinal': 0}
    loaded = {'modules': {'kernel': types.SimpleNamespace(ordinary_mapping=lambda g:
                   __import__('json').loads(source.canonical(mapping(g))))},
              'state': {'candidates': {identity: candidate}, 'routing': {identity:
                   {'current_feature_sha256': source.sha(source.canonical(candidate))}}},
              'physical': {identity: (row, pin)}, 'diagnoses': {identity: {'geometry': value}}}
    products = Products()
    instance = objects.Objects(products, loaded, {7: ({'source_id': 7}, geometry)},
                               {7: {'record_ordinal': 2, 'source_id': 7}})
    instance.begin(identity)
    alias = instance.alias('candidate', identity, ['geometry'], value)
    if source.canonical(instance.resolve_alias(alias)) != source.canonical(value):
        raise ValueError('Genuine complete alias did not reconstruct')
    bad = copy.deepcopy(alias); bad['selector'] = ['missing']
    rejected('wrong original-object selector', lambda: instance.resolve_alias(bad))
    bad = copy.deepcopy(alias); bad['complete_candidate_feature_sha256'] = '0' * 64
    rejected('wrong containing feature binding', lambda: instance.resolve_alias(bad))
    bad = copy.deepcopy(alias); bad['whole_object_sha256'] = '0' * 64
    rejected('wrong reconstructed body hash', lambda: instance.resolve_alias(bad))
    native = next(a for rows in instance.native.values() for a in rows
                  if a['periodic_offset'] == 360)
    instance.verify_alias(native, source.canonical(instance.resolve_alias(native)))
    bad = copy.deepcopy(native); bad['original_native_record']['record_ordinal'] = 3
    rejected('wrong original native record binding', lambda: instance.resolve_alias(bad))
    bad = copy.deepcopy(native); bad['periodic_offset'] = True
    rejected('boolean periodic frame', lambda: instance.resolve_alias(bad))
    original_body = source.canonical(value)
    retained = instance.retain(value)
    if 'complete_inverse_alias' not in retained or products.rows:
        raise ValueError('Equal original did not retain an executed inverse alias')
    changed = copy.deepcopy(value); changed['coordinates'][0][1][0] = 2
    retained = instance.retain(changed)
    if 'complete_ordinary_geometry_sha256' not in retained or len(products.rows) != 1 or \
            source.canonical(products.rows[0][1]['geometry']) != source.canonical(changed):
        raise ValueError('Changed geometry body was omitted')
    rejected('cached inverse alias cannot accept changed body',
             lambda: instance.verify_alias(alias, source.canonical(changed)))
    if source.canonical(value) != original_body:
        raise ValueError('Control altered original geometry')
    checks.append({'control': 'original and periodic aliases reconstructed; changed map body retained', 'passed': True})
    return checks
