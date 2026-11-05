#!/usr/bin/env python3
"""Offline pinned-input parity verifier. Caller authenticates the manifest pin."""
import argparse
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

LIMITS = {
    'proposal': ('proposal.json', 8 << 20),
    'water_presentation': ('water-presentation.json', 8 << 20),
    'references': ('review-references.json', 8 << 20),
    'records': ('presentation-records-local.json', 8 << 20),
    'original_module': ('original-review.mjs', 1 << 20),
    'candidate_module': ('data-driven-review.mjs', 1 << 20),
    'parity_checker': ('verify_presentation_parity.mjs', 1 << 20),
}
F_ADD_SEALS=getattr(fcntl,'F_ADD_SEALS',1033)
F_GET_SEALS=getattr(fcntl,'F_GET_SEALS',1034)
F_SEAL_SEAL=getattr(fcntl,'F_SEAL_SEAL',1)
F_SEAL_SHRINK=getattr(fcntl,'F_SEAL_SHRINK',2)
F_SEAL_GROW=getattr(fcntl,'F_SEAL_GROW',4)
F_SEAL_WRITE=getattr(fcntl,'F_SEAL_WRITE',8)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError('duplicate JSON key')
        result[k] = v
    return result

def strict_json(raw):
    def finite_float(value):
        parsed=Decimal(value)
        f=float(parsed)
        if not parsed.is_finite() or not math.isfinite(f) or Decimal(repr(f)) != parsed:
            raise ValueError('number loses precision in JavaScript')
        return parsed
    def finite_int(value):
        parsed=int(value)
        try:
            f=float(parsed)
        except OverflowError:
            raise ValueError('integer loses precision in JavaScript') from None
        if not math.isfinite(f) or int(f)!=parsed:
            raise ValueError('integer loses precision in JavaScript')
        return parsed
    return json.loads(raw, object_pairs_hook=pairs, parse_float=finite_float, parse_int=finite_int,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))

def equal_json(a, b):
    # Exact decimal semantics; bool must not compare equal to integer 0 or 1.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is bool and type(b) is bool and a == b
    if isinstance(a, (int, Decimal)) and isinstance(b, (int, Decimal)):
        return Decimal(a) == Decimal(b)
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(equal_json(x,y) for x,y in zip(a,b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal_json(a[k],b[k]) for k in a)
    return a == b

def bounded(path, limit):
    with open(path, 'rb') as f:
        before=os.fstat(f.fileno())
        if before.st_size > limit:
            raise ValueError('oversized input')
        raw=f.read(limit+1)
        after=os.fstat(f.fileno())
    if len(raw)>limit or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=before.st_size:
        raise ValueError('input changed while reading')
    return raw

def sealed(raw):
    if sys.platform != 'linux' or not hasattr(os, 'memfd_create'):
        raise RuntimeError('Linux sealed memfd support required')
    fd=os.memfd_create('worldatlas-presentation', os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view)
            if count<=0: raise OSError('short memfd write')
            view=view[count:]
        os.lseek(fd,0,os.SEEK_SET)
        seals=F_SEAL_WRITE|F_SEAL_GROW|F_SEAL_SHRINK|F_SEAL_SEAL
        fcntl.fcntl(fd,F_ADD_SEALS,seals)
        if fcntl.fcntl(fd,F_GET_SEALS) & seals != seals: raise RuntimeError('sealing failed')
        return fd
    except BaseException:
        os.close(fd)
        raise

def collect_limited(proc, timeout=30, stdout_limit=24<<20, stderr_limit=1<<20):
    buffers={'stdout':bytearray(),'stderr':bytearray()}
    limits={'stdout':stdout_limit,'stderr':stderr_limit}
    selector=selectors.DefaultSelector()
    selector.register(proc.stdout,selectors.EVENT_READ,'stdout')
    selector.register(proc.stderr,selectors.EVENT_READ,'stderr')
    deadline=time.monotonic()+timeout
    try:
        while selector.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0: raise TimeoutError('parity subprocess timed out')
            for key,_ in selector.select(remaining):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                name=key.data
                buffers[name].extend(chunk)
                if len(buffers[name])>limits[name]: raise ValueError(name+' exceeded output limit')
        code=proc.wait(timeout=max(0.001,deadline-time.monotonic()))
        if code: raise ValueError('index parity failed: '+buffers['stderr'][:1000].decode('utf8',errors='replace'))
        return bytes(buffers['stdout'])
    finally:
        selector.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stdout.close()
        proc.stderr.close()

def run_checker(inputs):
    names=('proposal.json','water-presentation.json','review-references.json','presentation-records-local.json','original-review.mjs','data-driven-review.mjs')
    fds=[]
    try:
        for name in names: fds.append(sealed(inputs[name]))
        checker=sealed(inputs['verify_presentation_parity.mjs']);fds.append(checker)
        proc=subprocess.Popen(['node','--input-type=module','-',*[str(fd) for fd in fds[:-1]]],stdin=checker,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=tuple(fds[:-1]),env={'PATH':os.environ.get('PATH','')})
        return strict_json(collect_limited(proc))
    finally:
        for fd in fds: os.close(fd)

def verify(manifest_path, expected_manifest_sha, input_dir):
    manifest_raw=bounded(manifest_path, 1 << 20)
    if len(expected_manifest_sha)!=64 or digest(manifest_raw)!=expected_manifest_sha:
        raise ValueError('manifest hash mismatch')
    manifest=strict_json(manifest_raw)
    valid_v1=set(manifest)=={'schema','release_id','assets'} and manifest.get('schema')=='worldatlas-presentation-parity-manifest-v1'
    valid_v2=set(manifest)=={'schema','release_id','assets','sources'} and manifest.get('schema')=='worldatlas-presentation-parity-manifest-v2' and isinstance(manifest.get('sources'),dict)
    if not (valid_v1 or valid_v2) or not isinstance(manifest['release_id'],str) or not manifest['release_id']:
        raise ValueError('invalid manifest')
    assets=manifest['assets']
    if not isinstance(assets,dict) or set(assets)!=set(LIMITS):
        raise ValueError('invalid asset inventory')
    inputs={}
    for key,(name,limit) in LIMITS.items():
        pin=assets[key]
        if not isinstance(pin,str) or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('invalid input hash')
        raw=bounded(Path(input_dir)/name,limit)
        if digest(raw)!=pin:
            raise ValueError('input hash mismatch: '+key)
        if key in ('proposal','water_presentation','references','records'):
            strict_json(raw)
        inputs[name]=raw
    # Sealed input descriptors and bounded pipes prevent path swaps after hashing.
    # Executable and caller-supplied manifest authenticity are separate concerns.
    result=run_checker(inputs)
    if not isinstance(result,dict) or set(result)!={'original','migrated','report'}:
        raise ValueError('invalid parity output')
    reference=strict_json(inputs['review-references.json'])
    if not equal_json(reference,result['original']) or not equal_json(reference,result['migrated']):
        raise ValueError('lossless reference parity mismatch')
    report=result['report']
    if report.get('full_index_equal') is not True or type(report.get('land_leaves')) is not int or report['land_leaves'] < 1:
        raise ValueError('unexpected parity report')
    return {'status':'parity-verified-not-deployed','release_id':manifest['release_id'],'manifest_sha256':expected_manifest_sha,'parity':report,'limitations':['Caller must independently authenticate the manifest pin and Neon export.','This does not establish browser rendering or authorize deployment.']}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--input-dir',required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.manifest,a.manifest_sha256,a.input_dir),sort_keys=True))

