"""Shared effective reference-policy lookup for Python global-review consumers."""
import copy,gzip,json,pathlib

def effective_source_policies(base,bundle):
 if not isinstance(base,dict)or not isinstance(base.get('countries'),dict)or bundle.get('version')!=1 or not isinstance(bundle.get('policy_corrections'),list):raise ValueError('Invalid source-policy correction bundle')
 result=copy.deepcopy(base);seen=set()
 for correction in bundle['policy_corrections']:
  iso=correction.get('profile_iso')
  if not iso or iso in seen or not correction.get('id'):raise ValueError('Duplicate or missing source-policy correction identity')
  seen.add(iso);retained=correction.get('before_policy');after=correction.get('after_policy')
  if not isinstance(retained,dict)or not isinstance(after,dict)or not isinstance(after.get('role'),str)or not after['role'].strip()or not isinstance(after.get('effective_level'),str)or not after['effective_level'].strip():raise ValueError('Corrected source policy requires a role and effective level')
  current=result['countries'].get(iso);without={key:value for key,value in current.items()if key!='source_policy_correction'}if isinstance(current,dict)else None
  if without!=retained and without!=after:raise ValueError('Source policy changed since correction: '+iso)
  result['countries'][iso]=copy.deepcopy(after);result['countries'][iso]['source_policy_correction']={'id':correction['id'],'bundle_id':bundle['id'],'status':'source-role-corrected-semantic-open','evidence_ids':list(correction['evidence_ids']),'local_granularity_approved':False}
 return result

def load_effective_source_policies(root=None):
 root=pathlib.Path(root)if root is not None else pathlib.Path(__file__).resolve().parents[1]
 base=json.loads((root/'data/location-policy.json').read_bytes());bundle=json.loads(gzip.decompress((root/'data/source-policy-corrections/europe-v1.json.gz').read_bytes()));return effective_source_policies(base,bundle)
