#!/usr/bin/env python3
"""Recreate the three exact record extracts from the retained originals and archived result rows.
This extracts source/accepted comparison records only; it performs no spatial analysis.
"""
import argparse, base64, gzip, hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMIT = '0198938719a5666b6726fb6a1e45779926eefeb2'
sha = lambda b: hashlib.sha256(b).hexdigest()
def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, separators=(',', ':')) .encode() + b'\n')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output', type=pathlib.Path, default=ROOT/'records'); args=ap.parse_args()
    proposal=json.loads((ROOT/'inputs/root-philippines-ten-full-family-source-fit-proposal.json').read_bytes())
    source_raw=(ROOT/'inputs/gb-PHL-ADM3.original').read_bytes()
    assert sha(source_raw)=='2ece3d44a5c6a2afb385ffbf3a6b88d83e4d3a3e7eed9a52cb3be1bc59e289fc'
    source=json.loads(source_raw); ids=set(proposal['contact_ids']); native={x.rsplit(':',1)[-1] for x in ids}
    originals=[f for f in source['features'] if f.get('properties',{}).get('shapeID') in native]
    assert len(originals)==22 and {f['properties']['shapeID'] for f in originals}==native
    write_json(args.output/'original-source-features-22.json', {'type':'FeatureCollection','features':originals})
    current=[proposal['full_current_contacts'][i]['full_feature'] for i in sorted(ids)]
    assert len(current)==22 and {f['id'] for f in current}==ids
    write_json(args.output/'current-contact-features-22.json', {'type':'FeatureCollection','features':current})
    expected={r['component']:r for r in proposal['routing_rows']}; paths=sorted({r['whole_physical_containing_file'] for r in proposal['routing_rows']}); selected={}
    for path in paths:
        blob=subprocess.check_output(['git','show',f'{COMMIT}:{path}'])
        for line in gzip.decompress(blob).splitlines():
            if not line: continue
            row=json.loads(line); component=row.get('component_id')
            if component in expected:
                assert component not in selected
                digest=sha(canonical(row)); assert digest==expected[component]['whole_physical_row_sha256']
                selected[component]={'record':row,'canonical_sha256':digest,'raw_line_sha256':sha(line),'raw_line_bytes_base64':base64.b64encode(line).decode('ascii'),'source_file':path}
    assert set(selected)==set(expected) and len(selected)==22
    package={'source_commit':COMMIT,'source_files':paths,'records':[{'component':i,**selected[i]} for i in sorted(selected)]}
    write_json(args.output/'physical-comparison-rows-22.json',package)
    print(json.dumps({'result':'PASS','source_contacts':len(originals),'current_contacts':len(current),'physical_rows':len(selected),'physical_files':len(paths),'source_sha256':sha(source_raw)},sort_keys=True))
if __name__=='__main__': main()
