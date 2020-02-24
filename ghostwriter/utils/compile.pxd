# cython: language_level=3
from ghostwriter.parser.fileparser cimport ShouldReplaceFileCallbackFn


cdef class FileSyncReplace(ShouldReplaceFileCallbackFn):
    cdef FileChecksums filecheck
    cpdef bint apply(self, str temp, str orig) except *


cdef class FileChecksums:
    cdef dict fmap
    cpdef bint should_replace(self, str temp, str orig)


cdef class SnippetError(Exception):
    cdef public str module
    cdef public str fn_name
    cdef public str message