"""Whole emitted-byte/reference readback only; no geometry operators or queries."""
import gzip,hashlib,io,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SCIENCE='1208538e0ae9dba868bcf9fffc34301ea825b588'
LIMIT=33554432

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ordinary(base,name):
    if pathlib.PurePosixPath(name).is_absolute() or any(p in ('','..','.')for p in name.split('/')):raise ValueError('Unsafe ordinary evidence path')
    path=base/name
    if path.is_symlink() or not path.is_file() or path.stat().st_size>LIMIT:raise ValueError('Ordinary bounded evidence required')
    if any(p.is_symlink()for p in path.parents if p!=ROOT.parent):raise ValueError('Symlink evidence ancestor')
    return path.read_bytes()
def references(value,result):
    if isinstance(value,dict):
        if 'complete_geometry_object_sha256'in value:
            if set(value)!= {'complete_geometry_object_sha256'}:raise ValueError('Ambiguous whole geometry alias')
            result.add(value['complete_geometry_object_sha256'])
        else:
            for child in value.values():references(child,result)
    elif isinstance(value,list):
        for child in value:references(child,result)
def main():
    reports=[json.loads(ordinary(HERE,n+'/report.json'))for n in ('r1','r2')]
    if reports[0]['products']!=reports[1]['products']:raise ValueError('Distinct actual scientific descriptor families')
    product_rows=[];components=[];objects=set();refs=set()
    for d in reports[0]['products']:
        if d['bytes']>LIMIT or d['uncompressed_bytes']>LIMIT:raise ValueError('Declared complete scientific bound')
        one=ordinary(HERE,'r1/'+d['path']);two=ordinary(HERE,'r2/'+d['path'])
        if one!=two or len(one)!=d['bytes']or sha(one)!=d['sha256']:raise ValueError('Actual complete scientific body differs')
        with gzip.GzipFile(fileobj=io.BytesIO(one))as f:raw=f.read(LIMIT+1)
        if len(raw)!=d['uncompressed_bytes']or sha(raw)!=d['uncompressed_sha256']:raise ValueError('Decoded whole scientific body differs')
        for line in raw.splitlines():
            row=json.loads(line)
            if d['path'].startswith('components-'):components.append(row);references(row,refs)
            else:
                identity=row['geometry_sha256']
                if identity in objects or sha(canonical(row['geometry']))!=identity:raise ValueError('Duplicate or changed whole geometry object')
                objects.add(identity)
        product_rows.append(d)
        del one,two,raw
    expected=json.loads(ordinary(HERE,'scope-candidates.json'));scope=json.loads(ordinary(HERE,'scope.json'))
    if {x['component_id']for x in components}!={x['id']for x in expected} or len(components)!=46:raise ValueError('Complete46 emitted scope differs')
    if refs!=objects or len(objects)!=776:raise ValueError('Missing, extra or unbound complete geometry object')
    expected_by_id={x['id']:x for x in expected}
    for row in components:
        feature=row['whole_candidate_feature'];original=expected_by_id[row['component_id']]
        if feature['geometry']!={'complete_geometry_object_sha256':sha(canonical(original['geometry']))}:raise ValueError('Candidate exact pointset alias differs')
        if {k:v for k,v in feature.items()if k!='geometry'}!={k:v for k,v in original.items()if k!='geometry'}:raise ValueError('Candidate whole context differs')
        if len(row['mapping_equality'])!=6 or len(row['hierarchy_mapping_equality'])!=3 or not all([*row['mapping_equality'].values(),*row['hierarchy_mapping_equality'].values()]):raise ValueError('Original mapping mismatch must stay explicit')
    if sum(len(r['query_replays'])for r in components)!=209:raise ValueError('Incomplete209 emitted relations')
    equal_fields=('execution_commit','runtime','scope_components','numeric_siblings','nonnumeric_siblings','actual_query_replays','geometry_objects','actual_validity_cache','statuses','preflight','limits')
    for key in equal_fields:
        if reports[0][key]!=reports[1][key]:raise ValueError('Scientific report semantics differ '+key)
    if reports[0]['execution_commit']!=SCIENCE:raise ValueError('Wrong frozen execution vintage')
    for code in reports[0]['preflight']['code']:
        raw=ordinary(ROOT,code['path']);old=subprocess.check_output(['git','-C',str(ROOT),'show',SCIENCE+':'+code['path']])
        if raw!=old or len(raw)!=code['bytes']or sha(raw)!=code['sha256']:raise ValueError('Frozen18 code/config bytes differ')
    proof={'status':'PASS','scope_components':46,'query_relations':209,'geometry_objects':len(objects),'scientific_product_count':len(product_rows),'scientific_products':product_rows,'full_geometry_references_resolved':True,'exact_candidate_geometry_and_context_bindings':46,'six_plus_three_original_mapping_comparisons':46,'scientific_execution_commit':SCIENCE,'equal_report_fields':equal_fields,'encoded_scientific_bytes_each':sum(x['bytes']for x in product_rows),'maximum_decoded_scientific_body':max(x['uncompressed_bytes']for x in product_rows),'limits':['No third source query, geometry operator or exact point-membership cohort.','Actual execution reports/times/paths remain separately truthful; equality concerns scientific bodies and specified semantic fields.','Whole geometry aliases authenticate coordinates, not geographic/repair authority.']}
    print(json.dumps(proof,sort_keys=True))
if __name__=='__main__':main()
