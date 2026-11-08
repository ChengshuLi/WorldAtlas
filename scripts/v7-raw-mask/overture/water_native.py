"""Compile and bind the pinned GDAL batch helper in the new shard output."""
import ctypes
import hashlib
import os
from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.append(str(_SCRIPTS))
import stage_external
import shutil
import subprocess

import numpy as np
import pyarrow as pa
from osgeo import gdal


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WaterBatch:
    def __init__(self, output, method='hybrid'):
        if method not in ('hybrid','vector','tiled'):raise ValueError('native_method must be hybrid, vector or tiled')
        self.method=method
        source = Path(__file__).with_suffix('.cpp')
        compiler = shutil.which('c++')
        if not compiler:
            raise ValueError('a C++17 compiler is required for native water batches')
        binary = Path(output) / 'water-native.so'
        env = {**os.environ, 'TMPDIR': str(output), 'TMP': str(output), 'TEMP': str(output)}
        stage_external.run([compiler, '-std=c++17', '-O3', '-fPIC', '-shared',
                        str(source), '-o', str(binary), '-ldl', '-pthread'], check=True, env=env)
        self.lib = ctypes.CDLL(str(binary))
        self.lib.water_error.restype = ctypes.c_char_p
        self.lib.water_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.water_batch.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
        self.lib.water_batch.restype = ctypes.c_int64
        # Resolve GDAL through the already loaded Python extension's dependency
        # tree, rather than accidentally loading a different system GDAL.
        library = gdal._gdal.__file__
        if self.lib.water_init(os.fsencode(library), gdal.VersionInfo().encode()):
            raise ValueError('native water initialization failed: ' + self.error())
        self.threads = len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1)
        self.provenance = {'method':method,'validation_threads':self.threads,
            'source_sha256': sha(source), 'binding_sha256': sha(__file__),
            'binary_sha256': sha(binary), 'compiler': stage_external.run(
                [compiler, '--version'], text=True, check=True, stdout=subprocess.PIPE).stdout.splitlines()[0], 'gdal': gdal.VersionInfo()}
        self.timings = {'parse_validate_index_seconds':0.,'tile_burn_seconds':0.}

    def error(self):
        return self.lib.water_error().decode()

    def burn(self, raster, geometry, selected, grid, tile):
        if isinstance(geometry,pa.ExtensionArray) and geometry.type.extension_name in ('geoarrow.wkb','geoarrow.large_wkb'):
            geometry=geometry.storage
        if not (pa.types.is_binary(geometry.type) or pa.types.is_large_binary(geometry.type)):
            raise ValueError('GeoParquet geometry must be a binary WKB array')
        buffers = geometry.buffers()
        pointer = lambda b: b.address if b is not None else None
        status = np.zeros(len(geometry), dtype=np.uint8)
        selected = np.ascontiguousarray(selected, dtype=np.uint8)
        grid = np.asarray(grid, dtype=np.float64)
        timings = np.zeros(2,dtype=np.float64)
        result = self.lib.water_batch(int(raster.this), pointer(buffers[2]), pointer(buffers[1]),
            int(pa.types.is_large_binary(geometry.type)), geometry.offset, pointer(buffers[0]),
            selected.ctypes.data, len(geometry), grid.ctypes.data, tile, {'tiled':0,'vector':1,'hybrid':2}[self.method],self.threads,
            status.ctypes.data,timings.ctypes.data)
        if result < 0:
            raise ValueError('native water batch failed: ' + self.error())
        for key,value in zip(self.timings,timings):self.timings[key]+=float(value)
        return status, result - 1 if result else None
