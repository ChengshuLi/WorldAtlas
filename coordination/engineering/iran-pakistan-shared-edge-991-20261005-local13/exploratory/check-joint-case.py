import sys,json,pathlib,importlib.util
sys.path.insert(0,str(pathlib.Path('scripts').resolve()))
p=pathlib.Path('scripts/check-geographic-regression.py');spec=importlib.util.spec_from_file_location('geographic_regression',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
staged=json.loads(pathlib.Path('coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json').read_text())
prior=json.loads(pathlib.Path('.cache/shared-edge-991/prototype-v1.json').read_text())[-1]
before={f['id']:f for f in staged['baseline']};after=json.loads(json.dumps(before));subjects=staged['subject_ids']
for country,id in zip(['IRN','PAK'],subjects):after[id]['geometry']=prior['candidates'][country]
report=m.compare(before,after)
pathlib.Path('.cache/shared-edge-991/joint-case-regression-v1.json').write_text(json.dumps(report)+'\n')
print(json.dumps({'status':report['status'],'regressions':report['regressions'],'geometry_errors':report['geometry_errors'],'findings':[{'kind':f['properties']['kind'],'ids':f['properties']['location_ids'],'area':f['properties']['source_geometry_area_square_degrees'],'bounds':f['properties']['bounds']}for f in report['findings']['features']]}))
