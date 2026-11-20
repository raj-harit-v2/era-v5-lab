"""sha256 of files, each computed once, in parallel.

  from hashing import HashCache, code_sha256
  cache = HashCache(Path("<run>/cache/sha256.json"))   # on disk, so a resumed run does not hash again; or HashCache()
  cache.sha256(path)                                  # one file
  cache.sha256_many(paths)                            # many files at once, in threads: {path: hex digest}
  cache.remember(path, digest)                        # a file known to hold these bytes (a hard link just made)
  cache.save()                                        # write the on-disk cache (atomically)
  code_sha256(script, cache)                          # (one sha256 of a script and its helper modules, {file: sha256})

The pipeline hashes the same data several times: the digest of the cleaned folder, apply_dedup.py's input and output,
the digest of the deduplicated folder, and again on every resumed run. This hashes each file once.

A FILE IS THE SAME FILE while its (device, inode, size, mtime, change time) are the same. The pipeline never edits a
file in place: every writer writes a .tmp file and renames it, which gives a new inode and new times, so a rewritten
file is always hashed again. The change time moves on every write and every metadata change, setting mtime back
included: it is st_ctime on Linux and macOS, where no program can set it, and NTFS's ChangeTime on Windows (read with
GetFileInformationByHandleEx; os.stat's st_ctime there is the creation time), which a program could set on purpose but
no editor does. So an in-place edit that puts mtime back is hashed again, and so is a new file that got a reused inode
number. Making a hard link moves the change time too (the link count changed), so apply_dedup.py tells the cache that
a part it hard-linked has its input's sha256 (remember). A file system without inode numbers falls back to the path in
the key; one with a coarse clock (FAT's 2 s) could miss an in-place edit of the same size within one tick. For a full
re-hash, pass enabled=False (hash_cache: false in the runner's config).

SPEED: files are read in 1 MiB blocks; hashlib releases the GIL while it hashes a block and file reads release it too,
so `workers` threads hash `workers` files at once, which helps on SSDs and network storage. One spinning disk stays
bounded by its read speed.

ON DISK: a JSON object {key: sha256}, written to .tmp and renamed. A missing, unreadable or malformed file starts an
empty cache: the cache is only ever a shortcut, never trusted over the file. It only grows (one short line per file
ever hashed); delete it to start again.
"""
import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BLOCK = 1 << 20
VERSION = 3  # the key format; a cache written with another version is ignored
HERE = Path(__file__).resolve().parent
HELPERS = ("arrowtools.py", "hashing.py", "runlock.py")  # the shared modules every pipeline script runs on


def file_sha256(path):
    """The sha256 of one file, read in 1 MiB blocks. No cache."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(BLOCK), b""):
            h.update(block)
    return h.hexdigest()


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _BasicInfo(ctypes.Structure):  # FILE_BASIC_INFO
        _fields_ = [("CreationTime", ctypes.c_longlong), ("LastAccessTime", ctypes.c_longlong),
                    ("LastWriteTime", ctypes.c_longlong), ("ChangeTime", ctypes.c_longlong),
                    ("FileAttributes", wintypes.DWORD)]

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                 wintypes.DWORD, wintypes.HANDLE]
    _k32.CreateFileW.restype = wintypes.HANDLE
    _k32.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    _k32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL
    _INVALID = ctypes.c_void_p(-1).value
    # FILE_READ_ATTRIBUTES; share read, write and delete (a rename elsewhere is not blocked); OPEN_EXISTING;
    # FILE_FLAG_BACKUP_SEMANTICS (any file); FileBasicInfo
    _ACCESS, _SHARE, _OPEN, _FLAGS, _BASIC = 0x80, 0x7, 3, 0x02000000, 0

    def change_time(path, st):
        """NTFS's ChangeTime of the file (100 ns units), or st_ctime_ns where it cannot be read (then the key just
        differs, and the file is hashed again)."""
        h = _k32.CreateFileW(os.fspath(path), _ACCESS, _SHARE, None, _OPEN, _FLAGS, None)
        if h is None or h == _INVALID:
            return f"c{st.st_ctime_ns}"
        try:
            info = _BasicInfo()
            if not _k32.GetFileInformationByHandleEx(h, _BASIC, ctypes.byref(info), ctypes.sizeof(info)):
                return f"c{st.st_ctime_ns}"
            return f"n{info.ChangeTime}"
        finally:
            _k32.CloseHandle(h)
else:
    def change_time(path, st):
        """st_ctime_ns: the last change of the file's data or metadata."""
        return f"c{st.st_ctime_ns}"


def identity(path):
    """The cache key of a file: device, inode, size, mtime and change time (the path instead of the inode where there is
    none)."""
    st = os.stat(path)
    where = f"{st.st_dev}:{st.st_ino}" if st.st_ino else os.path.abspath(path)
    return f"{where}:{st.st_size}:{st.st_mtime_ns}:{change_time(path, st)}"


class HashCache:
    """sha256 of files keyed on their identity. Thread-safe. `path`: where to keep it between runs (None: memory only).
    `workers`: threads for sha256_many. `enabled=False` hashes every file every time (an audit run)."""

    def __init__(self, path=None, workers=None, enabled=True):
        self.path = Path(path) if path else None
        self.workers = max(1, workers or min(32, (os.cpu_count() or 2)))
        self.enabled = enabled
        self._lock = threading.Lock()
        self._known = self._load() if (self.path and enabled) else {}
        self.hits = self.misses = 0

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict) or data.get("version") != VERSION or not isinstance(data.get("sha256"), dict):
            return {}
        return {k: v for k, v in data["sha256"].items() if isinstance(k, str) and isinstance(v, str) and len(v) == 64}

    def sha256(self, path):
        """The sha256 of one file, from the cache when the file is unchanged."""
        if not self.enabled:
            return file_sha256(path)
        key = identity(path)
        with self._lock:
            hit = self._known.get(key)
            if hit is not None:
                self.hits += 1
                return hit
        digest = file_sha256(path)
        if identity(path) != key:  # changed while it was read: hash what is there now, and cache nothing
            return file_sha256(path)
        with self._lock:
            self._known[key] = digest
            self.misses += 1
        return digest

    def remember(self, path, digest):
        """Record that the file at `path`, as it is now, holds the bytes with this sha256: a hard link just made to a file
        already hashed. Nothing is recorded in an audit run (enabled=False), which hashes every file it is asked for."""
        if self.enabled:
            key = identity(path)
            with self._lock:
                self._known[key] = digest

    def sha256_many(self, paths):
        """{path: sha256} for many files, hashed in `workers` threads. The result follows the order of `paths`."""
        paths = list(paths)
        if len(paths) <= 1 or self.workers == 1:
            return {p: self.sha256(p) for p in paths}
        with ThreadPoolExecutor(max_workers=min(self.workers, len(paths))) as pool:
            return dict(zip(paths, pool.map(self.sha256, paths)))

    def save(self):
        """Write the cache to `path`, atomically (.tmp, then rename)."""
        if not (self.path and self.enabled):
            return
        with self._lock:
            known = dict(self._known)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps({"version": VERSION, "sha256": known}, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)


def code_sha256(script, cache=None, extra=()):
    """(one sha256 for a script and the modules it runs on, {file name: sha256}): the script, the shared HELPERS and the
    `extra` file names (next to this file). A fix in a helper changes it, so apply_dedup.py, which resumes only with the
    same code, does not keep parts an older helper wrote."""
    files = [Path(script)] + [HERE / name for name in (*HELPERS, *extra)]
    each = {}
    for f in files:
        each.setdefault(f.name, cache.sha256(f) if cache is not None else file_sha256(f))
    combined = hashlib.sha256("".join(f"{name}  {h}\n" for name, h in each.items()).encode("utf-8")).hexdigest()
    return combined, each
