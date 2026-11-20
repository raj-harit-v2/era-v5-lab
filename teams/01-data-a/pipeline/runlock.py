"""One writer per output folder: an operating-system lock that is released when the process ends, even when it is killed.

  from runlock import exclusive, Busy
  with exclusive(out_folder):        # raises Busy if another process holds it
      ...write into out_folder...

The lock is the file <folder>.lock next to the folder, never inside it, so it does not enter the folder's digest. It is
held with fcntl.flock (Linux, macOS) or msvcrt.locking (Windows) on that file: the system drops it with the process, so
a killed run never leaves a stale lock to delete by hand. The file itself stays (empty); that is harmless. Two runs into
the same folder would otherwise interleave their writes (the same .tmp names, the same summary), which is how a partly
written output looks finished.

Only "someone else holds it" (EAGAIN, EWOULDBLOCK, EACCES, EDEADLOCK) is Busy. A file system that cannot lock at all
(ENOLCK, ENOSYS, EOPNOTSUPP: some NFS, FUSE or Lustre mounts) gets a warning on stderr and the run goes on without the
lock, rather than every run stopping; any other error is raised as it is. On NFS, flock is emulated with byte-range
locks, which still exclude other processes (and other machines) but not a second lock taken by the same process.
"""
import errno
import os
import sys
from contextlib import contextmanager
from pathlib import Path

BUSY = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}
UNSUPPORTED = {errno.ENOLCK, errno.ENOSYS, errno.EOPNOTSUPP, getattr(errno, "ENOTSUP", errno.EOPNOTSUPP)}


class Busy(Exception):
    """Another process is writing into the same folder."""


def lock_path(folder):
    folder = Path(folder).resolve()
    return folder.with_name(folder.name + ".lock")


def _lock(f):
    """Take the lock on the open file f without waiting; OSError if it cannot be taken."""
    if os.name == "nt":
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(f):
    if os.name == "nt":
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def exclusive(folder):
    """Hold the lock of `folder` for the with-block; raise Busy at once if another process holds it."""
    path = lock_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+b")
    locked = False
    try:
        try:
            _lock(f)
            locked = True
        except OSError as e:
            if e.errno in BUSY:
                raise Busy(f"another process is writing into {folder} (it holds {path}); wait for it to finish") from None
            if e.errno not in UNSUPPORTED:
                raise
            print(f"runlock: the file system of {path.parent} cannot lock files ({os.strerror(e.errno)}); going on "
                  f"without the lock, so make sure no other run writes into {folder}", file=sys.stderr, flush=True)
        yield path
    finally:
        if locked:
            try:
                _unlock(f)
            except OSError:
                pass
        f.close()
