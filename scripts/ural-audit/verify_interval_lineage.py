#!/usr/bin/env python3
"""Verify that a selected coordinate interval matches an archived GeoJSON feature."""
import argparse,hashlib,json

def verify(archive, selected, feature_id):
    features=[f for f in archive['features'] if f.get('properties',{}).get('cut_id')==feature_id]
    if len(features)!=1 or features[0]['geometry']['type']!='LineString':raise ValueError('feature missing or ambiguous')
    source=features[0]['geometry']['coordinates']
    if not selected or any(not isinstance(p,list) or len(p)!=2 for p in selected):raise ValueError('invalid selected interval')
    starts=[i for i,p in enumerate(source) if p==selected[0]]
    matches=[i for i in starts if source[i:i+len(selected)]==selected]
    return {'selected_vertices':len(selected),'start_positions_1based':[i+1 for i in matches],'exact_match':bool(matches)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',required=True);p.add_argument('--archive-sha256',required=True);p.add_argument('--selected',required=True);p.add_argument('--feature-id',required=True)
    a=p.parse_args(); raw=open(a.archive,'rb').read()
    if hashlib.sha256(raw).hexdigest()!=a.archive_sha256:raise ValueError('archive checksum mismatch')
    result=verify(json.loads(raw),json.load(open(a.selected)),a.feature_id);print(json.dumps(result))
    if not result['exact_match']:raise SystemExit(1)
