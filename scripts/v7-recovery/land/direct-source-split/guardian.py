#!/usr/bin/env /usr/bin/python3
"""Hold the stage-2 process group and kill it if the monitor disappears."""
import json,os,select,signal,subprocess,sys,time

def kill_group():
 os.killpg(os.getpgrp(),signal.SIGKILL)

def main():
 if len(sys.argv)<5:raise ValueError('guardian requires control/status fds and driver command')
 control,status=map(int,sys.argv[1:3]);cmd=sys.argv[3:]
 signal.signal(signal.SIGPIPE,signal.SIG_IGN)
 def emit(obj):
  try:os.write(status,(json.dumps(obj,separators=(',',':'))+'\n').encode())
  except (BrokenPipeError,OSError):kill_group()
 def read_command():
  data=os.read(control,256)
  if not data:kill_group()
  return data
 emit({'event':'ready','group':os.getpgrp(),'guardian':os.getpid()})
 if read_command()!=b'START\n':kill_group()
 # The driver starts only after the monitor has sampled this guardian and
 # explicitly sent START. No monitor pipe descriptor is inherited by it.
 child=subprocess.Popen(cmd,close_fds=True,stdout=subprocess.DEVNULL)
 emit({'event':'started','driver_pid':child.pid})
 while True:
  ready,_,_=select.select([control],[],[],.05)
  if ready:
   command=read_command()
   if command==b'KILL\n':kill_group()
   kill_group()
  rc=child.poll()
  if rc is not None:
   emit({'event':'done','returncode':rc})
   break
 while True:
  command=read_command()
  if command==b'RELEASE\n':return
  if command==b'KILL\n':kill_group()
  kill_group()

if __name__=='__main__':
 try:main()
 except BaseException:
  # Keep the group leader alive until group kill; otherwise its PGID can be reused.
  kill_group()
