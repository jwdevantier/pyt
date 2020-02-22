# cython: language_level=3
import typing as t
from ghostwriter.utils.cogen.tokenizer cimport (
    TokenType, Token, Tokenizer, Location)


cdef class Node:
    pass


cdef class Literal(Node):
    cpdef public str value


cdef class Expr(Node):
    cpdef public str value


cdef class Line(Node):
    cpdef public str prefix
    cpdef public list children  # type: t.List[t.Union[Literal,Expr]]


cdef class Block(Node):
    cpdef public str block_prefix
    cpdef public str keyword
    cpdef public str args
    cpdef public list children  # type: t.List[Line, Block]


cdef class NodeFactory:
    pass


cdef class If(Node):
    cpdef public list conds  # type: t.List[Block]


cdef class Program(Node):
    cpdef public list lines  # type: t.List[Node]


cdef class ParserError(Exception):
    cpdef public str error
    cpdef public Location location


cdef class UnhandledTokenError(ParserError):
    cpdef public Token token
    cpdef public str state


cdef class ExpectedTokenTypeError(ParserError):
    cpdef public Token token
    cpdef public TokenType expected_type


cdef class ExpectedTokenError(ParserError):
    cpdef public Token token
    cpdef public Token expected


cdef class IndentationError(ParserError):
    cpdef public str block_indentation
    cpdef public str line_indentation


cdef class InvalidBlockNestingError(ParserError):
    cpdef public str expected
    cpdef public str actual


cdef class CogenParser:
    # fields
    cdef:
        Tokenizer tokenizer
        Token curr_token
        list prefix_blocks  # type: t.List[str]
        str prefix_block_head
        str prefix_line

    # internal methods
    cdef:
        Token peek(self)
        Token advance(self)

        Line _parse_line(self)
        If _parse_if_block(self)
        Block _parse_block(self)

    # API
    cpdef Program parse_program(self)
