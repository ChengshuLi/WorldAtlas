"""Atomic directory publication without replacing an existing destination."""
import ctypes
import os


def _bind_rename():
    libc = ctypes.CDLL(None, use_errno=True)
    path = ctypes.c_char_p
    flag = ctypes.c_uint
    try:
        rename = libc.renameat2
    except AttributeError:
        rename = libc.renamex_np
        rename.argtypes = [path, path, flag]
        rename.restype = ctypes.c_int
        rename_excl = 0x00000004
        return lambda source, destination: rename(source, destination, rename_excl)
    rename.argtypes = [ctypes.c_int, path, ctypes.c_int, path, flag]
    rename.restype = ctypes.c_int
    at_fdcwd, rename_noreplace = -100, 1
    return lambda source, destination: rename(at_fdcwd, source, at_fdcwd, destination, rename_noreplace)


_rename = _bind_rename()


def move_noreplace(source, destination):
    if _rename(os.fsencode(source), os.fsencode(destination)) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), os.fsdecode(destination))
