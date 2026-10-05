#!/usr/bin/env python3
"""Reproduce the licensed Georef department roster crosswalk for exact #442 IDs."""
import argparse, hashlib, json, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_SHA256 = '31afdfe5983b6d7648eba1eafc7a5a8fe3c591abdca4b17c311c08c75d361e92'
EXPECTED_SCOPE_SHA256 = '63f3030ff6c3903e9578994651bf1a316c689d2568d263ed4813dd7171423ee6'
PARENT_CODES = {
 'framework:province:buenos-aires:df466c06286c':'06', 'framework:province:cordoba:beae6ba6b36e':'14',
 'framework:province:chaco:87e685fd273c':'22', 'framework:province:formosa:6ec8d4a4a329':'34',
 'framework:province:la-pampa:d10ea068ae3a':'42', 'framework:province:santa-fe:1f6b7cf8fad3':'82'}
ALIASES = {'ezeiza': {'josemezeiza'}, 'coroneldemarinalrosales': {'coroneldemarinaleonardorosales'},
 'bolivar': {'sancarlosdebolivar'}, 'constitucion': {'villaconstitucion'}}

def norm(s):
 s=unicodedata.normalize('NFKD',s or '')
 s=''.join(c for c in s if not unicodedata.combining(c)).casefold()
 s=re.sub(r'^(departamento|departamentos|partido|partidos|dpto\.?|depto\.?)\s+','',s)
 return ''.join(c for c in s if c.isalnum())
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,default=Path(__file__).with_name('departamentos.geojson'))
 ap.add_argument('--comparisons',type=Path,default=Path(__file__).parents[2]/'geometry-comparisons.jsonl')
 ap.add_argument('--output',type=Path,default=Path(__file__).with_name('georef-crosswalk.jsonl'))
 ap.add_argument('--summary',type=Path,default=Path(__file__).with_name('georef-crosswalk-summary.json'))
 a=ap.parse_args()
 digest=sha(a.source)
 if digest != EXPECTED_SHA256: raise SystemExit(f'Unexpected source SHA256 {digest}')
 fc=json.loads(a.source.read_text(encoding='utf-8'))
 feats=fc.get('features',[])
 byname=defaultdict(list)
 for f in feats:
  p=f['properties']; byname[norm(p.get('nombre',''))].append(p)
 byalias=defaultdict(set)
 for k,vals in ALIASES.items():
  for v in vals: byalias[k].add(v); byalias[v].add(k)
 rows=[]
 for line in a.comparisons.read_text(encoding='utf-8').splitlines():
  old=json.loads(line); key=norm(old['baseline_name']); keys={key}|byalias.get(key,set())
  matches={p['id']:p for k in keys for p in byname.get(k,[])}
  matches=list(matches.values()); expected=PARENT_CODES[old['parent_id']]
  same=[p for p in matches if str((p.get('provincia') or {}).get('id',''))==expected]
  if len(same)==1: status='unique-name-and-expected-province'
  elif len(same)>1: status='ambiguous-within-expected-province'
  elif len(matches)==1: status='unique-name-other-province'
  elif matches: status='ambiguous-name-no-expected-province-match'
  else: status='no-normalized-name-or-explicit-alias-match'
  rows.append({'id':old['id'],'baseline_name':old['baseline_name'],'frozen_parent_id':old['parent_id'],
   'expected_indec_province_code':expected,'candidate_status':status,'candidate_count':len(matches),
   'expected_province_candidate_count':len(same),
   'candidates':[{'indec_department_code':p.get('id'),'name':p.get('nombre'),'official_name':p.get('nombre_completo'),
     'indec_province_code':(p.get('provincia') or {}).get('id'),'province_name':(p.get('provincia') or {}).get('nombre'),
     'source':p.get('fuente'),'category':p.get('categoria')} for p in sorted(matches,key=lambda x:(str((x.get('provincia') or {}).get('id')),str(x.get('id'))))],
   'prior_assessment_classification':old['assessment_classification'],
   'interpretation_limit':'Georef/IGN identity and administrative-parent cross-check only. No geometry adjudication, legal boundary finding, roster-completeness conclusion, or change to prior classification.'})
 if len(rows)!=241 or len({r['id'] for r in rows})!=241: raise SystemExit('Scope does not contain 241 unique IDs')
 scopehash=hashlib.sha256('\n'.join(r['id'] for r in rows).encode()).hexdigest()
 if scopehash!=EXPECTED_SCOPE_SHA256: raise SystemExit(f'Unexpected scope hash {scopehash}')
 with a.output.open('w',encoding='utf-8') as f:
  for r in rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
 summary={'source_sha256':digest,'source_bytes':a.source.stat().st_size,'source_feature_count':len(feats),
  'source_unique_ids':len({f.get('properties',{}).get('id') for f in feats}),
  'scope_count':len(rows),'scope_ids_sha256':scopehash,
  'candidate_status_counts':dict(sorted(Counter(r['candidate_status'] for r in rows).items())),
  'prior_assessment_counts':dict(sorted(Counter(r['prior_assessment_classification'] for r in rows).items())),
  'rows_with_unique_expected_province_candidate':sum(r['expected_province_candidate_count']==1 for r in rows),
  'rows_with_no_candidate':sum(r['candidate_count']==0 for r in rows),
  'limitations':['The service describes periodic updates but does not publish a precise data vintage for this response.',
   'Georef documents IGN as the geometry origin for departments; this is not an independent legal-boundary source.',
   'A department feature matching name and parent code does not establish inclusion of every offshore/island component, feature completeness, legal limit, or suitability for release.',
   'This is a names/codes/parent crosswalk; prior geographic classifications are copied verbatim and not upgraded.']}
 a.summary.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
