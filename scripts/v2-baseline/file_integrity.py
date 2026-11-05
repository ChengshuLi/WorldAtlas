"""Hash and validate local file pins for research inputs."""
import hashlib
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def pin(spec):
 if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or not isinstance(spec['path'],str) or not isinstance(spec['sha256'],str) or len(spec['sha256'])!=64 or any(x not in '0123456789abcdef' for x in spec['sha256']):raise ValueError('invalid input pin')
 p=Path(spec['path']).resolve()
 if sha(p)!=spec['sha256']:raise ValueError('input hash mismatch: '+str(p))
 return p

