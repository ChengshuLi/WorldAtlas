"""Tiny literal scientific method/callable controls, not the complete family."""
import hashlib,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).absolute().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def execute(receipt):
    sys.path[:0]=json.loads((HERE/'runtime-plan.json').read_bytes())['site_paths']
    run=load('method_entry',HERE/'run.py');guard=load('method_guard',HERE/'code_guard.py')
    ell=load('ellipsoidal_area',HERE/'methods/ellipsoidal_area.py');geo=load('geometry',HERE/'methods/geometry.py');science=load('method_science',HERE/'science.py')
    modules={'ellipsoidal_area':ell,'geometry':geo,'science':science};rows=[]
    for name,module in modules.items():guard.all_callables(module,Path(module.__file__).read_bytes())
    square={'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
    def shifted(dx):return {'type':'Polygon','coordinates':[[[x+dx,y]for x,y in square['coordinates'][0]]]}
    prefix='research/geography/mongolia-russia-gap-source-fitness-20261007/'
    def compare(dx):
        physical={'features':[{'id':'tiny-complete-component','properties':{},'geometry':square}]}
        data={'features':[{'geometry':shifted(dx),'properties':{'fixture':'whole tiny source'}}]}
        raw=json.dumps(data).encode();catalogue={'products':[{'key':'gb:'+country+':ADM2','parts':[{'path':country}], 'feature_count':1,'advertised_feature_count':1,'original_sha256':hashlib.sha256(raw).hexdigest()}for country in ('MNG','RUS')]}
        captured={prefix+'inputs/complete-family.json':json.dumps({'component_count':1}).encode(),prefix+'inputs/physical-component-features.geojson':json.dumps(physical).encode(),prefix+'inputs/route-component-rows.jsonl':json.dumps({'component':'tiny-complete-component','current_geometry_sha256':hashlib.sha256(json.dumps(square).encode()).hexdigest()}).encode(),prefix+'inputs/current-contact-features.geojson':json.dumps({'features':[]}).encode(),prefix+'sources/mongolia-mris/mng-adm2-nso-featurelayer-full.geojson':raw,'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json':json.dumps(catalogue).encode()}
        return science.compare(captured,{'MNG':raw,'RUS':raw},geo,ell)
    for dx,label,expected in [(0,'same complete pointsets genuine positive',1),(2,'disjoint actual method',0),(1,'line-only boundary actual method',0)]:
        out=compare(dx)
        assert all(v['relations'][0]['intersecting_feature_count']==expected for v in out['products'].values())
        assert out['mris_mongolia_nso_adm2']['relations'][0]['intersecting_feature_count']==expected
        rows.append({'name':label,'passed':True,'full_tiny_result':out})
    def reject(label,operation):
        try:operation()
        except ValueError as e:rows.append({'name':label,'passed':True,'error':str(e)});return
        raise AssertionError(label+' did not reject')
    old=ell.area;ell.area=lambda g:0
    try:reject('actual imported helper callable substitution',lambda:guard.all_callables(ell,(HERE/'methods/ellipsoidal_area.py').read_bytes()))
    finally:ell.area=old
    bindings=run.scientific_bindings(modules)
    import shapely
    old=shapely.intersection;shapely.intersection=lambda *a:None
    try:reject('actual external scientific callable substitution',lambda:run.require_scientific_bindings(modules,bindings))
    finally:shapely.intersection=old
    old=ell.WEIGHTS.copy();ell.WEIGHTS[0]+=1
    try:reject('actual quadrature-global mutation',lambda:run.require_scientific_bindings(modules,bindings))
    finally:ell.WEIGHTS[:]=old
    run.require_scientific_bindings(modules,bindings)
    receipt.write_text(json.dumps({'status':'PASS','controls':rows,'count':len(rows),'caller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limits':['Three tiny complete synthetic source/target rectangles use literal comparison/predicate/ellipsoidal methods. No actual48-component sources, source extraction, acquisition or world graph are read. This is not either qualifying comparison run.']},indent=2)+'\n')
    print(json.dumps({'status':'PASS','controls':len(rows),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}))
if __name__=='__main__':execute(Path(sys.argv[1]))
