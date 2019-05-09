# cython: language_level=3
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy
from libc.locale cimport setlocale, LC_ALL
from libc.stdio cimport (fopen, fclose, fwrite, feof, FILE)
import tempfile
import os
import typing as t

# C api docs: https://devdocs.io/c/io/fopen

################################################################################
## DEFINITIONS
################################################################################

ctypedef unsigned int wint_t
DEF PARSER_LINEBUF_SIZ = 512

cdef extern from "stdio.h" nogil:
    char *strstr(const char *haystack, const char *needle)

cdef extern from "wchar.h" nogil:
    # ctypedef Py_UNICODE wchar_t
    wchar_t *fgetws(wchar_t *buf, int count, FILE *stream)
    wchar_t *wcsstr(const wchar_t *haystack, const wchar_t *needle);
    wchar_t *wcscpy(wchar_t *dest, const wchar_t *src)
    wchar_t *wcsncpy(wchar_t *dest, const wchar_t *src, size_t n);
    size_t wcslen(const wchar_t *s); #TODO: remove
    size_t wcsnlen_s(const wchar_t *s, size_t strsz);

    wchar_t *wmemset( wchar_t *dest, wchar_t ch, size_t count );
    int wcscmp( const wchar_t *lhs, const wchar_t *rhs );

cdef extern from "wctype.h" nogil:
    int iswspace(wchar_t ch)  # wint_t
    int iswlower(wint_t ch)  #wint_t

################################################################################
## Utils
################################################################################
def tmp_file(path):
    in_dir = os.path.dirname(path)
    fname = f"{os.path.basename(path)}."

    tf = tempfile.NamedTemporaryFile(
        dir=in_dir, prefix=fname, suffix='.tmp', delete=False)
    fname = tf.name
    tf.close()
    return fname

################################################################################
## CString
################################################################################
cdef class CString:

    def __init__(self, size_t initial_size):
        if initial_size == 0:
            raise ValueError("initial_size must be a positive integer")
        initial_size = initial_size + 1 # reserve space for null character

        self.ptr = NULL
        self.ptr = <wchar_t *> malloc(initial_size * sizeof(wchar_t))
        if self.ptr == NULL:
            raise MemoryError("cannot allocate string buffer")
        wmemset(self.ptr, '\0', 1) # terminate "string"
        self.buflen = initial_size
        self.strlen = 0

    def __dealloc__(self):
        if self.ptr != NULL:
            free(self.ptr)

    cdef int ncpy_wchar(self, wchar_t *src, size_t n):
        cdef wchar_t *new_ptr = NULL
        if n == 0:
            n = wcslen(src) # does NOT include null terminator
        if n >= self.buflen:
            new_ptr = <wchar_t *> realloc(self.ptr, (n + 1) * sizeof(wchar_t))
            if new_ptr == NULL:
                return -1
            self.buflen = n + 1
            self.ptr = new_ptr
        memcpy(self.ptr, src, n * sizeof(wchar_t))
        self.ptr[n] = '\0'
        self.strlen = n
        return 0

    cdef int ncpy_unicode(self, unicode s, size_t n):
        cdef:
            wchar_t *src = s
        return self.ncpy_wchar(src, n)

    cdef void reset(self):
        self.ptr[0] = '\0'
        self.strlen = 0

    cdef size_t len(self):
        return self.strlen

    cdef unicode repr(self):
        return (
            "#CString["
            "buflen: {}, "
            "strlen: {}, "
            "ptr: {}"
            "]"
        ).format(self.buflen, self.strlen, self.ptr)

    def __repr__(self):
        return self.repr()

# TODO: consider rewriting CString back to pure C
#       It's OK that ParserState triggers some Python - but CString-interaction
#       Bascially locks down the GIL now.
#
#       Also, having the top-level object (ParserState) retain all references
#       still means that cleanup will become easy

################################################################################
## ParserState
################################################################################
DEF BUF_LINE_LEN = 512
DEF BUF_SNIPPET_NAME_LEN = 80
DEF BUF_INDENT_BY_LEN = 40

# TODO: is it OK that tag_open == tag_close (e.g. '@@')
cdef class ParserState:

    def __init__(
            self,
            fpath_src: str, fpath_dst: t.Optional[str],
            tag_open: str = '<@@', tag_close: str = '@@>',
            buf_len_line = BUF_LINE_LEN,
            buf_snippet_name_len = BUF_SNIPPET_NAME_LEN,
            buf_indent_by_len = BUF_INDENT_BY_LEN):
        self.fh_in = self.fh_out = NULL

        if buf_len_line <= 0:
            raise ValueError("buf_len_line must be positive")

        self.tmp_file_path = CString(250)
        self.reset(fpath_src, fpath_dst)

        # tag_open (e.g. '<@@')
        self.tag_open = CString(len(tag_open))
        if self.tag_open.ncpy_unicode(tag_open, len(tag_open)) != 0:
            raise MemoryError("tag_open")

        # tag_close (e.g. '@@>')
        self.tag_close = CString(len(tag_close))
        if self.tag_close.ncpy_unicode(tag_close, len(tag_close)) != 0:
            raise MemoryError("tag_close")

        # snippet_start
        self.snippet_start = CString(buf_snippet_name_len)

        # snippet_end
        self.snippet_end = CString(buf_snippet_name_len)

        # line (buffer)
        self.line = CString(buf_len_line)

    def reset(self, fpath_src: str, fpath_dst: t.Optional[str]):
        # TODO: also reset lune number (where IS the line number?) and so on
        # Close input file if necessary
        if self.fh_in != NULL:
            fclose(self.fh_in)
            self.fh_in = NULL

        # Open input file
        fpath_src_bs = fpath_src.encode('UTF-8')
        fh_in_str = fpath_src_bs
        self.fh_in = fopen(fh_in_str, 'rb')
        if self.fh_in == NULL:
            raise FileNotFoundError(2, f"input file '{fpath_src}' not found")

        # If overwriting the input file - generate a tempfile for output
        if not fpath_dst:
            fname_dst = tmp_file(fpath_src)
            self.tmp_file_path = CString(len(fpath_dst))

        # Close output file if necessary
        if self.fh_out != NULL:
            fclose(self.fh_out)
            self.fh_out = NULL

        # Open output file
        fname_dst_bs = fpath_dst.encode('UTF-8')
        fh_out_str = fname_dst_bs
        self.fh_out = fopen(fh_out_str, 'wb')
        if self.fh_out == NULL:
            # TODO: better error needed
            raise RuntimeError(f"failed to open output file: '{fname_dst}'")



    def __dealloc__(self):
        if self.fh_in != NULL:
            fclose(self.fh_in)
        if self.fh_out != NULL:
            fclose(self.fh_out)

    cdef repr(self):
        return (
            "#ParserState["
            "fh_in: {}, "
            "fh_out: {}, "
            "tmp_file_path: {}, "
            "snippet_start: {}, "
            "snippet_end: {}, "
            "]"
        ).format(
            '<null FILE*>' if self.fh_in == NULL else 'FILE*',
            '<null FILE*>' if self.fh_out == NULL else 'FILE*',
            self.tmp_file_path.repr() if self.tmp_file_path else '<null CString>',

            self.tag_open.repr() if self.tag_open else '<null CString>',
            self.tag_close.repr() if self.tag_close else '<null CString>',

            self.snippet_start.repr() if self.snippet_start else '<null CString>',
            self.snippet_end.repr() if self.snippet_end else '<null CString>',

            self.line.repr() if self.line else '<null CString>',
        )

    def __repr__(self):
        return self.repr()