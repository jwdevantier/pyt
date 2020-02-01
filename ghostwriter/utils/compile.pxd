# cython: language_level=3
from ghostwriter.parser.fileparser cimport ShouldReplaceFileCallbackFn


cdef class FileSyncReplace(ShouldReplaceFileCallbackFn):
    cpdef bint apply(self, str temp, str orig) except *


cdef class FileChecksums:
    cdef dict fmap
    cpdef bint should_replace(self, str temp, str orig)