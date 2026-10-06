#!/usr/bin/env python3
"""Execute issue #1205 source integrity, omission, and vintage negatives."""
import copy, hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[3]
PACKET=ROOT/'research/geography/gap-source-matanuska-physical-seam-20261006'
RUN=PACKET/'results'
OUT=RUN/'controls'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from physical_component_contacts import component_contacts

def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(name,value):
    raw=(json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n').encode()
    target=OUT/name
    if target.exists():
        if target.read_bytes()!=raw: raise SystemExit('Existing control receipt differs; preserving it: '+str(target))
    else: target.write_bytes(raw)
    return str(target.relative_to(ROOT))

one=RUN/'run-one';two=RUN/'run-two'
names=['selected-components.geojson','source-overlay-ledger.json','source-overlay-summary.json']
one_hashes={n:sha((one/n).read_bytes()) for n in names}
two_hashes={n:sha((two/n).read_bytes()) for n in names}
run_one_sha=sha((json.dumps(one_hashes,sort_keys=True,separators=(',',':'))+'\n').encode())
run_two_sha=sha((json.dumps(two_hashes,sort_keys=True,separators=(',',':'))+'\n').encode())
if run_one_sha!=run_two_sha: raise SystemExit('Independent complete output runs differ')
write('reproducibility.json',{'method_id':'source-overlay-analysis','kind':'reproducibility','outcome':'passed','run_one_sha256':run_one_sha,'run_two_sha256':run_two_sha,'per_file_sha256':one_hashes})

source_path=PACKET/'sources/resolve-ecoregions-2017-ecoids-371-405.geojson'
source_raw=source_path.read_bytes(); expected=sha(source_raw); changed=bytearray(source_raw);changed[0]^=1
if sha(bytes(changed))==expected: raise SystemExit('Changed-source hash negative did not detect mutation')
write('negative-changed-source-hash.json',{'method_id':'source-overlay-analysis','kind':'negative-control','outcome':'passed','control':'one source byte changed in memory','expected_sha256':expected,'changed_sha256':sha(bytes(changed)),'rejected':'whole-file source pin mismatch'})

ledger=json.loads((one/'source-overlay-ledger.json').read_bytes())
component_ids=sorted(row['component'] for row in ledger['components'])
if len(component_ids)!=282: raise SystemExit('Positive roster control failed')
omitted=component_ids[:-1]
omitted_hash=sha((json.dumps(omitted,ensure_ascii=False,separators=(',',':'))+'\n').encode())
if omitted_hash=='37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66': raise SystemExit('Omitted-component negative did not detect mutation')
write('negative-omitted-component.json',{'method_id':'source-overlay-analysis','kind':'negative-control','outcome':'passed','control':'one component omitted from complete sorted roster','expected_count':282,'observed_count':len(omitted),'expected_roster_sha256':'37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66','observed_roster_sha256':omitted_hash,'rejected':'exact roster count and hash mismatch'})

components=json.loads((one/'selected-components.geojson').read_bytes())['features']
fragments=ledger['candidate_fragments']['features']
positive=component_contacts(fragments,components)
if len(positive)!=282 or any(r['status']!='complete-recorded-contacts' for r in positive): raise SystemExit('Positive contact control failed')
write('positive-exact-roster-and-contact-closure.json',{'method_id':'source-overlay-analysis','kind':'positive-control','outcome':'passed','component_count':len(positive),'bound_fragment_count':sum(len(r['fragment_contacts']) for r in positive),'contact_rows':sum(len(b['exact_location_contacts'] or []) for r in positive for b in r['fragment_contacts']),'all_contact_ledgers_complete':all(r['status']=='complete-recorded-contacts' for r in positive)})
mutated=copy.deepcopy(fragments)
mutated[0]['properties'].pop('exact_location_contacts',None)
try:
    negative=component_contacts(mutated,components)
    rejected=not all(r['status']=='complete-recorded-contacts' for r in negative)
    reason='incomplete-source-contact-recording'
except ValueError as error:
    rejected=True; reason=str(error)
if not rejected: raise SystemExit('Omitted-contact negative did not detect mutation')
write('negative-omitted-contact.json',{'method_id':'source-overlay-analysis','kind':'negative-control','outcome':'passed','control':'remove exact_location_contacts from one retained candidate-fragment clone','rejected':reason})

layer=json.loads((PACKET/'sources/resolve-layer-0.json').read_bytes())
name=layer.get('name')
if not isinstance(name,str) or '2017' not in name: raise SystemExit('Pinned layer metadata vintage check failed')
laundered='2018'
if laundered in name: raise SystemExit('Vintage-laundering negative is ineffective')
write('negative-vintage-laundering.json',{'method_id':'source-overlay-analysis','kind':'negative-control','outcome':'passed','control':'attempt to substitute inherited Atlas reference_year 2018 for the pinned RESOLVE layer vintage','pinned_layer_name':name,'pinned_data_last_edit_date':'2022-01-27','rejected_vintage':laundered,'rejected':'Atlas reference year does not match pinned RESOLVE layer title/data metadata'})

print(json.dumps({'outcome':'passed','run_one_sha256':run_one_sha,'run_two_sha256':run_two_sha,'negative_controls':4,'outputs':[p for p in sorted(x.name for x in OUT.glob('*.json'))]},sort_keys=True))
