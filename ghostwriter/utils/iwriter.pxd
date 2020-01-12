# cython: language_level=3

cdef class IWriter:
    cpdef void write(self, str contents) except *