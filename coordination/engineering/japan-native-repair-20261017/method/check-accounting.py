"""Compare complete original interval, diagnostic, patch and constructor cell/owner sets.
Usage: python check-accounting.py READ_ONLY_REPO AUTHORITY_COMMIT FRESH_OUTPUT
"""
import pathlib,subprocess,json,gzip,hashlib,collections,sys
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();assert len(sys.argv)==4 and len(H)==40 and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));P='coordination/engineering/japan-native-repair-20261017';sha=lambda b:hashlib.sha256(b).hexdigest()
def raw(p,c=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',c+':'+p])
def pin(p,c=H):
 b=raw(p,c);d={'path':p,'commit':c,'mode':'100644','git_blob_oid':subprocess.check_output(['git','-C',str(W),'rev-parse',c+':'+p],text=True).strip(),'bytes':len(b),'sha256':sha(b)}
 if p.endswith('.gz'):b=gzip.decompress(b);d.update(decoded_bytes=len(b),decoded_sha256=sha(b))
 return d
js=lambda p:json.loads(raw(p))
frozen=[]
for b in range(22,28):frozen+=json.loads(gzip.decompress(raw(P+f'/frozen-queue/block-{b:03}.json.gz')))
original={(x,y,o[0]) for y,a,z,o,s,c in frozen for x in range(a,z)};assert len(original)==106333 and sum(z-a for y,a,z,*_ in frozen)==106333 and len(frozen)==36063
patch=js(P+'/source-stage/native-patch.json');pk={(x,r['y'],o) for r in patch['rows'] for a,z,o in r['runs'] for x in range(a,z)};diag=js(P+'/native-diagnostic-001/native-diagnostic.json');dk={(x,r['y'],o) for r in diag['supported_rows'] for a,z,o in r['runs'] for x in range(a,z)};assert pk==dk==original and not diag['held_rows'] and diag['held_cells']==0
con=js(P+'/native-authority-001/constructor-result.json');rows=con['ledger_rows'];assert len(rows)==556 and len({r['target_id'] for r in rows})==556 and all(r['disposition']=='assigned' for r in rows);ak={(x,r['y'],o) for t in rows for r in t['native_rows'] for a,z,o in r['runs'] for x in range(a,z)};assert ak==original and sum(t['native_cells'] for t in rows)==106333
scope=js(P+'/source-stage/source-scope-assessment.json');byowner={r['pixelIndex']:r for r in scope['target_checks']};count=collections.Counter(o for x,y,o in original);assert all(count[o]==s['candidate_cells'] for o,s in byowner.items());assert count[22]==431 and count[24492]==30;assert {t['target_id'] for t in rows}=={s['id'] for s in byowner.values()}
historical=js(P+'/historical-001/historical-applicability.json');assert all((c['x'],c['y'],c['owner']) in ak for r in historical['overlap'] for c in r['cells'])
result={'original_cells':106333,'original_intervals':36063,'original_owners':556,'supported_cells':106333,'held_cells':0,'supported_owners':556,'wholly_held_owners':0,'source_members':608,'tokyo_member_count':53,'tokyo_cells':431,'fudai_cells':30,'complete_source_features':1789,'separate_physical_companion_cells':21791,'separate_physical_companion_owners':540,'prior_historical_overlap_cells':9,'exact_original_patch_diagnostic_constructor_keys_equal':True,'owner_counts':[{'owner':i,'id':byowner[i]['id'],'original_cells':count[i],'supported_cells':count[i],'held_cells':0} for i in sorted(count)],'inputs':[pin(P+'/source-stage/native-patch.json'),pin(P+'/native-diagnostic-001/native-diagnostic.json'),pin(P+'/native-authority-001/constructor-result.json')],'limits':['This compares authentic original/diagnostic/constructor cell sets and owners; it is not current selected owner-zero, final emitted consumption, legal jurisdiction or current dry-land approval.','All source dates, licences, old whole-candidate unknowns and the separate physical companion remain unchanged.']}
assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir();b=(json.dumps(result,separators=(',',':'))+'\n').encode();(O/'original-scope-disposition.json').write_bytes(b);(O/'preparation.json').write_text(json.dumps({'complete':True,'bytes':len(b),'sha256':sha(b)})+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['owner_counts','inputs','limits']},indent=2))
