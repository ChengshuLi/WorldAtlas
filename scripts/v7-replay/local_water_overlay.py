#!/usr/bin/env python3
"""Make a clearly labeled local runtime snapshot from pinned Neon + user overlay.

This does not write Neon. Downstream must explicitly support this schema and
validate the land snapshot pin separately; ordinary Neon-only tools reject it.
"""
import argparse,copy,hashlib,json
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def make(base,water,overlay,base_path,base_sha,water_path,water_sha,overlay_path,overlay_sha):
 if base.get('source') not in {'neon-export','local-derived-from-neon-export'} or base.get('decision_revision',{}).get('status')!='draft':raise ValueError('base must be a pinned draft land snapshot')
 if water.get('source')!='neon-export' or water.get('decision_revision',{}).get('status')!='draft':raise ValueError('water snapshot must be a pinned draft Neon export')
 if base.get('entity_revision')!=water.get('entity_revision') or base.get('category_bindings')!=water.get('category_bindings'):raise ValueError('land/water entity registry mismatch')
 if overlay.get('schema')!='worldatlas-local-water-decision-overlay-v1' or overlay.get('source')!='local-user-directed-overlay-not-neon':raise ValueError('invalid local overlay')
 neon_path=Path(overlay['neon_water_structure']['path']);raw=neon_path.read_bytes()
 if sha(raw)!=overlay['neon_water_structure']['sha256']:raise ValueError('Neon water structure pin mismatch')
 neon=json.loads(raw)
 current={b['basin_id']:(b['source_feature_id'],b['geometry_sha256'],b['method'],b['participant_entity_ids'],b['tie_rules'],b['source_id'],b['source_version'],b['feature_id']) for b in neon['basins']}
 previous={b['id']:(b['source_feature_id'],b['geometry_sha256'],b['assignment_method'],b['participant_entity_ids'],b.get('tie_rules'),b['source_id'],b['source_version'],b['feature_id']) for b in water.get('basins',[])}
 if previous!=current:raise ValueError('base land snapshot basin set differs from current Neon water structure')
 # The older full water export is only a carrier for schema-complete records.
 # Independently compare every used water source, seed and southern route with
 # the latest current-Neon structure before copying any of them.
 assets=[x for x in water.get('sources',[]) if x.get('source_id')=='seavox-sea-areas']
 if len(assets)!=1 or any(assets[0].get(k)!=neon['source_asset'].get(k) for k in ('source_id','version','sha256','r2_bucket','r2_key','size_bytes')):raise ValueError('current Neon water source mismatch')
 ns={x['seed_id']:x for x in neon['ocean_seeds']};ws={x['seed_id']:x for x in water['ocean_seeds']}
 if set(ns)!=set(ws) or any(any(ns[k].get(z)!=ws[k].get(z) for z in ('endpoint_id','entity_id')) for k in ns):raise ValueError('current Neon ocean seed mismatch')
 ne={x['endpoint_id']:x for x in neon['endpoints']};we={x['endpoint_id']:x for x in water['endpoints']}
 nr={x['route_id']:x for x in neon['routes']};wr={x['route_id']:x for x in water['routes']}
 chosen=overlay['ocean']['retain_southern_meridians_from_neon']
 ids={x['endpoint_id'] for x in ws.values()}
 for key in chosen:
  if key not in nr or key not in wr or nr[key]['route_type']!='meridian' or wr[key]['route_type']!='meridian':raise ValueError('current Neon southern route mismatch')
  npoints=[x['endpoint_id'] for x in nr[key]['points']];wpoints=[x['endpoint_id'] for x in wr[key]['points']]
  if npoints!=wpoints:raise ValueError('current Neon southern endpoints mismatch')
  ids.update(npoints)
 for key in ids:
  if key not in ne or key not in we or any(abs(float(ne[key][axis])-float(we[key][axis]))>1e-12 for axis in ('longitude','latitude')):raise ValueError('current Neon endpoint coordinate mismatch')
 if base['decision_revision'].get('entity_revision')!=neon['decision_revision']['entity_revision']:raise ValueError('entity revision mismatch')
 out=copy.deepcopy(base);out['schema']='worldatlas-local-water-effective-snapshot-v1';out['source']='local-user-directed-overlay-not-neon'
 out['local_overlay_provenance']={'base_land_snapshot_path':str(Path(base_path).resolve()),'base_land_snapshot_sha256':base_sha,'base_land_snapshot_source':base['source'],'water_neon_snapshot_path':str(Path(water_path).resolve()),'water_neon_snapshot_sha256':water_sha,'overlay_path':str(Path(overlay_path).resolve()),'overlay_sha256':overlay_sha,'neon_water_structure_sha256':sha(raw),'status':'non-publishing-user-directed-overlay','neon_status_changed':False}
 # Water is separately pinned; never claim it came from the land snapshot.
 if out.get('basins'):raise ValueError('land snapshot unexpectedly contains basins')
 out['basins']=copy.deepcopy(water['basins'])
 for field,key in (('sources','source_id'),('features','feature_id'),('endpoints','endpoint_id')):
  existing={x[key]:x for x in out.get(field,[])}
  for x in water.get(field,[]):
   if x[key] in existing and existing[x[key]]!=x:raise ValueError('land/water record collision in '+field)
   if x[key] not in existing:out.setdefault(field,[]).append(copy.deepcopy(x));existing[x[key]]=x
 if out.get('ocean_seeds'):raise ValueError('land snapshot unexpectedly contains ocean seeds')
 out['ocean_seeds']=copy.deepcopy(water['ocean_seeds'])
 policies=[p for p in out.get('policies',[]) if p.get('kind') not in {'coastline_assignment','closed_water_assignment','ocean_fill'}]
 for selected in overlay['policy_overlays']:
  orig=next((p for p in neon['water_assignment_policies'] if p['policy_id']==selected['neon_policy_id']),None)
  if orig is None or orig['definition']!=selected['definition'] or orig['evidence']!=selected['neon_evidence']:raise ValueError('policy overlay differs from pinned Neon proposal')
  d=copy.deepcopy(selected['definition'])
  if d.get('distance')!='wgs84_ellipsoidal_center_to_center' or d.get('ellipsoid')!='WGS84':raise ValueError('non-WGS84 selected')
  policies.append({'id':selected['neon_policy_id'],'kind':selected['kind'],'definition':d,'evidence':{'execution_status':'local_user_authorized_overlay','original_neon_evidence':copy.deepcopy(selected['neon_evidence'])}})
 if {p['kind'] for p in policies if p['kind'] in {'coastline_assignment','closed_water_assignment'}}!={'coastline_assignment','closed_water_assignment'}:raise ValueError('missing coast/closed policies')
 # Preserve the user-directed ordering without inventing an order among basins.
 if any(p.get('kind')=='layer_precedence' for p in policies):raise ValueError('land snapshot unexpectedly contains precedence policy')
 e=overlay.get('stage_order_evidence',{})
 if not e.get('message_id') or not e.get('user_exact_text'):raise ValueError('missing user stage-order evidence')
 names=['named-'+b['id'] for b in water['basins']]
 if not names or len(set(names))!=len(names):raise ValueError('invalid named layers')
 policies.append({'id':'local-user-water-layer-order-v1','kind':'layer_precedence','definition':{'priorities':{'coastal-band':0,**{name:1 for name in names}},'allowed_overrides':[{'winner':name,'loser':'coastal-band'} for name in names]},'evidence':{'execution_status':'local_user_authorized_overlay','user_message_id':e['message_id'],'user_exact_text':e['user_exact_text'],'same_priority_named_overlaps':'report as ambiguity; do not choose a winner silently'}})
 source_ocean=neon['ocean_fill_policy'];definition=copy.deepcopy(source_ocean['definition']);local=overlay['ocean'];
 if not isinstance(local.get('routes'),list) or not local['routes']:raise ValueError('bad local ocean route set')
 southern=local['retain_southern_meridians_from_neon']; routes={r['route_id']:r for r in water['routes']}
 if len(set(southern))!=len(southern) or any(k not in routes or routes[k]['route_type']!='meridian' for k in southern):raise ValueError('missing southern meridians')
 out['routes']=copy.deepcopy(base.get('routes',[]))+[copy.deepcopy(routes[k]) for k in southern]; endpoints=out['endpoints']
 for r in local['routes']:
  if len(r['points'])!=2:raise ValueError('unsupported route shape')
  ids=[]
  for i,p in enumerate(r['points']):
   eid=f'{r["id"]}-endpoint-{i}';ids.append(eid);endpoints.append({'endpoint_id':eid,'name':p.get('name',eid),'longitude':p['longitude'],'latitude':p['latitude'],'evidence':{'source':'local-overlay','coordinate_evidence':p}})
  kind='lonlat_polyline' if r['kind']=='latitude_parallel' else r['kind']
  if kind not in ('lonlat_polyline','wgs84_geodesic') or (r['kind']=='latitude_parallel' and any(p['latitude']!=r['latitude'] for p in r['points'])):raise ValueError('unexpected ocean route')
  out['routes'].append({'route_id':r['id'],'route_type':kind,'parameters':{'max_step_km':r['max_step_km']} if kind=='wgs84_geodesic' else {},'points':[{'ordinal':i,'endpoint_id':x} for i,x in enumerate(ids)],'evidence':{'source':'local-user-directed-overlay','overlay_sha256':overlay_sha}})
 definition['route_ids']=[r['id'] for r in local['routes']]+southern
 policies.append({'id':source_ocean['policy_id'],'kind':'ocean_fill','definition':definition,'evidence':{'execution_status':'local_user_authorized_overlay','original_neon_evidence':copy.deepcopy(source_ocean['evidence'])}})
 out['policies']=policies
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--water',required=True);p.add_argument('--overlay',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 br=Path(a.base).read_bytes();wr=Path(a.water).read_bytes();orr=Path(a.overlay).read_bytes();o=make(json.loads(br),json.loads(wr),json.loads(orr),a.base,sha(br),a.water,sha(wr),a.overlay,sha(orr))
 with open(a.out,'x') as f:json.dump(o,f,ensure_ascii=False,sort_keys=True,separators=(',',':'));f.write('\n')
 print('local_runtime_snapshot_sha256',sha(Path(a.out).read_bytes()))
if __name__=='__main__':main()


def verify(doc):
    p=doc.get('local_overlay_provenance',{})
    bp=Path(p.get('base_land_snapshot_path',''));wp=Path(p.get('water_neon_snapshot_path',''));op=Path(p.get('overlay_path',''))
    br=bp.read_bytes();wr=wp.read_bytes();orr=op.read_bytes()
    if sha(br)!=p.get('base_land_snapshot_sha256') or sha(wr)!=p.get('water_neon_snapshot_sha256') or sha(orr)!=p.get('overlay_sha256'):raise ValueError('local land/water/overlay hash mismatch')
    expected=make(json.loads(br),json.loads(wr),json.loads(orr),bp,sha(br),wp,sha(wr),op,sha(orr))
    if doc!=expected:raise ValueError('materialized local snapshot is not the exact verified overlay')
    return True

def selected(snapshot,record):
    e=record.get('evidence',{})
    return (e.get('execution_status')=='selected_for_research' or (snapshot.get('_local_overlay_verified') is True and e.get('execution_status')=='local_user_authorized_overlay'))

def land_snapshot_hash(snapshot,water_sha):
    if snapshot.get('_local_overlay_verified') is True:return snapshot['local_overlay_provenance']['base_land_snapshot_sha256']
    return water_sha
