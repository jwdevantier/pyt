# cython: language_level=3
from libc.stdio cimport FILE
import typing as t
from pyt.protocols import IWriter

ctypedef Py_UNICODE wchar_t

cdef extern from "wchar.h" nogil:
    ctypedef struct mbstate_t:
        pass

ctypedef unsigned int PARSE_RES
cdef enum:
    PARSE_OK = 0
    PARSE_READ_ERR = 1  # test - permissions issues
    PARSE_WRITE_ERR = 2
    PARSE_EXPECTED_SNIPPET_OPEN = 3
    PARSE_EXPECTED_SNIPPET_CLOSE = 4
    PARSE_SNIPPET_NAMES_MISMATCH = 5

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

cdef extern from "wcsenc.h" nogil:
    ctypedef struct wcsenc_t:
        pass

snippet_cb = t.Callable[[Context, IWriter], None]

ctypedef void* c_snippet_cb

cdef class FileWriter:
    cdef FILE *out
    cdef wcsenc_t *encoder
    cdef bint got_newline
    cpdef void write(self, str s)

    @staticmethod
    cdef FileWriter from_handle(FILE *fh, wcsenc_t *encoder)

cdef class Parser:
    # file handlers for input and output files
    cdef FILE *fh_in
    cdef FILE *fh_out

    cdef str temp_file_suffix

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
    cdef wcsenc_t *encoder

    cdef cstr *snippet_indent

    cdef repr(self)
    cdef int cpy_snippet_indentation(self) nogil
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