# cython: language_level=3
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy
from libc.locale cimport setlocale, LC_ALL
from libc.stdio cimport (fopen, fclose, fwrite, fflush, feof, perror, FILE, fseek, fread)
import tempfile
from os.path import dirname as os_path_dirname, basename as os_path_basename
from os import replace as os_replace
import typing as t
import logging

log = logging.getLogger(__name__)

# C api docs: https://devdocs.io/c/

################################################################################
## DEFINITIONS
################################################################################

cdef:
    const char *FILE_READ = 'rt'
    const char *FILE_WRITE = 'wt+'
    wchar_t NEWLINE = '\n'

ctypedef unsigned int wint_t
DEF PARSER_LINEBUF_SIZ = 512

cdef extern from "stdio.h" nogil:
    char *strstr(const char *haystack, const char *needle)

cdef extern from "wchar.h" nogil:
    int wcscmp(const wchar_t *lhs, const wchar_t *rhs);
    wchar_t *fgetws(wchar_t *buf, int count, FILE *stream)
    wchar_t *wcsstr(const wchar_t *haystack, const wchar_t *needle);
    wchar_t *wcscpy(wchar_t *dest, const wchar_t *src)
    wchar_t *wcsncpy(wchar_t *dest, const wchar_t *src, size_t n);
    size_t wcslen(const wchar_t *s);  #TODO: <--- remove
    size_t wcsnlen_s(const wchar_t *s, size_t strsz);

    wchar_t *wmemset(wchar_t *dest, wchar_t ch, size_t count);
    size_t wcsrtombs(char *dst, const wchar_t ** src, size_t len, mbstate_t*ps);

    size_t WCS_WRITE_ERROR;

cdef extern from "stdlib.h" nogil:
    size_t wcstombs(char *dst, const wchar_t *src, size_t len);

cdef extern from "wctype.h" nogil:
    int iswspace(wchar_t ch)  # wint_t
    int iswlower(wint_t ch)  #wint_t

cdef extern from "wcsenc.h" nogil:
    ctypedef struct wcsenc_t:
        pass

    wcsenc_t *wcsenc_new(size_t charlen)
    void wcsenc_free(wcsenc_t *self)
    void wcsenc_reset(wcsenc_t *self)
    size_t wcsenc_encode_wcs(wcsenc_t *self, wchar_t *str, size_t len)
    size_t wcsenc_bufsiz(wcsenc_t *self)
    char *wcsenc_buf(wcsenc_t *self)


################################################################################
## Utils
################################################################################
def tmp_file(path):
    in_dir = os_path_dirname(path)
    fname = f"{os_path_basename(path)}."

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
    cdef wchar_t *new_ptr = <wchar_t *> realloc(self.ptr, (n + 1) * sizeof(wchar_t))
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

cdef inline size_t cstr_len(cstr *self) nogil:
    return self.strlen

cdef inline size_t cstr_buflen(cstr *self) nogil:
    return self.strlen * sizeof(wchar_t)

cdef inline wchar_t *cstr_ptr(cstr *self) nogil:
    return self.ptr

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
            wchar_t *s_ptr = s
            int ret = file_write(self.out, self.encoder, s_ptr, len(s))
        if ret:
            raise PytError("failed to write to file")
        self.got_newline = s.endswith('\n')

    def __dealloc__(self):
        if fflush(self.out) != 0:
            raise PytError("failed to flush output - file may miss contents")

    def __repr__(self):
        return f"<FileWriter out: {'open' if self.out != NULL else 'null'}>"

    # Use this factory method to initialize.
    # This is done because all arguments to __init__ are coerced to Python objects
    # see https://cython.readthedocs.io/en/latest/src/userguide/extension_types.html#existing-pointers-instantiation
    @staticmethod
    cdef FileWriter from_handle(FILE *fh, wcsenc_t *encoder):
        cdef FileWriter w = FileWriter.__new__(FileWriter)
        w.out = fh
        w.encoder = encoder
        # Empty snippets need no additional newline, the tags will appear on
        # separate lines by default.
        w.got_newline = True
        return w

################################################################################
## Context
################################################################################
cdef class Context:
    def __init__(self, cb: snippet_cb, src: str, dst: t.Optional[str]):
        self.src = src
        self.dst = dst or ""
        self.env = {}
        self.on_snippet = <c_snippet_cb> cb

################################################################################
## Parser
################################################################################
DEF BUF_LINE_LEN = 512
DEF BUF_SNIPPET_NAME_LEN = 80
DEF BUF_INDENT_BY_LEN = 40

cdef inline int file_write(FILE *fh, wcsenc_t *encoder, wchar_t *str, size_t strlen) nogil:
    cdef:
        size_t encoded = WCS_WRITE_ERROR
        size_t written = 0
    encoded = wcsenc_encode_wcs(encoder, str, strlen)
    if encoded == WCS_WRITE_ERROR:
        perror("Write failed. Failed to encode wide character string (wcs) to system locale")
        return -1
    written = fwrite(wcsenc_buf(encoder), sizeof(char), encoded, fh)
    if written != encoded:
        perror("Write failed. Failed to write encoded string to file")
        return -1
    return 0

def parse_result_err(PARSE_RES res) -> str:
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

        #
        self.encoder = wcsenc_new(buf_len_line)
        if self.encoder == NULL:
            raise MemoryError("allocating wide-character (wcs) converter")

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
        wcsenc_reset(self.encoder)
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
        cdef:
            wchar_t *line_ptr = self.line.ptr
        return file_write(self.fh_out, self.encoder, line_ptr, self.line.strlen)

    cdef void expand_snippet(self, Context ctx):
        cdef:
            wchar_t buf = '\0'
            FileWriter fw = FileWriter.from_handle(self.fh_out, self.encoder)
            str prefix = self.snippet_indent.ptr
            str snippet = self.snippet_start.cstr.ptr
        (<object> ctx.on_snippet)(ctx, snippet, prefix, fw)

        # ensure snippet ends with a newline
        # (so that snippet end line is printed properly)
        if not fw.got_newline:
            file_write(self.fh_out, self.encoder, &NEWLINE, 1)

    cdef PARSE_RES doparse(self, Context ctx) nogil:
        cdef int read_status = READ_OK
        # setlocale(LC_ALL, "en_GB.utf8")  # TODO: move into parser state
        setlocale(LC_ALL, "UTF-8")
        while True:
            read_status = self.readline()
            if read_status:
                if read_status == READ_ERR:
                    with gil:
                        log.error(f"READ_ERR outer")
                    return PARSE_READ_ERR
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
                read_status = self.readline()
                if read_status:
                    # TODO: investigate, is it OK to break and have outer loop
                    #       attempt to read the line again even though EOF?
                    if read_status == READ_ERR:
                        with gil:
                            log.error(f"READ_ERR inner!")
                        return PARSE_READ_ERR
                    break

                if self.snippet_find(self.snippet_end) != 0:
                    continue  # old output, skip
                if self.snippet_end.type != SNIPPET_CLOSE:
                    return PARSE_EXPECTED_SNIPPET_CLOSE

                if snippet_cmp(self.snippet_start, self.snippet_end) != 0:
                    return PARSE_SNIPPET_NAMES_MISMATCH

                with gil:
                    self.expand_snippet(ctx)
                if self.writeline() != 0:
                    return PARSE_WRITE_ERR
                break  # Done, go back to outer state

    def parse(self, cb: snippet_cb, fname_src: str, fname_dst: t.Optional[str]) -> PARSE_RES:

        cdef Context ctx = Context(cb, fname_src, fname_dst)
        self.reset(fname_src, fname_dst)

        try:
            return self.doparse(ctx)
        finally:
            # TODO: if temporary file, rename/move
            #print("TODO: iff. using tempfile - rename/overwrite old file")
            if fflush(self.fh_out) != 0:
                print("pyterror - flushing failed")
                raise PytError("flushing output failed!")
            if self.fh_out != NULL:
                fclose(self.fh_out)
                self.fh_out = NULL
            if self.fh_in != NULL:
                fclose(self.fh_in)
                self.fh_in = NULL
            if fname_dst == None:
                print("no out - overwrite input file")
                os_replace(self.tmp_file_path.ptr, fname_src)
