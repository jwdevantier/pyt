cdef class Token:
    pass

cdef class CtrlToken(Token):
    cpdef public str prefix
    cpdef public str keyword
    cpdef public str args

cdef class ExprToken(Token):
    cpdef public str expr

cdef class TextToken(Token):
    cpdef public str text

cdef class NewlineToken(Token):
    pass