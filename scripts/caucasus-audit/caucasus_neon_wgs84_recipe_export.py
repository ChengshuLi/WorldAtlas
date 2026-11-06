"""Canonicalize the selected Caucasus WGS84 recipe from Neon jsonb text."""
import argparse,hashlib,json
from pathlib import Path

def unique(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError('duplicate JSON key')
  out[k]=v
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--recipe-text',required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args();value=json.loads(Path(a.recipe_text).read_text(),object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite number')))
 if not isinstance(value,dict) or value.get('schema')!='caucasus-approved-wgs84-recipe-v2':raise ValueError('wrong recipe schema')
 raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
 if hashlib.sha256(raw).hexdigest()!=a.sha256:raise ValueError('Neon recipe hash mismatch')
 with open(a.output,'xb') as f:f.write(raw)
 print('recipe_sha256',a.sha256,'bytes',len(raw))
if __name__=='__main__':main()
