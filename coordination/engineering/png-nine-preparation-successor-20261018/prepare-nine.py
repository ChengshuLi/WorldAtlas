"""Package-specific PNG preparation proposal. Never invokes an authority producer.
Usage: python prepare-nine.py READ_ONLY_REPO FRESH_OUTPUT
All historical evidence is immutable; only nine coverage/patch keys are proposed.
"""
import collections, copy, gzip, hashlib, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
SIZE = 262166
OWNER = 35458
TARGET = 'gb:PNG:ADM3:22992897B15196249368430'
COMPONENT = 'physical-component:bd9a49aa576d16c7ceac2ac5e3668d5e9627e2a88b99af69bd4ace2b3348a95e'
KEYS = ((239881,138071,35458),(239882,138070,35458),(239882,138071,35458),
        (239883,138070,35458),(239883,138071,35458),(239883,138072,35458),
        (239884,138071,35458),(239884,138072,35458),(239885,138072,35458))
CONTACTS = {'gb:PNG:ADM1:602756B63375710548767', 'gb:PNG:ADM2:67681753B98961984818312', TARGET}
MANIFEST_SHA = '056abd27574f630c18aa0a66ca0b247b5dd782bf2e020c46a902c35aaea9cd7f'
REVIEW_SHA = '3d0477a7572df3e01beac22764d5bb95e247f8d298c904570e9c98708cf88ae0'

def require(ok, message):
    if not ok: raise ValueError(message)

def digest(b): return hashlib.sha256(b).hexdigest()
def encode(x): return (json.dumps(x, ensure_ascii=False, separators=(',', ':'))+'\n').encode()

def load(repo):
    manifest = HERE.joinpath('input-pins.json').read_bytes()
    require(digest(manifest) == MANIFEST_SHA, 'changed input manifest')
    review = HERE.joinpath('independent-correction-review.json').read_bytes()
    require(digest(review) == REVIEW_SHA, 'missing or changed independent correction review')
    pins = json.loads(manifest); data = {}; raw = {}
    env = {**os.environ, 'GIT_NO_LAZY_FETCH':'1', 'GIT_NO_REPLACE_OBJECTS':'1'}
    command = ['git', '--no-lazy-fetch', '-c', 'protocol.allow=never', '-C', str(repo)]
    for name, pin in pins.items():
        entry = subprocess.check_output(command+['ls-tree','-z',pin['commit'],'--',pin['path']], env=env)
        expected = f"100644 blob {pin['git_blob_oid']}\t{pin['path']}\0".encode()
        require(entry == expected, 'immutable tree mismatch: '+name)
        b = subprocess.check_output(command+['cat-file','blob',pin['git_blob_oid']], env=env)
        require(len(b)==pin['bytes'] and digest(b)==pin['sha256'], 'body custody mismatch: '+name)
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin['git_blob_oid'], 'blob identity')
        raw[name]=b
        decoded = gzip.decompress(b) if pin['path'].endswith('.gz') else b
        if 'decoded_sha256' in pin:
            require(digest(decoded)==pin['decoded_sha256'] and len(decoded)==pin['decoded_bytes'], 'decoded custody')
        data[name]=json.loads(decoded)
    return data, raw, pins

def unpack(rows, values=False):
    out={}
    for row in rows:
        y=row['y']; require(type(y) is int and 0<=y<SIZE, 'row')
        for run in row['runs']:
            require(len(run)==(4 if values else 3), 'run shape')
            a,z,o=run[:3]
            require(all(type(n) is int for n in (a,z,o)) and 0<=a<z<=SIZE, 'run bounds')
            for x in range(a,z):
                k=(x,y,o); require(k not in out, 'duplicate key');out[k]=run[3] if values else 'land'
    return out

def pack(data, values=False):
    rows=collections.defaultdict(list)
    for (x,y,o),v in sorted(data.items(), key=lambda item:(item[0][1],item[0][0],item[0][2])):
        run=[x,x+1,o]+([v] if values else [])
        if rows[y] and rows[y][-1][1]==x and rows[y][-1][2:]==run[2:]: rows[y][-1][1]=x+1
        else: rows[y].append(run)
    return [{'y':y,'runs':runs} for y,runs in sorted(rows.items())]

def coverage(t):
    return unpack([{'y':r['y'],'runs':[[a,z,t['pixelIndex'],kind] for a,z,kind in r['runs']]} for r in t['coverage_rows']], True)

def project(d):
    """Called only after exact immutable input admission. Public CLI has no overrides."""
    original={}; contacts={}; roster={r['source_index']:r for r in d['original-roster']}
    intervals=0
    for number in (32,33,34):
        for y,a,z,owners,sids,kind in d[f'frozen-queue/block-{number:03}.json.gz']:
            require(len(owners)==1, 'original owner cardinality');intervals+=1
            for x in range(a,z):
                k=(x,y,owners[0]);require(k not in original, 'original duplicate');original[k]=kind
                if k in KEYS: contacts[k]={roster[i]['source_id'] for i in sids}
    require(len(original)==56552 and intervals==20060 and set(original.values())=={'land'}, 'original scope')
    require(all(original.get(k)=='land' and contacts.get(k)==CONTACTS for k in KEYS), 'original key/class/contact')
    supported=unpack(d['previous/native-patch.json']['rows']); held=unpack(d['previous/held-original.json']['rows'], True)
    require(len(supported)==56476 and len(held)==76 and not supported.keys() & held.keys() and supported.keys()|held.keys()==original.keys(), 'previous partition')
    prior=d['previous/prior-source-fitness-holds.json']
    components=[c for c in prior['components'] if c['component_id']==COMPONENT]
    require(len(components)==1 and sorted(map(tuple,components[0]['original_keys']))==list(KEYS), 'exact prior component keys')
    require(all(held.get(k)=='unresolved_prior_source_fitness' for k in KEYS), 'prior hold reason')
    require(set(map(tuple,prior['original_keys']))=={k for k,v in held.items() if v=='unresolved_prior_source_fitness'}, 'complete prior holds')
    diag=d['native-diagnostic-001/native-diagnostic.json']; native=unpack(diag['supported_rows']); nativeheld=unpack(diag['held_rows'])
    assigned={k for k,v in unpack(diag['decision_rows'],True).items() if v=='assigned_cells'}
    require(unpack(diag['requested_rows']).keys()==original.keys(), 'diagnostic original scope')
    require(all(k in native and k in assigned and k not in nativeheld for k in KEYS), 'native support/territorial hold')
    proof=d['proof/exact-native-centres-result.json']; controls=d['proof/exact-native-controls-result.json']
    require(proof['size']==SIZE and proof['longitude_rule']=='(360*x+180-180*size)/size, exact rational', 'coordinate contract')
    require([tuple(r['key_x_y_owner']) for r in proof['rows']]==list(KEYS), 'proof key roster')
    expected={'candidate':'inside','mapped_land_support':'inside','missing_reconstruction':'outside','outside_mapped_L1_context':'outside','source_union_intersection':'inside','component_minus_source_union':'outside'}
    require(all(r['states']==expected and len(r['extra_residue_separations'])==2 for r in proof['rows']), 'reviewed point predicates')
    require(controls['adverse_refusals']==11 and controls['whole_multipart_refusal_retained'], 'reviewed negative controls')
    oldsource=d['previous/source-evidence.json']; compact=d['compaction-001/source-evidence.json']
    oldtargets=[t for t in oldsource['targets'] if t['pixelIndex']==OWNER]; targets=[t for t in compact['targets'] if t['pixelIndex']==OWNER]
    require(len(oldtargets)==len(targets)==1 and oldtargets[0]['id']==targets[0]['id']==TARGET, 'direct target')
    oldtarget=oldtargets[0]; target=targets[0]
    require({k:v for k,v in oldtarget.items() if k!='coverage_rows'}=={k:v for k,v in target.items() if k!='coverage_rows'}, 'unchanged complete source operands')
    require(all(coverage(target).get(k)=='mapped_land_support' for k in KEYS), 'current physical coverage')
    require(not target['territorial_exclusions'], 'target territorial operands')
    physical=[r for r in d['physical']['results'] if r['target']==TARGET]
    require(len(physical)==1 and physical[0]['issues']==[], 'current physical issues')
    require(target['source_receipt_sha256']==d['_physical_sha'], 'physical receipt binding')
    for t in oldsource['targets']:
        require(coverage(t)=={k:'mapped_land_support' for k in supported if k[2]==t['pixelIndex']}, 'previous coverage partition')
    after_supported={**supported, **{k:'land' for k in KEYS}}; after_held={k:v for k,v in held.items() if k not in KEYS}
    require(len(after_supported)==56485 and len(after_held)==67 and after_supported.keys()|after_held.keys()==original.keys(), 'successor conservation')
    result_source=copy.deepcopy(oldsource)
    for t in result_source['targets']:
        if t['pixelIndex']==OWNER:
            c={**coverage(oldtarget),**{k:'mapped_land_support' for k in KEYS}}
            t['coverage_rows']=[{'y':r['y'],'runs':[[a,z,v] for a,z,o,v in r['runs']]} for r in pack(c,True)]
    summary=copy.deepcopy(d['previous/original-scope-partition.json'])
    summary.update(supported_cells=56485,held_cells=67,held_reason_counts=dict(collections.Counter(after_held.values())),prior_source_fitness_held_cells=49,
        historical_prior_source_fitness_held_cells=58, proposed_only=True, native_authority_executed=False,
        historical_whole_component_status='unknown', numerical_scope='exact nine current native centres only')
    for row in summary['owner_counts']:
        if row['owner']==OWNER: row['supported_cells']+=9;row['held_cells']-=9
    products={'source-evidence.json':result_source,'native-patch.json':{'rows':pack(after_supported)},'held-original.json':{'rows':pack(after_held,True)},'original-scope-partition.json':summary}
    receipt={'original_cells':56552,'previous_supported':56476,'proposed_supported':56485,'remaining_held':67,'proposed_added_keys':list(KEYS),
        'old_supported_preserved':all(after_supported[k]==v for k,v in supported.items()),'other_held_preserved':after_held=={k:v for k,v in held.items() if k not in KEYS},
        'complete_original_contacts_preserved':True,'source_changes_only_nine_coverage_keys':True,'authority_executed':False,'acceptance_credit':0}
    return products, receipt

def main():
    require(len(sys.argv)==3, __doc__); repo=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]).absolute()
    require(out.parent.is_dir() and not out.exists() and all(not p.is_symlink() for p in (out,*out.parents)), 'fresh safe output')
    d,raw,pins=load(repo);d['_physical_sha']=pins['physical']['sha256']
    # Completed preparation binds its product bytes; all historical dependency pins remain in the summary.
    prep=d['previous/preparation.json']
    for name,pin in prep['outputs'].items():
        require(len(raw['previous/'+name])==pin['bytes'] and digest(raw['previous/'+name])==pin['sha256'], 'historical completed preparation')
    products,receipt=project(d)
    products['successor-rejoin.json']=receipt
    products['preparation.json']={'complete':True,'proposal_only':True,'inputs':pins,'independent_correction_review_sha256':REVIEW_SHA,
       'outputs':{n:{'bytes':len(encode(v)),'sha256':digest(encode(v))} for n,v in products.items()},'authority_execution':'requires distinct review and new stock constructor'}
    out.mkdir()
    for name,value in products.items():
        with (out/name).open('xb') as f:f.write(encode(value))
    print(json.dumps(receipt))

if __name__=='__main__': main()
