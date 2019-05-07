# cython: language_level=3
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcpy
from libc.locale cimport setlocale, LC_ALL
from libc.stdio cimport (fopen, fclose, feof, FILE)
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
    ctypedef Py_UNICODE wchar_t
    wchar_t *fgetws(wchar_t *buf, int count, FILE *stream)
    wchar_t *wcsstr(const wchar_t *haystack, const wchar_t *needle);
    wchar_t *wcscpy(wchar_t *dest, const wchar_t *src)
    wchar_t *wcsncpy(wchar_t *dest, const wchar_t *src, size_t n);
    size_t wcslen(const wchar_t *s);
    wchar_t *wmemset( wchar_t *dest, wchar_t ch, size_t count );

cdef extern from "wctype.h" nogil:
    int iswspace(wchar_t ch)  # wint_t
    int iswlower(wint_t ch)  #wint_t

################################################################################
## C-Strings
################################################################################
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
    initial_size = initial_size + 1 # set aside space for NULL
    cstr = <cstring *> malloc(sizeof(cstring))
    if cstr == NULL:
        return NULL

    cstr.buf = NULL
    cstr.buf = <wchar_t *> malloc(initial_size * sizeof(wchar_t))
    if cstr.buf == NULL:
        free(cstr)
        return NULL
    wmemset(cstr.buf, '\0', 1) # NULL it out
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
        n = wcslen(src) # does not include NULL
        # print(f"wchar_t* length: {n}")
    if n >= dst.buflen:
        # print("cstring_ncpy_wchar: realloc needed")
        new_ptr = <wchar_t *> realloc(dst.buf, (n + 1) * sizeof(wchar_t))
        if new_ptr == NULL:
            return -1
        dst.buflen = n + 1
        dst.buf = new_ptr
        # print("realloc done")
    memcpy(dst.buf, src, n * sizeof(wchar_t))
    dst.buf[n] = '\0'
    dst.strlen = n
    return 0

cdef int cstring_ncpy_unicode(cstring *dst, unicode s, size_t n):
    cdef:
        wchar_t *src = s
        wchar_t *new_ptr = NULL
    if n == 0:
        n = wcslen(src)
    if n >= dst.buflen:
        # print("cstring_ncpy_unicode: realloc needed")
        # realloc needed
        new_ptr = <wchar_t *> realloc(dst.buf, (n + 1) * sizeof(wchar_t))
        if new_ptr == NULL:
            return -1
        dst.buflen = n + 1
        dst.buf = new_ptr
    memcpy(dst.buf, src, n * sizeof(wchar_t))
    dst.buf[n] = '\0'
    dst.strlen = n
    return 0

cdef void cstring_clear(cstring *cstr):
    cstr.buf[0] = '\0'
    cstr.strlen = 0

cdef size_t cstring_len(cstring *dst):
    return dst.strlen

cdef unicode cstring_repr(cstring *cstr):
    if cstr == NULL:
        return "<null (cstring*)>"
    return "#cstring(buflen: {}, strlen: {}, buf: {})".format(
        cstr.buflen, cstr.strlen,
        '<null>' if cstr.buf == NULL else cstr.buf
    )

################################################################################
## Snippet
################################################################################
cdef enum SNIPPET_TYPE:
    SNIPPET_NONE
    SNIPPET_OPEN
    SNIPPET_CLOSE

cdef struct snippet:
    cstring *cstr
    SNIPPET_TYPE type

cdef snippet *snippet_new(size_t bufsiz):
    cdef:
        snippet *s = NULL
        cstring *cstr = NULL

    cstr = cstring_new(bufsiz)
    if cstr == NULL:
        return NULL

    s = <snippet *>malloc(sizeof(snippet))
    if s == NULL:
        free(cstr)
        return NULL
    s.cstr = cstr
    s.type = SNIPPET_NONE
    return s

cdef void snippet_clear(snippet *s):
    cstring_clear(s.cstr)
    s.type = SNIPPET_NONE

cdef void snippet_free(snippet *s):
    if s.cstr != NULL:
        cstring_free(s.cstr)
    free(s)

cdef int snippet_find(snippet *dst, ParseState *state):
    cdef:
        wchar_t *start = NULL
        wchar_t *end = NULL
        SNIPPET_TYPE typ = SNIPPET_OPEN
        int ret = 0
    start = wcsstr(state.buf, state.tag_open.buf)
    if start == NULL:
        print("snippet_find start")
        return -1

    # advance beyond the snippet prefix itself
    start = start + state.tag_open.strlen

    # tag sits at the end of the line-buffer, abort
    if (start - state.buf) >= state.buflen:
        print("snippet_find OOB")
        return -1

    if start[0] == '/': # end snippet, advance past slash, too
        typ = SNIPPET_CLOSE
        start = start +1

    # find snippet suffix, use 'start' to enforce ordering of tags
    # and limit the search scope.
    end = wcsstr(start, state.tag_close.buf)
    if end == NULL:
        print("snippet_find end")
        return -1

    ret = cstring_ncpy_wchar(dst.cstr, start, end-start)
    if ret != 0:
        print("snippet_find cpy")
        return ret
    dst.type = typ
    return 0

################################################################################
## Other
################################################################################
class PytError(Exception):
    pass


cdef size_t count_indent_chars(wchar_t *s):
    # calculate number of leading whitespace characters
    cdef:
        size_t indent_chars = 0
        wchar_t *pos = s
    while True:
        # print(f"count_indent_chars iter: '{pos[0]}'")
        if pos[0] == '\n' or not iswspace(pos[0]):
            break
        pos = pos + 1
        indent_chars = indent_chars + 1
    return indent_chars



def tmp_file(path):
    in_dir = os.path.dirname(path)
    fname = f"{os.path.basename(path)}."

    tf = tempfile.NamedTemporaryFile(
        dir=in_dir, prefix=fname, suffix='.tmp', delete=False)
    fname = tf.name
    tf.close()
    return fname


cdef struct ParseState:
    FILE *fh_in
    FILE *fh_out
    cstring *tmp_file_path
    size_t line_num

    cstring *tag_open
    cstring *tag_close
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
        "tag_open: {}, "
        "tag_close: {}, "
        "buflen: {}, "
        "buf: {}"
        ")").format(
        '<null (FILE*)>' if (state.fh_in == NULL) else 'FILE*',
        '<null (FILE*)>' if (state.fh_out == NULL) else 'FILE*',
        cstring_repr(state.tmp_file_path),
        state.line_num,
        cstring_repr(state.tag_open),
        cstring_repr(state.tag_close),
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
            # print("readline: READ_EOF")
            return READ_EOF
        # print("readline: READ_ERR")
        return READ_ERR
    state.line_num = state.line_num + 1
    # print("readline: READ_OK")
    return READ_OK

cdef ParseState *state_new():
    cdef ParseState *state = NULL
    print("state_new: called")
    state = <ParseState *> malloc(sizeof(ParseState))
    if not state:
        raise MemoryError("failed to allocate ParseState object")
    state.fh_in = state.fh_out = NULL
    state.tmp_file_path = state.tag_open = state.tag_close = state.buf = NULL
    state.buflen = state.line_num = 0

    print("state_new: returning")
    return state

cdef int state_init(
        ParseState *state,
        fname_src: str, fname_dst: t.Optional[str],
        tag_open: str, tag_close: str,
        buflen: int) except -1:
    # Initialize state_init struct - WARNING: does *not* clean up on failure, use state_free!
    cdef:
        char *fname_out = NULL
        char *fname_in = NULL
    print("state_init called")
    # print("state_init: 1")
    if state == NULL:
        raise MemoryError("expected to get an initialized state object")
    if buflen <= 0:
        raise ValueError("buflen must be a positive integer")
    state.buflen = buflen
    # print("state_init: 2")

    # Open input file
    fname_src_bs = fname_src.encode('UTF-8')
    fname_in = fname_src_bs
    state.fh_in = fopen(fname_in, 'rb')
    if state.fh_in == NULL:
        raise FileNotFoundError(2, f"Input file not found:'{fname_src}'")
    # print("state_init: fh_in opened")

    # If overwriting the input file - generate a tempfile for output
    if not fname_dst:
        overwriting = True
        fname_dst = tmp_file(fname_src)
        state.tmp_file_path = cstring_new(len(fname_dst))
        if not state.tmp_file_path:
            raise MemoryError("tmp_file_path: failed to allocate cstring")
        cstring_ncpy_unicode(state.tmp_file_path, fname_dst, len(fname_dst))
    else:
        overwriting = False

    # Open output file
    fname_dst_bs = fname_dst.encode('UTF-8')
    fname_out = fname_dst_bs
    state.fh_out = fopen(fname_out, 'wb')
    if state.fh_out == NULL:
        # TODO: find better error
        raise RuntimeError(f"Failed to open output file: '{fname_dst}'")
    # print("state_init: fh_out('" + fname_dst + "') opened")

    # allocate tag_open cstring
    state.tag_open = cstring_new(len(tag_open))
    if state.tag_open == NULL:
        raise MemoryError("state_init: failed to allocate tag_open cstring")
    if cstring_ncpy_unicode(state.tag_open, tag_open, len(tag_open)) != 0:
        raise MemoryError("state_init: failed to init tag_open cstring")
    # print(f"c len(tag_open): {len(tag_open)} ('{tag_open}')")

    # allocate tag_close cstring
    state.tag_close = cstring_new(len(tag_close))
    if state.tag_close == NULL:
        raise MemoryError("state_init: failed to allocate tag_close cstring")
    if cstring_ncpy_unicode(state.tag_close, tag_close, len(tag_close)) != 0:
        raise MemoryError("state_init: failed to init tag_open cstring")

    # Allocate line buffer
    state.buf = <wchar_t *> malloc(buflen * sizeof(wchar_t))
    if not state.buf:
        raise MemoryError("failed to allocate line buffer")

    print("state_init returning")
    return 0

cdef state_free(ParseState *state):
    print("state_free called")

    # Close input file
    if state.fh_in != NULL:
        fclose(state.fh_in)

    # Close output file
    if state.fh_out != NULL:
        fclose(state.fh_out)

    # Free tmp_file_path cstring
    if state.tmp_file_path != NULL:
        cstring_free(state.tmp_file_path)

    # Free tag_open cstring
    if state.tag_open != NULL:
        cstring_free(state.tag_open)

    # Free tag_close cstring
    if state.tag_close != NULL:
        cstring_free(state.tag_close)

    # Free line buffer
    if state.buf != NULL:
        free(state.buf)

    # Finally, free state struct itself
    print("state_free finished")
    free(state)

cdef int do_read_file(ParseState *state) except -1:
    cdef:
        int ret = READ_OK
        wchar_t *match_start = NULL
        cstring *line_prefix = NULL
        snippet *s_open = snippet_new(70)
        snippet *s_close = snippet_new(70)
        size_t indentation = 0
    print("do_read_file: called")
    if s_open == NULL or s_close == NULL:
        raise PytError("failed to allocate memory for s_open/s_close")
    setlocale(LC_ALL, "en_GB.utf8")

    print(f"match open '{state.tag_open.buf}', close: '{state.tag_close.buf}'")

    try:
        while not ret:
            print("do_read_file: iter")
            ret = readline(state)
            if ret:
                print("do_read_file: iter BREAK")
                break

            match_start = wcsstr(state.buf, state.tag_open.buf)
            print(f"line: '{state.buf}': {'no match' if match_start == NULL else 'match'}")
            if match_start != NULL:
                #begin - extract snippet name
                print("MATCH")
                # TODO: rewrite - must actually match a full close tag
                #if wcsstr(state.buf, state.tag_close.buf) != NULL:
                #    raise PytError("..unexpected close tag!")
                indentation = count_indent_chars(state.buf)
                if line_prefix == NULL:
                    line_prefix = cstring_new(indentation + 1)
                    if not line_prefix:
                        raise PytError("line_prefix: failed to allocate cstring")
                # TODO: REFACTOR SNIPPET EXTRACTION CODE
                if snippet_find(s_open, state) == 0:
                    print(f"snippet: {s_open.cstr.buf}")
                cstring_ncpy_wchar(line_prefix, state.buf, indentation)
                print(f"indentation({indentation}): '{line_prefix.buf}' (len: {cstring_len(line_prefix)})")
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
        if s_open != NULL:
            snippet_free(s_open)
        if s_close != NULL:
            snippet_free(s_close)
    return 0

def read_file(
        fname_src: str, fname_dst: t.Optional[str],
        tag_open: str, tag_close: str):
    cdef:
        ParseState *state = NULL
    if not fname_dst:
        fname_dst = ''
    print("pre state make")

    state = state_new()
    try:
        state_init(state, fname_src, fname_dst, tag_open, tag_close, PARSER_LINEBUF_SIZ)
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
