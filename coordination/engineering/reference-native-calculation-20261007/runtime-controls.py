"""Actual scientific callable/category mutation negatives, without target GIS."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def run():
    spec=importlib.util.spec_from_file_location('native_runtime_controls',HERE/'runtime.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    guard=runtime.original_guard();reference,objects=guard.load_original()
    positive=runtime.warm(guard,objects);expected=runtime.snapshot(guard,objects)
    runtime.authenticate(guard,objects,expected);passed=['actual tiny native/ellipsoidal positive','unchanged complete actual runtime positive']
    def mutation(label,obj,name,value):
        old=getattr(obj,name);setattr(obj,name,value)
        try:
            try:runtime.authenticate(guard,objects,expected)
            except ValueError:passed.append(label)
            else:raise AssertionError('Actual runtime mutation did not reject: '+label)
        finally:setattr(obj,name,old)
        runtime.authenticate(guard,objects,expected)
    mutation('actual summarize_changed mutation',reference,'summarize_changed',lambda *args:({}, {}, {}))
    mutation('actual climate_summary mutation',reference,'climate_summary',lambda *args:((1,1,1),None))
    mutation('actual terrain summary mutation',objects['TOPO'],'summarize',lambda *args:((1,1,1),None,None))
    mutation('actual vegetation summary mutation',objects['VEG'],'chosen_summary',lambda *args:(None,{}))
    mutation('actual in-memory terrain categories',objects['TOPO'],'CLASSES',['changed']+objects['TOPO'].CLASSES[1:])
    mutation('actual imported RasterGrid reader',reference.RasterGrid,'__getitem__',lambda *args:None)
    mutation('actual aliased canonical operator',reference,'canonical',lambda g:g)
    result={'status':'PASS','actual_controls':len(passed),'controls':passed,'tiny_positive':positive,'no_complete_source_or_target_GIS_calculation':True}
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':run()
