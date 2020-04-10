# cython: language_level=3
from typing import List


cdef class Error(Exception):
    cpdef str error_message(self)
    cpdef str error_details(self)


cpdef str error_details(e, str indentation = ?)
cpdef str error_message(e)


cdef class FrameInfo:
    # name of file containing code (or "<string>")
    cpdef public str filename
    # line number
    cpdef public int lineno
    # name of function/method/module
    cpdef public str name
    # actual code fragment
    cpdef public str line


cdef class ExceptionInfo:
    cpdef public Exception exc
    cpdef public list stacktrace

    cdef str _error_message

    cpdef str error_message(self)
    cpdef str error_details(self)


cpdef ExceptionInfo catch_exception_info()


cdef class WrappedException(Error):
    cpdef public ExceptionInfo ei
