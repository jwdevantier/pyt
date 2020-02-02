from os import scandir
from os.path import relpath
from re import compile as re_compile
from multiprocessing import Pipe, Process
from watchgod.watcher import Change
from ghostwriter.cli.conf import Configuration
from ghostwriter.utils import itools


def or_pattern(patterns: list):
    """Compile pattern matching any of the regex strings in `patterns`."""
    cdef str entry
    return re_compile('|'.join(f'(?:{entry})' for entry in patterns)).match


cdef class AllWatcher:
    def __init__(self, root_path):
        self.files = {}
        self.root_path = root_path
        self.check()

    cpdef bint should_watch_dir(self, DirEntry entry):
        return True

    cpdef bint should_watch_file(self, DirEntry entry):
        return True

    cpdef void _walk(self, str dir_path, set changes, dict new_files) except *:
        for entry in scandir(dir_path):
            if entry.is_dir():
                if self.should_watch_dir(entry):
                    self._walk(entry.path, changes, new_files)
            elif self.should_watch_file(entry):
                mtime = entry.stat().st_mtime
                new_files[entry.path] = mtime
                old_mtime = self.files.get(entry.path)
                if not old_mtime:
                    changes.add((Change.added, entry.path))
                elif old_mtime != mtime:
                    changes.add((Change.modified, entry.path))

    cpdef set check(self):
        changes = set()
        new_files = {}
        try:
            self._walk(str(self.root_path), changes, new_files)
        except OSError as e:
            # happens when a directory has been deleted between checks
            # logger.warning('error walking file system: %s %s', e.__class__.__name__, e)
            pass

        # look for deleted
        deleted = self.files.keys() - new_files.keys()
        if deleted:
            changes |= {(Change.deleted, entry) for entry in deleted}

        self.files = new_files
        return changes


cdef class CompileWatcher(AllWatcher):
    def __init__(self, path: str, *, config: Configuration):
        if config.parser.ignore_patterns:
            self.ignore_file = or_pattern(config.parser.ignore_patterns)
        else:
            self.ignore_file = lambda _: None
        self.include_file = or_pattern(config.parser.include_patterns)
        if config.parser.ignore_dir_patterns:
            self.ignore_dir = or_pattern(config.parser.ignore_dir_patterns)
        else:
            self.ignore_dir = lambda _: None
        self.temp_file_suffix = config.parser.temp_file_suffix
        super().__init__(path)

    cpdef bint should_watch_dir(self, DirEntry entry):
        cdef dir_path = relpath(entry.path, self.root_path)
        return self.ignore_dir(dir_path) is None  # Should add dirs and subdirs here, too

    cpdef bint should_watch_file(self, DirEntry entry):
        cdef file_path = relpath(entry.path, self.root_path)
        if file_path.endswith(self.temp_file_suffix) or self.ignore_file(file_path):
            return False
        return self.include_file(file_path) is not None


cdef class SearchPathsWatcher(AllWatcher):
    IGNORED_DIRS = {'.git', '__pycache__', 'site-packages', 'env', 'venv', '.env', '.venv'}

    def __init__(self, path: str):
        super().__init__(path)

    cpdef bint should_watch_dir(self, DirEntry entry):
        return entry.name not in self.IGNORED_DIRS

    cpdef bint should_watch_file(self, DirEntry entry):
        return entry.name.endswith('.py')


cdef class MPScheduler:
    def __init__(self, int num_processes):
        self._pipe_snd = []
        self._pipe_rcv = []
        self._procs = []
        self.num_processes = num_processes
        self._next_pipe_ndx = 0

        for n in range(self.num_processes):
            snd, rcv = Pipe()
            self._pipe_snd.append(snd)
            self._pipe_rcv.append(rcv)

    cpdef void _target(self, str worker_id, object jobs: Connection):
        """the starting point of the worker process"""
        pass

    cdef void _spawn_procs(self):
        cdef int n
        assert self._procs == [], "cannot spawn before cleaning up old processes"
        for n in range(self.num_processes):
            proc = Process(target=self._target, args=(f"worker-{n}", self._pipe_rcv[n],), daemon=True)
            self._procs.append(proc)
            proc.start()

    cdef void _kill_procs(self):
        for fn in itools.join(
                (lambda: p.send("<stop>") for p in self._pipe_snd),
                (p.join for p in self._procs)):
            try:
                fn()
            except:
                pass
        self._procs = []

    def close(self) -> None:
        self._kill_procs()
        for fn in itools.join((p.close for p in self._pipe_rcv), (p.close for p in self._pipe_snd)):
            try:
                fn()
            except:
                pass

    def __enter__(self):
        self._spawn_procs()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._kill_procs()

    cpdef void submit_one(self, object item):
        cdef int _next_pipe_ndx = self._next_pipe_ndx
        self._pipe_snd[_next_pipe_ndx].send(item)
        _next_pipe_ndx += 1
        if _next_pipe_ndx == self.num_processes:
            self._next_pipe_ndx = 0
        else:
            self._next_pipe_ndx = _next_pipe_ndx
