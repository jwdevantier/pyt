# cython: language_level=3
from typing import List

cdef class EvalError(Exception):
    cpdef str error_message(self)
    cpdef str error_details(self)


cdef class WrappedException(EvalError):
    cdef public list stacktrace_lines  # type: List[str]
    cdef str _error
