"""Bind complete authenticated foreign originals as territorial negatives.
Usage: Python bind-complete-source-negatives.py REPO INPUT_COMMIT OUTPUT_DIR
All 122 originals are considered for all 334 targets. Only complete part-bbox
disjointness can omit an operand. Never clip, choose a claimant, or change scope.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys
W=pathlib.Path(sys.argv[1]);H=subprocess.check_output(['git','-C',str(W),'rev-parse',sys.argv[2]+'^{commit}']).decode().strip();O=pathlib.Path(sys.argv[3]);P='coordination/engineering/russia-repair-delivery-20261017/'
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p])
def get(p):return json.loads(raw(P+p))
def sha(b):return hashlib.sha256(b).hexdigest()
def geombytes(g):return json.dumps(g,sort_keys=True,separators=(',',':')).encode()
def bounds(g):
 polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];out=[]
 for poly in polys:
  coords=[point for ring in poly for point in ring];out.append([min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)])
 return out
def overlap(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
custody=get('source-review/source-custody.json');stages=get('source-stage/original-stage-inputs.json');config=get('config/source-evidence.json');roster=[];geoms={}
for family in custody['families']:
 if family['family'].startswith('gb:RUS:'):continue
 rec=family['catalogue_record'];chunks=[]
 for pin in family['parts']:
  b=raw(pin['path'],pin['commit']);assert len(b)==pin['bytes'] and sha(b)==pin['sha256'];z=gzip.decompress(b);assert len(z)==pin['decoded_bytes'] and sha(z)==pin['decoded_sha256'];chunks.append(z)
 b=b''.join(chunks);assert len(b)==rec['original_bytes'] and sha(b)==rec['original_sha256'];features=json.loads(b)['features'];assert len(features)==rec['feature_count']
 for i,f in enumerate(features):
  ident=family['family']+':'+f['properties']['shapeID'];g=f['geometry'];gb=geombytes(g);geoms[ident]=g;roster.append({'source_id':ident,'family':family['family'],'source_ordinal':i+1,'source_name':f['properties']['shapeName'],'geometry_sha256':sha(gb),'geometry_bytes':len(gb),'complete_polygon_part_bounds':bounds(g),'product_parts':family['parts']})
assert len(roster)==122 and len(stages)==334
stage={s['target']:s for s in stages};bindings=[];estimated=0
for target in config['source_evidence']['targets']:
 assert target['territorial_exclusions']==[]
 bb=bounds(stage[target['id']]['consumed']['geometry']);match=[r for r in roster if any(overlap(a,b) for a in bb for b in r['complete_polygon_part_bounds'])]
 target['territorial_exclusions']=[geoms[r['source_id']] for r in match];estimated+=sum(r['geometry_bytes'] for r in match)
 bindings.append({'target_id':target['id'],'pixelIndex':target['pixelIndex'],'complete_target_source_part_bounds':bb,'negative_operands':[{'source_id':r['source_id'],'negative_ordinal':i,'geometry_sha256':r['geometry_sha256']} for i,r in enumerate(match)],'omitted_complete_originals_proved_bbox_disjoint':[r['source_id'] for r in roster if r not in match]})
assert len(bindings)==334
# Every original frozen positive contact must remain an exact negative operand.
counts=get('source-review/source-competitor-native-counts.json');byowner={r['pixelIndex']:{v['source_id'] for v in r['negative_operands']} for r in bindings}
for y,a,z,o,ids in counts['non_russian_original_competitor_intervals']:assert set(ids)<=byowner[o]
summary={'complete_foreign_originals':len(roster),'targets':len(bindings),'whole_frozen_denominator':2566967,'original_competitor_cells':sum(r[2]-r[1] for r in counts['non_russian_original_competitor_intervals']),'negative_operand_bindings':sum(len(r['negative_operands']) for r in bindings),'estimated_repeated_geometry_bytes':estimated}
blob=(json.dumps(config,separators=(',',':'),ensure_ascii=False)+'\n').encode();free=os.statvfs(W).f_bavail*os.statvfs(W).f_frsize
summary.update(config_bytes=len(blob),free_bytes_before=free)
print(json.dumps(summary),flush=True)
assert free>3*len(blob)+268435456,'Insufficient shared space for configuration, constructed evidence, outputs and reserve'
report={'version':1,'geometry_hash_method':'SHA-256 of UTF-8 Python json.dumps(geometry, sort_keys=True, separators=(comma,colon)); custody checksum only, not the shared native valueSha identity','method':'Complete original polygon-part bbox applicability; retain entire matching source feature as non-overridable territorial negative','input_commit':H,'summary':summary,'complete_original_roster':roster,'target_bindings':bindings,'limits':['These are competing retained source claims, not current legal boundaries or a sovereignty judgment.','All original repair cells remain in the diagnostic denominator, including every competing-source contact.','Territorial applicability exceptions are absent. Foreign negatives grant no ownership and cannot override physical negatives.','Every omitted original is whole-feature bbox-disjoint from the complete original target source; no selected-cell, area threshold or metadata label excludes it.']}
O.mkdir(parents=True,exist_ok=False);(O/'source-evidence-complete-negatives.json').write_bytes(blob);(O/'complete-source-negative-bindings.json').write_text(json.dumps(report,separators=(',',':'),ensure_ascii=False)+'\n')
