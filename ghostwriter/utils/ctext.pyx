# would ignore/fix each 'empty' line (whitespace-only)
from libc.limits cimport INT_MAX
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
from libc.string cimport memcpy

ctypedef Py_UNICODE wchar_t


cdef extern from "wctype.h" nogil:
    # all whitespace characters except newlines
    int iswblank(wchar_t ch ); # wint_t
    int iswspace(wchar_t ch)  # wint_t


cpdef str deindent_block(str s):
    cdef:
        wchar_t *curr       # cursor in buffer, current position
        wchar_t *start      # start - to be calculated by determining where the first line begins.
        wchar_t *end        # end -
        wchar_t *out_buf    #
        wchar_t *out_curr   #
        Py_ssize_t min_prefix = INT_MAX
        Py_ssize_t curr_line_prefix = 0
        wchar_t *line_start
        str out_str

    s = s.rstrip()          # skip trailing whitespace
    curr = s
    end = curr + len(s)

    # determine start of first non-empty line
    start = curr
    while curr != end:
        if not iswblank(curr[0]):
            if curr[0] == '\n':
                start = curr + 1
            else:
                break
        curr += 1
    # => start points to start of first non-empty line
    #raise RuntimeError(f"'{curr[0]}' at {curr - <wchar_t *>s} => start: {start - <wchar_t *>s}")

    #raise RuntimeError("Allocating memory")
    out_buf = <wchar_t *>PyMem_Malloc((end - start) * sizeof(wchar_t))
    if not out_buf:
        raise MemoryError("failed to get memory")

    # Calculate the minimum level of prefixing we can expect to skip
    curr = start  # reset - start at first line with contents
    while curr != end:
        line_start = curr

        # phase 1 - determine prefix
        # --------------------------
        while curr != end and iswblank(curr[0]):
            curr += 1
        if curr == end:
            break  # exit loop entirely (TODO: sanity-check)

        # update min_prefix iff. line is less indented than any before
        curr_line_prefix = curr - line_start
        if curr_line_prefix < min_prefix:
            min_prefix = curr_line_prefix

        # phase 2 - skip to end of line.
        # ------------------------------
        while curr != end and curr[0] != '\n':
            curr += 1
        if curr == end:
            break  # exit loop entirely (TODO: sanity-check)
        curr += 1  # skip the newline

    #raise RuntimeError("Copying to new buffer")
    # => min_prefix is now set to the minimum prefix needed

    # write out to new buffer
    # (scan \n - to \n, copying over as needed)
    curr = start  # reset
    out_curr = out_buf
    #raise RuntimeError(f"min_prefix={min_prefix}")
    while curr != end:
        # phase 1 - skip min_prefix characters
        curr += min_prefix
        # TODO: should be impossible to exceed buffer length, right?
        #       (rstrip => no trailing whitespace lines, min_prefix being MINIMUM)
        line_start = curr
        while curr != end and curr[0] != '\n':
            curr += 1
        #raise RuntimeError(f"memcpy(out_curr, line_start, {curr - line_start} / {(curr - line_start) * sizeof(wchar_t)})")

        # include newline in output
        if curr[0] == '\n':
            curr += 1

        # copy dedented line to output buffer
        memcpy(out_curr, line_start, (curr - line_start) * sizeof(wchar_t)) # TODO: update _new_buff
        out_curr += curr - line_start

        if curr == end:
            break

    out_str = out_buf[: out_curr - out_buf]
    PyMem_Free(out_buf)
    return out_str
