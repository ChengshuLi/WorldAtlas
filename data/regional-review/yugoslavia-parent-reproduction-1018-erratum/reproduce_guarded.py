#!/usr/bin/env python3
"""Guard the exact #1189 Yugoslavia parent-study scope and reproduce into new outputs."""
import argparse, hashlib, json, pathlib, subprocess, tempfile, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=pathlib.Path(__file__).resolve().parent
OLD=ROOT/'data/regional-review/followup-yugoslavia-423-parent-tiers-20261005'
SNAP=OWN/'issue-snapshot.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def fail(s): raise SystemExit('guard failed: '+s)
def git_blob(commit,path): return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',required=True); ap.add_argument('--units-override'); a=ap.parse_args()
    dest=pathlib.Path(a.output_dir).resolve()
    # Refuse an existing destination before reading/emitting any products.
    if dest.exists(): fail('output directory already exists; no files written')
    contract=json.loads(SNAP.read_text()); body=contract['body']; marker='<!-- worldatlas-work:v1\n'; raw=body.split(marker,1)[1].split('\n-->',1)[0]; work=json.loads(raw); eq=work['evidence_quality']; pins=eq['pins']; baseline='7646e0962afab6cc4f566439bb2f96890ae4b91e'
    if len(eq['subject_ids'])!=295 or len(set(eq['subject_ids']))!=295: fail('declared subject scope is not exactly 295 unique IDs')
    if not pins: fail('immutable input pin set is empty')
    for spec,want in sorted(pins.items()):
        commit,path=spec.split(':',1); got=sha(git_blob(commit,path))
        if got!=want: fail(f'pin mismatch: {spec} expected {want} got {got}')
    oldunits=git_blob(baseline,'data/regional-review/regional-review-d282e62cf0209796/unit-assessments.json')
    units_path=pathlib.Path(a.units_override).resolve() if a.units_override else None
    units=json.loads(units_path.read_text() if units_path else oldunits)
    scope=json.loads(git_blob(baseline,'data/regional-review/regional-review-d282e62cf0209796/scope.json'))
    if set(scope['member_location_ids']) != {x for x in eq['subject_ids'] if x.startswith('gb:')} or len(scope['member_location_ids'])!=278: fail('native source roster differs from declared 278 scoped subjects')
    if len(units['rows'])!=278 or {r['location_id'] for r in units['rows']}!=set(scope['member_location_ids']): fail('missing, duplicate, or outside child identity')
    source=ROOT/'data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09'
    features={}
    for cc,lev in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]:
        fc=json.loads((source/f'geoBoundaries-{cc}-{lev}.geojson').read_text())
        for f in fc['features']:
            p=f['properties']; sid=p['shapeID']
            if sid in features: fail('duplicate source shapeID '+sid)
            features[sid]=(cc,lev,p)
    for r in units['rows']:
        x=features.get(r['source_shape_id'])
        if not x or x[:2]!=(r['location_id'].split(':')[1],'ADM2'): fail('source feature missing/wrong collection: '+r['location_id'])
        if x[2].get('shapeName')!=r['source_shape_name']: fail('source shapeName mismatch: '+r['location_id'])
    parents=json.loads(git_blob(baseline,'data/regional-review/regional-review-d282e62cf0209796/province-assessments.json'))['assessments']
    if {p['province_id'] for p in parents}!={x for x in eq['subject_ids'] if x.startswith('framework:province:')} or len(parents)!=17: fail('parent identity scope mismatch')
    metadata={}
    for cc in ('SRB','SVN'):
        path=source/f'geoBoundaries-{cc}-ADM1-metaData.json'; m=json.loads(path.read_text()); metadata[cc]={'boundaryYear':m['boundaryYear'],'boundaryType':m['boundaryType'],'boundaryCanonical':m.get('boundaryCanonical'),'source':m['boundarySource'],'license':m['boundaryLicense'],'sourceDataUpdateDate':m.get('sourceDataUpdateDate'),'buildDate':m.get('buildDate')}
    rows=[]
    for p in sorted(parents,key=lambda z:z['province_id']):
        pid=p['province_id']; matches=[props for cc,lev,props in features.values() if lev=='ADM1' and cc==('SRB' if any(r['parent_id']==pid and r['location_id'].startswith('gb:SRB:') for r in units['rows']) else 'SVN') and props.get('shapeName','').casefold()==p['name'].casefold()]
        synthetic=pid in {'framework:province:ankaran-ancarano:3995388bc628','framework:province:izola-isola:bc2149bec285','framework:province:piran-pirano:1d929956088b'}
        if synthetic:
            vintage='unknown'; typ='synthetic one-child Atlas wrapper; no independent parent source feature'; matched=[]
        else:
            cc='SRB' if any(r['parent_id']==pid and r['location_id'].startswith('gb:SRB:') for r in units['rows']) else 'SVN'
            if len(matches)!=1: fail('expected unique same-name source parent for '+pid)
            vintage=metadata[cc]['boundaryYear']; typ=metadata[cc]['boundaryType']+' / '+str(metadata[cc].get('boundaryCanonical')); matched=[x['shapeID'] for x in matches]
        rows.append({'parent_id':pid,'name':p['name'],'source_vintage':vintage,'source_type':typ,'source_collection':'SRB-ADM1' if pid.startswith('framework:province:') and any(r['parent_id']==pid and r['location_id'].startswith('gb:SRB:') for r in units['rows']) else ('SVN-ADM1' if not synthetic else 'none'),'matching_parent_shape_ids':matched,'scoped_child_count':sum(r['parent_id']==pid for r in units['rows']),'source_metadata':None if synthetic else metadata['SRB' if vintage=='2017' else 'SVN']})
    # Validation is complete. Create the new destination exclusively before emission.
    try: dest.mkdir(parents=True,exist_ok=False)
    except FileExistsError: fail('output directory already exists; no files written')
    # Execute both unchanged historical generators twice with only output destinations redirected.
    # Each run uses a new exclusive private directory and verifies every output hash.
    outputs=[]
    for run in (1,2):
        rd=dest/f'run-{run}'; rd.mkdir(exist_ok=False)
        for name,files in [('parent-study',['parent-study.json','issue-1016-overlap.csv']),('geometry-overlay',['geometry-comparison.json'])]:
            srcfile=OLD/('reproduce-parent-study.py' if name=='parent-study' else 'reproduce-geometry-overlay.py')
            code=srcfile.read_text()
            if name=='parent-study':
                code=code.replace("OUT = pathlib.Path(__file__).resolve().parent / 'parent-study.json'",f"OUT = pathlib.Path({str(rd/'parent-study.json')!r})")
                code=code.replace("pathlib.Path(__file__).resolve().parent/'issue-1016-overlap.csv'",f"pathlib.Path({str(rd/'issue-1016-overlap.csv')!r})")
            else: code=code.replace("OUT=pathlib.Path(__file__).resolve().parent/'geometry-comparison.json'",f"OUT=pathlib.Path({str(rd/'geometry-comparison.json')!r})")
            exec(compile(code,str(srcfile),'exec'),{'__name__':'__main__','__file__':str(srcfile)})
        runrec={}
        for fn in ('parent-study.json','issue-1016-overlap.csv','geometry-comparison.json'):
            b=(rd/fn).read_bytes(); runrec[fn]={'bytes':len(b),'sha256':sha(b)}
        outputs.append(runrec)
    if outputs[0]!=outputs[1]: fail('two fresh generator runs differ')
    expected={'parent-study.json':'7dc99f764c7f4148cd4e54d2e75b93afc7613ee04e7d9eea1d57959c2b4b1951','issue-1016-overlap.csv':'5e33ac57ee4982803c72fca78bfe6226663b42c2e716b28bd46e2a6e6311bb0a','geometry-comparison.json':'c365fceb6d68c011f82340a6693c6658b503e312c64a631ac2a4b63b1bb3c59d'}
    if {k:v['sha256'] for k,v in outputs[0].items()}!=expected: fail('reproduced historical output hashes differ')
    (dest/'parent-vintage-type-erratum.json').write_text(json.dumps({'version':1,'issue':1189,'parent_count':len(rows),'parents':rows,'interpretation':'Corrected source vintage is the source metadata boundaryYear. boundaryType/canonical are separate layer semantics. Three synthetic wrappers have no independent source polygon and vintage remains unknown.'},sort_keys=True,ensure_ascii=False,indent=2)+'\n')
    (dest/'reproduction-record.json').write_text(json.dumps({'version':1,'issue':1189,'baseline':baseline,'declared_subject_count':295,'native_children':278,'parents':17,'pinned_input_count':len(pins),'whole_file_pins_verified':True,'child_feature_and_shapeName_correspondence':'278/278 exact','two_fresh_runs':outputs,'source_name_drift_fixture':'Use --units-override with one source_shape_name mutation; exact source correspondence guard rejects before generating outputs.','preservation':'Every run output goes to a new exclusive directory. Existing destinations are refused before any products are emitted. Historical originals are only read.'},sort_keys=True,indent=2)+'\n')
    print(json.dumps({'output_dir':str(dest),'runs':outputs,'parents':len(rows),'children':278,'pins':len(pins)}))
if __name__=='__main__': main()
