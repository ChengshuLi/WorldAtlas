"""Retain complete unresolved physical evidence; withhold its two positive owners.
Usage: python hold-unsupported-physical.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
This does not narrow or edit the physical product or original denominator.
"""
import json,pathlib,subprocess,hashlib,sys,collections,os
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/usa-repair-delivery-20261017';assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));pins=[]
def read(p):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',C+':'+p],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'},timeout=30);pins.append({'commit':C,'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
js=lambda p:json.loads(read(p))
assert read(P+'/probes/hold-unsupported-physical.py')==pathlib.Path(__file__).read_bytes()
x=js(P+'/native-config-001/source-evidence-config.json');patch=js(P+'/native-config-001/native-requested-patch.json');physical=js(P+'/physical-001/whole-target-support.json');owners={45121:'gb:USA:ADM2:52423323B29513042802619',46976:'gb:USA:ADM2:52423323B80760419757691'}
for owner,sid in owners.items():
 r=next(r for r in physical['results']if r['target']==sid);assert {'source':2380,'reason':['invalid-original-source-polygon']}in r['issues']
selected=x['source_evidence']['targets'];removed=[t for t in selected if t['pixelIndex']in owners];assert {t['id']for t in removed}==set(owners.values())and len(removed)==2
x['source_evidence']['targets']=[t for t in selected if t['pixelIndex']not in owners]
rows=[];held=[]
for r in patch['rows']:
 runs=[]
 for a,z,o in r['runs']:
  if o in owners:
   for xx in range(a,z):held.append({'y':r['y'],'x':xx,'owner_index':o,'reason':'whole-owner physical admission unresolved: original GSHHG source2380 invalid polygon'})
  else:runs.append([a,z,o])
 if runs:rows.append({'y':r['y'],'runs':runs})
assert len(held)==604 and collections.Counter(r['owner_index']for r in held)=={45121:55,46976:549}
assert sum(z-a for r in rows for a,z,o in r['runs'])==105990 and len({o for r in rows for a,z,o in r['runs']})==348
report={'kind':'conservative-whole-owner-physical-admission-hold','held_keys':held,'held_cells':604,'held_owners':2,'source_record':2380,'complete_physical_output_unchanged':x['source_evidence']['physical_evidence'],'preserved_physical_input':x['source_evidence']['physical_input'],'original_keys':107131,'requested_cells':105990,'requested_owners':348,'source_only_preholds':537,'foreign_original_keys_still_requested':63,'potential_source_physical_ceiling':105927,'inputs':pins,'limits':['Whole-owner hold is conservative because the admitted constructor cannot interpret this retained invalid-source issue; it is not proof all604 original keys are physically wrong.','No original source, physical record, negative family or accepted target geometry is edited. Other-owner target records and all coverage remain literal.','The first failed diagnostic is retained separately. This scoped continuation does not replay source or physical producers.']}
products={'source-evidence-config.json':x,'native-requested-patch.json':{'rows':rows},'physical-admission-holds.json':report};encoded={n:(json.dumps(v,separators=(',',':'))+'\n').encode()for n,v in products.items()};assert sum(map(len,encoded.values()))<16*1024*1024 and not O.exists();O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'outputs':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in encoded.items()},'held':604,'requested':105990}))
