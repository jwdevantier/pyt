# cython: language_level=3
from ghostwriter.utils.cogen.tokenizer cimport (
    TokenType, Token, Tokenizer, Location)


cdef class Node:
    pass


cdef class ParserError(Exception):
    cpdef public str error
    cpdef public Location location

cdef class UnexpectedTokenError(ParserError):
    cpdef public Token token

cdef class InvalidBlockNestingError(ParserError):
    cpdef public str expected
    cpdef public str actual


cdef class InvalidEndBlockArgsError(ParserError):
    cpdef public str end_kw


cdef class Program(Node):
    cpdef public list lines


cdef class Block(Node):
    cpdef public CLine header
    cpdef public list lines


cdef class If(Node):
    # list of IfCond'es, else desugars info if/elif True
    cpdef public list conds


cdef class Literal(Node):
    cpdef public str value


cdef class Expr(Node):
    cpdef public str value


cdef class Line(Node):
    cpdef public list contents


cdef class CLine(Node):
    cpdef public str keyword
    cpdef public str args


cdef class Component(Node):
    cpdef public str identifier
    cpdef public str args
    cpdef public list lines


cdef class CogenParser:
    # fields
    cdef:
        Tokenizer tokenizer
        Token curr_token

    # internal methods
    cdef:
        Token peek(self)
        Token advance(self)

        CLine _parse_cline(self)
        Line _parse_line(self)

        Node _parse_block_node(self, CLine header)
        Block _parse_block(self, CLine header)
        If _parse_if_block(self, CLine header)

    # API
    cpdef Program parse_program(self)
