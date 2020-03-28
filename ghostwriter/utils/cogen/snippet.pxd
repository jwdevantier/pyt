# cython: language_level=3

cdef class SnippetEvalException(Exception):
    cdef str _error
    cdef str _error_details

    cpdef public str error_details(self)
    cpdef str error(self)
