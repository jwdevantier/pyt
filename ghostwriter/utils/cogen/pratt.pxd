# cython: language_level=3


cdef class Node:
    pass

ctypedef object nud_fn
ctypedef object led_fn
ctypedef object TOKEN
ctypedef object NODE

cdef class UnexpectedTokenError(Exception):
    cdef:
        str token_type

cdef class Definition:
    cdef:
        str token_type
        size_t lbp
        nud_fn nud_fn
        led_fn led_fn

        NODE nud(self, TOKEN token, Parser parser)
        NODE led(self, TOKEN token, Parser parser, NODE left)

cdef class Grammar:
    cdef:
        dict definitions
        size_t rbp(self, TOKEN token)
        NODE parse_nud(self, TOKEN first, Parser parser)
        NODE parse_led(self, TOKEN first, Parser parser, NODE left)

cdef class Parser:
    cdef:
        Grammar grammar
        object tokenizer
        TOKEN curr_token
        dict definitions

    cdef TOKEN advance(self, str typ)
    cpdef NODE parse(self, size_t rbp=?)
