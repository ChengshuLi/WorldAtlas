"""Bounded ordinary immutable input reader for issue1261."""
import ast
import gzip
import hashlib
import io
import json
import pathlib
import re
import subprocess

LIMIT = 33554432


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(path):
    if not isinstance(path,str) or path.startswith('/') or '\\' in path or any(p in ('','.','..') for p in path.split('/')):
        raise ValueError('Unsafe ordinary input path')
    return path


def checked_encoded(raw,descriptor):
    if descriptor['bytes'] > LIMIT or len(raw) > LIMIT:
        raise ValueError('Encoded ordinary input bound')
    if len(raw)!=descriptor['bytes'] or digest(raw)!=descriptor['sha256']:
        raise ValueError('Encoded whole input differs')
    return raw


def checked_decoded(raw,descriptor):
    checked_encoded(raw,descriptor)
    if 'uncompressed_bytes' not in descriptor:
        return raw
    if descriptor['uncompressed_bytes'] > LIMIT:
        raise ValueError('Declared decoded ordinary input bound')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        decoded=stream.read(LIMIT+1)
        if len(decoded)>LIMIT or stream.read(1):
            raise ValueError('Actual decoded ordinary input bound')
    if len(decoded)!=descriptor['uncompressed_bytes'] or digest(decoded)!=descriptor['uncompressed_sha256']:
        raise ValueError('Decoded whole input differs')
    return decoded


def ordinary_git(repo,commit,path,descriptor):
    if re.fullmatch('[a-f0-9]{40}',commit) is None:
        raise ValueError('Exact lowercase40hex immutable input commit required')
    safe_path(path)
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
    tree=git('ls-tree','-z',commit,'--',path).decode().rstrip('\0')
    if not tree or '\t' not in tree:
        raise ValueError('Missing ordinary committed input')
    meta,name=tree.split('\t',1);mode,kind,oid=meta.split()
    if mode not in ('100644','100755') or kind!='blob' or name!=path:
        raise ValueError('Require unique ordinary committed input')
    if int(git('cat-file','-s',oid))>LIMIT:
        raise ValueError('Actual committed encoded input bound')
    return checked_encoded(git('cat-file','blob',oid),descriptor)


def existing_reconstructor(source_raw,expected_sha,canonical_json):
    """Bind complete existing source, extract only the exact two pure functions.

    This avoids importing unused historical detector/builders and their imports.
    Both full source and extracted executed byte strings must enter final pins.
    """
    if digest(source_raw)!=expected_sha:
        raise ValueError('Existing complete reconstruction source differs')
    source=source_raw.decode();tree=ast.parse(source);needed=['contact_key','reconstruct'];nodes={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed}
    if set(nodes)!=set(needed):
        raise ValueError('Missing existing reconstruction function')
    exact='\n\n'.join(ast.get_source_segment(source,nodes[name]) for name in needed)+'\n'
    environment={'canonical_json':canonical_json,'digest':digest}
    exec(compile(exact,'<authenticated existing pure reconstruction functions>','exec'),environment)
    return environment['reconstruct'],environment['contact_key'],dict(whole_source_sha256=digest(source_raw),exact_executed_functions_sha256=digest(exact.encode()))
