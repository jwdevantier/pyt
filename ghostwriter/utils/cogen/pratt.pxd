# cython: language_level=3
from ghostwriter.utils.cogen.tokenizer cimport TokenType

ctypedef Py_ssize_t (*token_type_fn)(void *o)

cdef class Node:
    pass

ctypedef object nud_fn
ctypedef object led_fn
ctypedef object TOKEN
ctypedef object NODE

cdef class UnexpectedTokenError(Exception):
    cdef:
        Py_ssize_t token_type

cdef class Definition:
    cdef:
        TokenType token_type
        size_t lbp
        nud_fn nud_fn
        led_fn led_fn

        NODE nud(self, TOKEN token, Parser parser)
        NODE led(self, TOKEN token, Parser parser, NODE left)

cdef class Grammar:
    cdef:
        dict definitions
        cdef Definition get_definition(self, Py_ssize_t token_type)

cdef class Parser:
    cdef:
        Grammar grammar
        object tokenizer
        TOKEN curr_token
        dict definitions
        token_type_fn token_type

    @staticmethod
    cdef Parser new(Grammar grammar, object tokenizer, token_type_fn token_type)

    cdef TOKEN advance(self, TokenType typ)
    cpdef NODE parse(self, size_t rbp=?)

    cdef:
        size_t _rbp(self, TOKEN token)
        NODE _parse_nud(self, TOKEN token)
        NODE _parse_led(self, TOKEN token, NODE left)
