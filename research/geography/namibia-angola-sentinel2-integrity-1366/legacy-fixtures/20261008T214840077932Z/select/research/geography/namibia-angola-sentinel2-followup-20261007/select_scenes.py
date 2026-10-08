#!/usr/bin/env python3
"""Freeze one cloud-screened Sentinel-2 L2A item per MGRS tile/season window."""
from __future__ import annotations
import glob, hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
WINDOWS={
 '2019-wet':['S2B_33KZA_20190221_0_L2A','S2B_34KBF_20190221_0_L2A','S2B_34KCF_20190221_0_L2A','S2A_34KDF_20190223_0_L2A'],
 '2019-dry':['S2A_33KZA_20190904_0_L2A','S2A_34KBF_20190904_0_L2A','S2B_34KCF_20190909_0_L2A','S2B_34KDF_20190906_0_L2A'],
 '2020-wet':['S2A_33KZA_20200122_0_L2A','S2A_34KBF_20200122_0_L2A','S2A_34KCF_20200122_0_L2A','S2A_34KDF_20200119_0_L2A'],
 '2020-dry':['S2A_33KZA_20200809_0_L2A','S2A_34KBF_20200809_0_L2A','S2B_34KCF_20200814_0_L2A','S2B_34KDF_20200811_0_L2A'],
}
items={}
for path in glob.glob(str(ROOT/'inputs'/'earth-search-stac-*-page-*.json')):
 if any(f'earth-search-stac-{window}-page-' in path for window in WINDOWS):
  for feature in json.loads(pathlib.Path(path).read_text())['features']:
   items[feature['id']]=feature
selected=[]
for window,ids in WINDOWS.items():
 for ident in ids:
  if ident not in items: raise SystemExit(f'missing item {ident}')
  item=items[ident]; p=item['properties']
  if float(p['s2:processing_baseline'])>=4: raise SystemExit(f'baseline is not original-era for {ident}')
  if p.get('earthsearch:boa_offset_applied') is not False: raise SystemExit(f'offset flag unexpected for {ident}')
  if float(p.get('eo:cloud_cover',100))>=20: raise SystemExit(f'cloud screen failed for {ident}')
  tile=p['grid:code']; expected=f'MGRS-{ident.split("_")[1]}'
  if tile!=expected: raise SystemExit(f'tile/id mismatch: {tile} {ident}')
  selected.append({'window':window,'item':item})
bywindow={w:sorted((x['item']['properties']['datetime'] for x in selected if x['window']==w)) for w in WINDOWS}
span_days={w:(max(v)-min(v)).total_seconds()/86400 for w,v in []}
payload={'version':1,'selection_basis':'One low-cloud, original-era (<04.00) processing-baseline item per MGRS tile in each seasonal window. Dates are near-synoptic within each window; selection was frozen before per-pixel analysis. Whole-tile cloud and no-data percentages are metadata screening fields only.','windows':{w:{'item_ids':[x['item']['id'] for x in selected if x['window']==w],'acquisition_times_utc':sorted(x['item']['properties']['datetime'] for x in selected if x['window']==w)} for w in WINDOWS},'selected_items':[x['item'] for x in selected]}
out=ROOT/'inputs'/'selected-sentinel2-items.json'; raw=(json.dumps(payload,sort_keys=True,indent=2)+'\n').encode();out.write_bytes(raw)
print(json.dumps({'item_count':len(selected),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'windows':payload['windows']},indent=2))
