"""Strict dry-run comparison, not sufficient to authorize mixed-land reuse."""
import copy,hashlib,json
from decimal import Decimal
WATER_KINDS={'coastline_assignment','closed_water_assignment'}
REVISION_LISTS=('affiliations','list1_entries','list1_entry_evidence_sources','ecoregion_source_refs','polygon_corroboration_refs')

def _unique_pairs(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
def _number(value):
 result=Decimal(value)
 if not result.is_finite():raise ValueError('nonfinite JSON number')
 return result
def _constant(value):raise ValueError('nonfinite JSON number')

def checked_snapshot(raw,expected):
 if not isinstance(raw,bytes) or len(raw)>16*1024*1024 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('snapshot byte pin mismatch or cap exceeded')
 doc=json.loads(raw,object_pairs_hook=_unique_pairs,parse_float=_number,parse_constant=_constant)
 if not isinstance(doc,dict) or doc.get('source')!='neon-export' or doc.get('schema') not in {'worldatlas-geography-decision-draft-evidence-v1','worldatlas-geography-decision-draft-evidence-v3'}:raise ValueError('expected draft Neon export')
 r=doc.get('decision_revision',{});e=doc.get('entity_revision',{})
 if not isinstance(r.get('id'),str) or not r['id'] or r.get('status')!='draft' or e.get('status')!='draft' or not isinstance(e.get('id'),str) or not e['id'] or r.get('entity_revision')!=e['id']:raise ValueError('bad draft revision or entity identity')
 return doc

def land_projection(doc):
 d=copy.deepcopy(doc);rev=d['decision_revision'];rid=rev['id'];rev['id']='__REVISION__';rev.pop('evidence',None)
 policies=d.get('policies')
 if not isinstance(policies,list) or any(not isinstance(p,dict) for p in policies):raise ValueError('invalid policies list')
 d['policies']=[p for p in policies if p.get('kind') not in WATER_KINDS]
 for name in REVISION_LISTS:
  items=d.get(name,[])
  if not isinstance(items,list):raise ValueError('invalid revision-bound list')
  for record in items:
   if not isinstance(record,dict) or record.get('decision_revision')!=rid:raise ValueError('invalid record revision')
   record['decision_revision']='__REVISION__'
 p=d.get('list1_policy')
 if p is not None:
  if not isinstance(p,dict) or p.get('decision_revision')!=rid:raise ValueError('invalid list1 policy revision')
  p['decision_revision']='__REVISION__'
 return d

def _exact_equal(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(_exact_equal(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(_exact_equal(x,y) for x,y in zip(a,b))
 return a==b

def compare(raw_land,land_sha,raw_water,water_sha):
 land=checked_snapshot(raw_land,land_sha);water=checked_snapshot(raw_water,water_sha)
 if land['decision_revision']['id']==water['decision_revision']['id']:raise ValueError('expected distinct revisions')
 old=[p for p in land['policies'] if p.get('kind') in WATER_KINDS];new=[p for p in water['policies'] if p.get('kind') in WATER_KINDS]
 if old or len(new)!=2 or {x.get('kind') for x in new}!=WATER_KINDS:raise ValueError('expected exactly two new water policy records')
 if not _exact_equal(land_projection(land),land_projection(water)):raise ValueError('land-relevant snapshot content changed')
 return {'status':'projection-match-only-not-lineage-authorization','land_snapshot_sha256':land_sha,'water_snapshot_sha256':water_sha,'land_revision':land['decision_revision']['id'],'water_revision':water['decision_revision']['id'],'limitations':['This checks content equivalence only; it does not authenticate Neon, the land build, input source bytes, or report/monitor/trace lineage.','Revision evidence is excluded; this diagnostic does not establish equivalence for consumers that inspect it. All other non-water snapshot content is compared exactly.']}
