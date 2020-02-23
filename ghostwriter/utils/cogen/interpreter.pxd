# cython: language_level=3

from ghostwriter.utils.iwriter cimport IWriter
from ghostwriter.utils.cogen.parser cimport (
    Program, Block, If, Line, Literal, Expr, Node
)


cdef class Writer(IWriter):
    cdef:
        IWriter _writer
        list _prefixes
        str _curr_prefix

    cpdef void indent(self, str prefix)
    cpdef void dedent(self)
    cpdef void write(self, str contents)
    cpdef void write_prefix(self)
    cpdef void newline(self)


cdef class InterpreterError(Exception):
    pass


cdef class RenderArgTypeError(InterpreterError):
    cdef public str expr
    cdef public str typ


cdef class UnknownNodeType(InterpreterError):
    cdef public Node node


cdef class UnknownBlockType(InterpreterError):
    cdef public Block block


cpdef void interpret(Program program, Writer w, dict blocks, dict scope) except *
