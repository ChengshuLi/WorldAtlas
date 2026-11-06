#!/usr/bin/env python3
"""Restore and verify the archived exact Ural selector export from Neon JSON.

Input is a JSON object containing the selector_pinned_export provenance entry,
or the entry itself. Fetch it from the reviewed boundary row. No credentials
or raw geographic data are kept in this script.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

EXPECTED_GZIP='756e518fd7dc73a392b860bab5f7c52cc1a8b7c00989e3b151e525fec947b785'
EXPECTED_RAW='615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc'

def restore(obj):
    entry=obj.get('selector_pinned_export',obj)
    if entry.get('encoding')!='gzip-base64' or entry.get('gzip_sha256')!=EXPECTED_GZIP or entry.get('uncompressed_sha256')!=EXPECTED_RAW:
        raise ValueError('unexpected selector export metadata')
    packed=base64.b64decode(entry['base64'],validate=True)
    if hashlib.sha256(packed).hexdigest()!=EXPECTED_GZIP:raise ValueError('selector archive hash mismatch')
    raw=gzip.decompress(packed)
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_RAW:raise ValueError('selector export hash mismatch')
    return raw

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--neon-json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raw=restore(json.loads(a.neon_json.read_bytes()))
    with a.output.open('xb') as f:f.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':EXPECTED_RAW,'output':str(a.output)}))

if __name__=='__main__':main()
