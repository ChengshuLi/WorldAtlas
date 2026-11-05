"""Linux atomic rename that never replaces an existing destination."""
import ctypes,os
libc=ctypes.CDLL(None,use_errno=True)
def move_noreplace(source,destination):
 try:fn=libc.renameat2
 except AttributeError:raise RuntimeError('atomic no-replace rename unavailable')
 fn.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];fn.restype=ctypes.c_int
 src=os.fsencode(source);dst=os.fsencode(destination)
 if fn(-100,src,-100,dst,1)!=0:
  err=ctypes.get_errno();raise OSError(err,os.strerror(err),os.fsdecode(destination))
