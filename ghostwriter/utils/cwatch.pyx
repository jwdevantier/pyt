from os import scandir
from re import compile as re_compile
from watchgod.watcher import Change
from ghostwriter.cli.conf import Configuration
from os.path import relpath



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


def compiler_input_files(AllWatcher w, path: str):
    for entry in scandir(path):
        if entry.is_dir():
            if w.should_watch_dir(entry):
                yield from compiler_input_files(w, entry.path)
        elif w.should_watch_file(entry):
            yield entry.path