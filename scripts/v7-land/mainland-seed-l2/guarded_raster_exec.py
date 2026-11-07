"""Parent-death-protected rasterizer exec without application memory ceilings."""
import ctypes,os,resource,signal,sys
if __name__=='__main__':
 if len(sys.argv)<3:raise SystemExit('usage: guarded_raster_exec.py PARENT_PID SCRIPT [ARGS...]')
 expected=int(sys.argv[1]);libc=ctypes.CDLL(None,use_errno=True)
 if libc.prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError(ctypes.get_errno(),'prctl failed')
 if os.getppid()!=expected:raise SystemExit('parent exited before guard installed')
 resource.setrlimit(resource.RLIMIT_CPU,(1800,1800));resource.setrlimit(resource.RLIMIT_FSIZE,(2<<30,2<<30))
 os.execv('/usr/bin/python3',['/usr/bin/python3','-u']+sys.argv[2:])
