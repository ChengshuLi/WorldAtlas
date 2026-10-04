#!/usr/bin/env python3
"""Fast integrity and negative-control checks for issue #476 outputs."""
import ast, csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(name):
    with (ROOT/name).open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def require(ok, message):
    if not ok: raise SystemExit('FAIL: '+message)

scope=json.loads((ROOT/'issue-scope-pinned.json').read_text())
ids=scope['member_location_ids']
require(len(ids)==227 and len(set(ids))==227,'issue roster must contain 227 unique subjects')
assessment=rows('assessment.csv')
require(len(assessment)==227 and {r['id'] for r in assessment}==set(ids),'assessment roster differs from exact issue roster')
require(all(r['assessment_status']=='insufficient-evidence' for r in assessment),'unsupported correction or approval status')
require(sum(r['parent_assignment_assessment']=='supported' for r in assessment)==220,'parent supported count changed')
unresolved=[r for r in assessment if r['parent_assignment_assessment']=='insufficient-evidence']
require(len(unresolved)==7,'expected six FCT label variances and one duplicate-name ambiguity')
fct=[r for r in unresolved if r['baseline_parent_label']=='abuja federal capital territory']
require(len(fct)==6 and all('label variance' in r['parent_assignment_reason'] for r in fct),'FCT nomenclature cases are not explicitly unresolved')
bassa=[r for r in unresolved if r['name']=='Bassa']
require(len(bassa)==1 and set(ast.literal_eval(bassa[0]['current_candidate_codes']))=={'NG023004','NG032002'},'Bassa alternatives were lost or selected')
partition=rows('area-partition-inventory.csv')
require(len(partition)==774 and len({r['location_id'] for r in partition})==774,'full Nigeria assignment partition incomplete or duplicated')
require({r['location_id'] for r in partition if r['in_issue_476_scope']=='True'}==set(ids),'assigned partition differs from issue')
require(len(rows('administrative-scope.csv'))==13,'area plus 12 province scope rows expected')
followups=json.loads((ROOT/'followup-issues.json').read_text())
require(set(followups)=={'761','762','763','764'},'four bounded follow-up IDs required')
require(set(followups['761'])==set(ids) and set(followups['762'])==set(ids),'land and settlement follow-ups must cover exact parent roster')
require(set(followups['763'])=={r['id'] for r in unresolved},'parent follow-up must cover seven exact unresolved subjects')
require(len(followups['764'])==1 and followups['764'][0]=='gb:NGA:ADM2:59680162B82021418174103','point follow-up must cover exact Kwali subject')
for row in rows('administrative-scope.csv'):
    linked={str(x) for x in json.loads(row['related_followup_issue_ids'])}
    expected={'761','762'} | ({'763'} if set(json.loads(row['owned_subject_ids'])) & set(followups['763']) else set()) | ({'764'} if set(json.loads(row['owned_subject_ids'])) & set(followups['764']) else set())
    if row['scope_level']=='area': expected={'761','762','763','764'}
    require(linked==expected,f"follow-up links mismatch in {row['scope_level']} {row['name']}")
anomalies=rows('settlement-point-anomalies.csv')
require(len(anomalies)==1 and anomalies[0]['point_object_id']=='143477','settlement point anomaly inventory changed')
neighbor=rows('neighbor-edge-screen.csv')
require({r['neighbor'] for r in neighbor}=={'Benin','Niger','Chad','Cameroon'},'four assigned neighbor screens are incomplete')
account=json.loads((ROOT/'generated-data-accounting.json').read_text())
for entry in account['outputs']:
    p=ROOT/entry['path']
    require(p.is_file() and digest(p)==entry['sha256'] and p.stat().st_size==entry['bytes'],f"generated accounting mismatch: {entry['path']}")
    require(sum(1 for _ in p.open(encoding='utf-8'))-1==entry['rows_excluding_header'],f"row accounting mismatch: {entry['path']}")
# Negative controls: duplicated roster and a mutated output hash must fail equivalent predicates.
duplicate_roster=ids+[ids[0]]
require(not (len(duplicate_roster)==len(set(duplicate_roster))),'duplicate-subject negative control did not fail')
expected=next(x['sha256'] for x in account['outputs'] if x['path']=='assessment.csv')
require(digest(ROOT/'assessment.csv')!=hashlib.sha256((ROOT/'assessment.csv').read_bytes()+b' mutation').hexdigest(),'mutated-hash negative control did not fail')
require(digest(ROOT/'assessment.csv')==expected,'assessment hash differs from generated ledger')
print(json.dumps({'status':'verified','subjects':len(assessment),'parent_supported':220,'parent_unresolved':7,
                  'province_and_area_scopes':13,'neighbor_edges':len(neighbor),'outputs_hash_checked':len(account['outputs']),
                  'negative_controls':'duplicate subject and altered hash predicates reject'},indent=2))
