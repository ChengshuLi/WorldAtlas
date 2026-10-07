"""Exclusive scoped entry; immutable full input preflight precedes operators."""
import argparse,datetime,json,pathlib,re,subprocess,sys,time
import reader,trace
HERE=pathlib.Path(__file__).resolve().parent
NS='coordination/engineering/north-slope46-construction-trace-20261007/'
CODE=('run.py','reader.py','trace.py','controls.py','kernel.py','exact_predicates.py','scope.json','scope-candidates.json','input-index.json','runtime-pins.json','issue-snapshot.json')+tuple('legacy/'+n for n in ('producer.py','comparison.py','inputs.py','immutable.py','ellipsoidal_area.py','input-config.json','transport.py'))

def code_guard(repo,commit):
    if not re.fullmatch('[a-f0-9]{40}',commit) or reader.old.git(repo,'rev-parse','HEAD').decode().strip()!=commit:
        raise ValueError('Exact current full immutable code commit required')
    closure=[]
    for name in CODE:
        path=HERE/name
        if path.is_symlink()or not path.is_file():raise ValueError('Ordinary executed closure required')
        raw=path.read_bytes();actual=reader.old.git(repo,'show',commit+':'+NS+name)
        if raw!=actual:raise ValueError('Changed executed code/config '+name)
        closure.append({'path':NS+name,'bytes':len(raw),'sha256':reader.digest(raw)})
    original_commit='bec82842ad5d9cf07e38a78395df8d5e7a6f4591'
    original_prefix='coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
    for name in tuple(n for n in CODE if n.startswith('legacy/'))+('kernel.py','exact_predicates.py'):
        raw=(HERE/name).read_bytes()
        if raw!=reader.old.git(repo,'show',original_commit+':'+original_prefix+name):
            raise ValueError('Literal accepted original dependency changed '+name)
    for module in (reader,reader.transport,trace,trace.kernel,trace.kernel.exact,reader.old,reader.old.comparison,reader.old.inputs,reader.old.immutable,reader.old.ellipsoidal_area):
        path=pathlib.Path(module.__file__).resolve()
        if not path.is_relative_to(HERE) or path.read_bytes()!=reader.old.git(repo,'show',commit+':'+NS+str(path.relative_to(HERE))):
            raise ValueError('Actual transitive imported module closure differs')
    return closure

def runtime():
    import numpy,shapely,pyproj
    result={'python':sys.version.split()[0],'numpy':numpy.__version__,'shapely':shapely.__version__,'GEOS':shapely.geos_version_string,'pyproj':pyproj.__version__,'executable':sys.executable}
    if {k:result[k]for k in ('python','numpy','shapely','GEOS','pyproj')}!={'python':'3.12.14','numpy':'2.3.5','shapely':'2.1.2','GEOS':'3.13.1','pyproj':'3.7.2'}:raise ValueError('Original runtime differs')
    pinned=json.loads((HERE/'runtime-pins.json').read_bytes())
    for pin in pinned['actual_whole_runtime_files']:
        path=pathlib.Path(pin['path']);raw=path.read_bytes()
        if len(raw)!=pin['bytes']or reader.digest(raw)!=pin['sha256']:raise ValueError('Original runtime body changed '+pin['path'])
    result['actual_whole_runtime_files']=pinned['actual_whole_runtime_files']
    return result

def safe_output(repo,out):
    if not out.is_absolute()or'..'in out.parts or not out.resolve().is_relative_to(repo/'.cache')or out.exists()or out.is_symlink():raise ValueError('Fresh exclusive owned cache output required')
    for p in out.parents:
        if p.is_symlink():raise ValueError('Output symlink ancestor')
        if p==repo:break

class Objects:
    def __init__(self,products):self.products=products;self.seen=set()
    def retain(self,value):
        if isinstance(value,dict):
            if value.get('type')in ('Polygon','MultiPolygon','GeometryCollection','LineString','MultiLineString','Point','MultiPoint','LinearRing'):
                raw=reader.canonical(value);key=reader.digest(raw)
                if key not in self.seen:
                    self.products.emit('geometry-objects',{'geometry_sha256':key,'geometry':value});self.seen.add(key)
                return {'complete_geometry_object_sha256':key}
            return {k:self.retain(v)for k,v in value.items()}
        if isinstance(value,list):return [self.retain(v)for v in value]
        return value

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);parser.add_argument('--out',type=pathlib.Path,required=True);parser.add_argument('--input-only',action='store_true');args=parser.parse_args();repo=HERE.parents[2]
    safe_output(repo,args.out);closure=code_guard(repo,args.commit);rt=runtime();started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    state=reader.load(repo)
    preflight={'status':'PASS','mode':'input-only; no scoped geometry operators','execution_commit':args.commit,'runtime':rt,'code':closure,'inputs':state['receipts'],'complete_current_candidate_roster':95173,'scope_components':46,'numeric_siblings':28,'nonnumeric_siblings':18,'query_relations':209,'original_physical_restoration':state['original_physical_restoration'],'native':state['native_proof'],'contact':state['contact'],'current_contact_proof':state['current_contact_proof'],'output_created':args.out.exists()}
    if args.input_only:
        print(json.dumps(preflight,sort_keys=True));return
    products=reader.old.Products(args.out);objects=Objects(products);counts={};queries=0
    validity=reader.old.comparison.ValidityCache();shifted={}
    for ordinal,identity in enumerate(sorted(state['features'])):
        result=trace.execute(state['features'][identity],state['physical'][identity],state['sources'],validity,shifted);result['prior_numeric_diagnosis']=state['diagnoses'].get(identity);queries+=len(result.get('query_replays',[]));counts[result['status']]=counts.get(result['status'],0)+1
        products.emit('components',objects.retain(result));print(json.dumps({'scoped_components':ordinal+1,'total':46,'component':identity,'status':result['status']}),flush=True)
    descriptors=products.finish()
    if queries!=209:raise ValueError('Incomplete209 actual local query replays')
    report={'version':1,'issue':1353,'execution_commit':args.commit,'runtime':rt,'command':sys.argv,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-clock,'scope_components':46,'numeric_siblings':28,'nonnumeric_siblings':18,'actual_query_replays':queries,'geometry_objects':len(objects.seen),'actual_validity_cache':{'checks':validity.checks,'hits':validity.hits},'statuses':counts,'products':descriptors,'preflight':preflight,'limits':['Original v7 source-relative cohort; not a fresh v8/world measurement.','Whole source/query/mapping discrepancies and all siblings remain explicit.','No coordinate alteration, precision repair, political/source approval, absent-water inference or Atlas fill.']}
    (args.out/'report.json').write_bytes(reader.canonical(report));print(json.dumps({'status':'PASS','products':len(descriptors),'output_encoded_bytes':sum(p['bytes']for p in descriptors),'actual_query_replays':queries,'counts':counts}))
if __name__=='__main__':main()
