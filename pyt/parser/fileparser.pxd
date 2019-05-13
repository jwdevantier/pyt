# cython: language_level=3
from libc.stdio cimport FILE
import typing as t
from pyt.protocols import IWriter

ctypedef Py_UNICODE wchar_t

cdef struct cstr:
    size_t buflen
    wchar_t *ptr
    size_t strlen

cdef enum SNIPPET_TYPE:
    SNIPPET_NONE
    SNIPPET_OPEN
    SNIPPET_CLOSE

cdef struct snippet:
    cstr *cstr
    SNIPPET_TYPE type
    size_t line_num

snippet_cb = t.Callable[[Context, IWriter], None]

ctypedef void* c_snippet_cb

cdef class Parser:
    # file handlers for input and output files
    cdef FILE *fh_in
    cdef FILE *fh_out

    # buffer holding the name of the temporary file made iff
    # input and eventual output file are the same (in-place writing)
    cdef cstr *tmp_file_path

    # buffers holding the literals identifying the tags
    # opening and ending a snippet (e.g. '<@@' and '@@>' respectively)
    cdef cstr *tag_open
    cdef cstr *tag_close

    # buffers for holding information on the snippet start/end tags
    # (name, line number...)
    # TODO: change to Snippet class
    cdef snippet *snippet_start
    cdef snippet *snippet_end

    # buffer holding a line of input from fh_in
    cdef cstr *line
    cdef size_t line_num


    cdef repr(self)
    cdef int snippet_find(self, snippet* dst) nogil
    cdef int readline(self) nogil
    cdef int writeline(self) nogil
    cdef void expand_snippet(self, Context ctx)
    cdef unsigned int doparse(self, Context ctx) nogil

cdef class Context:
    cdef readonly wchar_t *src
    cdef readonly wchar_t *dst
    cpdef readonly dict env
    cdef c_snippet_cb on_snippet