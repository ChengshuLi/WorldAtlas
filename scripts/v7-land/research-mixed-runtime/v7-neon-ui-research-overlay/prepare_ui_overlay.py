#!/usr/bin/env python3
"""Prepare a local V7 overlay; never publishes or edits its source bundle."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

def read_pinned(path, expected, limit=1024*1024):
    with open(path,'rb') as f:
        before=os.fstat(f.fileno())
        if before.st_size>limit: raise ValueError('oversized input: '+str(path))
        raw=f.read(limit+1)
        after=os.fstat(f.fileno())
    identity=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    if len(raw)>limit or len(raw)!=before.st_size or identity(before)!=identity(after): raise ValueError('input changed while reading: '+str(path))
    if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('input hash mismatch: '+str(path))
    return raw.decode('utf-8')

def replace_one(text, old, new):
    if text.count(old)!=1: raise ValueError('expected exactly one UI patch anchor')
    return text.replace(old,new,1)

def build(args):
    def unique_pairs(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError('duplicate manifest key')
            out[k]=v
        return out
    manifest=json.loads(read_pinned(args.manifest,args.manifest_sha256),object_pairs_hook=unique_pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid manifest number')))
    if (not isinstance(manifest,dict) or manifest.get('schema')!='worldatlas-presentation-parity-manifest-v2'
            or manifest.get('release_id')!=args.release_id or not isinstance(manifest.get('assets'),dict)
            or manifest['assets'].get('candidate_module')!=args.renderer_sha256):
        raise ValueError('renderer does not match pinned release manifest')
    app=read_pinned(args.app,args.app_sha256)
    page=read_pinned(args.html,args.html_sha256)
    renderer=read_pinned(args.renderer,args.renderer_sha256)
    client=read_pinned(args.client,args.client_sha256)
    app=replace_one(app,"import { buildReferenceIndex, validateReferenceIndex, waterReviewReason } from './review-references.js';",
                    "import { buildReferenceIndex, validateReferenceIndex, waterReviewReason } from './data-driven-review.mjs';\nimport { loadPresentationEnvelope, readPinnedJSON } from './presentation-client.mjs';")
    app=replace_one(app," const r=await fetch(versionedAsset('proposal.json'));if(!r.ok)throw Error('Review proposal.json is not available');meta=await r.json();",
                    " const cfg=document.documentElement.dataset;\n const envelope=await loadPresentationEnvelope({endpoint:cfg.presentationEndpoint,expectedManifestSha256:cfg.presentationManifestSha256,expectedReleaseId:cfg.presentationReleaseId});\n const r=await fetch(versionedAsset('proposal.json'));meta=await readPinnedJSON(envelope,'proposal',r);")
    app=replace_one(app," const presResponse=await fetch(versionedAsset('water-presentation.json'));if(!presResponse.ok)throw Error('Validated continent presentation index is not available');const presentation=await presResponse.json();",
                    " const presResponse=await fetch(versionedAsset('water-presentation.json'));const presentation=await readPinnedJSON(envelope,'water_presentation',presResponse);")
    app=replace_one(app," const refResponse=await fetch(versionedAsset('review-references.json'));if(!refResponse.ok)throw Error('List-reference mapping index is not available');const references=await refResponse.json();",
                    " const refResponse=await fetch(versionedAsset('review-references.json'));const references=await readPinnedJSON(envelope,'references',refResponse);")
    app=replace_one(app,' const expectedReferences=buildReferenceIndex(meta,presentation,presentation.source);',' const expectedReferences=buildReferenceIndex(meta,presentation,presentation.source,envelope.records);')
    old='<html lang="en" data-data-base="../data/">'
    attrs=' data-presentation-endpoint="'+html.escape(args.endpoint,quote=True)+'" data-presentation-manifest-sha256="'+html.escape(args.manifest_sha256,quote=True)+'" data-presentation-release-id="'+html.escape(args.release_id,quote=True)+'"'
    page=replace_one(page,old,old[:-1]+attrs+'>')
    import re
    page,n=re.subn(r'<script type="module" src="\./app\.js\?v=[0-9a-f]+"></script>','<script type="module" src="./app-neon.js"></script>',page)
    if n!=1: raise ValueError('unexpected UI script tag')
    out=Path(args.output)
    if out.exists() and any(out.iterdir()): raise ValueError('output directory must be empty')
    out.mkdir(parents=True,exist_ok=True)
    for name,content in [('index.html',page),('app-neon.js',app),('data-driven-review.mjs',renderer),('presentation-client.mjs',client)]:
        (out/name).write_text(content,encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('app','app-sha256','html','html-sha256','renderer','renderer-sha256','client','client-sha256','manifest','manifest-sha256','release-id','endpoint','output'):
        p.add_argument('--'+n,required=True)
    build(p.parse_args())
