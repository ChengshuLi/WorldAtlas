from pathlib import Path
import json,subprocess,gzip,hashlib,difflib
r=Path('.cache/runtime-integration-sea318-current458-20261010');h=r/'sea318-adapter-hunk.mjs';s=h.read_text()
s=s.replace("const rule=request.source_rule;\n  demand(rule.profile", "const rule=request.source_rule;\n  demand(request.report.sha256==='2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0'\n    &&report.execution_commit==='104091cfecd9c83a53f3e6e62f95b0a0c8074351','Unsupported original physical-comparison authority');\n  demand(rule.profile")
s=s.replace("for(const pin of rule.inputs){demand(!bodies.has(pin.path)","for(const pin of rule.inputs){demand(pin.kind===undefined&&!bodies.has(pin.path)")
s=s.replace('pin.path===packed.delivered_product.path','pin.path===packed.original_product.path').replace('physicalProduct[key]===packed.delivered_product[key]','physicalProduct[key]===packed.original_product[key]')
h.write_text(s)
b=(r/'caller-base458.mjs').read_text();p=(r/'caller-proposed318.mjs').read_text();start=p.index('// Accepted original SEA318');end=p.index('const RETAINED_ADMINISTRATIVE_HANDOFFS=',start);p=p[:start]+s+p[end:];(r/'caller-proposed318.mjs').write_text(p)
(r/'sea318-caller.patch').write_text(''.join(difflib.unified_diff(b.splitlines(True),p.splitlines(True),fromfile='a/scripts/additive-gap-repair.mjs',tofile='b/scripts/additive-gap-repair.mjs')))
fit=json.load(open(r/'administrative-source-rule-fit.json'));row=next(x for x in fit['cases']if x['country_codes']==['BRN']);sources=[];pins=[]
for q in row['original_physical_query_custody']['complete_query_source_pointsets']:
 raw=subprocess.check_output(['git','-C','.worldatlas-checkout','show','0635e6d935f6953005e87a2b1290ddacbe55f337:'+q['source_file']]);decoded=gzip.decompress(raw)
 assert len(raw)==q['bytes'] and hashlib.sha256(raw).hexdigest()==q['sha256'] and len(decoded)==q['uncompressed_bytes'] and hashlib.sha256(decoded).hexdigest()==q['uncompressed_sha256']
 source=json.loads(decoded)['source'];sources.append({k:v for k,v in source.items()if k not in ['polygon_geometry','complete_pointset_coordinates_when_no_polygon_object']});pins.append(q)
(r/'BRN-original-query-metadata.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
pre=json.load(open('.cache/runtime-integration-sea318-source30-20261010/current-selected-complete-target-preimages.json'));target=row['original_administrative_comparison']['record']['uniquely_covering_compatible_recorded_subject']['id'];t=next(x for x in pre if x['target_id']==target)
import base64
binding={'target_id':target}
for kind in ['feature','geometry']:
 raw=t['canonical_'+kind+'_utf8'].encode();binding[kind+'_sha256']=hashlib.sha256(raw).hexdigest();binding[kind+'_bytes_base64']=base64.b64encode(raw).decode()
(r/'BRN-target-canonical-bindings.json').write_text(json.dumps([binding],indent=2)+'\n');(r/'BRN-complete-current-target.json').write_text(json.dumps(t['feature'],ensure_ascii=False,indent=2)+'\n')
print(json.dumps({n:{'bytes':(r/n).stat().st_size,'sha256':hashlib.sha256((r/n).read_bytes()).hexdigest()}for n in ['caller-proposed318.mjs','sea318-caller.patch','BRN-original-query-metadata.json','BRN-target-canonical-bindings.json']}))
