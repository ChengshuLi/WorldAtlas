#!/usr/bin/env python3
"""Reconstruct pinned Ural divider/config bytes from selected Neon exports, not cells."""
import argparse,hashlib,json
from pathlib import Path
BOUNDARY='5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2';CLOSURE='6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a';DIVIDER='299d42f1dfd990b04c90e14fe8e93167f2d38e776de8ead2074adbbc0de26161';CONFIG='5581be926e0f8a0f6712594ac97abe86a5a9dcaf13dcd5476c34c8a50f208cf5';START=[51.9025683,47.2522618]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(b):return hashlib.sha256(b).hexdigest()
def derive(snapshot,observation):
 b=next(x for x in snapshot['mainland_boundaries'] if x['boundary_id']=='ural_kara_coast_to_caspian');c=next(x for x in snapshot['routes'] if x['route_id']=='europe_caspian_closure_v1');assert b['geometry_sha256']==digest(raw(b['geometry']))==BOUNDARY and c['geometry_sha256']==digest(raw(c['geometry']))==CLOSURE;line=b['geometry']['coordinates'];idx=[i for i,p in enumerate(line) if p==START];assert len(idx)==1;divider=line[idx[0]:]+c['geometry']['coordinates'][1:4];db=raw(divider);assert digest(db)==DIVIDER;cfg=observation['apply']['config'];assert cfg['sha256']['divider']==DIVIDER and observation['lineage']['selected_boundary_sha256']==BOUNDARY and observation['lineage']['selected_closure_sha256']==CLOSURE;cb=json.dumps(cfg,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False).encode();assert digest(cb)==CONFIG;return db,cb
def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--observation',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args();d=Path(a.output_dir);d.mkdir(exist_ok=False);db,cb=derive(json.load(open(a.snapshot)),json.load(open(a.observation)));(d/'divider.json').write_bytes(db);(d/'config.json').write_bytes(cb);print('divider',digest(db),'config',digest(cb))
if __name__=='__main__':main()
