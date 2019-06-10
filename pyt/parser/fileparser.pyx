# cython: language_level=3
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy
from libc.locale cimport setlocale, LC_ALL
from libc.stdio cimport (fopen, fclose, fwrite, fflush, feof, perror, FILE, fseek, fread)
import tempfile
import os
import typing as t

# C api docs: https://devdocs.io/c/

################################################################################
## DEFINITIONS
################################################################################

cdef:
    const char *FILE_READ = 'rb'
    const char *FILE_WRITE = 'wb+'
    wchar_t NEWLINE = '\n'

ctypedef unsigned int wint_t
DEF PARSER_LINEBUF_SIZ = 512

cdef extern from "stdio.h" nogil:
    char *strstr(const char *haystack, const char *needle)

cdef extern from "wchar.h" nogil:
    wchar_t *fgetws(wchar_t *buf, int count, FILE *stream)
    wchar_t *wcsstr(const wchar_t *haystack, const wchar_t *needle);
    wchar_t *wcscpy(wchar_t *dest, const wchar_t *src)
    wchar_t *wcsncpy(wchar_t *dest, const wchar_t *src, size_t n);
    size_t wcslen(const wchar_t *s);  #TODO: remove
    size_t wcsnlen_s(const wchar_t *s, size_t strsz);

    wchar_t *wmemset(wchar_t *dest, wchar_t ch, size_t count);
    int wcscmp(const wchar_t *lhs, const wchar_t *rhs);

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


class PytError(Exception):
    pass


################################################################################
## CString
################################################################################
cdef struct cstr:
    size_t buflen
    wchar_t *ptr
    size_t strlen

cdef cstr *cstr_new(size_t initial_size) nogil:
    cdef cstr *self = NULL
    if initial_size == 0:
        return NULL  # TODO: interface with errno
    initial_size = initial_size + 1  # reserve space for null character

    self = <cstr *> malloc(sizeof(cstr))
    if self == NULL:
        return NULL

    self.ptr = NULL
    self.ptr = <wchar_t *> malloc(initial_size * sizeof(wchar_t))
    if self.ptr == NULL:
        free(self)
        return NULL
    wmemset(self.ptr, '\0', 1)  # terminate "string"
    self.buflen = initial_size
    self.strlen = 0
    return self

cdef void cstr_free(cstr *self) nogil:
    if self == NULL:
        return
    if self.ptr != NULL:
        free(self.ptr)
    free(self)

cdef int cstr_realloc(cstr *self, size_t n) nogil:
    new_ptr = <wchar_t *> realloc(self.ptr, (n + 1) * sizeof(wchar_t))
    if new_ptr == NULL:
        return -1
    self.buflen = n + 1
    self.ptr = new_ptr
    return 0

cdef int cstr_ncpy_wchar(cstr *self, wchar_t *src, size_t n) nogil:
    if n == 0:
        n = wcslen(src)  # does NOT include null terminator
    if n >= self.buflen:
        if cstr_realloc(self, n) != 0:
            return -1
    memcpy(self.ptr, src, n * sizeof(wchar_t))
    self.ptr[n] = '\0'
    self.strlen = n
    return 0

cdef int cstr_ncpy_unicode(cstr *self, unicode s, size_t n):
    cdef:
        wchar_t *src = s
    return cstr_ncpy_wchar(self, src, n)

cdef void cstr_reset(cstr *self) nogil:
    wmemset(self.ptr, '\0', 1)  # terminate "string"
    self.strlen = 0

cdef size_t cstr_len(cstr *self) nogil:
    return self.strlen

cdef unicode cstr_repr(cstr *self):
    if self == NULL:
        return "<null cstr*>"
    return (
        "#CString["
        "buflen: {}, "
        "strlen: {}, "
        "ptr: {}"
        "]"
    ).format(self.buflen, self.strlen, self.ptr)

################################################################################
## Snippet
################################################################################
cdef struct snippet:
    cstr *cstr
    SNIPPET_TYPE type
    size_t line_num

cdef unicode snippet_type(SNIPPET_TYPE t):
    if t == SNIPPET_NONE:
        return "SNIPPET_NONE"
    elif t == SNIPPET_OPEN:
        return "SNIPPET_OPEN"
    elif t == SNIPPET_CLOSE:
        return "SNIPPET_CLOSE"
    else:
        return "UNKNOWN_SNIPPET"

cdef snippet *snippet_new(size_t bufsiz) nogil:
    cdef:
        snippet *self = NULL
        cstr *cstr = NULL

    cstr = cstr_new(bufsiz)
    if cstr == NULL:
        return NULL

    self = <snippet *> malloc(sizeof(snippet))
    if self == NULL:
        free(cstr)
        return NULL
    self.cstr = cstr
    self.type = SNIPPET_NONE
    self.line_num = 0
    return self

cdef void snippet_reset(snippet *self) nogil:
    cstr_reset(self.cstr)
    self.type = SNIPPET_NONE
    self.line_num = 0

cdef void snippet_free(snippet *self) nogil:
    if self.cstr != NULL:
        cstr_free(self.cstr)
    free(self)

cdef int snippet_cmp(snippet *lhs, snippet *rhs) nogil:
    return wcscmp(lhs.cstr.ptr, rhs.cstr.ptr)

cdef unicode snippet_repr(snippet *self):
    if self == NULL:
        return "<null snippet*>"
    return (
        "#snippet["
        "cstr: {}, "
        "type: {}, "
        "line_num: {}"
        "]"
    ).format(cstr_repr(self.cstr), snippet_type(self.type), self.line_num)

################################################################################
## FileWriter
################################################################################
cdef class FileWriter:
    cpdef void write(self, str s):
        cdef:
            size_t written = 0
            wchar_t *ss = s  # TODO: look into this, does it work?
        if fwrite(ss, sizeof(wchar_t) * len(s), 1, self.out) != 1:
            raise PytError("write failed")
        return

    def __dealloc__(self):
        if fflush(self.out) != 0:
            raise PytError("failed to flush output - file may miss contents")

    def __repr__(self):
        return f"<FileWriter out: {'open' if self.out != NULL else 'null'}>"

    # Use this factory method to initialize.
    # This is done because all arguments to __init__ are coerced to Python objects
    # see https://cython.readthedocs.io/en/latest/src/userguide/extension_types.html#existing-pointers-instantiation
    @staticmethod
    cdef FileWriter from_handle(FILE *fh):
        cdef FileWriter w = FileWriter.__new__(FileWriter)
        w.out = fh
        return w

################################################################################
## Context
################################################################################
cdef class Context:
    def __init__(self, cb: snippet_cb, src: str, dst: str):
        self.src = src
        self.dst = dst
        self.env = {}
        self.on_snippet = <c_snippet_cb> cb

################################################################################
## Parser
################################################################################
DEF BUF_LINE_LEN = 512
DEF BUF_SNIPPET_NAME_LEN = 80
DEF BUF_INDENT_BY_LEN = 40

ctypedef unsigned int PARSE_RES
cdef enum:
    PARSE_OK = 0
    PARSE_READ_ERR = 1  # test - permissions issues
    PARSE_WRITE_ERR = 2
    PARSE_EXPECTED_SNIPPET_OPEN = 3
    PARSE_EXPECTED_SNIPPET_CLOSE = 4
    PARSE_SNIPPET_NAMES_MISMATCH = 5

cdef unicode parse_result_err(PARSE_RES res):
    if res == PARSE_OK:
        return "Parse OK"
    elif res == PARSE_READ_ERR:
        return "Failed to read from input file"
    elif res == PARSE_WRITE_ERR:
        return "Failed to write to output file"
    elif res == PARSE_EXPECTED_SNIPPET_OPEN:
        return "Unexpected tag, expected a snippet open tag"
    elif res == PARSE_EXPECTED_SNIPPET_CLOSE:
        return "Unexpected tag, expected a snippet close tag"
    elif res == PARSE_SNIPPET_NAMES_MISMATCH:
        return "open and close tags do not have matching names - nesting error?"
    else:
        return "Unknown parse error!"

cdef enum:
    READ_EOF = -1
    READ_OK = 0
    READ_ERR = 1
    READ_LINE_TOO_LONG = 2

# TODO: is it OK that tag_open == tag_close (e.g. '@@')
cdef class Parser:
    def __init__(
            self,
            tag_open: str = '<@@', tag_close: str = '@@>',
            size_t buf_len_line = BUF_LINE_LEN,
            size_t buf_snippet_name_len = BUF_SNIPPET_NAME_LEN,
            size_t buf_indent_by_len = BUF_INDENT_BY_LEN):
        self.fh_in = self.fh_out = NULL

        if buf_len_line <= 0:
            raise ValueError("buf_len_line must be positive")

        #self.tmp_file_path = CString(250)
        self.tmp_file_path = cstr_new(250)
        if self.tmp_file_path == NULL:
            raise MemoryError("allocating tmp_file_path")

        # tag_open (e.g. '<@@')
        self.tag_open = cstr_new(len(tag_open))
        if self.tag_open == NULL:
            raise MemoryError("allocating tag_open")
        if cstr_ncpy_unicode(self.tag_open, tag_open, len(tag_open)) != 0:
            raise MemoryError("tag_open")

        # tag_close (e.g. '@@>')
        self.tag_close = cstr_new(len(tag_close))
        if self.tag_close == NULL:
            raise MemoryError("allocating tag_close")
        if cstr_ncpy_unicode(self.tag_close, tag_close, len(tag_close)) != 0:
            raise MemoryError("tag_close")

        # snippet_start
        self.snippet_start = snippet_new(buf_snippet_name_len)
        if self.snippet_start == NULL:
            raise MemoryError("allocating snippet_start")

        # snippet_end
        self.snippet_end = snippet_new(buf_snippet_name_len)
        if self.snippet_end == NULL:
            raise MemoryError("allocating snippet_end")

        # line (buffer)
        self.line = cstr_new(buf_len_line)
        if self.line == NULL:
            raise MemoryError("allocating line")
        self.line_num = 0

        # snippet indentation (buffer)
        self.snippet_indent = cstr_new(buf_len_line)
        if self.snippet_indent == NULL:
            raise MemoryError("allocating snippet indentation prefix")

    def reset(self, fpath_src: str, fpath_dst: t.Optional[str]):
        # If overwriting the input file - generate a tempfile for output
        cstr_reset(self.tmp_file_path)
        if not fpath_dst:
            fpath_dst = tmp_file(fpath_src)
            if cstr_ncpy_unicode(self.tmp_file_path, fpath_dst, len(fpath_dst)) != 0:
                raise MemoryError("failed to copy string to tmp_file_path")

        # Close input file if necessary
        if self.fh_in != NULL:
            fclose(self.fh_in)
            self.fh_in = NULL

        self.line_num = 0

        # Open input file
        fpath_src_bs = fpath_src.encode('UTF-8')
        fh_in_str = fpath_src_bs
        self.fh_in = fopen(fh_in_str, FILE_READ)
        if self.fh_in == NULL:
            raise FileNotFoundError(2, f"input file '{fpath_src}' not found")

        # Close output file if necessary
        if self.fh_out != NULL:
            fclose(self.fh_out)
            self.fh_out = NULL

        # Open output file
        fname_dst_bs = fpath_dst.encode('UTF-8')
        fh_out_str = fname_dst_bs
        self.fh_out = fopen(fh_out_str, FILE_WRITE)
        if self.fh_out == NULL:
            # TODO: better error needed
            raise RuntimeError(f"failed to open output file: '{fpath_dst}'")

        snippet_reset(self.snippet_start)
        snippet_reset(self.snippet_end)

        cstr_reset(self.line)
        self.line_num = 0
        cstr_reset(self.snippet_indent)

    def __dealloc__(self):
        if self.fh_in != NULL:
            fclose(self.fh_in)
        if self.fh_out != NULL:
            fclose(self.fh_out)

        if self.tmp_file_path != NULL:
            cstr_free(self.tmp_file_path)

        if self.tag_open != NULL:
            cstr_free(self.tag_open)
        if self.tag_close != NULL:
            cstr_free(self.tag_close)

        if self.snippet_start != NULL:
            snippet_free(self.snippet_start)
        if self.snippet_end != NULL:
            snippet_free(self.snippet_end)

        if self.line != NULL:
            cstr_free(self.line)

        if self.snippet_indent != NULL:
            cstr_free(self.snippet_indent)

    cdef repr(self):
        return (
            "#Parser["
            "\n\tfh_in: {}, "
            "\n\tfh_out: {}, "
            "\n\ttmp_file_path: {}, "
            "\n\ttag_open: {}, "
            "\n\ttag_close: {}, "
            "\n\tsnippet_start: {}, "
            "\n\tsnippet_end: {}, "
            "\n\tline: {}"
            "\n\tlinenum: {}"
            "\n\tsnippet indent: {}"
            "]"
        ).format(
            '<null FILE*>' if self.fh_in == NULL else 'FILE*',
            '<null FILE*>' if self.fh_out == NULL else 'FILE*',
            cstr_repr(self.tmp_file_path),
            cstr_repr(self.tag_open),
            cstr_repr(self.tag_close),
            snippet_repr(self.snippet_start),
            snippet_repr(self.snippet_end),
            cstr_repr(self.line),
            self.line_num,
            cstr_repr(self.snippet_indent)
        )

    def __repr__(self):
        return self.repr()

    cdef int cpy_snippet_indentation(self) nogil:
        cdef:
            wchar_t *start = self.line.ptr
            wchar_t *end = NULL
        end = start
        while iswspace(end[0]):
            end += 1
        return cstr_ncpy_wchar(self.snippet_indent, start, end - start)

    cdef int snippet_find(self, snippet *dst) nogil:
        cdef:
            wchar_t *start = NULL
            wchar_t *end = NULL
            SNIPPET_TYPE typ = SNIPPET_OPEN
            int ret = 0
        start = wcsstr(self.line.ptr, self.tag_open.ptr)
        if start == NULL:
            # print("snippet_find start")
            return -1

        # advance beyond the snippet prefix itself
        start = start + self.tag_open.strlen

        # tag sits at the end of the line-buffer, abort
        if (start - self.line.ptr) >= self.line.buflen:
            # print("snippet_find OOB")
            return -1

        if start[0] == '/':  # end snippet, advance past slash, too
            typ = SNIPPET_CLOSE
            start = start + 1

        # find snippet suffix, use 'start' to enforce ordering of tags
        # and limit the search scope.
        end = wcsstr(start, self.tag_close.ptr)
        if end == NULL:
            # print("snippet_find end")
            return -1

        ret = cstr_ncpy_wchar(dst.cstr, start, end - start)
        if ret != 0:
            # print("snippet_find cpy")
            return ret
        dst.type = typ
        dst.line_num = self.line_num
        return 0

    cdef int readline(self) nogil:
        cdef:
            wchar_t *start = self.line.ptr
            size_t buflen = self.line.buflen
            size_t n_total_read = 0
            size_t n_iter_read = 0

        while True:
            if not fgetws(start, buflen, self.fh_in):
                if feof(self.fh_in):
                    return READ_EOF
                return READ_ERR
            n_iter_read = wcslen(start)
            if n_iter_read != (buflen - 1):
                self.line.strlen = n_total_read + n_iter_read
                break
            if cstr_realloc(self.line, self.line.buflen * 2) != 0:
                return READ_ERR
            n_total_read += n_iter_read
            start = self.line.ptr + n_total_read
            buflen = self.line.buflen - n_total_read
        return READ_OK

    cdef int writeline(self) nogil:
        cdef size_t nchars_written = -1
        nchars_written = fwrite(self.line.ptr, sizeof(wchar_t) * self.line.strlen, 1, self.fh_out)
        if nchars_written != 1:
            perror("write failed")
            return -1
        return 0

    cdef void expand_snippet(self, Context ctx):
        cdef wchar_t buf = '\0'
        cdef FileWriter fw = FileWriter.from_handle(self.fh_out)
        cdef str prefix = self.snippet_indent.ptr
        (<object> ctx.on_snippet)(ctx, prefix, fw)

        # ensure snippet ends with a newline
        # (so that snippet end line is printed properly)
        fseek(self.fh_out, -sizeof(wchar_t), 1)
        fread(&buf, sizeof(wchar_t), 1, self.fh_out)
        if buf != '\n':
            fwrite(&NEWLINE, sizeof(wchar_t), 1, self.fh_out)

    cdef PARSE_RES doparse(self, Context ctx) nogil:
        cdef int ret = READ_OK
        setlocale(LC_ALL, "en_GB.utf8")  # TODO: move into parser state
        while True:
            ret = self.readline()
            if ret:
                break

            if self.writeline() != 0:
                return PARSE_WRITE_ERR
            # line written to new file - if not a snippet start - skip to next
            if self.snippet_find(self.snippet_start) != 0:
                continue
            if self.snippet_start.type != SNIPPET_OPEN:
                return PARSE_EXPECTED_SNIPPET_OPEN
            self.cpy_snippet_indentation()

            while True:  # Got the opening snippet, look for closing snippet
                ret = self.readline()
                if ret:
                    # TODO: investigate, is it OK to break and have outer loop
                    #       attempt to read the line again even though EOF?
                    break

                if self.snippet_find(self.snippet_end) != 0:
                    continue  # old output, skip
                if self.snippet_end.type != SNIPPET_CLOSE:
                    return PARSE_EXPECTED_SNIPPET_CLOSE

                if snippet_cmp(self.snippet_start, self.snippet_end) != 0:
                    return PARSE_SNIPPET_NAMES_MISMATCH

                #print(f"SNIPPET '{self.snippet_start.cstr.ptr}' from {self.snippet_start.line_num}-{self.snippet_end.line_num}")
                # TODO: run snippet code, write in the results here
                # TODO: also - expand output to be aligned with snippet indentation
                with gil:
                    self.expand_snippet(ctx)
                if self.writeline() != 0:
                    return PARSE_WRITE_ERR
                break  # Done, go back to outer state

    def parse(self, cb: snippet_cb, fname_src: str, fname_dst: t.Optional[str]) -> t.Optional[str]:
        cdef PARSE_RES res = PARSE_OK
        cdef Context ctx = Context(cb, fname_src, fname_dst)
        self.reset(fname_src, fname_dst)

        try:
            res = self.doparse(ctx)
            if res != PARSE_OK:
                return parse_result_err(res)
        finally:
            # TODO: if temporary file, rename/move
            print("TODO: iff. using tempfile - rename/overwrite old file")
            if fflush(self.fh_out) != 0:
                print("pyterror - flushing failed")
                raise PytError("flushing output failed!")
