"""Execute pinned helper with bounded resources and parent-death protection."""
import ctypes,os,resource,signal,sys
if __name__=='__main__':
 if len(sys.argv)<3:raise SystemExit('usage: guarded_exec.py PARENT_PID CHECKER [ARGS...]')
 expected=int(sys.argv[1]);libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError(ctypes.get_errno(),'prctl failed')
 if os.getppid()!=expected:raise SystemExit('parent exited before guard installed')
 resource.setrlimit(resource.RLIMIT_AS,(768<<20,768<<20));resource.setrlimit(resource.RLIMIT_CPU,(1800,1800));resource.setrlimit(resource.RLIMIT_FSIZE,(8<<20,8<<20))
 os.execv('/usr/bin/python3',['/usr/bin/python3','-u']+sys.argv[2:])
