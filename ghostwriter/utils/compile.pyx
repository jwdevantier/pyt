from typing import Tuple, Iterator, Set
from watchgod.watcher import Change
from ghostwriter.utils.fhash cimport file_hash

Changeset = Set[Tuple[Change, str]]

cdef class FileSyncReplace(ShouldReplaceFileCallbackFn):
    def __init__(self, FileChecksums filecheck):
        self.filecheck = filecheck

    cpdef bint apply(self, str temp, str orig) except *:
        return self.filecheck.should_replace(temp, orig)


cdef class FileChecksums:
    def __init__(self):
        self.fmap = {}

    cpdef bint should_replace(self, str temp, str orig):
        new_hash = file_hash(temp)
        if orig not in self.fmap:
            orig_hash = file_hash(orig)
            self.fmap[orig] = orig_hash
        else:
            orig_hash = self.fmap[orig]
        # replace file iff. contents have changed from the parsing
        return orig_hash != new_hash

    def sync(self, changeset: Changeset) -> Iterator[Tuple[Change, str]]:
        """Lazily synchronizes file checksums based on incoming changeset

        Parameters
        ----------
        changeset : Changeset
            Changes detected by the file system watcher represented as a set
            of 2-tuples of change-type (added, modified, deleted) and the file
            path.

        Returns
        -------
            Iterator for sync operation. Genuine changes (where files are
            modified) are returned.
        """
        cdef dict fmap = self.fmap
        for typ, fpath in changeset:
            if typ == Change.modified:
                new_hash = file_hash(fpath)
                old_hash = fmap.get(fpath, None)
                if new_hash != old_hash:
                    fmap[fpath] = new_hash
                    yield typ, fpath
            elif typ == Change.added:
                fmap[fpath] = file_hash(fpath)
                yield typ, fpath
            elif typ == Change.deleted:
                fmap.pop(fpath, None)


# def xcompiler_input_files(AllWatcher w, path: str):
#     for entry in scandir(path):
#         if entry.is_dir():
#             if w.should_watch_dir(entry):
#                 yield from compiler_input_files(w, entry.path)
#         elif w.should_watch_file(entry):
#             yield entry.path

cdef class Compile:
    pass