"""Losslessly compact/expand an unselected Caucasus selector recipe.

This packs consecutive source vertices only. Edge interpolations remain
explicit. It does not claim minimal basin selection or historical lineage.
"""
import argparse
import hashlib
import json
import math


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def valid_ref(q):
    ref=q['ref']
    if q['kind']=='vertex':
        if len(ref)!=2 or any(type(x)!=int or x<0 for x in ref):raise ValueError('bad vertex')
    elif q['kind']=='edge':
        if len(ref)!=3 or any(type(x)!=int or x<0 for x in ref[:2]) or not isinstance(ref[2],(float,int)) or not math.isfinite(ref[2]) or not 0<=ref[2]<=1:raise ValueError('bad edge')
    else:raise ValueError('bad kind')


def compact(recipe,original_hash):
    if recipe.get('schema')!='caucasus-selector-research-v1' or recipe.get('status')!='unselected_research':raise ValueError('wrong input')
    src=recipe['hydro_selectors']
    if len(src)!=1893:raise ValueError('wrong selector count')
    for q in src:valid_ref(q)
    output=[];i=0
    while i<len(src):
        q=src[i]
        if q['kind']=='edge':
            output.append({'kind':'edge','ref':q['ref']});i+=1;continue
        shape,start=q['ref'];count=1;step=1
        if i+1<len(src) and src[i+1]['kind']=='vertex' and src[i+1]['ref'][0]==shape:
            delta=src[i+1]['ref'][1]-start
            if abs(delta)==1:
                step=delta
                while i+count<len(src):
                    n=src[i+count]
                    if n['kind']!='vertex' or n['ref'] != [shape,start+count*step]:break
                    count+=1
        output.append({'kind':'vertices','shape':shape,'start':start,'count':count,'step':step})
        i+=count
    header={k:v for k,v in recipe.items() if k!='hydro_selectors'}
    return {'schema':'caucasus-selector-runs-research-v1','original_recipe_sha256':original_hash,'header':header,'hydro_segments':output}


def expand(value):
    if value.get('schema')!='caucasus-selector-runs-research-v1':raise ValueError('wrong compact schema')
    out=[]
    for s in value['hydro_segments']:
        if s['kind']=='edge':
            q={'kind':'edge','ref':s['ref']};valid_ref(q);out.append(q)
        elif s['kind']=='vertices':
            shape,start,count,step=(s[x] for x in ('shape','start','count','step'))
            if any(type(x)!=int for x in (shape,start,count,step)) or shape<0 or start<0 or count<1 or len(out)+count>1893 or step not in (-1,1):raise ValueError('bad vertex run')
            for k in range(count):
                q={'kind':'vertex','ref':[shape,start+k*step]};valid_ref(q);out.append(q)
        else:raise ValueError('bad run type')
    if len(out)!=1893:raise ValueError('wrong expanded length')
    recipe=dict(value['header']);recipe['hydro_selectors']=out
    if sha(canonical(recipe))!=value['original_recipe_sha256']:raise ValueError('round-trip hash mismatch')
    return recipe


p=argparse.ArgumentParser(description=__doc__)
p.add_argument('mode',choices=('compact','expand'))
p.add_argument('--input',required=True)
p.add_argument('--input-sha256',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
with open(a.input,'rb') as f:raw=f.read()
if sha(raw)!=a.input_sha256:raise ValueError('input hash mismatch')
data=json.loads(raw)
if a.mode=='compact':
    if raw!=canonical(data):raise ValueError('original recipe must use canonical encoding')
    result=compact(data,sha(raw))
    if sha(canonical(expand(result)))!=sha(raw):raise ValueError('compression round-trip mismatch')
else:result=expand(data)
encoded=canonical(result)
with open(a.output,'xb') as f:f.write(encoded)
print('output_sha256',sha(encoded),'bytes',len(encoded))
if a.mode=='compact':
    segments=result['hydro_segments']
    print('segments',len(segments),'vertex_runs',sum(x['kind']=='vertices' for x in segments),
          'interpolations',sum(x['kind']=='edge' for x in segments),
          'shape_ids',len(set(x['shape'] if x['kind']=='vertices' else x['ref'][0] for x in segments)))
