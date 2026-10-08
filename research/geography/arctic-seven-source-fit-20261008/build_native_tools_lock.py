#!/usr/bin/env python3
"""Pin the native tools and linked libraries used by streamed archive extraction."""
from __future__ import annotations
import argparse, hashlib, json, platform, shutil, subprocess
import shlex
from pathlib import Path

PACKET=Path(__file__).resolve().parent
COMMANDS=['bash','git','tar','tee','sha256sum','cmp','mktemp','unlink','rmdir','mkdir','otool','grep','wc','sync','uname','tr','ln','awk','shasum']

def sha(raw):return hashlib.sha256(raw).hexdigest()
def descriptor(path,kind):
 path=Path(path); raw=path.read_bytes()
 return {'path':str(path),'kind':kind,'bytes':len(raw),'sha256':sha(raw)}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--vintage',default='r9');args=parser.parse_args()
 binaries={}; resolution_shims={}
 for command in COMMANDS:
  if command in ('git','otool'):
   discovered=Path(shutil.which(command)).resolve()
   path=Path(subprocess.check_output(['xcrun','--find',command],text=True).strip())
   if discovered!=path.resolve():resolution_shims[command]=discovered
  else:path=Path(shutil.which(command))
  if not path.is_file():raise RuntimeError('Native command is not a file: '+command)
  binaries[command]=path.resolve()
 dependencies=set(); linked={}
 for path in set(binaries.values()):
  output=subprocess.check_output([str(binaries['otool']),'-L',str(path)],stderr=subprocess.STDOUT).decode()
  for line in output.splitlines()[1:]:
   dep=line.strip().split(' (compatibility version',1)[0]
   if dep.startswith('/'):
    available=Path(dep).exists()
    linked[dep]={'available_as_file':available}
    if available:dependencies.add(Path(dep))
 files={str(path.resolve()):descriptor(path.resolve(),'executable') for path in set(binaries.values())}
 for path in resolution_shims.values():files[str(path)]=descriptor(path,'resolver-shim')
 for path in dependencies:
  real=path.resolve()
  if real.is_file():files[str(real)]=descriptor(real,'shared-library')
 lock={'version':1,'platform':platform.platform(),'system':platform.system(),
  'release':platform.release(),'machine':platform.machine(),
  'commands':{name:str(path) for name,path in binaries.items()},
  'resolution_shims':{name:{'path':str(shim),'sha256':files[str(shim)]['sha256'],'executed_path':str(binaries[name]),'resolver':'xcrun --find'} for name,shim in resolution_shims.items()},
  'dependency_policy':'Every executable used by the archive extraction script, each resolved on-disk dynamic library reported by otool -L, and each Xcode resolver shim for git/otool are whole-file SHA-256 pinned. Commands execute only their resolved absolute tool path; resolver shims are recorded but never invoked. OS release and architecture are also recorded.',
  'linked_libraries':linked,'files':sorted(files.values(),key=lambda row:row['path']),
  'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files.values())}
 raw=(json.dumps(lock,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 target=PACKET/f'native-tools-lock-{args.vintage}.json'
 if target.is_symlink():raise ValueError('Native tool lock path must not be a symlink')
 if target.exists():
  if target.read_bytes()!=raw:raise FileExistsError('Native tool lock differs; preserve it and use a new reviewed runtime vintage')
 else:target.write_bytes(raw)
 shell=['#!/bin/bash',f'NATIVE_TOOLS_TOTAL_BYTES={lock["total_bytes"]}',f'NATIVE_TOOLS_LOCK_SHA256={sha(raw)}',
  f'NATIVE_SYSTEM={shlex.quote(platform.system())}',f'NATIVE_RELEASE={shlex.quote(platform.release())}',
  f'NATIVE_MACHINE={shlex.quote(platform.machine())}']
 for name,path in binaries.items():
  var='NATIVE_'+name.upper().replace('-','_')
  shell.append(f'{var}={shlex.quote(str(path))}')
  shell.append(f'{name}() {{ "${var}" "$@"; }}')
 shell.extend(['verify_native_tools() {',
  '  test "$("$NATIVE_UNAME" -s)" = "$NATIVE_SYSTEM"',
  '  test "$("$NATIVE_UNAME" -r)" = "$NATIVE_RELEASE"',
  '  test "$("$NATIVE_UNAME" -m)" = "$NATIVE_MACHINE"'])
 for index,row in enumerate(lock['files']):
  shell.append(f'  actual_{index}=$("$NATIVE_SHA256SUM" {shlex.quote(row["path"])})')
  shell.append(f'  test "${{actual_{index}%% *}}" = {row["sha256"]}')
 shell.append('}')
 shell_path=PACKET/f'native-tools-lock-{args.vintage}.sh'
 if shell_path.is_symlink():raise ValueError('Native tool shell lock path must not be a symlink')
 shell_raw=('\n'.join(shell)+'\n').encode()
 if shell_path.exists():
  if shell_path.read_bytes()!=shell_raw:raise FileExistsError('Native tool shell lock differs; preserve it and use a new reviewed runtime vintage')
 else:shell_path.write_bytes(shell_raw)
 print(json.dumps({'status':'native-tools-lock-built','file_count':lock['file_count'],'bytes':lock['total_bytes'],'sha256':sha(raw)},sort_keys=True))
if __name__=='__main__':main()
