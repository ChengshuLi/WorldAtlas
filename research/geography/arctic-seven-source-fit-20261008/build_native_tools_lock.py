#!/usr/bin/env python3
"""Pin the native tools and linked libraries used by streamed archive extraction."""
from __future__ import annotations
import hashlib, json, platform, shutil, subprocess
import shlex
from pathlib import Path

PACKET=Path(__file__).resolve().parent
COMMANDS=['bash','git','tar','tee','sha256sum','cmp','mktemp','unlink','rmdir','mkdir','otool','grep','wc','sync','uname','tr']

def sha(raw):return hashlib.sha256(raw).hexdigest()
def descriptor(path,kind):
 path=Path(path); raw=path.read_bytes()
 return {'path':str(path),'kind':kind,'bytes':len(raw),'sha256':sha(raw)}
def main():
 binaries={}
 for command in COMMANDS:
  path=Path(shutil.which(command))
  if not path.is_file():raise RuntimeError('Native command is not a file: '+command)
  binaries[command]=path
 dependencies=set(); linked={}
 for path in set(binaries.values()):
  output=subprocess.check_output(['otool','-L',str(path)],stderr=subprocess.STDOUT).decode()
  for line in output.splitlines()[1:]:
   dep=line.strip().split(' (compatibility version',1)[0]
   if dep.startswith('/'):
    available=Path(dep).exists()
    linked[dep]={'available_as_file':available}
    if available:dependencies.add(Path(dep))
 files={str(path.resolve()):descriptor(path.resolve(),'executable') for path in set(binaries.values())}
 for path in dependencies:
  real=path.resolve()
  if real.is_file():files[str(real)]=descriptor(real,'shared-library')
 lock={'version':1,'platform':platform.platform(),'system':platform.system(),
  'release':platform.release(),'machine':platform.machine(),
  'commands':{name:str(path) for name,path in binaries.items()},
  'dependency_policy':'Every executable used by the archive extraction script and each resolved on-disk dynamic library reported by otool -L are whole-file SHA-256 pinned. OS release and architecture are also recorded.',
  'linked_libraries':linked,'files':sorted(files.values(),key=lambda row:row['path']),
  'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files.values())}
 raw=(json.dumps(lock,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 target=PACKET/'native-tools-lock.json'
 if target.is_symlink():raise ValueError('Native tool lock path must not be a symlink')
 if target.exists():
  if target.read_bytes()!=raw:raise FileExistsError('Native tool lock differs; preserve it and use a new reviewed runtime vintage')
 else:target.write_bytes(raw)
 shell=['#!/bin/bash',f'NATIVE_TOOLS_TOTAL_BYTES={lock["total_bytes"]}',f'NATIVE_TOOLS_LOCK_SHA256={sha(raw)}',
  f'NATIVE_SYSTEM={shlex.quote(platform.system())}',f'NATIVE_RELEASE={shlex.quote(platform.release())}',
  f'NATIVE_MACHINE={shlex.quote(platform.machine())}','verify_native_tools() {',
  '  test "$(uname -s)" = "$NATIVE_SYSTEM"','  test "$(uname -r)" = "$NATIVE_RELEASE"','  test "$(uname -m)" = "$NATIVE_MACHINE"']
 for index,row in enumerate(lock['files']):
  shell.append(f'  actual_{index}=$(sha256sum {shlex.quote(row["path"])})')
  shell.append(f'  test "${{actual_{index}%% *}}" = {row["sha256"]}')
 shell.append('}')
 shell_path=PACKET/'native-tools-lock.sh'
 if shell_path.is_symlink():raise ValueError('Native tool shell lock path must not be a symlink')
 shell_raw=('\n'.join(shell)+'\n').encode()
 if shell_path.exists():
  if shell_path.read_bytes()!=shell_raw:raise FileExistsError('Native tool shell lock differs; preserve it and use a new reviewed runtime vintage')
 else:shell_path.write_bytes(shell_raw)
 print(json.dumps({'status':'native-tools-lock-built','file_count':lock['file_count'],'bytes':lock['total_bytes'],'sha256':sha(raw)},sort_keys=True))
if __name__=='__main__':main()
