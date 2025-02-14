# cython: language_level=3
from libc.stdio cimport FILE
from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.error cimport Error

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
    PARSE_EXCEPTION = 1000


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


cdef class SnippetCallbackFn:
    cpdef void apply(self, Context ctx, str snippet, str prefix, IWriter fw) except *


cdef class ShouldReplaceFileCallbackFn:
    cpdef bint apply(self, str temp, str orig) except *


cdef class ShouldReplaceFileAlways(ShouldReplaceFileCallbackFn):
    pass


cdef class GhostwriterError(Error):
    cpdef str _error_message


cdef class ParseError(Error):
    cpdef public PARSE_RES error_code
    cpdef public str message
    cpdef public str details
    cpdef public size_t line_num
    cpdef public str fpath


cdef class SnippetError(Error):
    cpdef public Exception exc
    cpdef public str snippet_name
    cpdef public str fpath
    cpdef public size_t line_num


cdef class FileWriter(IWriter):
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

    cdef bint expanded_snippet
    cdef ShouldReplaceFileCallbackFn should_replace_file
    cdef object post_process

    # the temporary file used before overwriting the input file or rejecting its contents
    cdef str temp_file_path
    cdef char* temp_file_path_ascii

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

    cdef void reset(self, str fpath) except *
    cdef repr(self)
    cdef int cpy_snippet_indentation(self) nogil
    cdef int snippet_find(self, snippet* dst) nogil
    cdef int readline(self) nogil
    cdef expand_snippet(self, Context ctx)
    cdef PARSE_RES doparse(self, Context ctx) nogil except PARSE_EXCEPTION
    cpdef parse(self, SnippetCallbackFn cb: SnippetCallbackFn, str fpath: str)


cdef class Context:
    cdef readonly wchar_t *src
    cpdef readonly dict env
    cdef readonly SnippetCallbackFn on_snippet
