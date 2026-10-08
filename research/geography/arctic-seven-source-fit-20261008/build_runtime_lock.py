#!/usr/bin/env python3
"""Inventory the exact Python/GIS runtime used for admitted source-fit phases."""
from __future__ import annotations
import hashlib, json, platform, shutil, subprocess, sys
from pathlib import Path

PACKET=Path(__file__).resolve().parent

def sha(raw):return hashlib.sha256(raw).hexdigest()
def entry(path):
 path=Path(path)
 if path.is_symlink():
  raw=str(path.readlink()).encode()
  return {'kind':'symlink','path':str(path),'bytes':len(raw),'sha256':sha(raw),'target':raw.decode()}
 if not path.is_file():return None
 raw=path.read_bytes()
 return {'kind':'file','path':str(path),'bytes':len(raw),'sha256':sha(raw)}

def main():
 import numpy, pyproj, shapely
 base=Path(sys.base_prefix); prefix=Path(sys.prefix)
 version=f'{sys.version_info.major}.{sys.version_info.minor}'
 stdlib=base/'lib'/f'python{version}'
 site=prefix/'lib'/f'python{version}'/'site-packages'
 if not stdlib.is_dir() or not site.is_dir():raise RuntimeError('Expected isolated Python standard library and venv site-packages')
 paths={Path(sys.executable),Path(sys.executable).resolve(),base/'pyvenv.cfg'}
 paths.update(Path(value) for value in sys.path if value.endswith('.zip') and Path(value).is_file())
 for root in [stdlib,site]:
  for path in root.rglob('*'):
   if path.is_symlink():paths.add(path)
   elif path.is_file():paths.add(path)
 # The base runtime contains an unused global site-packages tree; exclude it.
 paths={p for p in paths if p==Path(sys.executable) or p==Path(sys.executable).resolve() or p==base/'pyvenv.cfg' or not p.is_relative_to(stdlib/'site-packages')}
 rows=[x for x in (entry(p) for p in sorted(paths,key=str)) if x]
 if len({x['path'] for x in rows})!=len(rows):raise RuntimeError('Duplicate runtime paths')
 linkage={}
 otool=shutil.which('otool')
 for row in rows:
  path=Path(row['path'])
  if row['kind']!='file' or not (path.suffix in ('.so','.dylib') or path.name.startswith('python3.')):continue
  try: output=subprocess.check_output([otool,'-L',str(path)],stderr=subprocess.STDOUT).decode()
  except (OSError,subprocess.CalledProcessError):continue
  deps=[]
  for line in output.splitlines()[1:]:
   dep=line.strip().split(' (compatibility version',1)[0]
   if dep:deps.append({'identifier':dep,'available_as_file':Path(dep).exists() if dep.startswith('/') else None})
  linkage[row['path']]=deps
 lock={'version':1,'python_version':sys.version.split()[0],'python_executable':sys.executable,
  'python_prefix':sys.prefix,'python_base_prefix':sys.base_prefix,'platform':platform.platform(),
  'system':platform.system(),'release':platform.release(),'machine':platform.machine(),
  'package_versions':{'numpy':numpy.__version__,'pyproj':pyproj.__version__,'shapely':shapely.__version__},
  'native_dependency_policy':'All ordinary Python, extension and package runtime files under the active stdlib/site-packages roots are pinned individually. Linked library identifiers for Python/GIS extension modules are recorded; OS-provided shared-cache libraries rely on the pinned host platform/release when their bytes are not exposed as ordinary files.',
  'native_linkage':linkage,
  'files':rows,'file_count':len(rows),'total_bytes':sum(x['bytes'] for x in rows)}
 raw=(json.dumps(lock,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 target=PACKET/'runtime-lock.json'
 if target.is_symlink():raise ValueError('Runtime lock path must not be a symlink')
 if target.exists():
  if target.read_bytes()!=raw:raise FileExistsError('Runtime lock differs; preserve it and use a newly reviewed runtime vintage')
 else:target.write_bytes(raw)
 print(json.dumps({'status':'runtime-lock-built','path':str(target),'files':len(rows),'bytes':lock['total_bytes'],'sha256':sha(raw),'python':lock['python_version']},sort_keys=True))

if __name__=='__main__':main()
