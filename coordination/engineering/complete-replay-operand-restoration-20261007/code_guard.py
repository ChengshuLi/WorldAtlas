"""Actual project callable authentication before acquisition adapters.

callable_guard is the literal accepted issue1376 function with its original
whole source provenance retained. Cooperative provenance, not a sandbox.
"""
import hashlib
import ast
import json
import pathlib
import struct
import types

def callable_guard(module, raw, names):
    # Marshal reference/intern tables can differ for byte-identical loaded code.
    # Compare every public execution field and recursively typed constants instead.
    fields = ('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals',
              'co_stacksize','co_flags','co_code','co_consts','co_names','co_varnames',
              'co_filename','co_name','co_qualname','co_firstlineno','co_linetable',
              'co_exceptiontable','co_freevars','co_cellvars')
    def shape(value):
        if isinstance(value,types.CodeType):
            return ['code',[[name,shape(getattr(value,name))] for name in fields]]
        if value is None:return ['none']
        if value is Ellipsis:return ['ellipsis']
        if type(value) is bool:return ['bool',value]
        if type(value) is int:return ['int',str(value)]
        if type(value) is float:return ['float',struct.pack('>d',value).hex()]
        if type(value) is complex:return ['complex',shape(value.real),shape(value.imag)]
        if type(value) is str:return ['str',value]
        if type(value) is bytes:return ['bytes',value.hex()]
        if type(value) is tuple:return ['tuple',[shape(x) for x in value]]
        if type(value) is frozenset:
            return ['frozenset',sorted((shape(x) for x in value),key=lambda x:json.dumps(x,sort_keys=True))]
        raise ValueError('Unsupported immutable callable constant: '+type(value).__name__)
    def fingerprint(code):
        return json.dumps(shape(code),ensure_ascii=True,separators=(',',':')).encode()
    compiled = compile(raw,str(pathlib.Path(module.__file__)), 'exec')
    expected = {}
    def collect(code):
        expected[code.co_qualname] = code
        for value in code.co_consts:
            if isinstance(value,types.CodeType):
                collect(value)
    collect(compiled)
    rows = []
    for name in names:
        value = module
        for part in name.split('.'):
            value = getattr(value,part)
        actual = getattr(value,'__code__',None)
        if actual is None or name not in expected or fingerprint(actual) != fingerprint(expected[name]):
            raise ValueError('Actual in-memory project callable differs: '+module.__name__+'.'+name)
        rows.append({'module':module.__name__,'callable':name,
                     'code_sha256':hashlib.sha256(fingerprint(actual)).hexdigest()})
    return rows


def all_callables(module, raw):
    # Derive required names from frozen source, never from the possibly mutated
    # live inventory. A deleted callable or a builtin replacement must fail.
    names=[]
    proxy=types.ModuleType(module.__name__)
    proxy.__file__=module.__file__
    for node in ast.parse(raw).body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            names.append(node.name)
            setattr(proxy,node.name,getattr(module,node.name,None))
        elif isinstance(node,ast.ClassDef):
            actual=getattr(module,node.name,None)
            if not isinstance(actual,type) or actual.__module__!=module.__name__:
                raise ValueError('Actual declared class differs: '+node.name)
            methods=types.SimpleNamespace()
            setattr(proxy,node.name,methods)
            for member in node.body:
                if not isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    continue
                implementation=vars(actual).get(member.name)
                decorators=[d.id for d in member.decorator_list if isinstance(d,ast.Name)]
                descriptor=next((d for d in decorators if d in ('staticmethod','classmethod','property')),None)
                required={'staticmethod':staticmethod,'classmethod':classmethod,'property':property}.get(descriptor,types.FunctionType)
                if type(implementation) is not required:
                    raise ValueError('Actual declared callable descriptor differs: '+node.name+'.'+member.name)
                if descriptor in ('staticmethod','classmethod'):
                    implementation=implementation.__func__
                elif descriptor=='property':
                    if implementation.fset is not None or implementation.fdel is not None:
                        raise ValueError('Undeclared property mutation binding')
                    implementation=implementation.fget
                setattr(methods,member.name,implementation)
                names.append(node.name+'.'+member.name)
    if len(names)!=len(set(names)):
        raise ValueError('Duplicate declared callable needs explicit binding')
    return callable_guard(proxy,raw,sorted(names))


def modules_guard(modules, code_baseline):
    proof=[]
    for name,module in modules.items():
        path=pathlib.Path(module.__file__)
        relative=str(path.relative_to(pathlib.Path(code_baseline.repo)))
        raw=code_baseline.materialized_bytes(relative)
        proof.extend(all_callables(module,raw))
    reader=modules['reader'];old=modules['producer']
    if reader.old is not old or old.comparison is not modules['comparison'] or old.inputs is not modules['inputs'] or old.immutable is not modules['immutable'] or reader.transport is not modules['transport'] or reader.ComponentContext.component is not modules['transport'].Context.component or modules['trace'].reader is not reader or modules['trace'].kernel is not modules['kernel']:
        raise ValueError('Actual project module/callable cross-binding differs')
    return proof
