"""Directed actual manual-object/runtime controls; no source/GIS invocation."""
import json
from pathlib import Path
import sys
import runtime

module, objects = runtime.load_original()
expected = runtime.snapshot(objects)
results = []
runtime.authenticate(objects, expected)
results.append({'case': 'actual ordinary manual imports', 'status': 'PASS'})

def rejects(name, mutate, restore):
    mutate()
    try:
        try:
            runtime.authenticate(objects, expected)
        except ValueError as error:
            results.append({'case': name, 'status': 'PASS', 'actual_rejection': str(error)})
        else:
            raise AssertionError('Drift accepted: ' + name)
    finally:
        restore()
    runtime.authenticate(objects, expected)

old_sha = module.sha
rejects('actual consumed sha callable replacement',
        lambda: setattr(module, 'sha', lambda path: '0' * 64),
        lambda: setattr(module, 'sha', old_sha))
old_proof = module.source_proof
rejects('actual source_proof callable replacement',
        lambda: setattr(module, 'source_proof', lambda index, sources: {}),
        lambda: setattr(module, 'source_proof', old_proof))
old_file = module.OWN.__file__
rejects('actual manual OWN object source redirection',
        lambda: setattr(module.OWN, '__file__', module.TOPO.__file__),
        lambda: setattr(module.OWN, '__file__', old_file))
import numpy
old_version = numpy.__version__
rejects('actual imported package version mutation',
        lambda: setattr(numpy, '__version__', '0.0.0'),
        lambda: setattr(numpy, '__version__', old_version))
old_executable = sys.executable
rejects('actual executable path mutation',
        lambda: setattr(sys, 'executable', '/bin/sh'),
        lambda: setattr(sys, 'executable', old_executable))
old_constructor=module.zipfile.ZipFile.__init__
rejects('actual ZIP constructor replacement',
        lambda:setattr(module.zipfile.ZipFile,'__init__',lambda *args,**kwargs:None),
        lambda:setattr(module.zipfile.ZipFile,'__init__',old_constructor))
old_reader=module.zipfile.ZipExtFile.read
rejects('actual ZIP native reader replacement',
        lambda:setattr(module.zipfile.ZipExtFile,'read',lambda *args,**kwargs:b''),
        lambda:setattr(module.zipfile.ZipExtFile,'read',old_reader))
print(json.dumps({'status': 'PASS', 'controls': results,
                  'source_proof_invoked': False, 'native_or_GIS_calculations': False}, sort_keys=True))
