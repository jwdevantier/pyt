
cdef class IWriter:
    cpdef void write(self, str contents) except *:
        pass