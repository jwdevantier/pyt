# cython: language_level=3
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport strcpy, memcpy
from libc.locale cimport setlocale, LC_ALL
from libc.stdio cimport (
fopen, fclose, fgets, fwrite, ftell, fseek, feof,
SEEK_SET, SEEK_CUR, SEEK_END, FILE)
import tempfile
import os
import typing as t

ctypedef unsigned int wint_t

cdef extern from "stdio.h" nogil:
    char *strstr(const char *haystack, const char *needle)

cdef extern from "wchar.h" nogil:
    ctypedef Py_UNICODE wchar_t
    wchar_t *fgetws(wchar_t *buf, int count, FILE *stream)
    wchar_t *wcsstr(const wchar_t *dest, const wchar_t *src)
    wchar_t *wcscpy(wchar_t *dest, const wchar_t *src)
    wchar_t *wcsncpy(wchar_t *dest, const wchar_t *src, size_t n);
    size_t wcslen(const wchar_t *s);

cdef extern from "wctype.h" nogil:
    int iswspace(wchar_t ch)  # wint_t
    int iswlower(wint_t ch)  #wint_t

class PytError(Exception):
    pass


cdef size_t count_indent_chars(wchar_t *s):
    # calculate number of leading whitespace characters
    cdef:
        size_t indent_chars = 0
        wchar_t *pos = s
    while True:
        print(f"count_indent_chars iter: '{pos[0]}'")
        if pos[0] == '\n' or not iswspace(pos[0]):
            break
        pos = pos + 1
        indent_chars = indent_chars + 1
    return indent_chars

cdef enum:
    TAG_OPEN = 1
    TAG_CLOSE = 2

cdef int tag_type(wchar_t *tag):
    if tag[2] == '/':
        return TAG_CLOSE
    return TAG_OPEN

#cdef cstring *snippet_name()

# C api docs: https://devdocs.io/c/io/fopen

def tmp_file(path):
    in_dir = os.path.dirname(path)
    fname = f"{os.path.basename(path)}."

    tf = tempfile.NamedTemporaryFile(
        dir=in_dir, prefix=fname, suffix='.tmp', delete=False)
    fname = tf.name
    tf.close()
    return fname

cdef struct cstring:
    size_t buflen
    wchar_t *buf
    size_t strlen

cdef cstring *cstring_new(size_t initial_size):
    cdef:
        cstring *cstr = NULL
        wchar_t *cbuf = NULL
    if initial_size == 0:
        return NULL
    cstr = <cstring *> malloc(sizeof(cstring))
    if cstr == NULL:
        return NULL

    cstr.buf = NULL
    cstr.buf = <wchar_t *> malloc(initial_size * sizeof(wchar_t))
    if cstr.buf == NULL:
        free(cstr)
        return NULL
    cstr.buflen = initial_size
    cstr.strlen = 0
    return cstr

cdef void cstring_free(cstring *cstr):
    if cstr == NULL:
        return
    if cstr.buf != NULL:
        free(cstr.buf)
    free(cstr)

cdef int cstring_ncpy_wchar(cstring *dst, wchar_t *src, size_t n):
    cdef wchar_t *new_ptr = NULL
    if n == 0:
        # print("cstring_ncpy_wchar: determine wchar length by wcslen")
        n = wcslen(src)
        # print(f"wchar_t* length: {n}")
    if n >= dst.buflen:
        # print("cstring: realloc")
        new_ptr = <wchar_t *> realloc(dst.buf, (n + 1) * sizeof(wchar_t))
        if new_ptr == NULL:
            return -1
        dst.buflen = n + 1
        dst.buf = new_ptr
        # print("realloc done")
    memcpy(dst.buf, src, n * sizeof(wchar_t))
    dst.buf[n] = '\n'
    dst.strlen = n

cdef int cstring_ncpy_unicode(cstring *dst, unicode s, size_t n):
    cdef:
        wchar_t *src = s
        wchar_t *new_ptr = NULL
    if n == 0:
        n = wcslen(src)
    if n >= dst.buflen:
        # realloc needed
        new_ptr = <wchar_t *> realloc(dst.buf, (n + 1) * sizeof(wchar_t))
        if new_ptr == NULL:
            return -1
        dst.buflen = n + 1
        dst.buf = new_ptr
    memcpy(dst.buf, src, n * sizeof(wchar_t))
    dst.buf[n] = '\n'
    dst.strlen = n

cdef size_t cstring_len(cstring *dst):
    return dst.strlen

cdef unicode cstring_2_py(cstring *cstr):
    return cstr.buf[:cstr.strlen]

cdef unicode cstring_repr(cstring *cstr):
    if cstr == NULL:
        return "<null (cstring*)>"
    return "#cstring(buflen: {}, strlen: {}, buf: {})".format(
        cstr.buflen, cstr.strlen,
        '<null>' if cstr.buf == NULL else cstr.buf[:cstr.strlen]
    )

cdef struct ParseState:
    FILE *fh_in
    FILE *fh_out
    #char *tmp_file_path
    cstring *tmp_file_path
    size_t line_num

    #cstring *tag_open
    #cstring *tag_close
    size_t buflen
    wchar_t *buf

cdef unicode state_repr(ParseState *state):
    if state == NULL:
        return "<null (ParseState*)>"
    return (
        "#ParseState("
        "fh_in: {}, "
        "fh_out: {}, "
        "tmp_file_path: {}, "
        "line_num: {}, "
        "buflen: {}, "
        "buf: {}"
        ")").format(
        '<null (FILE*)>' if (state.fh_in == NULL) else 'FILE*',
        '<null (FILE*)>' if (state.fh_out == NULL) else 'FILE*',
        cstring_repr(state.tmp_file_path),
        state.line_num,
        state.buflen,
        '<null (wchar_t*)>' if (state.buf == NULL) else state.buf)

cdef enum:
    READ_EOF = -1
    READ_OK = 0
    READ_ERR = 1

cdef int readline(ParseState *state):
    # Read new line into buffer, advance linenumber if OK
    # signal errors otherwise (READ_ERR, READ_EOF)
    # print(f"readline: fgets(buf, buflen: {state.buflen}, fh_in)")
    if not fgetws(state.buf, state.buflen, state.fh_in):
        if feof(state.fh_in):
            print("readline: READ_EOF")
            return READ_EOF
        print("readline: READ_ERR")
        return READ_ERR
    state.line_num = state.line_num + 1
    print("readline: READ_OK")
    return READ_OK

cdef ParseState *state_new():
    cdef ParseState *state = NULL
    print("state_new: called")
    state = <ParseState *> malloc(sizeof(ParseState))
    if not state:
        raise MemoryError("failed to allocate ParseState object")
    state.fh_in = state.fh_out = state.tmp_file_path = state.buf = NULL
    state.buflen = state.line_num = 0

    print("state_new: returning")
    return state

cdef int state_init(
        ParseState *state,
        fname_src: str, fname_dst: t.Optional[str],
        buflen: int) except -1:
    cdef:
        char *fname_out = NULL
        char *fname_in = NULL
    print("state_init called")
    print("state_init: 1")
    if not state:
        raise MemoryError("expected to get an initialized state object")
    if buflen <= 0:
        raise ValueError("buflen must be a positive integer")
    state.buflen = buflen
    print("state_init: 2")

    fname_src_bs = fname_src.encode('UTF-8')
    fname_in = fname_src_bs
    print("state_init: 3")
    state.fh_in = fopen(fname_in, 'rb')
    if state.fh_in == NULL:
        raise FileNotFoundError(2, f"Input file not found:'{fname_src}'")
    print("state_init: 4")

    if not fname_dst:
        overwriting = True
        fname_dst = tmp_file(fname_src)
        state.tmp_file_path = cstring_new(len(fname_dst) + 1)
        if not state.tmp_file_path:
            raise MemoryError("tmp_file_path: failed to allocate cstring")
        cstring_ncpy_unicode(state.tmp_file_path, fname_dst, len(fname_dst))
    else:
        overwriting = False

    fname_dst_bs = fname_dst.encode('UTF-8')
    fname_out = fname_dst_bs
    print("opening '" + fname_dst + "'")
    state.fh_out = fopen(fname_out, 'wb')

    if state.fh_out == NULL:
        # TODO: find better error
        raise RuntimeError(f"Failed to open output file: '{fname_dst}'")

    #state.buf = <char *> malloc(buflen * sizeof(char))
    state.buf = <wchar_t *> malloc(buflen * sizeof(wchar_t))
    if not state.buf:
        raise MemoryError("failed to allocate line buffer")
    return 0

cdef state_free(ParseState *state):
    print("state_free called")
    if state.fh_in != NULL:
        fclose(state.fh_in)

    print("state_free fh_in closed")
    if state.fh_out != NULL:
        fclose(state.fh_out)
    print("state_free fh_out closed")
    if state.buf != NULL:
        free(state.buf)
    print("state_free buf freed")
    if state.tmp_file_path != NULL:
        cstring_free(state.tmp_file_path)

    free(state)

cdef int get_snippet_name(cstring *dst, ParseState *state):
    cdef:
        size_t offset = 0
        wchar_t *pos = state.buf

    while offset <= dst.buflen:
        pass
    return -1 if (offset > dst.buflen) else 0

cdef int do_read_file(ParseState *state) except -1:
    cdef:
        int ret = READ_OK
        wchar_t *match_start = NULL
        cstring *line_prefix = NULL
        cstring *snippet_name = NULL
        size_t indentation = 0
    print("do_read_file: called")
    setlocale(LC_ALL, "en_GB.utf8")

    try:
        while not ret:
            print("do_read_file: iter")
            ret = readline(state)
            if ret:
                print("do_read_file: iter BREAK")
                break
            match_start = wcsstr(state.buf, "<@")
            if match_start != NULL:
                #begin - extract snippet name
                if tag_type(match_start) == TAG_CLOSE:
                    raise PytError("unexpected closing tag!")
                indentation = count_indent_chars(state.buf)
                if line_prefix == NULL:
                    line_prefix = cstring_new(indentation + 1)
                    if not line_prefix:
                        raise PytError("line_prefix: failed to allocate cstring")
                if snippet_name == NULL:
                    snippet_name = cstring_new(100 + 1)  # plenty for most
                    if not snippet_name:
                        raise PytError("snippet_name: failed to allocate cstring")
                cstring_ncpy_wchar(line_prefix, state.buf, indentation)
                print(f"indentation({indentation}): '{cstring_2_py(line_prefix)}' (len: {cstring_len(line_prefix)})")
                # TODO: extract snippet name
                # TODO: keep consuming file (DON'T WRITE) until closing tag is reached
                # TODO: call generator, insert output into file.
                # TODO: break and continue anew.

                print("match - got <@ in line:")
                print(f"match: {match_start}")
                #print(f"indentation: {count_indent_chars(state.buf)}")
                #print(f"indentation: ")
    finally:
        if line_prefix != NULL:
            cstring_free(line_prefix)
        if snippet_name != NULL:
            cstring_free(snippet_name)

def read_file(fname_src: str, fname_dst: str = ''):
    cdef:
        ParseState *state = NULL
    print("pre state make")

    state = state_new()
    try:
        print("WTFH")
        state_init(state, fname_src, fname_dst, 512)
        do_read_file(state)

    except Exception as e:
        print("exception")
        if state != NULL and state.tmp_file_path != NULL:
            print("cleanup tmp")
            os.remove(state.tmp_file_path.buf)
        raise e
    finally:
        print("finally")
        # TODO: enable this - warning! will overwrite files then!
        #os.replace(fname_src, state.tmp_file_path.buf)
        print("STATE")
        print(state_repr(state))
        state_free(state)
