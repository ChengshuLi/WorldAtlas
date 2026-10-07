"""Actual literal GIS operators and in-memory category/runtime guards."""
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
CUSTODY=HERE.parent/'reference-source-custody-20261007'


def original_guard(expected_body=None):
    if expected_body is not None:
        import reader
        path=CUSTODY/'runtime.py'
        if reader.bounded(path,len(expected_body))!=expected_body:
            raise ValueError('Actual loaded original runtime body drift')
    spec=importlib.util.spec_from_file_location('literal_native_runtime_guard',CUSTODY/'runtime.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj


def snapshot(guard, objects):
    result=guard.snapshot(objects)
    reference=objects['reference'];topo=objects['TOPO'];veg=objects['VEG']
    import numpy as np
    import rasterio
    import shapely
    import math
    operators={'reference.summarize_changed':reference.summarize_changed,
        'reference.climate_summary':reference.climate_summary,
        'reference.canonical':reference.canonical,'reference.shape':reference.shape,
        'reference.make_valid':reference.make_valid,'reference.prepare':reference.prepare_geometries,
        'reference.STRtree':reference.STRtree,'reference.mapping':reference.mapping,
        'reference.RasterGrid.__init__':reference.RasterGrid.__init__,
        'reference.RasterGrid.__getitem__':reference.RasterGrid.__getitem__,
        'reference.rasterio.open':reference.rasterio.open,
        'reference.geometry_mask':reference.geometry_mask,
        'reference.from_bounds':reference.from_bounds,'reference.Window':reference.Window,
        'reference.VEG.chosen_summary':reference.VEG.chosen_summary,
        'reference.TOPO.summarize':reference.TOPO.summarize,
        'reference.ast.parse':reference.ast.parse,'reference.ast.literal_eval':reference.ast.literal_eval,
        'topo.geometry_mask':topo.geometry_mask,'topo.from_bounds':topo.from_bounds,
        'topo.mapping':topo.mapping,'vegetation.chosen_summary':veg.chosen_summary}
    for name in ['zeros','arange','cos','deg2rad','bincount','argmax','broadcast_to']:
        operators['numpy.'+name]=getattr(np,name)
    for name in ['floor','ceil']:
        operators['math.'+name]=getattr(math,name)
    result['actual_scientific_operators']={k:guard.callable_pin(v) for k,v in sorted(operators.items())}
    result['actual_scientific_constants']={'TOPO.CLASSES':list(topo.CLASSES)}
    return result


def authenticate(guard,objects,expected):
    actual=snapshot(guard,objects)
    if actual!=expected:
        raise ValueError('Actual scientific import/operator/category/runtime drift')
    return actual


def warm(guard, objects):
    """Tiny directed native windows, not either complete target calculation."""
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    from shapely.geometry import box
    reference=objects['reference'];step=1/120
    transform=from_origin(0,1,step,step)
    g=box(step/4,1-step*1.75,step*1.75,1-step/4)
    with MemoryFile() as memory:
        with memory.open(driver='GTiff',height=2,width=2,count=1,dtype='uint8',crs='EPSG:4326',transform=transform) as raster:
            raster.write(np.full((2,2),2,dtype='uint8'),1)
            climate,reason=reference.climate_summary(g,raster)
            terrain,reason2,coverage=objects['TOPO'].summarize(g,reference.RasterGrid(raster),transform)
            if climate is None or climate[0]!=2 or reason is not None or terrain is None or terrain[0]!=2 or reason2 is not None:
                raise ValueError('Actual literal native window positive failed')
    eco=[{'properties':{'BIOME_NAME':'directed fixture','ECO_ID':'directed fixture'}}]
    result,proof=objects['VEG'].chosen_summary(g,[0],[g],eco)
    if result is None or result['value']!='directed fixture':
        raise ValueError('Actual literal ellipsoidal vegetation positive failed')
    return {'scope':'tiny explicit 2x2 native window plus one complete synthetic vegetation polygon',
            'literal_climate':climate,'literal_terrain':terrain,'literal_vegetation':result,
            'no_complete_source_or_target_calculation':True}
